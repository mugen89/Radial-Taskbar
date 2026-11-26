// Pictures and website logos: reading pages, choosing among icons, tidying, keeping copies. No network needed.
// Run with RADIALTASKBAR_DATA pointing at an empty folder.
#include <cstdio>

#include "picture.h"
#include "shellutil.h"
#include "sitelogo.h"

using namespace rt;

static int bad = 0;
static void check(const std::string& n, bool ok, const std::string& extra = {}) {
  printf("%s %s %s\n", ok ? "ok  " : "FAIL", n.c_str(), ok ? "" : extra.c_str());
  if (!ok) bad++;
}
static void same(const std::string& n, const std::wstring& a, const std::wstring& b) { check(n, a == b, "got '" + narrow(a) + "' want '" + narrow(b) + "'"); }

static IconImage make(int w, int h, uint32_t bgra) {
  IconImage m;
  m.w = w;
  m.h = h;
  m.px.resize((size_t)w * h * 4);
  for (size_t i = 0; i < (size_t)w * h; i++) memcpy(&m.px[i * 4], &bgra, 4);
  return m;
}
static void box(IconImage& m, int x0, int y0, int w, int h, uint32_t bgra) {
  for (int y = y0; y < y0 + h; y++)
    for (int x = x0; x < x0 + w; x++) memcpy(&m.px[((size_t)y * m.w + x) * 4], &bgra, 4);
}
static uint32_t at(const IconImage& m, int x, int y) {
  uint32_t v;
  memcpy(&v, &m.px[((size_t)y * m.w + x) * 4], 4);
  return v;
}
static uint8_t alpha(const IconImage& m, int x, int y) { return (uint8_t)(at(m, x, y) >> 24); }

