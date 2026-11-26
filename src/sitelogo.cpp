#include "sitelogo.h"

#include <winhttp.h>

#include "json.h"
#include "picture.h"

namespace rt {

// ---------------------------------------------------------------- addresses
bool isWebAddress(const std::wstring& url) {
  std::wstring u = toLower(url.substr(0, 8));
  return u.rfind(L"http://", 0) == 0 || u.rfind(L"https://", 0) == 0;
}

static std::wstring originOf(const std::wstring& url) {  // "https://host:port"
  size_t a = url.find(L"://");
  if (a == std::wstring::npos) return {};
  size_t e = url.find_first_of(L"/?#", a + 3);
  return url.substr(0, e);
}

std::wstring siteHost(const std::wstring& url) {
  size_t a = url.find(L"://");
  std::wstring h = a == std::wstring::npos ? url : url.substr(a + 3);
  h = h.substr(0, h.find_first_of(L"/?#"));
  size_t at = h.rfind(L'@');
  if (at != std::wstring::npos) h = h.substr(at + 1);
  size_t port = h.rfind(L':');
  if (port != std::wstring::npos && h.find(L']') == std::wstring::npos) h.resize(port);
  h = toLower(h);
  return h.rfind(L"www.", 0) == 0 ? h.substr(4) : h;
}

bool privateHost(const std::wstring& hostIn) {
  std::wstring h = toLower(hostIn);
  while (!h.empty() && h.back() == L'.') h.pop_back();
  if (h.empty()) return true;
  if (h[0] == L'[') {  // an IPv6 address
    std::wstring a = h.substr(1, 4);
    return a.rfind(L"::", 0) == 0 || a.rfind(L"fe8", 0) == 0 || a.rfind(L"fe9", 0) == 0 || a.rfind(L"fea", 0) == 0 || a.rfind(L"feb", 0) == 0 || a.rfind(L"fc", 0) == 0 ||
           a.rfind(L"fd", 0) == 0;
  }
  if (h.find(L'.') == std::wstring::npos) return true;  // a name of the local network
  for (auto end : {L".local", L".localhost", L".internal", L".lan", L".home", L".corp", L".intranet", L".home.arpa"}) {
    std::wstring e = end;
    if (h.size() > e.size() && h.compare(h.size() - e.size(), e.size(), e) == 0) return true;
  }
  if (h.find_first_not_of(L"0123456789.") == std::wstring::npos || h.rfind(L"0x", 0) == 0) {  // an address in numbers
    unsigned v[4] = {};
    int n = 0, used = 0;
    if (swscanf(h.c_str(), L"%u.%u.%u.%u%n", &v[0], &v[1], &v[2], &v[3], &used) >= 4) n = 4;
    if (n != 4 || (size_t)used != h.size() || v[0] > 255 || v[1] > 255 || v[2] > 255 || v[3] > 255) return true;  // written in an odd way
    return v[0] == 0 || v[0] == 10 || v[0] == 127 || v[0] >= 224 || (v[0] == 169 && v[1] == 254) || (v[0] == 172 && v[1] >= 16 && v[1] <= 31) || (v[0] == 192 && v[1] == 168) ||
           (v[0] == 100 && v[1] >= 64 && v[1] <= 127);
  }
  return false;
}

std::wstring resolveUrl(const std::wstring& base, const std::wstring& ref) {
  std::wstring r = trim(ref);
  if (r.empty() || r.size() > 4000) return {};
  if (toLower(r.substr(0, 5)) == L"data:") return r;
  if (r.rfind(L"//", 0) == 0) return base.substr(0, base.find(L':') + 1) + r;
  if (isWebAddress(r)) return r;
  size_t colon = r.find(L':');
  if (colon != std::wstring::npos && colon < r.find_first_of(L"/?#")) return {};  // some other scheme
  std::wstring origin = originOf(base);
  if (origin.empty()) return {};
  if (r[0] == L'/') return origin + r;
  std::wstring path = base.substr(origin.size());
  path = path.substr(0, path.find_first_of(L"?#"));
  size_t slash = path.rfind(L'/');
  path = slash == std::wstring::npos ? L"/" : path.substr(0, slash + 1);
  while (true) {
    if (r.rfind(L"./", 0) == 0) {
      r = r.substr(2);
    } else if (r.rfind(L"../", 0) == 0) {
      r = r.substr(3);
      if (path.size() > 1) {
        size_t up = path.rfind(L'/', path.size() - 2);
        path = up == std::wstring::npos ? L"/" : path.substr(0, up + 1);
      }
    } else {
      break;
    }
  }
  return origin + path + r;
}

// ---------------------------------------------------------------- reading a page
namespace {
std::string lower(std::string s) {
  for (auto& c : s)
    if (c >= 'A' && c <= 'Z') c = (char)(c + 32);
  return s;
}

void putUtf8(std::string& o, unsigned long c) {
  if (c < 0x80) {
    o += (char)c;
  } else if (c < 0x800) {
    o += (char)(0xC0 | (c >> 6));
    o += (char)(0x80 | (c & 63));
  } else if (c < 0x10000) {
    o += (char)(0xE0 | (c >> 12));
    o += (char)(0x80 | ((c >> 6) & 63));
    o += (char)(0x80 | (c & 63));
  } else if (c < 0x110000) {
    o += (char)(0xF0 | (c >> 18));
    o += (char)(0x80 | ((c >> 12) & 63));
    o += (char)(0x80 | ((c >> 6) & 63));
    o += (char)(0x80 | (c & 63));
  }
}

std::string decodeEntities(const std::string& s) {
  std::string o;
  for (size_t i = 0; i < s.size(); i++) {
    size_t e = std::string::npos;
    if (s[i] == '&')
      for (size_t k = i + 1; k < s.size() && k <= i + 10; k++)
        if (s[k] == ';') {
          e = k;
          break;
        }
    if (e == std::string::npos) {
      o += s[i];
      continue;
    }
    std::string n = s.substr(i + 1, e - i - 1);
    if (n == "amp") o += '&';
    else if (n == "lt") o += '<';
    else if (n == "gt") o += '>';
    else if (n == "quot") o += '"';
    else if (n == "apos") o += '\'';
    else if (n == "nbsp") o += ' ';
    else if (n == "ndash") o += "-";
    else if (n == "mdash") o += "-";
    else if (n.size() > 1 && n[0] == '#') {
      bool hex = n[1] == 'x' || n[1] == 'X';
      unsigned long c = strtoul(n.c_str() + (hex ? 2 : 1), nullptr, hex ? 16 : 10);
      putUtf8(o, c ? c : ' ');
    } else {
      o += s[i];
      continue;
    }
    i = e;
  }
  return o;
}

using Attrs = std::vector<std::pair<std::string, std::string>>;

std::string attr(const Attrs& a, const char* name) {
  for (auto& kv : a)
    if (kv.first == name) return kv.second;
  return {};
}

// Reads the attributes of a tag; `i` points just after the tag's name and ends after its '>'.
Attrs readAttrs(const std::string& h, size_t& i) {
  Attrs out;
  auto space = [](char c) { return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\f' || c == '/'; };
  while (i < h.size() && h[i] != '>') {
    while (i < h.size() && space(h[i])) i++;
    if (i >= h.size() || h[i] == '>') break;
    size_t k = i;
    while (i < h.size() && h[i] != '=' && h[i] != '>' && !space(h[i])) i++;
    std::string name = lower(h.substr(k, i - k)), val;
    while (i < h.size() && (h[i] == ' ' || h[i] == '\n' || h[i] == '\t' || h[i] == '\r')) i++;
    if (i < h.size() && h[i] == '=') {
      i++;
      while (i < h.size() && (h[i] == ' ' || h[i] == '\n' || h[i] == '\t' || h[i] == '\r')) i++;
      if (i < h.size() && (h[i] == '"' || h[i] == '\'')) {
        char q = h[i++];
        size_t v = i;
        while (i < h.size() && h[i] != q) i++;
        val = h.substr(v, i - v);
        if (i < h.size()) i++;
      } else {
        size_t v = i;
        while (i < h.size() && h[i] != '>' && h[i] != ' ' && h[i] != '\n' && h[i] != '\t' && h[i] != '\r') i++;
        val = h.substr(v, i - v);
      }
    }
    if (!name.empty() && out.size() < 64) out.emplace_back(std::move(name), decodeEntities(val));
    if (i == k) i++;  // never stand still on something malformed
  }
  if (i < h.size()) i++;
  return out;
}

int sizeFrom(const std::string& sizes) {  // "16x16 32x32" -> 32, "any" -> 512
  int best = 0;
  std::string s = lower(sizes);
  if (s.find("any") != std::string::npos) return 512;
  for (size_t i = 0; i < s.size(); i++) {
    if (s[i] < '0' || s[i] > '9') continue;
    int v = atoi(s.c_str() + i);
    while (i < s.size() && s[i] >= '0' && s[i] <= '9') i++;
    if (i < s.size() && s[i] == 'x') best = std::max(best, v);
  }
  return best;
}

int sizeFromName(const std::string& url) {  // ".../favicon_144x144.png", ".../icon-192.png"
  size_t slash = url.rfind('/');
  std::string f = lower(slash == std::string::npos ? url : url.substr(slash + 1));
  int best = sizeFrom(f);
  if (best) return best <= 1024 ? best : 0;
  for (int v : {512, 384, 310, 256, 228, 196, 192, 180, 167, 152, 150, 144, 128, 120, 114, 96, 76, 72, 64, 57, 48, 32, 16}) {
    std::string d = std::to_string(v);
    size_t at = f.find(d);
    if (at == std::string::npos) continue;
    bool cleanL = at == 0 || f[at - 1] < '0' || f[at - 1] > '9';
    bool cleanR = at + d.size() >= f.size() || f[at + d.size()] < '0' || f[at + d.size()] > '9';
    if (cleanL && cleanR) return v;
  }
  return 0;
}

UINT codePageOf(std::string cs) {
  cs = lower(cs);
  auto has = [&](const char* n) { return cs.find(n) != std::string::npos; };
  if (has("windows-125")) return (UINT)atoi(cs.c_str() + cs.find("windows-") + 8);
  if (has("cp125")) return (UINT)atoi(cs.c_str() + cs.find("cp") + 2);
  if (has("iso-8859-")) {
    switch (atoi(cs.c_str() + cs.find("iso-8859-") + 9)) {
      case 2: return 28592;
      case 5: return 28595;
      case 7: return 28597;
      case 9: return 1254;
      default: return 1252;
    }
  }
  if (has("koi8-r")) return 20866;
  if (has("shift_jis") || has("shift-jis")) return 932;
  if (has("euc-kr")) return 949;
  if (has("gb2312") || has("gbk") || has("gb18030")) return 936;
  return CP_UTF8;
}

std::wstring toWide(const std::string& s, UINT cp) {
  int n = MultiByteToWideChar(cp, 0, s.c_str(), (int)s.size(), nullptr, 0);
  std::wstring w((size_t)std::max(0, n), 0);
  if (n > 0) MultiByteToWideChar(cp, 0, s.c_str(), (int)s.size(), w.data(), n);
  std::wstring o;
  for (wchar_t c : w) {  // one tidy line
    bool sp = c < 32 || c == L' ' || c == 0xA0;
    if (sp && (o.empty() || o.back() == L' ')) continue;
    o += sp ? L' ' : c;
  }
  return trim(o);
}

// "Home - Example" -> "Example". Prefers the part that looks like the address.
std::wstring shortTitle(const std::wstring& title, const std::wstring& host) {
  std::wstring label = host;
  // the part of the host a person would recognise: "bbc" in "news.bbc.co.uk"
  std::vector<std::wstring> parts;
  size_t at = 0;
  while (at <= host.size()) {
    size_t d = host.find(L'.', at);
    parts.push_back(host.substr(at, d == std::wstring::npos ? std::wstring::npos : d - at));
    if (d == std::wstring::npos) break;
    at = d + 1;
  }
  if (parts.size() >= 2) {
    size_t i = parts.size() - 2;
    if (i > 0 && parts.back().size() == 2 && parts[i].size() <= 3) i--;
    label = parts[i];
  }
  std::vector<std::wstring> seg;
  std::wstring cur;
  for (size_t i = 0; i < title.size(); i++) {
    wchar_t c = title[i];
    bool bar = c == L'|' || c == 0x00B7 || c == 0x2022 || c == 0x00BB;
    bool dash = (c == L'-' || c == 0x2013 || c == 0x2014 || c == L':') && i + 1 < title.size() && title[i + 1] == L' ' && (c == L':' || (i > 0 && title[i - 1] == L' '));
    if (bar || dash) {
      if (!trim(cur).empty()) seg.push_back(trim(cur));
      cur.clear();
    } else {
      cur += c;
    }
  }
  if (!trim(cur).empty()) seg.push_back(trim(cur));
  auto squash = [](const std::wstring& s) {
    std::wstring o;
    for (wchar_t c : toLower(s))
      if (iswalnum(c)) o += c;
    return o;
  };
  std::wstring key = squash(label);
  std::wstring best;
  for (auto& s : seg) {
    std::wstring q = squash(s);
    bool match = !key.empty() && !q.empty() && (q.find(key) != std::wstring::npos || (q.size() > 2 && key.find(q) != std::wstring::npos));
    if (match && (best.empty() || s.size() < best.size())) best = s;
  }
  if (best.empty() && seg.size() == 1) best = seg[0];
  if (best.empty() || best.size() > 32) return title.size() <= 28 ? title : std::wstring();
  return best;
}
}  // namespace

PageFacts readPage(const std::string& html, const std::wstring& pageUrl, const std::string& contentType) {
  PageFacts out;
  std::wstring base = pageUrl;
  std::string site, app, title;
  size_t cs = lower(contentType).find("charset=");
  UINT cp = cs == std::string::npos ? CP_UTF8 : codePageOf(contentType.substr(cs + 8));  // the page itself may say otherwise
  auto link = [&](const std::string& href, int size, int bonus) {
    std::wstring u = resolveUrl(base, widen(href));
    if (u.empty() || out.links.size() > 60) return;
    LogoLink l;
    l.url = u;
    l.size = size;
    l.score = bonus;
    out.links.push_back(std::move(l));
  };
  for (size_t i = 0; i + 1 < html.size(); i++) {
    if (html[i] != '<') continue;
    if (html.compare(i, 4, "<!--") == 0) {
      size_t e = html.find("-->", i + 4);
      if (e == std::string::npos) break;
      i = e + 2;
      continue;
    }
    size_t n = i + 1;
    while (n < html.size() && ((html[n] >= 'a' && html[n] <= 'z') || (html[n] >= 'A' && html[n] <= 'Z') || html[n] == '/')) n++;
    std::string tag = lower(html.substr(i + 1, std::min<size_t>(n - i - 1, 12)));
    if (tag == "/head" || tag == "body") break;
    if (tag == "script" || tag == "style" || tag == "noscript") {
      // Their text is not markup. Skip to the closing tag.
      std::string close = "</" + tag;
      size_t e = n;
      while (e < html.size()) {
        e = html.find("</", e);
        if (e == std::string::npos) break;
        if (lower(html.substr(e, close.size())) == close) break;
        e += 2;
      }
      if (e == std::string::npos || e >= html.size()) break;
      i = e;
      continue;
    }
    if (tag == "title") {
      size_t e = n;
      readAttrs(html, e);
      size_t z = html.find('<', e);
      if (title.empty() && z != std::string::npos && z - e < 600) title = decodeEntities(html.substr(e, z - e));
      i = z == std::string::npos ? html.size() : z - 1;
      continue;
    }
    if (tag != "link" && tag != "meta" && tag != "base") {
      i = std::max(i, n - 1);
      continue;
    }
    size_t e = n;
    Attrs a = readAttrs(html, e);
    i = e - 1;
    if (tag == "base") {
      std::wstring b = resolveUrl(base, widen(attr(a, "href")));
      if (!b.empty()) base = b;
    } else if (tag == "meta") {
      std::string prop = lower(attr(a, "property")), name = lower(attr(a, "name")), val = attr(a, "content");
      std::string cs = attr(a, "charset");
      if (!cs.empty()) cp = codePageOf(cs);
      else if (lower(attr(a, "http-equiv")) == "content-type" && lower(val).find("charset=") != std::string::npos) cp = codePageOf(val.substr(lower(val).find("charset=") + 8));
      if (prop == "og:site_name" && site.empty()) site = val;
      if ((name == "application-name" || name == "apple-mobile-web-app-title") && app.empty()) app = val;
    } else {
      std::string rel = " " + lower(attr(a, "rel")) + " ", href = attr(a, "href"), type = lower(attr(a, "type"));
      if (href.empty()) continue;
      int size = sizeFrom(attr(a, "sizes"));
      if (!size) size = sizeFromName(href);
      bool svg = type.find("svg") != std::string::npos || lower(href).find(".svg") != std::string::npos;
      if (rel.find(" apple-touch-icon") != std::string::npos) link(href, size ? size : 152, 14);
      else if (rel.find(" fluid-icon ") != std::string::npos) link(href, size ? size : 256, 4);
      else if (rel.find(" mask-icon ") != std::string::npos) continue;  // a one-colour silhouette
      else if (rel.find(" icon ") != std::string::npos) link(href, svg ? 200 : size ? size : 40, svg ? -20 : 10);
      else if (rel.find(" manifest ") != std::string::npos && out.manifest.empty()) out.manifest = resolveUrl(base, widen(href));
    }
  }
  std::wstring host = siteHost(pageUrl);
  auto fits = [](const std::wstring& s) { return !s.empty() && s.size() <= 32; };
  std::wstring s = toWide(site, cp), p = toWide(app, cp), t = toWide(title, cp);
  if (fits(s)) out.name = s;
  else if (fits(p)) out.name = p;
  else if (!t.empty()) out.name = shortTitle(t, host);
  return out;
}

void readManifest(const std::string& json, const std::wstring& manifestUrl, PageFacts& facts) {
  Json j;
  if (!Json::parse(json, j) || !j.isObj()) return;
  if (auto ic = j.find("icons"); ic && ic->isArr()) {
    for (auto& e : ic->a) {
      if (!e.isObj() || facts.links.size() > 80) continue;
      LogoLink l;
      l.url = resolveUrl(manifestUrl, widen(e.str("src")));
      l.size = sizeFrom(e.str("sizes"));
      if (!l.size) l.size = sizeFromName(e.str("src"));
      std::string purpose = lower(e.str("purpose"));
      bool svg = lower(e.str("type")).find("svg") != std::string::npos;
      l.score = svg ? -20 : 8;
      if (svg) l.size = 200;
      if (purpose.find("monochrome") != std::string::npos) continue;
      if (purpose.find("maskable") != std::string::npos && purpose.find("any") == std::string::npos) l.score -= 12;
      if (!l.url.empty()) facts.links.push_back(std::move(l));
    }
  }
  if (facts.name.empty()) {
    std::string n = j.str("short_name");
    if (n.empty()) n = j.str("name");
    if (!n.empty() && n.size() <= 40) facts.name = trim(widen(n));
  }
}

// Big enough first, then the closest to a comfortable size.
void rankLinks(std::vector<LogoLink>& v) {
  std::vector<LogoLink> out;
  for (auto& l : v) {
    bool dup = false;
    for (auto& o : out)
      if (o.url == l.url) dup = true;
    if (dup) continue;
    int s = l.size ? l.size : 40;
    int fit = s >= 128 ? 260 - std::min(120, abs(s - 192) / 6) : s >= 96 ? 190 + (s - 96) / 2 : s;
    l.score += fit;
    out.push_back(l);
  }
  std::stable_sort(out.begin(), out.end(), [](const LogoLink& a, const LogoLink& b) { return a.score > b.score; });
  v = std::move(out);
}

// ---------------------------------------------------------------- network
namespace {
struct Http {
  decltype(&WinHttpOpen) open = nullptr;
  decltype(&WinHttpSetTimeouts) timeouts = nullptr;
  decltype(&WinHttpSetOption) setOption = nullptr;
  decltype(&WinHttpQueryOption) queryOption = nullptr;
  decltype(&WinHttpCrackUrl) crack = nullptr;
  decltype(&WinHttpConnect) connect = nullptr;
  decltype(&WinHttpOpenRequest) request = nullptr;
  decltype(&WinHttpSendRequest) send = nullptr;
  decltype(&WinHttpReceiveResponse) receive = nullptr;
  decltype(&WinHttpQueryHeaders) headers = nullptr;
  decltype(&WinHttpReadData) read = nullptr;
  decltype(&WinHttpCloseHandle) close = nullptr;
  HINTERNET session = nullptr;
  bool publicOnly = true;  // a page on the internet must not send us to this PC or the local network

