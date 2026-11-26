#include "icons.h"

#include "picture.h"

#include <process.h>
#include <shobjidl.h>

namespace rt {

IconCache& icons() {
  static IconCache c;
  return c;
}

std::wstring IconCache::keyFor(const Pin& pin) {
  if (!pin.icon.empty()) {  // the way it is fitted is part of the key: img, img1, img2, img3
    std::wstring k = L"img";
    if (pin.iconShape != PicShape::Auto) k += std::to_wstring((int)pin.iconShape);
    return k + L"|" + expandEnv(pin.icon);
  }
  switch (pin.kind) {
    case Pin::Kind::App: return L"app|" + pin.target;
    case Pin::Kind::File: return L"file|" + expandEnv(pin.target);
    default: return {};
  }
}

// ---------------------------------------------------------------- decoding
void finishIcon(IconImage& img) {
  // Some providers hand back straight alpha; premultiply only when that is clearly the case.
  bool straight = false, anyAlpha = false;
  for (size_t i = 0; i + 3 < img.px.size(); i += 4) {
    uint8_t a = img.px[i + 3];
    if (a) anyAlpha = true;
    if (img.px[i] > a || img.px[i + 1] > a || img.px[i + 2] > a) { straight = true; }
  }
  if (!anyAlpha) {
    for (size_t i = 0; i + 3 < img.px.size(); i += 4) img.px[i + 3] = 255;
  } else if (straight) {
    for (size_t i = 0; i + 3 < img.px.size(); i += 4) {
      unsigned a = img.px[i + 3];
      for (int k = 0; k < 3; k++) img.px[i + k] = (uint8_t)((img.px[i + k] * a + 127) / 255);
    }
  }
  int x0 = img.w, y0 = img.h, x1 = -1, y1 = -1;
  for (int y = 0; y < img.h; y++)
    for (int x = 0; x < img.w; x++)
      if (img.px[((size_t)y * img.w + x) * 4 + 3] > 14) {
        x0 = std::min(x0, x); x1 = std::max(x1, x);
        y0 = std::min(y0, y); y1 = std::max(y1, y);
      }
  if (x1 < 0) { x0 = y0 = 0; x1 = img.w - 1; y1 = img.h - 1; }
  // Square crop around the visible pixels, kept inside the picture so it is never drawn stretched.
  float side = std::min((float)std::max(x1 - x0 + 1, y1 - y0 + 1) + 1.f, (float)std::min(img.w, img.h));
  float l = clampf((x0 + x1 + 1 - side) * 0.5f, 0.f, img.w - side), t = clampf((y0 + y1 + 1 - side) * 0.5f, 0.f, img.h - side);
  img.crop = D2D1::RectF(l, t, l + side, t + side);
}

static bool fromHBitmap(HBITMAP hb, IconImage& out) {
  BITMAP bm{};
  if (!GetObjectW(hb, sizeof bm, &bm) || bm.bmWidth <= 0 || bm.bmHeight == 0) return false;
  out.w = bm.bmWidth;
  out.h = abs(bm.bmHeight);
  out.px.resize((size_t)out.w * out.h * 4);
  BITMAPINFO bi{};
  bi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
  bi.bmiHeader.biWidth = out.w;
  bi.bmiHeader.biHeight = -out.h;
  bi.bmiHeader.biPlanes = 1;
  bi.bmiHeader.biBitCount = 32;
  HDC dc = GetDC(nullptr);
  int n = GetDIBits(dc, hb, 0, (UINT)out.h, out.px.data(), &bi, DIB_RGB_COLORS);
  ReleaseDC(nullptr, dc);
  if (n <= 0) return false;
  finishIcon(out);
  return true;
}

static bool fromHIcon(HICON hi, int size, IconImage& out) {
  BITMAPINFO bi{};
  bi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
  bi.bmiHeader.biWidth = size;
  bi.bmiHeader.biHeight = -size;
  bi.bmiHeader.biPlanes = 1;
  bi.bmiHeader.biBitCount = 32;
  void* bits = nullptr;
  HDC sdc = GetDC(nullptr), mdc = CreateCompatibleDC(sdc);
  HBITMAP hb = CreateDIBSection(sdc, &bi, DIB_RGB_COLORS, &bits, nullptr, 0);
  bool ok = false;
  if (hb) {
    HGDIOBJ old = SelectObject(mdc, hb);
    ok = DrawIconEx(mdc, 0, 0, hi, size, size, 0, nullptr, DI_NORMAL) != FALSE;
    GdiFlush();
    SelectObject(mdc, old);
    if (ok) ok = fromHBitmap(hb, out);
    DeleteObject(hb);
  }
  DeleteDC(mdc);
  ReleaseDC(nullptr, sdc);
  return ok;
}

static bool fromShellItem(const std::wstring& parsing, int size, IconImage& out) {
  ComPtr<IShellItemImageFactory> f;
  HRESULT hr = SHCreateItemFromParsingName(parsing.c_str(), nullptr, __uuidof(IShellItemImageFactory), (void**)f.GetAddressOf());
  if (FAILED(hr)) {
    logf("icons: no shell item %08lx", hr);
    return false;
  }
  HBITMAP hb = nullptr;
  SIZE sz{size, size};
  hr = f->GetImage(sz, SIIGBF_ICONONLY | SIIGBF_BIGGERSIZEOK, &hb);
  if (FAILED(hr)) logf("icons: GetImage %08lx", hr);
  if (FAILED(hr) || !hb) return false;
  bool ok = fromHBitmap(hb, out);
  DeleteObject(hb);
  if (!ok) return false;
  // Old programs only ship small icons. The shell centres those in a big square and draws a
  // faint frame around them, so judge by the solid pixels and fetch the native size instead.
  int x0 = out.w, y0 = out.h, x1 = -1, y1 = -1;
  for (int y = 0; y < out.h; y++)
    for (int x = 0; x < out.w; x++)
      if (out.px[((size_t)y * out.w + x) * 4 + 3] > 150) {
        x0 = std::min(x0, x); x1 = std::max(x1, x);
        y0 = std::min(y0, y); y1 = std::max(y1, y);
      }
  int solid = std::max(x1 - x0, y1 - y0) + 1;
  if (x1 >= 0 && solid < out.w * 0.46f) {
    IconImage alt;
    SIZE s2{48, 48};
    HBITMAP hb2 = nullptr;
    if (SUCCEEDED(f->GetImage(s2, SIIGBF_ICONONLY, &hb2)) && hb2) {
      if (fromHBitmap(hb2, alt)) out = std::move(alt);
      DeleteObject(hb2);
    }
  }
  return true;
}

bool loadIcon(const std::wstring& key, int size, IconImage& out) {
  size_t bar = key.find(L'|');
  if (bar == std::wstring::npos) return false;
  std::wstring kind = key.substr(0, bar), val = key.substr(bar + 1);
  if (kind == L"app") return fromShellItem(L"shell:AppsFolder\\" + val, size, out);
  if (kind == L"file") return fromShellItem(val, size, out);
  if (kind.compare(0, 3, L"img") == 0) {
    auto shape = (PicShape)(kind.size() > 3 ? clampi(kind[3] - L'0', 0, 3) : 0);
    std::wstring path = val;
    int idx = 0;
    size_t comma = val.find_last_of(L',');
    if (comma != std::wstring::npos && comma > 2) {
      wchar_t* end = nullptr;
      long n = wcstol(val.c_str() + comma + 1, &end, 10);
      if (end && *end == 0 && end != val.c_str() + comma + 1) { idx = (int)n; path = val.substr(0, comma); }
    }
    if (isPictureFile(path)) {
      std::string bytes;
      if (readFile(path, bytes) && decodePicture(bytes, 512, out, false)) {
        tidyPicture(out, shape, size);
        finishIcon(out);
        return true;
      }
      if (fileExt(path) != L".ico") return false;
    }
    HICON hi = nullptr;
    bool ok = false;
    if (SUCCEEDED(SHDefExtractIconW(path.c_str(), idx, 0, &hi, nullptr, (UINT)MAKELONG(size, 16))) && hi) {
      ok = fromHIcon(hi, size, out);
      DestroyIcon(hi);
    }
    if (!ok) ok = fromShellItem(path, size, out);
    if (ok && (shape == PicShape::Tile || shape == PicShape::Circle)) {
      tidyPicture(out, shape, size);
      finishIcon(out);
    }
    return ok;
  }
  return false;
}

// ---------------------------------------------------------------- cache
void IconCache::start(HWND notify, UINT message, int pixels, Mode mode) {
  px_ = pixels;
  mode_ = mode;
  notify_ = notify;
  msg_ = message;
  if (inited_) return;
  InitializeCriticalSection(&cs_);
  wake_ = CreateEventW(nullptr, FALSE, FALSE, nullptr);
  inited_ = true;
  thread_ = (HANDLE)_beginthreadex(nullptr, 0, threadMain, this, 0, nullptr);
  if (thread_) SetThreadPriority(thread_, THREAD_PRIORITY_BELOW_NORMAL);
}

void IconCache::stop() {
  if (!inited_) return;
  quit_ = true;
  SetEvent(wake_);
  if (thread_) {
    WaitForSingleObject(thread_, 1500);
    CloseHandle(thread_);
    thread_ = nullptr;
  }
}

unsigned __stdcall IconCache::threadMain(void* self) {
  auto* c = (IconCache*)self;
  if (c->mode_ == Mode::Direct) CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED | COINIT_DISABLE_OLE1DDE);
  c->run();
  if (c->mode_ == Mode::Direct) CoUninitialize();
  return 0;
}

