#include "skinart.h"

#include <dwrite_3.h>
#include <process.h>

namespace rt {

SkinArt& skinArt() {
  static SkinArt a;
  return a;
}

SkinArt::~SkinArt() {
  if (!inited_) return;
  EnterCriticalSection(&cs_);
  quit_ = true;
  queue_.clear();
  LeaveCriticalSection(&cs_);
  for (auto t : threads_) {
    ReleaseSemaphore(wake_, 1, nullptr);
    (void)t;
  }
  bool gone = true;
  for (auto t : threads_) {
    gone &= WaitForSingleObject(t, 3000) == WAIT_OBJECT_0;
    CloseHandle(t);
  }
  if (!gone) return;  // still busy with a file: the process is ending anyway, let it keep its lock
  CloseHandle(wake_);
  CloseHandle(idle_);
  DeleteCriticalSection(&cs_);
  if (cursor_) DestroyCursor(cursor_);
}

void SkinArt::startThreads() {
  if (!inited_) {
    inited_ = true;
    InitializeCriticalSection(&cs_);
    wake_ = CreateSemaphoreW(nullptr, 0, 1 << 20, nullptr);
    idle_ = CreateEventW(nullptr, TRUE, TRUE, nullptr);
  }
  if (!threads_.empty()) return;
  SYSTEM_INFO si;
  GetSystemInfo(&si);
  int n = clampi((int)si.dwNumberOfProcessors / 2, 1, 3);
  for (int i = 0; i < n; i++)
    if (HANDLE t = (HANDLE)_beginthreadex(nullptr, 0, threadMain, this, 0, nullptr)) threads_.push_back(t);
}

// ---------------------------------------------------------------- colour tuning
namespace {
// Rotates hue around the grey axis and scales saturation and brightness; keeps greys grey.
struct TuneMatrix {
  float m[9];
  explicit TuneMatrix(const Config::Tune& t) {
    float c = cosf(t.hue * kPi / 180.f) * t.sat, s = sinf(t.hue * kPi / 180.f) * t.sat;
    const float lr = 0.2126f, lg = 0.7152f, lb = 0.0722f;
    float k[9] = {lr + c * (1 - lr) + s * -lr, lg + c * -lg + s * -lg, lb + c * -lb + s * (1 - lb),
                  lr + c * -lr + s * 0.143f, lg + c * (1 - lg) + s * 0.140f, lb + c * -lb + s * -0.283f,
                  lr + c * -lr + s * -(1 - lr), lg + c * -lg + s * lg, lb + c * (1 - lb) + s * lb};
    for (int i = 0; i < 9; i++) m[i] = k[i] * t.light;
  }
  void run(float& r, float& g, float& b) const {
    float x = m[0] * r + m[1] * g + m[2] * b, y = m[3] * r + m[4] * g + m[5] * b, z = m[6] * r + m[7] * g + m[8] * b;
    r = x;
    g = y;
    b = z;
  }
};
}  // namespace

Color SkinArt::tuneColor(Color c, const Config::Tune& t) {
  if (t.plain()) return c;
  TuneMatrix(t).run(c.r, c.g, c.b);
  return {saturate(c.r), saturate(c.g), saturate(c.b), c.a};
}

// ---------------------------------------------------------------- making a picture
namespace {

struct Raw {
  int w = 0, h = 0;
  std::vector<uint8_t> px;  // straight BGRA
};

constexpr int kMaxSide = 4096, kMaxDraw = 2400;
constexpr size_t kMaxBytes = 320u << 20;
constexpr size_t kMaxWaiting = 160u << 20;  // finished, but not fetched yet

bool decode(IWICImagingFactory* wic, const std::string& bytes, Raw& out, REFWICPixelFormatGUID fmt, int bpp) {
  if (bytes.empty() || bytes.size() > 24u << 20) return false;
  ComPtr<IWICStream> st;
  ComPtr<IWICBitmapDecoder> dec;
  ComPtr<IWICBitmapFrameDecode> fr;
  ComPtr<IWICFormatConverter> cv;
  UINT w = 0, h = 0;
  if (FAILED(wic->CreateStream(&st)) || FAILED(st->InitializeFromMemory((BYTE*)bytes.data(), (DWORD)bytes.size())) ||
      FAILED(wic->CreateDecoderFromStream(st.Get(), nullptr, WICDecodeMetadataCacheOnDemand, &dec)) || FAILED(dec->GetFrame(0, &fr)) || FAILED(fr->GetSize(&w, &h)) ||
      !w || !h || w > (UINT)kMaxSide || h > (UINT)kMaxSide || FAILED(wic->CreateFormatConverter(&cv)) ||
      FAILED(cv->Initialize(fr.Get(), fmt, WICBitmapDitherTypeNone, nullptr, 0, WICBitmapPaletteTypeCustom)))
    return false;
  out.w = (int)w;
  out.h = (int)h;
  UINT stride = w * (UINT)bpp;
  out.px.resize((size_t)stride * h);
  return SUCCEEDED(cv->CopyPixels(nullptr, stride, (UINT)out.px.size(), out.px.data()));
}

bool resize(IWICImagingFactory* wic, const std::vector<uint8_t>& src, int w, int h, std::vector<uint8_t>& dst, int dw, int dh, REFWICPixelFormatGUID fmt, int bpp) {
  ComPtr<IWICBitmap> bm;
  ComPtr<IWICBitmapScaler> sc;
  if (FAILED(wic->CreateBitmapFromMemory((UINT)w, (UINT)h, fmt, (UINT)(w * bpp), (UINT)src.size(), (BYTE*)src.data(), &bm)) || FAILED(wic->CreateBitmapScaler(&sc))) return false;
  if (FAILED(sc->Initialize(bm.Get(), (UINT)dw, (UINT)dh, (WICBitmapInterpolationMode)4 /* high quality cubic */)) &&
      FAILED(sc->Initialize(bm.Get(), (UINT)dw, (UINT)dh, WICBitmapInterpolationModeFant)))
    return false;
  dst.resize((size_t)dw * dh * bpp);
  return SUCCEEDED(sc->CopyPixels(nullptr, (UINT)(dw * bpp), (UINT)dst.size(), dst.data()));
}

struct CacheHead {
  char magic[4];
  uint32_t version;
  uint64_t key;
  int32_t w, h, cw, ch;
};
constexpr uint32_t kCacheVersion = 4;

std::wstring skinCacheDir() { return joinPath(cacheDir(), L"skins"); }

uint64_t fnv(uint64_t h, const void* p, size_t n) {
  auto* b = (const uint8_t*)p;
  for (size_t i = 0; i < n; i++) h = (h ^ b[i]) * 0x100000001b3ull;
  return h;
}

}  // namespace

bool SkinArt::make(IWICImagingFactory* wic, const Job& j, Done& out) {
  const SkinImage& im = j.skin->images[(size_t)j.image];
  uint64_t key = 0xcbf29ce484222325ull;
  key = fnv(key, j.skin->id.data(), j.skin->id.size());
  key = fnv(key, &j.skin->stamp, 8);
  key = fnv(key, im.file.data(), im.file.size());
  key = fnv(key, im.mask.data(), im.mask.size());
  int flags[6] = {im.cols, im.rows, im.light, im.keep, im.sharp, j.wide};
  key = fnv(key, flags, sizeof flags);
  Config::Tune tune = im.keep ? Config::Tune{} : j.tune;
  float tn[3] = {tune.hue, tune.sat, tune.light};
  key = fnv(key, tn, sizeof tn);
  wchar_t name[40];
  swprintf(name, 40, L"%016llx.px", (unsigned long long)key);
  std::wstring file = joinPath(skinCacheDir(), name);

  if (j.persist) {
    HANDLE f = CreateFileW(file.c_str(), GENERIC_READ | FILE_WRITE_ATTRIBUTES, FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_FLAG_SEQUENTIAL_SCAN, nullptr);
    if (f != INVALID_HANDLE_VALUE) {
      CacheHead hd{};
      DWORD got = 0;
      LARGE_INTEGER size{};
      bool ok = ReadFile(f, &hd, sizeof hd, &got, nullptr) && got == sizeof hd && !memcmp(hd.magic, "RTPX", 4) && hd.version == kCacheVersion && hd.key == key && hd.w > 0 && hd.h > 0 &&
                hd.w <= kMaxSide * 2 && hd.h <= kMaxSide * 2 && hd.cw > 0 && hd.ch > 0 && GetFileSizeEx(f, &size) && size.QuadPart == (LONGLONG)(sizeof hd + (size_t)hd.w * hd.h * 4);
      if (ok) {
        out.w = hd.w;
        out.h = hd.h;
        out.cw = hd.cw;
        out.ch = hd.ch;
        out.px.resize((size_t)hd.w * hd.h * 4);
        ok = ReadFile(f, out.px.data(), (DWORD)out.px.size(), &got, nullptr) && got == out.px.size();
      }
      if (ok) {  // in use: spare it from the next clean-up
        FILETIME now;
        GetSystemTimeAsFileTime(&now);
        SetFileTime(f, nullptr, nullptr, &now);
      }
      CloseHandle(f);
      if (ok) return true;
    }
  }

  std::string bytes;
  Raw img, mask;
  if (!j.files->read(im.file, bytes) || !decode(wic, bytes, img, GUID_WICPixelFormat32bppBGRA, 4)) {
    logf("skin: cannot read the picture %s", im.file.c_str());
    return false;
  }
  if (!im.mask.empty() && j.files->read(im.mask, bytes) && decode(wic, bytes, mask, GUID_WICPixelFormat8bppGray, 1)) {
    if (mask.w != img.w || mask.h != img.h) {
      std::vector<uint8_t> r;
      if (resize(wic, mask.px, mask.w, mask.h, r, img.w, img.h, GUID_WICPixelFormat8bppGray, 1)) mask.px.swap(r);
      else mask.px.clear();
    }
    if (mask.px.size() == (size_t)img.w * img.h)
      for (size_t i = 0; i < mask.px.size(); i++) img.px[i * 4 + 3] = (uint8_t)((img.px[i * 4 + 3] * mask.px[i] + 127) / 255);
  }
  if (!tune.plain()) {
    TuneMatrix m(tune);
    for (size_t i = 0; i + 3 < img.px.size(); i += 4) {
      if (!img.px[i + 3]) continue;
      float b = img.px[i], g = img.px[i + 1], r = img.px[i + 2];
      m.run(r, g, b);
      img.px[i] = (uint8_t)clampf(b + 0.5f, 0, 255);
      img.px[i + 1] = (uint8_t)clampf(g + 0.5f, 0, 255);
      img.px[i + 2] = (uint8_t)clampf(r + 0.5f, 0, 255);
    }
  }
  // premultiplied; light carries no coverage of its own, so it adds to whatever is behind
  for (size_t i = 0; i + 3 < img.px.size(); i += 4) {
    unsigned a = img.px[i + 3];
    for (int k = 0; k < 3; k++) img.px[i + (size_t)k] = (uint8_t)((img.px[i + (size_t)k] * a + 127) / 255);
  }
  int cw = img.w / im.cols, ch = img.h / im.rows;
  if (cw < 1 || ch < 1) return false;
  int tw = std::min(j.wide, cw);
  if (!im.sharp && (cw > kMaxDraw || ch > kMaxDraw)) tw = std::min(tw, (int)((double)kMaxDraw * cw / std::max(cw, ch)));
  if (im.sharp || tw >= cw) {
    out.cw = cw;
    out.ch = ch;
    out.w = img.w;
    out.h = img.h;
    out.px = std::move(img.px);
  } else {
    int th = std::max(1, (int)lroundf((float)ch * tw / cw));
    bool sheet = im.cols * im.rows > 1;
    out.cw = tw;
    out.ch = th;
    out.w = tw * im.cols;
    out.h = th * im.rows;
    if (!sheet) {
      if (!resize(wic, img.px, img.w, img.h, out.px, tw, th, GUID_WICPixelFormat32bppPBGRA, 4)) return false;
    } else {  // frame by frame, so neighbours do not bleed into each other
      out.px.assign((size_t)out.w * out.h * 4, 0);
      std::vector<uint8_t> one((size_t)cw * ch * 4), small;
      for (int r = 0; r < im.rows; r++)
        for (int c = 0; c < im.cols; c++) {
          for (int y = 0; y < ch; y++) memcpy(&one[(size_t)y * cw * 4], &img.px[((size_t)(r * ch + y) * img.w + c * cw) * 4], (size_t)cw * 4);
          if (!resize(wic, one, cw, ch, small, tw, th, GUID_WICPixelFormat32bppPBGRA, 4)) return false;
          for (int y = 0; y < th; y++) memcpy(&out.px[((size_t)(r * th + y) * out.w + c * tw) * 4], &small[(size_t)y * tw * 4], (size_t)tw * 4);
        }
    }
  }
  if (im.light)
    for (size_t i = 3; i < out.px.size(); i += 4) out.px[i] = 0;

  if (j.persist) {
    SHCreateDirectoryExW(nullptr, skinCacheDir().c_str(), nullptr);
    std::wstring tmp = file + L"." + widen(newId()).substr(0, 6);
    HANDLE f = CreateFileW(tmp.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_FLAG_SEQUENTIAL_SCAN, nullptr);
    if (f != INVALID_HANDLE_VALUE) {
      CacheHead hd{{'R', 'T', 'P', 'X'}, kCacheVersion, key, out.w, out.h, out.cw, out.ch};
      DWORD n = 0, n2 = 0;
      bool ok = WriteFile(f, &hd, sizeof hd, &n, nullptr) && WriteFile(f, out.px.data(), (DWORD)out.px.size(), &n2, nullptr) && n2 == out.px.size();
      CloseHandle(f);
      if (!ok || !MoveFileExW(tmp.c_str(), file.c_str(), MOVEFILE_REPLACE_EXISTING)) DeleteFileW(tmp.c_str());
    }
  }
  return true;
}

void sweepSkinCache(bool all) {
  struct F {
    std::wstring path;
    uint64_t time, size;
  };
  std::vector<F> v;
  std::wstring dir = skinCacheDir();
  WIN32_FIND_DATAW d;
  HANDLE h = FindFirstFileW(joinPath(dir, L"*.px*").c_str(), &d);
  if (h == INVALID_HANDLE_VALUE) return;
  uint64_t total = 0;
  do {
    uint64_t t = (uint64_t)d.ftLastWriteTime.dwHighDateTime << 32 | d.ftLastWriteTime.dwLowDateTime;
    v.push_back({joinPath(dir, d.cFileName), t, (uint64_t)d.nFileSizeHigh << 32 | d.nFileSizeLow});
    total += v.back().size;
  } while (FindNextFileW(h, &d));
  FindClose(h);
  FILETIME ft;
  GetSystemTimeAsFileTime(&ft);
  uint64_t now = (uint64_t)ft.dwHighDateTime << 32 | ft.dwLowDateTime, day = 864000000000ull;
  std::sort(v.begin(), v.end(), [](const F& a, const F& b) { return a.time < b.time; });
  for (auto& f : v)
    if (all || now - std::min(now, f.time) > 14 * day || total > 120ull << 20)
      if (DeleteFileW(f.path.c_str())) total -= f.size;
  if (all) RemoveDirectoryW(dir.c_str());
}

// ---------------------------------------------------------------- worker
unsigned __stdcall SkinArt::threadMain(void* self) {
  CoInitializeEx(nullptr, COINIT_MULTITHREADED);
  ((SkinArt*)self)->run();
  CoUninitialize();
  return 0;
}

void SkinArt::run() {
  ComPtr<IWICImagingFactory> wic;
  for (;;) {
    WaitForSingleObject(wake_, INFINITE);
    Job j;
    EnterCriticalSection(&cs_);
    bool quit = quit_, have = !queue_.empty();
    if (have) {
      j = std::move(queue_.front());
      queue_.erase(queue_.begin());
    }
    LeaveCriticalSection(&cs_);
    if (quit) return;
    if (!have) continue;
    if (!wic) CoCreateInstance(CLSID_WICImagingFactory, nullptr, CLSCTX_INPROC_SERVER, __uuidof(IWICImagingFactory), (void**)wic.GetAddressOf());
    Done d;
    d.image = j.image;
    d.wide = j.wide;
    d.round = j.round;
    if (wic && !make(wic.Get(), j, d)) d.px.clear();
    EnterCriticalSection(&cs_);
    // Asked for only to have it on disk, or nobody is fetching at the moment: it can be asked for again.
    if (j.quiet || waiting_ + d.px.size() > kMaxWaiting) {
      d.dropped = true;
      std::vector<uint8_t>().swap(d.px);
    }
    waiting_ += d.px.size();
    done_.push_back(std::move(d));
    if (--inFlight_ == 0) SetEvent(idle_);
    LeaveCriticalSection(&cs_);
  }
}

// What nobody needs any more: on its way to be made, or made and not fetched.
void SkinArt::forget() {
  if (!inited_) return;
  EnterCriticalSection(&cs_);
  inFlight_ -= (int)queue_.size();
  queue_.clear();
  done_.clear();
  waiting_ = 0;
  if (inFlight_ == 0) SetEvent(idle_);
  LeaveCriticalSection(&cs_);
  for (auto& p : pics_) {
    auto& v = p.second;
    v.erase(std::remove_if(v.begin(), v.end(), [](const Sized& s) { return s.asked && !s.bmp; }), v.end());
  }
}

// ---------------------------------------------------------------- use
void SkinArt::use(std::shared_ptr<const Skin> t, const Config::Tune& tune, bool persist) {
  bool same = skin_ == t && (files_ || !skin_) && tune_.hue == tune.hue && tune_.sat == tune.sat && tune_.light == tune.light;
  persist_ = persist;
  if (same) return;
  bool sameSkin = skin_ == t && files_;
  skin_ = std::move(t);
  tune_ = tune;
  round_++;
  pics_.clear();
  bytes_ = 0;
  if (inited_) {
    EnterCriticalSection(&cs_);
    inFlight_ -= (int)queue_.size();
    queue_.clear();
    if (inFlight_ == 0) SetEvent(idle_);
    LeaveCriticalSection(&cs_);
  }
  if (sameSkin) return;
  files_ = skin_ ? SkinFiles::open(skin_->path) : nullptr;
  sounds_.clear();
  if (cursor_) DestroyCursor(cursor_);
  cursor_ = nullptr;
  cursorTried_ = false;
  dropFonts();
  if (skin_) loadFonts();
}

void SkinArt::drain() {
  std::vector<Done> got;
  EnterCriticalSection(&cs_);
  got.swap(done_);
  waiting_ = 0;
  LeaveCriticalSection(&cs_);
  for (auto& d : got) {
    if (d.round != round_) continue;
    if (d.dropped) {
      auto& v = pics_[d.image];
      v.erase(std::remove_if(v.begin(), v.end(), [&](const Sized& s) { return s.wide == d.wide && s.asked && !s.bmp; }), v.end());
      continue;
    }
    for (auto& s : pics_[d.image]) {
      if (s.wide != d.wide) continue;
      s.asked = false;
      if (d.px.empty()) {
        s.bad = true;
        continue;
      }
      if (bytes_ + d.px.size() > kMaxBytes) {
        s.bad = true;
        continue;
      }
      bytes_ += d.px.size();
      s.cw = d.cw;
      s.ch = d.ch;
      s.bmp = gfx().bitmap(d.px.data(), d.w, d.h, d.w * 4);
      s.bad = !s.bmp;
      s.fade = clock_ - s.born < 0.05f ? 1.f : 0.f;
      if (s.fade < 1) fading_ = true;
    }
  }
}

bool SkinArt::get(int image, float wide, Pic& out, bool moving, bool keep) {
  if (!skin_ || image < 0 || image >= (int)skin_->images.size() || !gfx().ready() || !files_) return false;
  if (gen_ != gfx().generation) {
    pics_.clear();
    bytes_ = 0;
    gen_ = gfx().generation;
    round_++;
  }
  const SkinImage& im = skin_->images[(size_t)image];
  int w = clampi((int)ceilf(wide), 2, kMaxSide);
  if (!persist_) w = std::min(kMaxSide, (w + 11) / 12 * 12);  // sizes change constantly while somebody drags a slider
  if (im.sharp) w = 1;
  startThreads();
  drain();
  auto& list = pics_[image];
  Sized* hit = nullptr;
  for (auto& s : list)
    if (s.wide == w) hit = &s;
  if (!hit) {
    // a size that is nearly the same will do
    for (auto& s : list)
      if (s.bmp && !s.bad && s.wide >= w && s.wide <= w + std::max(2, w / 50)) hit = &s;
  }
  if (!hit && moving) {
    for (auto& s : list)
      if (s.bmp && !s.bad && s.wide * 10 >= w * 9 && s.wide <= w * 2 && (!hit || s.wide < hit->wide)) hit = &s;
    if (!hit) {  // the next step of a ladder, so that only a few are ever made
      w = std::min(kMaxSide, (int)ceil(16.0 * pow(1.5, ceil(log(std::max(1.0, w / 16.0)) / log(1.5)))));
      for (auto& s : list)
        if (s.wide == w) hit = &s;
    }
  }
  if (!hit) {
    if (list.size() > 7) {  // sizes nobody asks for any more
      auto old = std::min_element(list.begin(), list.end(), [](const Sized& a, const Sized& b) { return a.used < b.used; });
      if (!old->asked) {
        if (old->bmp) {
          D2D1_SIZE_U z = old->bmp->GetPixelSize();
          bytes_ -= std::min(bytes_, (size_t)z.width * z.height * 4);
        }
        list.erase(old);
      }
    }
    Sized s;
    s.wide = w;
    s.asked = true;
    s.born = clock_;
    list.push_back(std::move(s));
    hit = &list.back();
    Job j;
    j.skin = skin_;
    j.files = files_;
    j.tune = tune_;
    j.image = image;
    j.wide = w;
    j.round = round_;
    j.persist = persist_ && keep;
    j.quiet = quiet_;
    EnterCriticalSection(&cs_);
    queue_.push_back(std::move(j));
    inFlight_++;
    ResetEvent(idle_);
    LeaveCriticalSection(&cs_);
    ReleaseSemaphore(wake_, 1, nullptr);
  }
  hit->used = tickNo_;
  const Sized* show = hit;
  if (!hit->bmp) {  // meanwhile any other size of the same picture
    for (auto& s : list)
      if (s.bmp && (!show->bmp || abs(s.wide - w) < abs(show->wide - w))) show = &s;
    if (!show->bmp) return false;
  }
  out.bmp = show->bmp.Get();
  out.fade = show->fade;
  out.cols = im.cols;
  out.rows = im.rows;
  out.frames = im.frames;
  out.cw = (float)show->cw;
  out.ch = (float)show->ch;
  out.sharp = im.sharp;
  out.light = im.light;
  return true;
}

void SkinArt::wait(DWORD ms) {
  if (!inited_) return;
  WaitForSingleObject(idle_, ms);
}

void SkinArt::tick(float dt) {
  clock_ += dt;
  tickNo_++;
  if (!fading_) return;
  fading_ = false;
  for (auto& p : pics_)
    for (auto& s : p.second)
      if (s.bmp && s.fade < 1.f) {
        s.fade = std::min(1.f, s.fade + dt * 7.f);
        fading_ |= s.fade < 1.f;
      }
}

void SkinArt::dropDevice() {
  pics_.clear();
  bytes_ = 0;
  round_++;
  if (!inited_) return;
  EnterCriticalSection(&cs_);
  inFlight_ -= (int)queue_.size();
  queue_.clear();
  done_.clear();
  waiting_ = 0;
  if (inFlight_ == 0) SetEvent(idle_);
  LeaveCriticalSection(&cs_);
}

void SkinArt::rest() {
  forget();
  if (files_) files_->letGo();
}

// ---------------------------------------------------------------- fonts, sounds, cursor
void SkinArt::loadFonts() {
  fonts_.clear();
  for (auto& f : skin_->fonts) {
    std::wstring fam;
    if (!f.file.empty()) {
      std::string bytes;
      std::wstring alias = L"skin:" + widen(skin_->id) + L":" + widen(f.name);
      if (files_ && files_->read(f.file, bytes) && gfx().addFont(alias, bytes)) fam = alias;
    }
    if (fam.empty())
      for (auto& c : f.families)
        if (gfx().hasFont(c)) {
          fam = c;
          break;
        }
    if (fam.empty()) fam = L"Segoe UI";
    fonts_.push_back({fam, f.weight});
  }
}
void SkinArt::dropFonts() {
  for (auto& f : fonts_)
    if (f.first.rfind(L"skin:", 0) == 0) gfx().removeFont(f.first);
  fonts_.clear();
}
std::wstring SkinArt::fontFamily(int font, int* weight) const {
  if (font < 0 || font >= (int)fonts_.size()) return {};
  if (weight) *weight = fonts_[(size_t)font].second;
  return fonts_[(size_t)font].first;
}
std::wstring SkinArt::fontByName(const std::string& name) const {
  if (skin_)
    for (size_t i = 0; i < skin_->fonts.size() && i < fonts_.size(); i++)
      if (skin_->fonts[i].name == name) return fonts_[i].first;
  return {};
}

// Windows trusts what the header of a sound says about its length. This keeps plain 8 or 16 bit sound and writes the
// header anew; anything else comes out empty.
static std::string cleanWav(const std::string& b) {
  auto u16 = [&](size_t at) { return (uint32_t)(uint8_t)b[at] | (uint32_t)(uint8_t)b[at + 1] << 8; };
  auto u32 = [&](size_t at) { return u16(at) | u16(at + 2) << 16; };
  if (b.size() < 44 || b.size() > 1u << 20 || b.compare(0, 4, "RIFF") || b.compare(8, 4, "WAVE")) return {};
  size_t end = (size_t)std::min<uint64_t>(b.size(), (uint64_t)u32(4) + 8), at = 12, fmt = 0;
  while (at + 8 <= end) {
    size_t n = u32(at + 4), body = at + 8;
    if (n > end - body) return {};
    if (!b.compare(at, 4, "fmt ") && n >= 16) {
      uint32_t tag = u16(body), ch = u16(body + 2), rate = u32(body + 4), bits = u16(body + 14);
      if (tag != 1 || ch < 1 || ch > 2 || rate < 4000 || rate > 192000 || (bits != 8 && bits != 16) || u16(body + 12) != ch * bits / 8) return {};
      fmt = body;
    } else if (!b.compare(at, 4, "data") && fmt) {
      uint32_t align = u16(fmt + 12), size = (uint32_t)(n / align * align), rate = u32(fmt + 4);
      if (!size) return {};
      std::string out = "RIFF";
      auto put = [&](uint32_t v, int bytes) {
        for (int i = 0; i < bytes; i++) out.push_back((char)(v >> (8 * i) & 255));
      };
      put(36 + size, 4);
      out += "WAVEfmt ";
      put(16, 4);
      put(1, 2);
      put(u16(fmt + 2), 2);
      put(rate, 4);
      put(rate * align, 4);
      put(align, 2);
      put(u16(fmt + 14), 2);
      out += "data";
      put(size, 4);
      out.append(b, body, size);
      if (size & 1) out.push_back(0);
      return out;
    }
    at = body + n + (n & 1);
  }
  return {};
}

bool SkinArt::sound(const char* event, std::string& wav) {
  if (!skin_ || !files_) return false;
  auto it = skin_->sounds.find(event);
  if (it == skin_->sounds.end()) return false;
  auto have = sounds_.find(event);
  if (have == sounds_.end()) {
    std::string b;
    b = files_->read(it->second, b, 1u << 20) ? cleanWav(b) : std::string();
    have = sounds_.emplace(event, std::move(b)).first;
  }
  wav = have->second;
  return !wav.empty();
}

HCURSOR SkinArt::cursor(float dpi) {
  if (!skin_ || skin_->cursor.image < 0 || !files_) return nullptr;
  if (cursorTried_ && cursorDpi_ == dpi) return cursor_;
  cursorTried_ = true;
  if (cursor_) DestroyCursor(cursor_);
  cursor_ = nullptr;
  cursorDpi_ = dpi;
  auto& g = gfx();
  if (!g.ensureFactories() || !g.wic) return nullptr;
  Job j;
  j.skin = skin_;
  j.files = files_;
  j.tune = tune_;
  j.image = skin_->cursor.image;
  j.wide = clampi((int)lroundf(skin_->cursor.size * dpi), 8, 256);
  Done d;
  if (!make(g.wic.Get(), j, d) || d.cw > 256 || d.ch > 256) return nullptr;
  BITMAPV5HEADER bi{};
  bi.bV5Size = sizeof bi;
  bi.bV5Width = d.cw;
  bi.bV5Height = -d.ch;
  bi.bV5Planes = 1;
  bi.bV5BitCount = 32;
  bi.bV5Compression = BI_BITFIELDS;
  bi.bV5RedMask = 0x00FF0000;
  bi.bV5GreenMask = 0x0000FF00;
  bi.bV5BlueMask = 0x000000FF;
  bi.bV5AlphaMask = 0xFF000000;
  void* bits = nullptr;
  HDC dc = GetDC(nullptr);
  HBITMAP col = CreateDIBSection(dc, (BITMAPINFO*)&bi, DIB_RGB_COLORS, &bits, nullptr, 0);
  ReleaseDC(nullptr, dc);
  HBITMAP mono = CreateBitmap(d.cw, d.ch, 1, 1, nullptr);
  if (col && mono && bits) {
    for (int y = 0; y < d.ch; y++) memcpy((uint8_t*)bits + (size_t)y * d.cw * 4, &d.px[(size_t)y * d.w * 4], (size_t)d.cw * 4);
    ICONINFO ii{};
    ii.fIcon = FALSE;
    ii.xHotspot = (DWORD)clampi((int)lroundf(skin_->cursor.hot.x * d.cw), 0, d.cw - 1);
    ii.yHotspot = (DWORD)clampi((int)lroundf(skin_->cursor.hot.y * d.ch), 0, d.ch - 1);
    ii.hbmColor = col;
    ii.hbmMask = mono;
    cursor_ = (HCURSOR)CreateIconIndirect(&ii);
  }
  if (col) DeleteObject(col);
  if (mono) DeleteObject(mono);
  return cursor_;
}

}  // namespace rt