int main() {
  if (!GetEnvironmentVariableW(L"RADIALTASKBAR_DATA", nullptr, 0)) {
    printf("set RADIALTASKBAR_DATA first\n");
    return 99;
  }
  OleInitialize(nullptr);

  // ------------------------------------------------ addresses
  same("host", siteHost(L"https://www.YouTube.com/feed?x=1"), L"youtube.com");
  same("host with port and user", siteHost(L"http://me@intranet:8080/x"), L"intranet");
  same("absolute", resolveUrl(L"https://a.com/x/y.html", L"https://b.com/i.png"), L"https://b.com/i.png");
  same("protocol relative", resolveUrl(L"https://a.com/x", L"//cdn.a.com/i.png"), L"https://cdn.a.com/i.png");
  same("root relative", resolveUrl(L"https://a.com/x/y.html?q#z", L"/i.png"), L"https://a.com/i.png");
  same("relative", resolveUrl(L"https://a.com/x/y.html", L"i/b.png"), L"https://a.com/x/i/b.png");
  same("up", resolveUrl(L"https://a.com/x/y/z.html", L"../i.png"), L"https://a.com/x/i.png");
  same("no path", resolveUrl(L"https://a.com", L"i.png"), L"https://a.com/i.png");
  same("other schemes refused", resolveUrl(L"https://a.com/", L"file:///c:/x.png"), L"");
  same("javascript refused", resolveUrl(L"https://a.com/", L"javascript:alert(1)"), L"");
  check("web addresses only", isWebAddress(L"HTTPS://x") && isWebAddress(L"http://x") && !isWebAddress(L"ms-settings:") && !isWebAddress(L"file:///c:/"));

  // ------------------------------------------------ pages
  PageFacts f = readPage("<!doctype html><html><head><title>Home - Example &amp; Co | News</title>"
                         "<!-- <link rel=icon href=/commented.png> -->"
                         "<script>var s = '<link rel=\"icon\" href=\"/script.png\">';</script>"
                         "<link rel='shortcut icon' href='/favicon.ico'>"
                         "<link sizes=\"32x32\" rel=\"icon\" type=\"image/png\" href=\"/f32.png\"/>"
                         "<link rel=\"apple-touch-icon\" sizes=\"180x180\" href=\"//cdn.example.com/touch.png\">"
                         "<link rel=mask-icon href=/mask.svg color=#000>"
                         "<link rel=icon type=image/svg+xml href=icon.svg sizes=any>"
                         "<link rel=\"stylesheet\" href=\"/style.css\"><link rel=manifest href=/m.json>"
                         "</head><body><link rel=icon href=/body.png></body>",
                         L"https://www.example.com/a/b");
  std::string all;
  for (auto& l : f.links) all += narrow(l.url) + " ";
  check("found the icons", f.links.size() == 4, all);
  check("comments, scripts, body and mask icons left out", all.find("commented") == std::string::npos && all.find("script.png") == std::string::npos && all.find("body") == std::string::npos && all.find("mask") == std::string::npos, all);
  same("manifest", f.manifest, L"https://www.example.com/m.json");
  same("name from the title", f.name, L"Example & Co");
  rankLinks(f.links);
  check("the big touch icon first", !f.links.empty() && f.links[0].url == L"https://cdn.example.com/touch.png", narrow(f.links[0].url));
  check("the small ico last", f.links.back().url.find(L"f32") != std::wstring::npos || f.links.back().url.find(L"favicon.ico") != std::wstring::npos);

  f = readPage("<head><base href=\"https://static.example.org/assets/\"><link rel=icon href=i.png sizes=192x192><meta property=og:site_name content=\"Moj Sajt\">", L"https://example.org/");
  check("base address", f.links.size() == 1 && f.links[0].url == L"https://static.example.org/assets/i.png", f.links.empty() ? "" : narrow(f.links[0].url));
  same("site name", f.name, L"Moj Sajt");
  f = readPage("<meta charset=windows-1251><title>\xCF\xEE\xF9\xE0</title>", L"https://abv.bg/");
  same("old code page", f.name, L"\x041F\x043E\x0449\x0430");
  f = readPage("<title>A very long marketing sentence about nothing in particular for everyone</title>", L"https://shop.example.com/");
  same("no name rather than a sentence", f.name, L"");
  f = readPage("<title>(3) YouTube</title>", L"https://www.youtube.com/");
  check("title with the host's name", f.name.find(L"YouTube") != std::wstring::npos, narrow(f.name));
  f = readPage("<title>BBC News - Home</title>", L"https://www.bbc.co.uk/news");
  same("country domains", f.name, L"BBC News");
  f = readPage("<title>\xCF\xEE\xF9\xE0</title>", L"https://abv.bg/", "text/html; charset=windows-1251");
  same("code page from the header", f.name, L"\x041F\x043E\x0449\x0430");
  f = readPage("<meta charset=utf-8><title>\xD0\x9F\xD0\xBE\xD1\x89\xD0\xB0</title>", L"https://abv.bg/", "text/html; charset=windows-1251");
  same("the page knows better", f.name, L"\x041F\x043E\x0449\x0430");
  // whose network an address belongs to
  for (auto h : {L"localhost", L"router", L"nas.local", L"10.0.0.5", L"127.0.0.1", L"192.168.1.1", L"172.16.0.1", L"172.31.255.1", L"169.254.1.1", L"100.64.0.1", L"0.0.0.0", L"[::1]",
                 L"[fe80::1]", L"[fd00::1]", L"2130706433", L"0x7f.0.0.1", L"127.1", L"224.0.0.1", L"app.corp", L"printer.home.arpa", L"x.localhost.", L""})
    check("private: " + narrow(h), privateHost(h));
  for (auto h : {L"youtube.com", L"www.abv.bg", L"8.8.8.8", L"172.15.0.1", L"172.32.0.1", L"192.169.0.1", L"100.63.0.1", L"[2a00:1450::1]", L"local.example.com", L"1.example.com"})
    check("public: " + narrow(h), !privateHost(h));
  {
    double t0 = nowSec();
    readPage("<title>" + std::string(1500000, '&') + "</title><link rel=icon href=\"" + std::string(1500000, '&') + "\">", L"https://a.com/");
    check("a page full of ampersands takes no time", nowSec() - t0 < 1.5, std::to_string(nowSec() - t0));
  }
  // malformed input must end, and stay inside
  readPage("<link rel=icon href=", L"https://a.com/");
  readPage("<link rel=\"icon href=/x", L"https://a.com/");
  readPage("<<<<<link<<link <a <meta <title", L"https://a.com/");
  readPage("<!-- never closed", L"https://a.com/");
  readPage("<script>never closed", L"https://a.com/");
  readPage(std::string(300000, '<'), L"https://a.com/");
  check("malformed pages are survived", true);

  PageFacts m;
  readManifest("{\"short_name\":\"Tube\",\"icons\":[{\"src\":\"i/48.png\",\"sizes\":\"48x48\"},{\"src\":\"/i/192.png\",\"sizes\":\"192x192\"},{\"src\":\"mono.png\",\"purpose\":\"monochrome\",\"sizes\":\"512x512\"},{\"src\":\"mask.png\",\"purpose\":\"maskable\",\"sizes\":\"192x192\"}]}",
               L"https://y.com/app/manifest.json", m);
  rankLinks(m.links);
  check("manifest icons", m.links.size() == 3 && m.links[0].url == L"https://y.com/i/192.png", m.links.empty() ? "" : narrow(m.links[0].url));
  same("manifest name", m.name, L"Tube");
  readManifest("not json", L"https://y.com/", m);

  // ------------------------------------------------ decoding
  IconImage red = make(64, 40, 0xFFFF0000), out;
  std::string png;
  check("encode", encodePng(red, png) && png.size() > 60 && png.compare(1, 3, "PNG") == 0);
  check("decode what was encoded", decodePicture(png, 512, out, false) && out.w == 64 && out.h == 40 && at(out, 10, 10) == 0xFFFF0000);
  check("scaled down to fit", decodePicture(png, 32, out, false) && out.w == 32 && out.h == 20);
  check("rubbish refused", !decodePicture("this is not a picture at all, just text", 512, out, false) && !decodePicture("", 512, out, false));
  IconImage clear = make(32, 32, 0);
  encodePng(clear, png);
  check("an empty picture is refused", !decodePicture(png, 512, out, false));
  std::string svg = "<?xml version=\"1.0\"?><svg xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\"><rect width=\"24\" height=\"24\" fill=\"#00ff00\"/></svg>";
  check("svg only where allowed", !decodePicture(svg, 256, out, false));
  bool drew = decodePicture(svg, 256, out, true);
  check("svg fills the square", drew && out.w == 256 && at(out, 250, 250) == 0xFF00FF00, drew ? std::to_string(at(out, 250, 250)) : "not drawn");

  svg = "<svg viewBox='0 0 10 20' width='10px' height='20px'><rect x='0' y='0' width='10' height='20' fill='red'/></svg>";
  drew = decodePicture(svg, 200, out, true);
  check("svg without a namespace, tall, keeps its shape", drew && at(out, 100, 100) == 0xFFFF0000 && alpha(out, 20, 100) == 0 && alpha(out, 180, 100) == 0);
  check("broken svg is refused", !decodePicture("<svg <svg <svg", 200, out, true) && !decodePicture("<svg width='", 200, out, true));

  // a bitmap with an alpha channel that nobody filled in
  {
    std::string bmp(54 + 4 * 4 * 4, 0);
    BITMAPFILEHEADER fh{};
    fh.bfType = 0x4D42;
    fh.bfOffBits = 54 + 70;
    BITMAPV4HEADER v4{};
    v4.bV4Size = sizeof v4;
    v4.bV4Width = 4;
    v4.bV4Height = 4;
    v4.bV4Planes = 1;
    v4.bV4BitCount = 32;
    v4.bV4V4Compression = BI_BITFIELDS;
    v4.bV4RedMask = 0xFF0000;
    v4.bV4GreenMask = 0xFF00;
    v4.bV4BlueMask = 0xFF;
    v4.bV4AlphaMask = 0xFF000000;
    fh.bfOffBits = sizeof fh + sizeof v4;
    bmp.assign((const char*)&fh, sizeof fh);
    bmp.append((const char*)&v4, sizeof v4);
    for (int i = 0; i < 16; i++) bmp.append("\x10\x20\xF0\x00", 4);
    check("colours without alpha are rescued", decodePicture(bmp, 512, out, false) && at(out, 1, 1) == 0xFFF02010, std::to_string(out.w));
  }

  // ------------------------------------------------ tidying
  IconImage t = make(120, 80, 0);
  box(t, 0, 10, 120, 60, 0xFFEE1122);  // a wide see-through logo, like a play button
  tidyPicture(t, PicShape::Auto, 144);
  finishIcon(t);
  check("a wide logo is squared, not stretched", t.w == t.h && t.w == 120 && alpha(t, 60, 5) == 0 && alpha(t, 60, 60) == 255);
  check("the visible part stays square", fabsf((t.crop.right - t.crop.left) - (t.crop.bottom - t.crop.top)) < 0.01f);
  t = make(200, 200, 0xFF3366CC);
  for (int i = 0; i < 200; i++) box(t, i, i, 1, 1, 0xFF000000 | (uint32_t)(i * 70));  // not a plain colour
  box(t, 0, 0, 200, 60, 0xFF11AA55);
  tidyPicture(t, PicShape::Auto, 144);
  check("a full picture gets round corners", t.w == 144 && alpha(t, 0, 0) == 0 && alpha(t, 72, 2) == 255 && alpha(t, 72, 72) == 255);
  t = make(200, 200, 0xFF3366CC);
  box(t, 60, 60, 80, 80, 0xFFFFFFFF);
  tidyPicture(t, PicShape::Plain, 144);
  check("as is stays as it is", t.w == 144 && alpha(t, 0, 0) == 255);
  t = make(300, 100, 0xFFFFFFFF);
  box(t, 120, 30, 60, 40, 0xFF0000FF);  // a small logo on a wide white picture
  tidyPicture(t, PicShape::Auto, 144);
  check("plain margins are trimmed", t.w == t.h && t.w < 120 && alpha(t, t.w / 2, t.h / 2) == 255, std::to_string(t.w) + "x" + std::to_string(t.h));
  t = make(100, 100, 0);
  box(t, 20, 20, 60, 60, 0xFF101010);  // a black logo, invisible on a dark wheel
  tidyPicture(t, PicShape::Auto, 144);
  check("a dark logo gets a light plate", at(t, t.w / 2, 4) == 0xFFFFFFFF, std::to_string(at(t, t.w / 2, 4)));
  t = make(100, 100, 0);
  box(t, 20, 20, 60, 60, 0xFFFFFFFF);
  tidyPicture(t, PicShape::Auto, 144);
  check("a white logo gets a dark plate", (at(t, t.w / 2, 4) & 0xFF) < 0x40 && alpha(t, t.w / 2, 4) == 255);
  t = make(400, 200, 0xFF3366CC);
  for (int x = 0; x < 400; x++) box(t, x, 0, 1, 200, 0xFF000000 | (uint32_t)(x * 37 % 255) << 8 | (uint32_t)(x % 251));
  tidyPicture(t, PicShape::Circle, 144);
  check("circle", t.w == t.h && alpha(t, 3, 3) == 0 && alpha(t, t.w / 2, t.h / 2) == 255);
  t = make(1, 1, 0xFF112233);
  tidyPicture(t, PicShape::Auto, 144);
  check("a single pixel is survived", t.w >= 1);
  IconImage off = make(64, 64, 0);
  box(off, 32, 0, 32, 64, 0xFF00FF00);  // visible only on the right
  finishIcon(off);
  check("off-centre icons are not stretched", off.crop.right - off.crop.left == off.crop.bottom - off.crop.top && off.crop.right <= 64.f && off.crop.left >= 0.f);

  // ------------------------------------------------ keeping copies
  encodePng(red, png);
  std::wstring kept = keepPicture(png, L"You/Tube: <logo>,1.");
  check("kept in the settings folder", !kept.empty() && fileExists(kept) && toLower(dirName(kept)) == toLower(imagesDir()), narrow(kept));
  check("with a safe name", fileName(kept).find_first_of(L"<>:\"/\\|?*,") == std::wstring::npos);
  check("rubbish is not kept", keepPicture("hello", L"x").empty());
  Pin p;
  p.icon = kept;
  same("key", IconCache::keyFor(p), L"img|" + kept);
  p.iconShape = PicShape::Circle;
  same("key says how it is fitted", IconCache::keyFor(p), L"img3|" + kept);
  check("loads through the icon path", loadIcon(IconCache::keyFor(p), 144, out) && out.w == out.h);
  Pin g;
  g.kind = Pin::Kind::Group;
  check("a group without a picture has no key", IconCache::keyFor(g).empty());

  // an unused copy goes away once it is old, a used one never does
  Config c;
  c.sanitize();
  std::wstring stale = keepPicture(png, L"stale"), used = keepPicture(png, L"used"), fresh = keepPicture(png, L"fresh");
  auto born = [&](const std::wstring& q, int daysAgo) {
    FILETIME t;
    GetSystemTimeAsFileTime(&t);
    ULARGE_INTEGER n{{t.dwLowDateTime, t.dwHighDateTime}};
    n.QuadPart -= (LONGLONG)daysAgo * 864000000000ll;
    t = {n.LowPart, n.HighPart};
    HANDLE h = CreateFileW(q.c_str(), FILE_WRITE_ATTRIBUTES, 0, nullptr, OPEN_EXISTING, 0, nullptr);
    SetFileTime(h, &t, nullptr, nullptr);
    CloseHandle(h);
  };
  auto age = [&](const std::wstring& q) {
    WIN32_FILE_ATTRIBUTE_DATA d{};
    GetFileAttributesExW(q.c_str(), GetFileExInfoStandard, &d);
    FILETIME t;
    GetSystemTimeAsFileTime(&t);
    ULARGE_INTEGER a{{t.dwLowDateTime, t.dwHighDateTime}}, b{{d.ftCreationTime.dwLowDateTime, d.ftCreationTime.dwHighDateTime}};
    return (double)(LONGLONG)(a.QuadPart - b.QuadPart) / 864000000000.0;
  };
  std::wstring later = keepPicture(png, L"later"), oldLink = joinPath(linksDir(), L"old.lnk"), usedLink = joinPath(linksDir(), L"used.lnk");
  SHCreateDirectoryExW(nullptr, linksDir().c_str(), nullptr);
  for (auto& q : {oldLink, usedLink}) createShortcut(q, expandEnv(L"%WINDIR%\\System32\\notepad.exe"), L"", L"");
  born(stale, 45);
  born(used, 45);
  born(fresh, 20);
  born(later, -300);  // a clock that was wrong
  born(oldLink, 45);
  born(usedLink, 45);
  Pin site = pinFromUrl(L"youtube.com");
  site.icon = used;
  Pin pad = pinFromPath(usedLink);
  c.profile().pins.push_back(site);
  Pin grp;
  grp.kind = Pin::Kind::Group;
  grp.children.push_back(pad);
  c.profile().pins.push_back(grp);
  sweepKept(c);
  check("nothing is swept unless the settings came from their own file", fileExists(stale) && fileExists(oldLink));
  c.intact = true;
  c.locked = true;
  sweepKept(c);
  check("nor while they could not be read", fileExists(stale));
  c.locked = false;
  sweepKept(c);
  check("unused for long is removed", !fileExists(stale) && !fileExists(oldLink));
  check("used stays", fileExists(used) && fileExists(usedLink));
  check("and counts as seen today", age(used) < 0.1 && age(usedLink) < 0.1);
  check("unused for a while stays", fileExists(fresh) && fabs(age(fresh) - 20) < 0.1);
  check("a date in the future is no reason to delete", fileExists(later));
  for (auto& q : {later, usedLink}) DeleteFileW(q.c_str());

  SiteInfo si;
  check("answers are read", parseSiteInfo("{\"image\":\"c:\\\\x.png\",\"name\":\"YouTube\"}", si) && si.image == L"c:\\x.png" && si.name == L"YouTube");
  check("broken answers are refused", !parseSiteInfo("{", si) && !parseSiteInfo("", si));

  for (auto& q : {kept, used, fresh}) DeleteFileW(q.c_str());
  gfx().shutdown();
  OleUninitialize();
  printf("\n%d failed\n", bad);
  return bad ? 1 : 0;
}