void IconCache::deliver(const std::wstring& key, IconImage img) {
  EnterCriticalSection(&cs_);
  ready_.emplace_back(key, std::move(img));
  inFlight_--;
  LeaveCriticalSection(&cs_);
  if (notify_) PostMessageW(notify_, msg_, 0, 0);
}

void IconCache::run() {
  while (!quit_) {
    std::vector<std::wstring> keys;
    EnterCriticalSection(&cs_);
    if (mode_ == Mode::Direct) {
      if (!queue_.empty()) {
        keys.push_back(queue_.front());
        queue_.erase(queue_.begin());
      }
    } else {
      keys.swap(queue_);
    }
    inFlight_ += (int)keys.size();
    LeaveCriticalSection(&cs_);
    if (keys.empty()) {
      WaitForSingleObject(wake_, INFINITE);
      continue;
    }
    if (mode_ == Mode::Helper) {
      serveFromHelper(keys);
      continue;
    }
    IconImage img;
    if (!loadIcon(keys[0], px_, img)) {
      logf("icons: could not load %s", narrow(keys[0]).c_str());
      img = IconImage{};
    }
    deliver(keys[0], std::move(img));
  }
}

// ---------------------------------------------------------------- disk cache and helper process
namespace {
struct CacheHead {
  char magic[4];
  uint32_t w, h;
  float crop[4];
  uint64_t srcTime, srcSize, made;
};
constexpr uint64_t kDay = 864000000000ull;  // in FILETIME units

uint64_t fileNow() {
  FILETIME f;
  GetSystemTimeAsFileTime(&f);
  return ((uint64_t)f.dwHighDateTime << 32) | f.dwLowDateTime;
}

std::wstring cacheFile(const std::wstring& key, int px) {
  uint64_t h = 1469598103934665603ull;
  for (wchar_t c : toLower(key)) h = (h ^ (uint64_t)c) * 1099511628211ull;
  wchar_t b[48];
  swprintf(b, 48, L"%016llx-%d.rti", (unsigned long long)h, px);
  static const std::wstring dir = [] {
    std::wstring d = joinPath(cacheDir(), L"icons");
    SHCreateDirectoryExW(nullptr, d.c_str(), nullptr);
    return d;
  }();
  return joinPath(dir, b);
}

// Changes when the thing behind the icon changes, so a replaced file gets a fresh picture.
void sourceStamp(const std::wstring& key, uint64_t& time, uint64_t& size) {
  time = size = 0;
  size_t bar = key.find(L'|');
  if (bar == std::wstring::npos || key.compare(0, bar, L"app") == 0) return;
  std::wstring path = key.substr(bar + 1);
  if (key.compare(0, 3, L"img") == 0) {
    size_t c = path.find_last_of(L',');
    if (c != std::wstring::npos && c > 2 && path.find_first_not_of(L"-0123456789", c + 1) == std::wstring::npos) path.resize(c);
  }
  WIN32_FILE_ATTRIBUTE_DATA a{};
  if (!GetFileAttributesExW(path.c_str(), GetFileExInfoStandard, &a) || (a.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) return;
  time = ((uint64_t)a.ftLastWriteTime.dwHighDateTime << 32) | a.ftLastWriteTime.dwLowDateTime;
  size = ((uint64_t)a.nFileSizeHigh << 32) | a.nFileSizeLow;
}

void writeCache(const std::wstring& key, int px, const IconImage& img) {
  CacheHead h{{'R', 'T', 'I', '2'}, (uint32_t)img.w, (uint32_t)img.h, {img.crop.left, img.crop.top, img.crop.right, img.crop.bottom}, 0, 0, fileNow()};
  sourceStamp(key, h.srcTime, h.srcSize);
  std::string d((const char*)&h, sizeof h);
  d.append((const char*)img.px.data(), img.px.size());
  writeFileAtomic(cacheFile(key, px), d);
}

// usable: there is something to show. fresh: no need to extract again.
bool readCache(const std::wstring& key, int px, IconImage& img, bool& fresh) {
  fresh = false;
  std::string d;
  CacheHead h;
  if (!readFile(cacheFile(key, px), d) || d.size() < sizeof h) return false;
  memcpy(&h, d.data(), sizeof h);
  if (memcmp(h.magic, "RTI2", 4) || h.w > 1024 || h.h > 1024 || d.size() != sizeof h + (size_t)h.w * h.h * 4) return false;
  uint64_t t, z, age = fileNow() - h.made;
  sourceStamp(key, t, z);
  bool same = (t == h.srcTime && z == h.srcSize) || (t == 0 && z == 0);
  fresh = same && age < (h.w ? 7 * kDay : kDay / 24);  // failures are retried after an hour
  img.w = (int)h.w;
  img.h = (int)h.h;
  img.crop = D2D1::RectF(h.crop[0], h.crop[1], h.crop[2], h.crop[3]);
  img.px.assign(d.begin() + sizeof h, d.end());
  return true;
}
}  // namespace

void IconCache::serveFromHelper(const std::vector<std::wstring>& keys) {
  std::vector<std::wstring> missing;
  for (auto& k : keys) {
    IconImage img;
    bool fresh;
    if (readCache(k, px_, img, fresh)) {
      if (fresh) {
        deliver(k, std::move(img));
        continue;
      }
      if (img.w && notify_) {  // show the old picture now, the new one when it is ready
        EnterCriticalSection(&cs_);
        ready_.emplace_back(k, img);
        LeaveCriticalSection(&cs_);
        PostMessageW(notify_, msg_, 0, 0);
      }
    }
    missing.push_back(k);
  }
  // The helper works through the list in order. If it stops making progress, the item it is on is to blame:
  // give up on that one only and carry on with the rest.
  for (int round = 0; !missing.empty() && round < 8 && !quit_; round++) {
    logf("icons: asking the helper for %d", (int)missing.size());
    std::string req = std::to_string(px_) + "\n";
    for (auto& k : missing) req += narrow(k) + "\n";
    std::wstring file = joinPath(cacheDir(), L"icons-" + std::to_wstring(GetCurrentProcessId()) + L"-" + std::to_wstring(GetTickCount64()) + L".req");
    HANDLE h = writeFileAtomic(file, req) ? startHelper(L"--icon-worker \"" + file + L"\"") : nullptr;
    size_t done = 0;
    auto harvest = [&] {
      bool any = false;
      while (done < missing.size()) {
        IconImage img;
        bool fresh;
        if (!readCache(missing[done], px_, img, fresh) || !fresh) break;
        deliver(missing[done++], std::move(img));
        any = true;
      }
      return any;
    };
    if (h) {
      double last = nowSec();
      for (;;) {
        bool ended = WaitForSingleObject(h, 250) == WAIT_OBJECT_0;
        if (harvest()) last = nowSec();
        if (ended || quit_) break;
        if (nowSec() - last > 9.0) {
          logf("icons: stuck on %s", narrow(missing[std::min(done, missing.size() - 1)]).c_str());
          TerminateProcess(h, 1);
          WaitForSingleObject(h, 1000);
          harvest();
          break;
        }
      }
      CloseHandle(h);
    }
    DeleteFileW(file.c_str());
    if (done < missing.size()) {
      writeCache(missing[done], px_, IconImage{});  // remembered as failed for a while
      deliver(missing[done], IconImage{});
      done++;
    }
    missing.erase(missing.begin(), missing.begin() + (ptrdiff_t)done);
    if (!h) break;
  }
  for (auto& k : missing) deliver(k, IconImage{});
}

int runIconHelper(const std::wstring& requestFile) {
  std::string text;
  if (!readFile(requestFile, text)) return 1;
  int px = 0;
  size_t at = 0;
  while (at < text.size()) {
    size_t nl = text.find('\n', at);
    if (nl == std::string::npos) nl = text.size();
    std::string line = text.substr(at, nl - at);
    at = nl + 1;
    if (line.empty()) continue;
    if (!px) {
      px = clampi(atoi(line.c_str()), 16, 512);
      continue;
    }
    std::wstring key = widen(line);
    IconImage img;
    if (!loadIcon(key, px, img)) {
      logf("icons: could not load %s", line.c_str());
      img = IconImage{};
    }
    writeCache(key, px, img);
  }
  return 0;
}

void IconCache::drain() {
  if (!inited_) return;
  std::vector<std::pair<std::wstring, IconImage>> got;
  EnterCriticalSection(&cs_);
  got.swap(ready_);
  LeaveCriticalSection(&cs_);
  for (auto& g : got) {
    auto& e = map_[g.first];
    e.queued = false;
    e.done = true;
    e.bad = g.second.w == 0;
    if (e.bad) e.badAt = nowSec();
    e.img = std::move(g.second);
    e.tinted = false;
    e.made.clear();
  }
}

void IconCache::request(const std::wstring& key) {
  if (key.empty() || !inited_) return;
  auto& e = map_[key];
  if (e.done && e.bad && nowSec() - e.badAt > 180.0) e.done = false;  // worth another try later
  if (e.done || e.queued) return;
  e.queued = true;
  EnterCriticalSection(&cs_);
  queue_.push_back(key);
  LeaveCriticalSection(&cs_);
  SetEvent(wake_);
}

bool IconCache::failed(const std::wstring& key) const {
  auto it = map_.find(key);
  return it != map_.end() && it->second.done && it->second.bad;
}

void IconCache::waitIdle(DWORD ms) {
  if (!inited_) return;
  double end = nowSec() + ms / 1000.0;
  for (;;) {
    EnterCriticalSection(&cs_);
    bool busy = !queue_.empty() || inFlight_ > 0;
    LeaveCriticalSection(&cs_);
    drain();
    if (!busy || nowSec() > end) break;
    Sleep(5);
  }
  drain();
}

void IconCache::dropDevice() {
  for (auto& kv : map_)
    kv.second.made.clear();
}

size_t IconCache::memoryUse() const {
  size_t n = 0;
  for (auto& kv : map_) n += kv.second.img.px.capacity();
  return n;
}

void IconCache::keepOnly(std::vector<std::wstring> keys) {
  std::sort(keys.begin(), keys.end());
  for (auto it = map_.begin(); it != map_.end();) {
    if (it->second.queued || std::binary_search(keys.begin(), keys.end(), it->first)) ++it;
    else it = map_.erase(it);
  }
}

ID2D1Bitmap1* IconCache::get(const std::wstring& key, IconTone tone, Color ink, D2D1_RECT_F* crop, Color paper) {
  if (key.empty()) return nullptr;
  auto it = map_.find(key);
  if (it == map_.end() || (!it->second.done && !it->second.queued)) {
    request(key);
    return nullptr;
  }
  Entry& e = it->second;
  if (!e.done || e.bad || !gfx().ready()) return nullptr;
  if (e.gen != gfx().generation) {
    e.made.clear();
    e.gen = gfx().generation;
  }
  bool inked = tone != IconTone::Original && tone != IconTone::Muted && tone != IconTone::Pixel;
  Entry::Made* hit = nullptr;
  int same = 0;
  Entry::Made* oldest = nullptr;
  for (auto& m : e.made) {
    if (m.tone != tone) continue;
    if (!inked || (m.ink == ink && m.paper == paper)) hit = &m;
    same++;
    if (!oldest || m.used < oldest->used) oldest = &m;
  }
  if (!hit) {
    IconImage made;
    const IconImage* use = &e.img;
    if (tone != IconTone::Original && toneIcon(e.img, tone, ink, paper, made)) use = &made;
    if (same >= 4) {
      hit = oldest;
    } else {
      e.made.emplace_back();
      hit = &e.made.back();
    }
    hit->tone = tone;
    hit->ink = ink;
    hit->paper = paper;
    hit->bmp = gfx().bitmap(use->px.data(), use->w, use->h, use->w * 4);
    hit->crop = use->crop;
  }
  hit->used = ++clock_;
  if (crop) *crop = hit->crop;
  return hit->bmp.Get();
}

Color IconCache::tint(const std::wstring& key, Color otherwise) {
  auto it = map_.find(key);
  if (it == map_.end() || !it->second.done || it->second.bad) return otherwise;
  if (!it->second.tinted) {
    it->second.tint = iconColor(it->second.img);
    it->second.tinted = true;
  }
  return it->second.tint;
}

}  // namespace rt