  bool start() {
    HMODULE m = LoadLibraryExW(L"winhttp.dll", nullptr, LOAD_LIBRARY_SEARCH_SYSTEM32);
    if (!m) return false;
    auto get = [&](auto& f, const char* n) {
      f = (std::remove_reference_t<decltype(f)>)(void*)GetProcAddress(m, n);
      return f != nullptr;
    };
    if (!get(open, "WinHttpOpen") || !get(timeouts, "WinHttpSetTimeouts") || !get(setOption, "WinHttpSetOption") || !get(queryOption, "WinHttpQueryOption") ||
        !get(crack, "WinHttpCrackUrl") || !get(connect, "WinHttpConnect") || !get(request, "WinHttpOpenRequest") || !get(send, "WinHttpSendRequest") ||
        !get(receive, "WinHttpReceiveResponse") || !get(headers, "WinHttpQueryHeaders") || !get(read, "WinHttpReadData") || !get(close, "WinHttpCloseHandle"))
      return false;
    session = open(L"Mozilla/5.0 (Windows NT 10.0; Win64; x64)", 4 /* automatic proxy */, nullptr, nullptr, 0);
    if (!session) return false;
    timeouts(session, 5000, 5000, 5000, 7000);
    DWORD all = 3;
    setOption(session, 118 /* decompression */, &all, sizeof all);
    DWORD h2 = 1;
    setOption(session, 133 /* allow HTTP/2 */, &h2, sizeof h2);
    DWORD never = WINHTTP_OPTION_REDIRECT_POLICY_NEVER;  // every hop is looked at first
    setOption(session, WINHTTP_OPTION_REDIRECT_POLICY, &never, sizeof never);
    return true;
  }
};

struct Reply {
  DWORD status = 0;
  std::wstring url;
  std::string type, body;
};

// Reads at most `limit` bytes. With `headOnly` it stops once the document's head is complete.
bool fetchOnce(Http& h, const std::wstring& url, size_t limit, const wchar_t* accept, bool headOnly, Reply& out, std::wstring& moved) {
  out = Reply{};
  moved.clear();
  if (!isWebAddress(url) || url.size() > 4000) return false;
  std::wstring host(300, 0), path(4200, 0), extra(4200, 0);
  URL_COMPONENTS c{};
  c.dwStructSize = sizeof c;
  c.lpszHostName = host.data();
  c.dwHostNameLength = 299;
  c.lpszUrlPath = path.data();
  c.dwUrlPathLength = 4199;
  c.lpszExtraInfo = extra.data();
  c.dwExtraInfoLength = 4199;
  if (!h.crack(url.c_str(), 0, 0, &c)) return false;
  std::wstring obj = path.c_str();
  std::wstring ex = extra.c_str();
  obj += ex.substr(0, ex.find(L'#'));
  if (obj.empty()) obj = L"/";
  HINTERNET con = h.connect(h.session, host.c_str(), c.nPort, 0);
  if (!con) return false;
  const wchar_t* types[] = {accept, nullptr};
  HINTERNET req = h.request(con, L"GET", obj.c_str(), nullptr, nullptr, types, c.nScheme == INTERNET_SCHEME_HTTPS ? WINHTTP_FLAG_SECURE : 0);
  bool ok = false;
  if (req) {
    DWORD noLogon = WINHTTP_AUTOLOGON_SECURITY_LEVEL_HIGH;  // never signs in as the person
    h.setOption(req, WINHTTP_OPTION_AUTOLOGON_POLICY, &noLogon, sizeof noLogon);
    const wchar_t* hdr = L"Accept-Language: en;q=0.9, *;q=0.5\r\n";
    if (h.send(req, hdr, (DWORD)-1, nullptr, 0, 0, 0) && h.receive(req, nullptr)) {
      DWORD cb = sizeof out.status;
      h.headers(req, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER, nullptr, &out.status, &cb, nullptr);
      wchar_t buf[4200];
      cb = sizeof buf;
      if (h.headers(req, WINHTTP_QUERY_CONTENT_TYPE, nullptr, buf, &cb, nullptr)) out.type = lower(narrow(buf));
      out.url = url;
      cb = sizeof buf;
      bool elsewhere = out.status == 301 || out.status == 302 || out.status == 303 || out.status == 307 || out.status == 308;
      if (elsewhere && h.headers(req, WINHTTP_QUERY_LOCATION, nullptr, buf, &cb, nullptr)) moved = resolveUrl(url, buf);
      size_t seen = 0;
      ok = !elsewhere;
      while (ok && out.body.size() < limit) {
        char part[16384];
        DWORD got = 0;
        if (!h.read(req, part, sizeof part, &got)) {
          ok = false;
          break;
        }
        if (!got) break;
        out.body.append(part, got);
        if (headOnly) {
          std::string tail = lower(out.body.substr(seen > 16 ? seen - 16 : 0));
          if (tail.find("</head") != std::string::npos || tail.find("<body") != std::string::npos) break;
          seen = out.body.size();
        }
      }
      if (!headOnly && out.body.size() >= limit) ok = false;  // far bigger than any logo
    }
    h.close(req);
  }
  h.close(con);
  return ok && out.status >= 200 && out.status < 300;
}

bool fetch(Http& h, std::wstring url, size_t limit, const wchar_t* accept, bool headOnly, Reply& out) {
  for (int hop = 0; hop < 7; hop++) {
    if (h.publicOnly && privateHost(siteHost(url))) return false;
    std::wstring moved;
    bool ok = fetchOnce(h, url, limit, accept, headOnly, out, moved);
    if (moved.empty()) return ok;
    if (toLower(url.substr(0, 6)) == L"https:" && toLower(moved.substr(0, 6)) != L"https:") return false;  // never from secure to plain
    url = moved;
  }
  return false;
}

bool dataUri(const std::wstring& url, std::string& bytes) {
  size_t comma = url.find(L',');
  if (comma == std::wstring::npos) return false;
  std::string meta = lower(narrow(url.substr(0, comma))), body = narrow(url.substr(comma + 1));
  std::string plain;
  for (size_t i = 0; i < body.size(); i++) {
    if (body[i] == '%' && i + 2 < body.size()) {
      plain += (char)strtoul(body.substr(i + 1, 2).c_str(), nullptr, 16);
      i += 2;
    } else {
      plain += body[i];
    }
  }
  if (meta.find(";base64") != std::string::npos) return unbase64(plain, bytes);
  bytes = plain;
  return true;
}

// A picture with a single colour is a placeholder, not a logo.
bool worthwhile(const IconImage& m) {
  if (m.w < 8 || m.h < 8) return false;
  int lo[4] = {255, 255, 255, 255}, hi[4] = {0, 0, 0, 0};
  for (size_t i = 0; i + 3 < m.px.size(); i += 4)
    for (int k = 0; k < 4; k++) {
      lo[k] = std::min<int>(lo[k], m.px[i + k]);
      hi[k] = std::max<int>(hi[k], m.px[i + k]);
    }
  for (int k = 0; k < 4; k++)
    if (hi[k] - lo[k] > 24) return true;
  return false;
}

// Some sites send a first-time visitor to a consent or sign-in page, which has somebody else's logo.
bool detour(const std::wstring& asked, const std::wstring& landed) {
  std::wstring x = siteHost(asked), y = siteHost(landed);
  if (x == y) return false;
  for (auto p : {L"consent.", L"login.", L"accounts.", L"account.", L"auth.", L"signin.", L"sso.", L"id."})
    if (y.rfind(p, 0) == 0 && x.rfind(p, 0) != 0) return true;
  return false;
}

SiteInfo lookUp(const std::wstring& url) {
  SiteInfo info;
  Http h;
  if (!h.start()) return info;
  h.publicOnly = !privateHost(siteHost(url));
  double end = nowSec() + 18.0;
  PageFacts facts;
  Reply page;
  std::vector<std::wstring> origins;  // where to try the well-known names
  auto addOrigin = [&](const std::wstring& u) {
    std::wstring o = originOf(u);
    if (!o.empty() && std::find(origins.begin(), origins.end(), o) == origins.end()) origins.push_back(o);
  };
  bool got = fetch(h, url, 3 * 1024 * 1024, L"text/html,application/xhtml+xml,*/*;q=0.8", true, page);
  logf("logo: page %lu, %d bytes", page.status, (int)page.body.size());
  bool same = got && !detour(url, page.url);
  if (same) {
    facts = readPage(page.body, page.url, page.type);
    if (!facts.manifest.empty() && isWebAddress(facts.manifest)) {
      Reply m;
      if (fetch(h, facts.manifest, 512 * 1024, L"application/manifest+json,application/json,*/*;q=0.5", false, m)) readManifest(m.body, m.url, facts);
    }
    addOrigin(page.url);
  }
  addOrigin(url);
  // A bare domain often only answers on "www.".
  std::wstring o0 = originOf(url);
  size_t sl = o0.find(L"://");
  if (sl != std::wstring::npos && o0.compare(sl + 3, 4, L"www.") != 0) {
    std::wstring bare = o0.substr(sl + 3);
    if (std::count(bare.begin(), bare.end(), L'.') == 1 && !same) addOrigin(o0.substr(0, sl + 3) + L"www." + bare + L"/");
  }
  if (!same && sl != std::wstring::npos && url.size() > o0.size() + 1 && nowSec() < end) {
    // The exact page sent us elsewhere: its front page may still say who it is.
    Reply front;
    if (fetch(h, o0 + L"/", 3 * 1024 * 1024, L"text/html,application/xhtml+xml,*/*;q=0.8", true, front) && !detour(url, front.url)) facts = readPage(front.body, front.url, front.type);
  }
  for (auto& o : origins) {
    LogoLink a, b;
    a.url = o + L"/apple-touch-icon.png";
    a.size = 152;
    a.score = -60;
    b.url = o + L"/favicon.ico";
    b.size = 48;
    b.score = -5;
    facts.links.push_back(a);
    facts.links.push_back(b);
  }
  rankLinks(facts.links);
  info.name = facts.name;

  std::string best;
  IconImage bestImg;
  int tries = 0;
  for (auto& l : facts.links) {
    if (tries >= 9 || nowSec() > end) break;
    if (bestImg.w >= 96) break;
    std::string bytes;
    if (l.url.size() > 5 && toLower(l.url.substr(0, 5)) == L"data:") {
      if (!dataUri(l.url, bytes)) continue;
    } else {
      tries++;
      Reply r;
      if (!fetch(h, l.url, 4 * 1024 * 1024, L"image/png,image/*;q=0.9,*/*;q=0.5", false, r)) continue;
      if (r.type.find("text/html") != std::string::npos) continue;
      bytes = std::move(r.body);
    }
    IconImage img;
    if (!decodePicture(bytes, 512, img, true) || !worthwhile(img)) continue;
    int side = std::max(img.w, img.h);
    logf("logo: %dx%d from %s", img.w, img.h, narrow(l.url.substr(0, 120)).c_str());
    if (side > std::max(bestImg.w, bestImg.h)) {
      best = std::move(bytes);
      bestImg = std::move(img);
    }
  }
  if (!best.empty()) info.image = keepPicture(best, siteHost(url));
  return info;
}

SiteInfo download(const std::wstring& url) {
  SiteInfo info;
  Http h;
  Reply r;
  h.publicOnly = !privateHost(siteHost(url));
  if (!h.start() || !fetch(h, url, 24 * 1024 * 1024, L"image/png,image/*;q=0.9,*/*;q=0.5", false, r)) return info;
  std::wstring name = fileStem(url.substr(0, url.find_first_of(L"?#")));
  info.image = keepPicture(r.body, name.empty() ? siteHost(url) : name);
  return info;
}
}  // namespace

// ---------------------------------------------------------------- the helper process
bool parseSiteInfo(const std::string& json, SiteInfo& out) {
  Json j;
  if (!Json::parse(json, j) || !j.isObj()) return false;
  out.image = widen(j.str("image"));
  out.name = widen(j.str("name"));
  return true;
}

int runLogoHelper(const std::wstring& requestFile) {
  std::string text;
  if (!readFile(requestFile, text)) return 1;
  std::vector<std::string> line;
  size_t at = 0;
  while (at < text.size()) {
    size_t nl = text.find('\n', at);
    if (nl == std::string::npos) nl = text.size();
    line.push_back(narrow(trim(widen(text.substr(at, nl - at)))));
    at = nl + 1;
  }
  if (line.size() < 3) return 1;
  std::wstring url = widen(line[0]);
  if (!isWebAddress(url)) return 2;
  SiteInfo info = line[2] == "image" ? download(url) : lookUp(url);
  Json j = Json::object();
  j.set("image", narrow(info.image));
  j.set("name", narrow(info.name));
  return writeFileAtomic(widen(line[1]), j.dump()) ? 0 : 3;
}

bool askSite(const std::wstring& url, bool isImage, SiteInfo& out) {
  if (!isWebAddress(url) || url.find(L'\n') != std::wstring::npos) return false;
  std::wstring stem = joinPath(cacheDir(), L"logo-" + std::to_wstring(GetCurrentProcessId()) + L"-" + widen(newId()).substr(0, 8));
  std::wstring req = stem + L".req", ans = stem + L".json";
  bool ok = false;
  if (writeFileAtomic(req, narrow(url) + "\n" + narrow(ans) + "\n" + (isImage ? "image" : "site") + "\n")) {
    if (HANDLE h = startHelper(L"--logo-worker \"" + req + L"\"")) {
      if (WaitForSingleObject(h, 32000) != WAIT_OBJECT_0) TerminateProcess(h, 1);
      CloseHandle(h);
      std::string text;
      ok = readFile(ans, text) && parseSiteInfo(text, out);
    }
  }
  DeleteFileW(req.c_str());
  DeleteFileW(ans.c_str());
  return ok;
}

}  // namespace rt
