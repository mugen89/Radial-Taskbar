#include "update.h"

#include <process.h>
#include <winhttp.h>

#include <cwctype>
#include <functional>

#include "json.h"

namespace rt {

struct Updater::Shared {
  mutable SRWLOCK lock = SRWLOCK_INIT;
  Now now;
  std::wstring asset;  // where the setup is
  bool busy = false;
  HWND hwnd = nullptr;
  UINT msg = 0;
  void tell() {  // under the lock
    if (hwnd) PostMessageW(hwnd, msg, 0, 0);
  }
};

namespace {

// WinHTTP is loaded when it is needed, like for the logos of websites.
struct Web {
  decltype(&WinHttpOpen) open = nullptr;
  decltype(&WinHttpSetTimeouts) timeouts = nullptr;
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

  bool start() {
    HMODULE m = LoadLibraryExW(L"winhttp.dll", nullptr, LOAD_LIBRARY_SEARCH_SYSTEM32);
    if (!m) return false;
    auto get = [&](auto& f, const char* n) {
      f = (std::remove_reference_t<decltype(f)>)(void*)GetProcAddress(m, n);
      return f != nullptr;
    };
    if (!get(open, "WinHttpOpen") || !get(timeouts, "WinHttpSetTimeouts") || !get(queryOption, "WinHttpQueryOption") || !get(crack, "WinHttpCrackUrl") ||
        !get(connect, "WinHttpConnect") || !get(request, "WinHttpOpenRequest") || !get(send, "WinHttpSendRequest") || !get(receive, "WinHttpReceiveResponse") ||
        !get(headers, "WinHttpQueryHeaders") || !get(read, "WinHttpReadData") || !get(close, "WinHttpCloseHandle"))
      return false;
    std::wstring agent = L"RadialTaskbar/" + widen(RT_VERSION_STR);  // nothing about the person or the PC
    session = open(agent.c_str(), 4 /* automatic proxy */, nullptr, nullptr, 0);
    if (!session) return false;
    timeouts(session, 10000, 10000, 15000, 30000);
    return true;
  }
  ~Web() {
    if (session) close(session);
  }
};

bool githubHost(const std::wstring& host) {
  std::wstring h = toLower(host);
  auto under = [&](const std::wstring& d) { return h == d || (h.size() > d.size() && h.compare(h.size() - d.size(), d.size(), d) == 0 && h[h.size() - d.size() - 1] == L'.'); };
  return under(L"github.com") || under(L"githubusercontent.com");
}

bool parts(Web& w, const std::wstring& url, std::wstring& host, std::wstring& path, INTERNET_PORT& port, bool& secure) {
  std::wstring hb(300, 0), pb(4200, 0), xb(4200, 0);
  URL_COMPONENTS c{};
  c.dwStructSize = sizeof c;
  c.lpszHostName = hb.data();
  c.dwHostNameLength = 299;
  c.lpszUrlPath = pb.data();
  c.dwUrlPathLength = 4199;
  c.lpszExtraInfo = xb.data();
  c.dwExtraInfoLength = 4199;
  if (url.size() > 4000 || !w.crack(url.c_str(), 0, 0, &c)) return false;
  host = hb.c_str();
  path = std::wstring(pb.c_str()) + xb.c_str();
  if (path.empty()) path = L"/";
  port = c.nPort;
  secure = c.nScheme == INTERNET_SCHEME_HTTPS;
  return true;
}

// One GET from GitHub over https. Redirects are followed, and where they end must still be GitHub. `take` receives the
// body piece by piece with the length announced (0 when unknown); returning false stops.
bool get(Web& w, const std::wstring& url, const wchar_t* extra, uint64_t limit, const std::function<bool(const char*, size_t, uint64_t)>& take, DWORD& status,
         std::wstring& err) {
  status = 0;
  std::wstring host, path;
  INTERNET_PORT port = 0;
  bool secure = false;
  if (!parts(w, url, host, path, port, secure) || !secure || !githubHost(host)) {
    err = L"That address is not one this program trusts.";
    return false;
  }
  HINTERNET con = w.connect(w.session, host.c_str(), port, 0);
  if (!con) {
    err = L"No connection. Is this PC online?";
    return false;
  }
  bool ok = false;
  HINTERNET req = w.request(con, L"GET", path.c_str(), nullptr, WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES, WINHTTP_FLAG_SECURE);
  if (req && w.send(req, extra, (DWORD)-1, nullptr, 0, 0, 0) && w.receive(req, nullptr)) {
    DWORD cb = sizeof status;
    w.headers(req, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER, nullptr, &status, &cb, nullptr);
    wchar_t final_[4200];
    DWORD len = sizeof final_;
    std::wstring fh, fp;
    INTERNET_PORT fport = 0;
    bool fs = false;
    if (w.queryOption(req, WINHTTP_OPTION_URL, final_, &len) && (!parts(w, final_, fh, fp, fport, fs) || !fs || !githubHost(fh))) {
      err = L"The download was sent somewhere this program does not trust.";
    } else if (status != 200) {
      err = L"The update server answered " + std::to_wstring(status) + L".";
    } else {
      wchar_t lenText[64];
      DWORD lb = sizeof lenText;
      uint64_t total = w.headers(req, WINHTTP_QUERY_CONTENT_LENGTH, nullptr, lenText, &lb, nullptr) ? _wcstoui64(lenText, nullptr, 10) : 0;
      if (total > limit) {
        err = L"That file is far bigger than it should be.";
      } else {
        static thread_local char buf[65536];
        uint64_t seen = 0;
        ok = true;
        for (;;) {
          DWORD got = 0;
          if (!w.read(req, buf, sizeof buf, &got)) {
            ok = false;
            err = L"The connection broke off. Try again.";
            break;
          }
          if (!got) break;
          seen += got;
          if (seen > limit || !take(buf, got, total)) {
            ok = false;
            if (err.empty()) err = seen > limit ? L"That file is far bigger than it should be." : L"Stopped.";
            break;
          }
        }
      }
    }
  } else {
    err = L"The update server could not be reached. Is this PC online?";
  }
  if (req) w.close(req);
  w.close(con);
  return ok;
}

std::wstring tempFolder() {
  wchar_t t[MAX_PATH + 2];
  DWORD n = GetTempPathW(MAX_PATH + 1, t);
  return n && n <= MAX_PATH ? std::wstring(t, n) : joinPath(dataDir(), L"temp");
}

std::wstring strip(std::wstring s) {
  for (const wchar_t* m : {L"**", L"__", L"`"})
    for (size_t at; (at = s.find(m)) != std::wstring::npos;) s.erase(at, wcslen(m));
  return s;
}

}  // namespace

std::wstring Updater::current = widen(RT_VERSION_STR);

Updater::Updater() : s_(std::make_shared<Shared>()) {}

Updater::~Updater() {
  AcquireSRWLockExclusive(&s_->lock);
  s_->hwnd = nullptr;  // a worker still busy finishes on its own
  ReleaseSRWLockExclusive(&s_->lock);
}

void Updater::notify(HWND h, UINT msg) {
  AcquireSRWLockExclusive(&s_->lock);
  s_->hwnd = h;
  s_->msg = msg;
  ReleaseSRWLockExclusive(&s_->lock);
}

Updater::Now Updater::now() const {
  AcquireSRWLockShared(&s_->lock);
  Now n = s_->now;
  ReleaseSRWLockShared(&s_->lock);
  return n;
}

int Updater::compare(const std::wstring& a, const std::wstring& b) {
  auto numbers = [](const std::wstring& v) {
    std::vector<long> out;
    size_t i = (!v.empty() && (v[0] == L'v' || v[0] == L'V')) ? 1 : 0;
    while (i < v.size() && out.size() < 4) {
      if (!iswdigit(v[i])) break;
      long n = 0;
      while (i < v.size() && iswdigit(v[i]) && n < 100000) n = n * 10 + (v[i++] - L'0');
      out.push_back(n);
      if (i < v.size() && v[i] == L'.') i++;
      else break;
    }
    out.resize(4, 0);
    return out;
  };
  auto x = numbers(a), y = numbers(b);
  for (int i = 0; i < 4; i++)
    if (x[i] != y[i]) return x[i] < y[i] ? -1 : 1;
  return 0;
}

// Release notes are written for a web page. Here they are plain lines: links keep only their words, addresses go.
std::wstring Updater::plainNotes(const std::string& markdown) {
  std::wstring t = widen(markdown.substr(0, 20000)), flat;
  for (size_t i = 0; i < t.size();) {
    if (t[i] == L'[') {
      size_t mid = t.find(L"](", i), end = mid == std::wstring::npos ? mid : t.find(L')', mid);
      if (end != std::wstring::npos && mid - i < 300) {
        flat += t.substr(i + 1, mid - i - 1);
        i = end + 1;
        continue;
      }
    }
    if (t[i] == L'<' && (t.compare(i + 1, 4, L"http") == 0 || t.compare(i + 1, 4, L"www.") == 0)) {
      size_t end = t.find(L'>', i);
      if (end != std::wstring::npos) {
        i = end + 1;
        continue;
      }
    }
    if (t[i] != L'\r') flat += t[i];
    i++;
  }
  std::wstring out;
  bool blank = true;
  for (size_t at = 0; at <= flat.size();) {
    size_t e = std::min(flat.find(L'\n', at), flat.size());
    std::wstring line = flat.substr(at, e - at);
    at = e + 1;
    if (toLower(line).find(L"full changelog") != std::wstring::npos || toLower(line).find(L"/compare/") != std::wstring::npos) continue;
    // addresses written out
    std::wstring kept;
    for (size_t i = 0; i < line.size();) {
      if (line.compare(i, 7, L"http://") == 0 || line.compare(i, 8, L"https://") == 0 || line.compare(i, 4, L"www.") == 0) {
        while (i < line.size() && !iswspace(line[i])) i++;
        continue;
      }
      kept += line[i++];
    }
    kept = trim(strip(kept));
    while (!kept.empty() && kept[0] == L'#') kept = trim(kept.substr(1));
    if (kept.size() > 1 && (kept[0] == L'-' || kept[0] == L'*') && kept[1] == L' ') kept = L"\x2022 " + trim(kept.substr(2));
    if (kept.empty()) {
      if (!blank) out += L"\n";
      blank = true;
      continue;
    }
    out += kept + L"\n";
    blank = false;
  }
  out = trim(out);
  if (out.size() > 3000) out = out.substr(0, 3000) + L"...";
  return out;
}

void Updater::check() { start(false); }
void Updater::download() { start(true); }

void Updater::start(bool fetch) {
  AcquireSRWLockExclusive(&s_->lock);
  bool go = !s_->busy && (!fetch || (s_->now.state == State::Available && !s_->asset.empty()));
  if (go) {
    s_->busy = true;
    s_->now.state = fetch ? State::Downloading : State::Checking;
    s_->now.error.clear();
    s_->now.got = 0;
    s_->tell();
  }
  ReleaseSRWLockExclusive(&s_->lock);
  if (!go) return;
  struct Arg {
    std::shared_ptr<Shared> s;
    bool fetch;
  };
  auto* arg = new Arg{s_, fetch};
  auto work = [](void* p) -> unsigned {
    std::unique_ptr<Arg> a((Arg*)p);
    Shared& s = *a->s;
    auto finish = [&](State st, const std::wstring& err) {
      AcquireSRWLockExclusive(&s.lock);
      s.now.state = st;
      s.now.error = err;
      s.busy = false;
      s.tell();
      ReleaseSRWLockExclusive(&s.lock);
    };
    Web w;
    if (!w.start()) {
      finish(State::Failed, L"Windows could not open a connection.");
      return 0;
    }
    std::wstring err;
    DWORD status = 0;
    if (!a->fetch) {
      std::string body;
      bool ok = get(w, L"https://" RT_RELEASES_HOST RT_RELEASES_PATH, L"Accept: application/vnd.github+json\r\nX-GitHub-Api-Version: 2022-11-28\r\n", 2u << 20,
                    [&](const char* d, size_t n, uint64_t) {
                      body.append(d, n);
                      return true;
                    },
                    status, err);
      if (!ok) {
        finish(State::Failed, status == 404 ? L"No version has been published yet." : err);
        return 0;
      }
      Json j;
      if (!Json::parse(body, j) || !j.isObj()) {
        finish(State::Failed, L"The answer about the newest version could not be read.");
        return 0;
      }
      std::wstring version = trim(widen(j.str("tag_name")));
      if (!version.empty() && (version[0] == L'v' || version[0] == L'V')) version.erase(0, 1);
      std::wstring asset;
      uint64_t size = 0;
      if (auto as = j.find("assets"); as && as->isArr())
        for (auto& e : as->a) {
          std::wstring n = toLower(widen(e.str("name")));
          std::wstring u = widen(e.str("browser_download_url"));
          if (n.size() > 9 && n.compare(n.size() - 9, 9, L"setup.exe") == 0 && u.rfind(L"https://github.com/", 0) == 0) {
            asset = u;
            size = (uint64_t)e.num("size", 0);
            break;
          }
        }
      bool newer = !version.empty() && compare(version, current) > 0;
      AcquireSRWLockExclusive(&s.lock);
      s.now.version = version;
      s.now.notes = plainNotes(j.str("body"));
      s.now.size = size;
      s.asset = asset;
      ReleaseSRWLockExclusive(&s.lock);
      if (newer && asset.empty()) finish(State::Failed, L"Version " + version + L" is out, but its setup is not ready yet. Try again later.");
      else finish(newer ? State::Available : State::Latest, {});
      return 0;
    }
    // the setup, into a folder of its own in the temp folder
    std::wstring url, version;
    uint64_t want = 0;
    AcquireSRWLockShared(&s.lock);
    url = s.asset;
    version = s.now.version;
    want = s.now.size;
    ReleaseSRWLockShared(&s.lock);
    std::wstring dir = joinPath(tempFolder(), RT_ID L"-Update"), file = joinPath(dir, L"RadialTaskbar-Setup-" + version + L".exe"), part = file + L".part";
    SHCreateDirectoryExW(nullptr, dir.c_str(), nullptr);
    DeleteFileW(part.c_str());
    HANDLE h = CreateFileW(part.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (h == INVALID_HANDLE_VALUE) {
      finish(State::Failed, L"The temp folder cannot be written to.");
      return 0;
    }
    double told = 0;
    uint64_t got = 0;
    char head[2] = {};
    bool ok = get(w, url, L"Accept: application/octet-stream\r\n", 400ull << 20,
                  [&](const char* d, size_t n, uint64_t total) {
                    if (got < 2)
                      for (size_t i = 0; i < n && got + i < 2; i++) head[got + i] = d[i];
                    DWORD wr = 0;
                    if (!WriteFile(h, d, (DWORD)n, &wr, nullptr) || wr != n) {
                      err = L"The download could not be saved. Is the disk full?";
                      return false;
                    }
                    got += n;
                    if (nowSec() - told > 0.1) {
                      told = nowSec();
                      AcquireSRWLockExclusive(&s.lock);
                      s.now.got = got;
                      if (total) s.now.size = total;
                      s.tell();
                      ReleaseSRWLockExclusive(&s.lock);
                    }
                    return true;
                  },
                  status, err);
    CloseHandle(h);
    if (ok && (head[0] != 'M' || head[1] != 'Z' || (want && got != want))) {
      ok = false;
      err = L"The download is not complete. Try again.";
    }
    if (ok && !MoveFileExW(part.c_str(), file.c_str(), MOVEFILE_REPLACE_EXISTING)) {
      ok = false;
      err = L"The download could not be kept.";
    }
    if (!ok) {
      DeleteFileW(part.c_str());
      AcquireSRWLockExclusive(&s.lock);
      s.now.got = 0;
      ReleaseSRWLockExclusive(&s.lock);
      finish(State::Available, {});  // the button can be pressed again
      AcquireSRWLockExclusive(&s.lock);
      s.now.error = err;
      s.tell();
      ReleaseSRWLockExclusive(&s.lock);
      return 0;
    }
    AcquireSRWLockExclusive(&s.lock);
    s.now.file = file;
    s.now.got = got;
    ReleaseSRWLockExclusive(&s.lock);
    finish(State::Ready, {});
    return 0;
  };
  uintptr_t t = _beginthreadex(nullptr, 0, work, arg, 0, nullptr);
  if (t) {
    CloseHandle((HANDLE)t);
    return;
  }
  delete arg;
  AcquireSRWLockExclusive(&s_->lock);
  s_->busy = false;
  s_->now.state = State::Failed;
  s_->now.error = L"Could not start looking.";
  s_->tell();
  ReleaseSRWLockExclusive(&s_->lock);
}

}  // namespace rt
