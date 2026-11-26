#include "picture.h"

#include <d2d1_3.h>
#include <d2d1svg.h>

namespace rt {

const wchar_t* const kPictureFilter = L"*.png;*.jpg;*.jpeg;*.webp;*.svg;*.ico;*.gif;*.bmp;*.tif;*.tiff;*.exe;*.dll;*.lnk";

bool isPictureFile(const std::wstring& path) {
  static const wchar_t* ext[] = {L".png", L".jpg", L".jpeg", L".webp", L".svg", L".ico", L".gif", L".bmp", L".tif", L".tiff", L".jfif", L".avif", L".heic"};
  std::wstring e = fileExt(path);
  for (auto x : ext)
    if (e == x) return true;
  return false;
}

// ---------------------------------------------------------------- decoding
static bool looksLikeSvg(const std::string& b) {
  size_t i = 0;
  if (b.size() > 3 && (uint8_t)b[0] == 0xEF && (uint8_t)b[1] == 0xBB && (uint8_t)b[2] == 0xBF) i = 3;
  while (i < b.size() && (b[i] == ' ' || b[i] == '\n' || b[i] == '\r' || b[i] == '\t')) i++;
  if (i >= b.size() || b[i] != '<') return false;
  return b.substr(i, 4096).find("<svg") != std::string::npos;
}

static bool visible(const IconImage& img) {
  for (size_t i = 3; i < img.px.size(); i += 4)
    if (img.px[i] > 20) return true;
  return false;
}

// Makes the drawing fill whatever square it is given: drops the size it asks for, after turning that into a view box
// if it has none. Pasted snippets may also lack the namespace.
static std::string fitSvg(const std::string& xml) {
  size_t a = xml.find("<svg");
  if (a == std::string::npos) return xml;
  size_t i = a + 4;
  std::string keep, width, height;
  bool view = false, ns = false, link = false;
  auto space = [](char c) { return c == ' ' || c == '\t' || c == '\n' || c == '\r'; };
  while (i < xml.size()) {
    while (i < xml.size() && space(xml[i])) i++;
    if (i >= xml.size() || xml[i] == '>' || xml[i] == '/') break;
    size_t k = i;
    while (i < xml.size() && xml[i] != '=' && xml[i] != '>' && !space(xml[i])) i++;
    std::string name = xml.substr(k, i - k), val;
    while (i < xml.size() && space(xml[i])) i++;
    if (i < xml.size() && xml[i] == '=') {
      i++;
      while (i < xml.size() && space(xml[i])) i++;
      if (i < xml.size() && (xml[i] == '"' || xml[i] == '\'')) {
        char q = xml[i++];
        size_t v = i;
        while (i < xml.size() && xml[i] != q) i++;
        val = xml.substr(v, i - v);
        if (i < xml.size()) i++;
      }
    }
    if (i == k) return xml;  // not something we understand
    if (name == "width") {
      width = val;
    } else if (name == "height") {
      height = val;
    } else {
      view |= name == "viewBox";
      ns |= name == "xmlns";
      link |= name == "xmlns:xlink";
      char q = val.find('"') == std::string::npos ? '"' : '\'';
      keep += " " + name + "=" + q + val + q;
    }
  }
  if (i >= xml.size()) return xml;
  float w = strtof(width.c_str(), nullptr), h = strtof(height.c_str(), nullptr);
  if (!view && w > 0 && h > 0 && width.find('%') == std::string::npos && height.find('%') == std::string::npos)
    keep += " viewBox=\"0 0 " + std::to_string(w) + " " + std::to_string(h) + "\"";
  if (!ns) keep += " xmlns=\"http://www.w3.org/2000/svg\"";
  if (!link && xml.find("xlink:") != std::string::npos) keep += " xmlns:xlink=\"http://www.w3.org/1999/xlink\"";
  return xml.substr(0, a) + "<svg" + keep + " width=\"100%\" height=\"100%\"" + xml.substr(i);
}

static bool renderSvg(const std::string& text, int size, IconImage& out) {
  auto& g = gfx();
  if (text.size() > 4 * 1024 * 1024 || !g.ensure()) return false;
  std::string xml = fitSvg(text);
  ComPtr<ID2D1DeviceContext5> dc;
  if (FAILED(g.aux.As(&dc))) return false;
  ComPtr<IStream> stream;
  stream.Attach(SHCreateMemStream((const BYTE*)xml.data(), (UINT)xml.size()));
  ComPtr<ID2D1SvgDocument> doc;
  if (!stream || FAILED(dc->CreateSvgDocument(stream.Get(), D2D1::SizeF((float)size, (float)size), &doc))) return false;
  auto tgt = g.target(size, size);
  auto rd = g.readable(size, size);
  if (!tgt || !rd) return false;
  dc->SetTarget(tgt.Get());
  dc->SetDpi(96, 96);
  dc->SetTransform(D2D1::Matrix3x2F::Identity());
  dc->BeginDraw();
  dc->Clear(D2D1::ColorF(0, 0, 0, 0));
  dc->DrawSvgDocument(doc.Get());
  HRESULT hr = dc->EndDraw();
  dc->SetTarget(nullptr);
  D2D1_MAPPED_RECT m{};
  if (FAILED(hr) || FAILED(rd->CopyFromBitmap(nullptr, tgt.Get(), nullptr)) || FAILED(rd->Map(D2D1_MAP_OPTIONS_READ, &m))) return false;
  out.w = out.h = size;
  out.px.resize((size_t)size * size * 4);
  for (int y = 0; y < size; y++) memcpy(&out.px[(size_t)y * size * 4], m.bits + (size_t)y * m.pitch, (size_t)size * 4);
  rd->Unmap();
  return visible(out);
}

// opaque: ignore the alpha channel.
static bool fromWic(IWICImagingFactory* wic, IWICBitmapDecoder* dec, int maxSide, bool opaque, IconImage& out) {
  UINT frames = 0, best = 0, bestW = 0;
  dec->GetFrameCount(&frames);
  // An .ico holds several sizes: take the largest. Animations only ever need their first frame.
  GUID fmt{};
  dec->GetContainerFormat(&fmt);
  if (fmt == GUID_ContainerFormatIco) {
    for (UINT i = 0; i < frames; i++) {
      ComPtr<IWICBitmapFrameDecode> f;
      UINT w = 0, h = 0;
      if (SUCCEEDED(dec->GetFrame(i, &f)) && SUCCEEDED(f->GetSize(&w, &h)) && w > bestW) {
        bestW = w;
        best = i;
      }
    }
  }
  ComPtr<IWICBitmapFrameDecode> fr;
  UINT w = 0, h = 0;
  if (FAILED(dec->GetFrame(best, &fr)) || FAILED(fr->GetSize(&w, &h)) || !w || !h) return false;
  if ((uint64_t)w * h > 120000000ull) return false;
  double k = std::min(1.0, (double)maxSide / std::max(w, h));
  UINT tw = std::max(1u, (UINT)lround(w * k)), th = std::max(1u, (UINT)lround(h * k));
  // Premultiply before scaling, so the colour hidden under transparent pixels cannot bleed into the edges.
  ComPtr<IWICFormatConverter> cv;
  ComPtr<IWICBitmapScaler> sc;
  if (FAILED(wic->CreateFormatConverter(&cv)) ||
      FAILED(cv->Initialize(fr.Get(), opaque ? GUID_WICPixelFormat32bppBGR : GUID_WICPixelFormat32bppPBGRA, WICBitmapDitherTypeNone, nullptr, 0, WICBitmapPaletteTypeCustom)) ||
      FAILED(wic->CreateBitmapScaler(&sc)) || FAILED(sc->Initialize(cv.Get(), tw, th, WICBitmapInterpolationModeFant)))
    return false;
  // Cameras store which way up they were held.
  WICBitmapTransformOptions turn = WICBitmapTransformRotate0;
  ComPtr<IWICMetadataQueryReader> meta;
  if (SUCCEEDED(fr->GetMetadataQueryReader(&meta))) {
    PROPVARIANT v;
    PropVariantInit(&v);
    if (SUCCEEDED(meta->GetMetadataByName(L"/app1/ifd/{ushort=274}", &v)) && v.vt == VT_UI2)
      turn = v.uiVal == 3 ? WICBitmapTransformRotate180 : v.uiVal == 6 ? WICBitmapTransformRotate90 : v.uiVal == 8 ? WICBitmapTransformRotate270
             : v.uiVal == 2 ? WICBitmapTransformFlipHorizontal : v.uiVal == 4 ? WICBitmapTransformFlipVertical : turn;
    PropVariantClear(&v);
  }
  IWICBitmapSource* src = sc.Get();
  ComPtr<IWICBitmap> held;
  ComPtr<IWICBitmapFlipRotator> rot;
  if (turn != WICBitmapTransformRotate0) {
    if (FAILED(wic->CreateBitmapFromSource(sc.Get(), WICBitmapCacheOnLoad, &held)) || FAILED(wic->CreateBitmapFlipRotator(&rot)) || FAILED(rot->Initialize(held.Get(), turn))) return false;
    src = rot.Get();
    rot->GetSize(&tw, &th);
  }
  out.w = (int)tw;
  out.h = (int)th;
  out.px.resize((size_t)tw * th * 4);
  if (FAILED(src->CopyPixels(nullptr, tw * 4, (UINT)out.px.size(), out.px.data()))) return false;
  if (opaque)
    for (size_t i = 3; i < out.px.size(); i += 4) out.px[i] = 255;
  return true;
}

static ComPtr<IWICImagingFactory> wicFactory() {
  ComPtr<IWICImagingFactory> wic;  // a fresh one: this is used from several threads
  CoCreateInstance(CLSID_WICImagingFactory, nullptr, CLSCTX_INPROC_SERVER, __uuidof(IWICImagingFactory), (void**)wic.GetAddressOf());
  return wic;
}

bool decodePicture(const std::string& bytes, int maxSide, IconImage& out, bool allowSvg) {
  out = IconImage{};
  if (bytes.size() < 16) return false;
  if (looksLikeSvg(bytes)) return allowSvg && renderSvg(bytes, std::min(maxSide, 512), out);
  auto wic = wicFactory();
  ComPtr<IWICStream> st;
  ComPtr<IWICBitmapDecoder> dec;
  if (!wic || FAILED(wic->CreateStream(&st)) || FAILED(st->InitializeFromMemory((BYTE*)bytes.data(), (DWORD)bytes.size())) ||
      FAILED(wic->CreateDecoderFromStream(st.Get(), nullptr, WICDecodeMetadataCacheOnDemand, &dec)))
    return false;
  if (fromWic(wic.Get(), dec.Get(), maxSide, false, out) && visible(out)) return true;
  // A picture whose alpha channel was never filled in: the colours are what was meant.
  if (out.w > 0 && fromWic(wic.Get(), dec.Get(), maxSide, true, out))
    for (size_t i = 0; i + 3 < out.px.size(); i += 4)
      if (out.px[i] || out.px[i + 1] || out.px[i + 2]) return true;
  out = IconImage{};
  return false;
}

bool encodePng(const IconImage& img, std::string& out) {
  auto wic = wicFactory();
  ComPtr<IStream> mem;
  mem.Attach(SHCreateMemStream(nullptr, 0));
  ComPtr<IWICBitmap> bmp;
  ComPtr<IWICFormatConverter> cv;
  ComPtr<IWICBitmapEncoder> enc;
  ComPtr<IWICBitmapFrameEncode> fr;
  GUID fmt = GUID_WICPixelFormat32bppBGRA;
  if (!wic || !mem || img.w <= 0 || img.h <= 0 ||
      FAILED(wic->CreateBitmapFromMemory((UINT)img.w, (UINT)img.h, GUID_WICPixelFormat32bppPBGRA, (UINT)img.w * 4, (UINT)img.px.size(), (BYTE*)img.px.data(), &bmp)) ||
      FAILED(wic->CreateFormatConverter(&cv)) ||
      FAILED(cv->Initialize(bmp.Get(), GUID_WICPixelFormat32bppBGRA, WICBitmapDitherTypeNone, nullptr, 0, WICBitmapPaletteTypeCustom)) ||
      FAILED(wic->CreateEncoder(GUID_ContainerFormatPng, nullptr, &enc)) || FAILED(enc->Initialize(mem.Get(), WICBitmapEncoderNoCache)) ||
      FAILED(enc->CreateNewFrame(&fr, nullptr)) || FAILED(fr->Initialize(nullptr)) || FAILED(fr->SetSize((UINT)img.w, (UINT)img.h)) ||
      FAILED(fr->SetPixelFormat(&fmt)) || FAILED(fr->WriteSource(cv.Get(), nullptr)) || FAILED(fr->Commit()) || FAILED(enc->Commit()))
    return false;
  STATSTG ss{};
  LARGE_INTEGER zero{};
  if (FAILED(mem->Stat(&ss, STATFLAG_NONAME)) || FAILED(mem->Seek(zero, STREAM_SEEK_SET, nullptr))) return false;
  out.resize((size_t)ss.cbSize.QuadPart);
  ULONG got = 0;
  return SUCCEEDED(mem->Read(out.data(), (ULONG)out.size(), &got)) && got == out.size();
}

std::wstring keepPicture(const std::string& bytes, const std::wstring& name) {
  IconImage img;
  std::string png;
  if (!decodePicture(bytes, 512, img, true) || !encodePng(img, png)) return {};
  std::wstring stem;
  for (wchar_t c : name) {
    if (stem.size() >= 40) break;
    stem += (c < 32 || wcschr(L"<>:\"/\\|?*%,", c)) ? L'-' : c;
  }
  stem = trim(stem);
  while (!stem.empty() && stem.back() == L'.') stem.pop_back();
  if (stem.empty()) stem = L"picture";
  SHCreateDirectoryExW(nullptr, imagesDir().c_str(), nullptr);
  std::wstring path = joinPath(imagesDir(), stem + L"-" + widen(newId()).substr(0, 8) + L".png");
  return writeFileAtomic(path, png) ? path : std::wstring();
}

// The creation time is the day something was last seen in use. (The write time belongs to the icon cache.)
static void sweepFolder(const std::wstring& dir, const wchar_t* pattern, const std::vector<std::wstring>& used) {
  constexpr int64_t kDay = 864000000000ll;
  auto num = [](FILETIME f) { return (int64_t)(((uint64_t)f.dwHighDateTime << 32) | f.dwLowDateTime); };
  FILETIME now;
  GetSystemTimeAsFileTime(&now);
  WIN32_FIND_DATAW fd;
  HANDLE h = FindFirstFileW(joinPath(dir, pattern).c_str(), &fd);
  if (h == INVALID_HANDLE_VALUE) return;
  do {
    std::wstring path = joinPath(dir, fd.cFileName);
    int64_t age = num(now) - num(fd.ftCreationTime);
    if (std::find(used.begin(), used.end(), toLower(fd.cFileName)) == used.end()) {
      if (age > 30 * kDay) DeleteFileW(path.c_str());
    } else if (age > kDay || age < -kDay) {
      HANDLE f = CreateFileW(path.c_str(), FILE_WRITE_ATTRIBUTES, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING, 0, nullptr);
      if (f != INVALID_HANDLE_VALUE) {
        SetFileTime(f, &now, nullptr, nullptr);
        CloseHandle(f);
      }
    }
  } while (FindNextFileW(h, &fd));
  FindClose(h);
}

void sweepKept(const Config& cfg) {
  if (cfg.locked || !cfg.intact) return;
  std::vector<std::wstring> pics, links;
  auto take = [&](const Pin& p) {
    if (!p.icon.empty()) pics.push_back(toLower(fileName(p.icon)));
    if (p.kind == Pin::Kind::File && fileExt(p.target) == L".lnk") links.push_back(toLower(fileName(p.target)));
  };
  for (auto& pr : cfg.profiles)
    for (auto& p : pr.pins) {
      take(p);
      for (auto& c : p.children) take(c);
    }
  sweepFolder(imagesDir(), L"*.png", pics);
  sweepFolder(linksDir(), L"*.lnk", links);
}

// ---------------------------------------------------------------- tidying
namespace {
uint8_t* at(IconImage& m, int x, int y) { return &m.px[((size_t)y * m.w + x) * 4]; }
const uint8_t* at(const IconImage& m, int x, int y) { return &m.px[((size_t)y * m.w + x) * 4]; }

IconImage blank(int w, int h, uint8_t b, uint8_t g, uint8_t r, uint8_t a) {
  IconImage m;
  m.w = w;
  m.h = h;
  m.px.resize((size_t)w * h * 4);
  for (size_t i = 0; i < m.px.size(); i += 4) {
    m.px[i] = b;
    m.px[i + 1] = g;
    m.px[i + 2] = r;
    m.px[i + 3] = a;
  }
  return m;
}

// Source over destination, both premultiplied.
void stamp(IconImage& dst, const IconImage& src, int ox, int oy) {
  for (int y = std::max(0, -oy); y < src.h && y + oy < dst.h; y++)
    for (int x = std::max(0, -ox); x < src.w && x + ox < dst.w; x++) {
      const uint8_t* s = at(src, x, y);
      uint8_t* d = at(dst, x + ox, y + oy);
      int inv = 255 - s[3];
      for (int k = 0; k < 4; k++) d[k] = (uint8_t)std::min(255, s[k] + (d[k] * inv + 127) / 255);
    }
}

IconImage cut(const IconImage& m, int x0, int y0, int w, int h) {
  IconImage o = blank(w, h, 0, 0, 0, 0);
  for (int y = 0; y < h; y++)
    for (int x = 0; x < w; x++) {
      int sx = x + x0, sy = y + y0;
      if (sx >= 0 && sy >= 0 && sx < m.w && sy < m.h) memcpy(at(o, x, y), at(m, sx, sy), 4);
    }
  return o;
}

template <class F>
void eachBorder(const IconImage& m, F&& f) {
  for (int x = 0; x < m.w; x++) {
    f(at(m, x, 0));
    f(at(m, x, m.h - 1));
  }
  for (int y = 1; y + 1 < m.h; y++) {
    f(at(m, 0, y));
    f(at(m, m.w - 1, y));
  }
}

bool opaqueEdge(const IconImage& m) {
  int n = 0, solid = 0;
  eachBorder(m, [&](const uint8_t* q) {
    n++;
    solid += q[3] >= 248;
  });
  return n && solid >= n * 0.97f;
}

bool plainEdge(const IconImage& m, uint8_t bg[3]) {
  std::vector<uint8_t> ch[3];
  eachBorder(m, [&](const uint8_t* q) {
    for (int k = 0; k < 3; k++) ch[k].push_back(q[k]);
  });
  for (int k = 0; k < 3; k++) {
    std::nth_element(ch[k].begin(), ch[k].begin() + (ptrdiff_t)(ch[k].size() / 2), ch[k].end());
    bg[k] = ch[k][ch[k].size() / 2];
  }
  int n = 0, same = 0;
  eachBorder(m, [&](const uint8_t* q) {
    n++;
    same += abs(q[0] - bg[0]) < 14 && abs(q[1] - bg[1]) < 14 && abs(q[2] - bg[2]) < 14;
  });
  return same >= n * 0.96f;
}

struct Box {
  int l = 1 << 30, t = 1 << 30, r = -1, b = -1;
  bool ok() const { return r >= l; }
  int w() const { return r - l + 1; }
  int h() const { return b - t + 1; }
  void add(int x, int y) {
    l = std::min(l, x);
    t = std::min(t, y);
    r = std::max(r, x);
    b = std::max(b, y);
  }
};

Box contentBox(const IconImage& m, const uint8_t* bg) {
  Box q;
  for (int y = 0; y < m.h; y++)
    for (int x = 0; x < m.w; x++) {
      const uint8_t* p = at(m, x, y);
      bool on = bg ? abs(p[0] - bg[0]) > 26 || abs(p[1] - bg[1]) > 26 || abs(p[2] - bg[2]) > 26 : p[3] > 14;
      if (on) q.add(x, y);
    }
  return q;
}

// -1 nearly all visible pixels are dark, +1 nearly all are light, 0 anything else.
int oneTone(const IconImage& m) {
  double n = 0, dark = 0, light = 0;
  for (size_t i = 0; i + 3 < m.px.size(); i += 4) {
    float a = m.px[i + 3];
    if (a < 90) continue;
    float l = (0.114f * m.px[i] + 0.587f * m.px[i + 1] + 0.299f * m.px[i + 2]) / a;
    n++;
    dark += l < 0.26f;
    light += l > 0.90f;
  }
  if (n < 1) return 0;
  return dark > n * 0.93 ? -1 : light > n * 0.95 ? 1 : 0;
}

void shrink(IconImage& m, int size) {
  if (m.w <= size && m.h <= size) return;
  auto wic = wicFactory();
  ComPtr<IWICBitmap> bmp;
  ComPtr<IWICBitmapScaler> sc;
  double k = (double)size / std::max(m.w, m.h);
  UINT w = std::max(1u, (UINT)lround(m.w * k)), h = std::max(1u, (UINT)lround(m.h * k));
  if (!wic ||
      FAILED(wic->CreateBitmapFromMemory((UINT)m.w, (UINT)m.h, GUID_WICPixelFormat32bppPBGRA, (UINT)m.w * 4, (UINT)m.px.size(), m.px.data(), &bmp)) ||
      FAILED(wic->CreateBitmapScaler(&sc)) || FAILED(sc->Initialize(bmp.Get(), w, h, WICBitmapInterpolationModeFant)))
    return;
  IconImage o = blank((int)w, (int)h, 0, 0, 0, 0);
  if (SUCCEEDED(sc->CopyPixels(nullptr, w * 4, (UINT)o.px.size(), o.px.data()))) m = std::move(o);
}

// Cuts the corners with smooth edges. radius is a fraction of the side; 0.5 gives a circle.
void roundOff(IconImage& m, float radius) {
  float hw = m.w * 0.5f, hh = m.h * 0.5f, r = std::min(hw, hh) * std::min(1.f, radius * 2.f);
  for (int y = 0; y < m.h; y++)
    for (int x = 0; x < m.w; x++) {
      float dx = fabsf(x + 0.5f - hw) - (hw - r), dy = fabsf(y + 0.5f - hh) - (hh - r);
      float d = sqrtf(std::max(dx, 0.f) * std::max(dx, 0.f) + std::max(dy, 0.f) * std::max(dy, 0.f)) + std::min(std::max(dx, dy), 0.f) - r;
      float c = saturate(0.5f - d);
      if (c >= 1.f) continue;
      uint8_t* q = at(m, x, y);
      for (int k = 0; k < 4; k++) q[k] = (uint8_t)lroundf(q[k] * c);
    }
}
}  // namespace

void squarePicture(IconImage& m) {
  if (m.w == m.h || m.w <= 0 || m.h <= 0) return;
  int side = std::max(m.w, m.h);
  IconImage o = blank(side, side, 0, 0, 0, 0);
  stamp(o, m, (side - m.w) / 2, (side - m.h) / 2);
  m = std::move(o);
}

void tidyPicture(IconImage& m, PicShape shape, int size) {
  if (m.w <= 0 || m.h <= 0) return;
  float round = 0.f;
  if (shape == PicShape::Plain) {
    squarePicture(m);
  } else if (opaqueEdge(m)) {
    round = shape == PicShape::Circle ? 0.5f : 0.225f;
    uint8_t bg[3];
    Box q;
    bool plain = plainEdge(m, bg);
    if (plain) q = contentBox(m, bg);
    if (plain && q.ok()) {
      // A logo on a plain background: keep the background, drop margins that only make it look small.
      int big = std::max(q.w(), q.h());
      float want = shape == PicShape::Circle ? 1.62f : 1.34f;
      bool loose = m.w != m.h || big < m.w * 0.60f || (shape == PicShape::Circle && big * 1.40f > m.w);
      if (loose) {
        int side = std::max(1, (int)lroundf(big * want));
        IconImage o = blank(side, side, bg[0], bg[1], bg[2], 255);
        stamp(o, cut(m, q.l, q.t, q.w(), q.h()), (side - q.w()) / 2, (side - q.h()) / 2);
        m = std::move(o);
      }
    } else if (m.w != m.h) {  // a photo: the middle of it
      int side = std::min(m.w, m.h);
      m = cut(m, (m.w - side) / 2, (m.h - side) / 2, side, side);
    }
  } else {
    int tone = oneTone(m);
    if (shape == PicShape::Auto && !tone) {
      squarePicture(m);
    } else {
      // A see-through logo on a plate of its own, light behind dark logos and the other way round.
      Box q = contentBox(m, nullptr);
      if (q.ok()) {
        int big = std::max(q.w(), q.h());
        int side = std::max(1, (int)lroundf(big * (shape == PicShape::Circle ? 1.62f : 1.42f)));
        IconImage o = tone > 0 ? blank(side, side, 0x2C, 0x26, 0x24, 255) : blank(side, side, 255, 255, 255, 255);
        stamp(o, cut(m, q.l, q.t, q.w(), q.h()), (side - q.w()) / 2, (side - q.h()) / 2);
        m = std::move(o);
        round = shape == PicShape::Circle ? 0.5f : 0.225f;
      } else {
        squarePicture(m);
      }
    }
  }
  shrink(m, size);
  if (round > 0.f) roundOff(m, round);
}

// ---------------------------------------------------------------- clipboard
static std::string globalBytes(HANDLE h) {
  std::string s;
  if (!h) return s;
  if (auto* p = (const char*)GlobalLock(h)) {
    s.assign(p, GlobalSize(h));
    GlobalUnlock(h);
  }
  return s;
}

// A copied bitmap arrives without its file header.
static std::string dibToBmp(const std::string& dib) {
  if (dib.size() < sizeof(BITMAPINFOHEADER)) return {};
  BITMAPINFOHEADER h;
  memcpy(&h, dib.data(), sizeof h);
  if (h.biSize < sizeof h || h.biSize > dib.size()) return {};
  size_t extra = 0;
  if (h.biBitCount <= 8) {
    extra = (h.biClrUsed ? std::min<size_t>(h.biClrUsed, 256) : (size_t)1 << h.biBitCount) * 4;
  } else if (h.biCompression == BI_BITFIELDS) {
    if (h.biSize == sizeof h) extra = 12;
    // Longer headers hold the colour masks, yet the ones Windows makes up itself repeat them after the header.
    else if (h.biSize >= 52 && dib.size() >= h.biSize + 12 && !memcmp(dib.data() + 40, dib.data() + h.biSize, 12)) extra = 12;
  }
  if (h.biSize + extra >= dib.size()) return {};
  BITMAPFILEHEADER f{};
  f.bfType = 0x4D42;
  f.bfOffBits = (DWORD)(sizeof f + h.biSize + extra);
  f.bfSize = (DWORD)(sizeof f + dib.size());
  std::string out((const char*)&f, sizeof f);
  return out + dib;
}

bool clipboardPicture(HWND owner, std::string& bytes, std::wstring& link) {
  bytes.clear();
  link.clear();
  bool open = false;
  for (int i = 0; i < 10 && !(open = OpenClipboard(owner) != FALSE); i++) Sleep(20);
  if (!open) return false;
  std::wstring file;
  for (auto name : {L"PNG", L"image/png", L"image/svg+xml"}) {
    if (!bytes.empty()) break;
    UINT f = RegisterClipboardFormatW(name);
    if (f && IsClipboardFormatAvailable(f)) bytes = globalBytes(GetClipboardData(f));
  }
  if (bytes.empty() && IsClipboardFormatAvailable(CF_HDROP)) {
    if (auto d = (HDROP)GetClipboardData(CF_HDROP)) {
      wchar_t p[2048];
      if (DragQueryFileW(d, 0, p, 2048) && isPictureFile(p)) file = p;
    }
  }
  if (bytes.empty() && file.empty()) {
    UINT f = IsClipboardFormatAvailable(CF_DIBV5) ? CF_DIBV5 : IsClipboardFormatAvailable(CF_DIB) ? CF_DIB : 0;
    if (f) bytes = dibToBmp(globalBytes(GetClipboardData(f)));
  }
  if (bytes.empty() && file.empty() && IsClipboardFormatAvailable(CF_UNICODETEXT)) {
    std::string raw = globalBytes(GetClipboardData(CF_UNICODETEXT));
    std::wstring t((const wchar_t*)raw.data(), raw.size() / sizeof(wchar_t));
    size_t z = t.find(L'\0');
    if (z != std::wstring::npos) t.resize(z);
    t = trim(t);
    std::wstring low = toLower(t.substr(0, 8));
    if (low.rfind(L"http://", 0) == 0 || low.rfind(L"https://", 0) == 0) {
      if (t.size() < 2000 && t.find_first_of(L" \r\n\t\"<>") == std::wstring::npos) link = t;
    } else if (t.find(L"<svg") != std::wstring::npos) {
      bytes = narrow(t);
    } else if (t.size() > 4 && t[1] == L':' && isPictureFile(t) && fileExists(t)) {
      file = t;
    }
  }
  CloseClipboard();
  if (!file.empty()) readFile(file, bytes);
  return !bytes.empty() || !link.empty();
}

}  // namespace rt
