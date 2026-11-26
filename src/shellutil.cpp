#include "shellutil.h"

#include <appmodel.h>
#include <process.h>
#include <propkey.h>
#include <propvarutil.h>
#include <shobjidl.h>

namespace rt {

// Defined here so the build does not depend on which import library carries them.
static const PROPERTYKEY kPKEY_AppUserModel_ID = {{0x9F4C2855, 0x9F79, 0x4B39, {0xA8, 0xD0, 0xE1, 0xD4, 0x2D, 0xE1, 0xD5, 0xF3}}, 5};
static const PROPERTYKEY kPKEY_Link_TargetParsingPath = {{0xB9B4B3FC, 0x2B51, 0x4A42, {0xB5, 0xD8, 0x32, 0x41, 0x46, 0xAF, 0xCF, 0x25}}, 2};
static const GUID kFOLDERID_AppsFolder = {0x1e87508d, 0x89c2, 0x42f0, {0x8a, 0x7e, 0x64, 0x5a, 0x0f, 0x50, 0xca, 0x58}};
static const GUID kBHID_EnumItems = {0x94f60519, 0x2850, 0x4924, {0xaa, 0x5a, 0xd1, 0x5e, 0x84, 0x86, 0x80, 0x39}};

static std::wstring takeCo(PWSTR p) {
  std::wstring s = p ? p : L"";
  CoTaskMemFree(p);
  return s;
}

static std::wstring propString(IPropertyStore* st, const PROPERTYKEY& key) {
  PROPVARIANT v;
  PropVariantInit(&v);
  std::wstring out;
  if (st && SUCCEEDED(st->GetValue(key, &v)) && v.vt == VT_LPWSTR && v.pwszVal) out = v.pwszVal;
  PropVariantClear(&v);
  return out;
}

// ---------------------------------------------------------------- shortcuts
bool readLink(const std::wstring& lnk, LinkInfo& out) {
  ComPtr<IShellLinkW> sl;
  if (FAILED(CoCreateInstance(CLSID_ShellLink, nullptr, CLSCTX_INPROC_SERVER, __uuidof(IShellLinkW), (void**)sl.GetAddressOf()))) return false;
  ComPtr<IPersistFile> pf;
  if (FAILED(sl.As(&pf)) || FAILED(pf->Load(lnk.c_str(), STGM_READ | STGM_SHARE_DENY_NONE))) return false;
  wchar_t buf[2048];
  if (sl->GetPath(buf, 2048, nullptr, SLGP_RAWPATH) == S_OK) out.target = expandEnv(buf);
  if (SUCCEEDED(sl->GetArguments(buf, 2048))) out.args = buf;
  if (SUCCEEDED(sl->GetWorkingDirectory(buf, 2048))) out.workDir = buf;
  int idx = 0;
  if (SUCCEEDED(sl->GetIconLocation(buf, 2048, &idx))) {
    out.icon = expandEnv(buf);
    out.iconIndex = idx;
  }
  ComPtr<IShellLinkDataList> dl;
  DWORD flags = 0;
  if (SUCCEEDED(sl.As(&dl)) && SUCCEEDED(dl->GetFlags(&flags))) out.admin = (flags & SLDF_RUNAS_USER) != 0;
  ComPtr<IPropertyStore> ps;
  if (SUCCEEDED(sl.As(&ps))) {
    out.aumid = propString(ps.Get(), kPKEY_AppUserModel_ID);
    if (out.target.empty()) {
      std::wstring t = propString(ps.Get(), kPKEY_Link_TargetParsingPath);
      if (!t.empty() && t.find(L'\\') != std::wstring::npos && fileExists(t)) out.target = t;
      // A packaged app's shortcut has no file target; its id is the target's name.
      else if (out.aumid.empty() && t.find(L'!') != std::wstring::npos) out.aumid = fileName(t);
    }
  }
  return true;
}

bool createShortcut(const std::wstring& lnk, const std::wstring& target, const std::wstring& args, const std::wstring& desc,
                    const std::wstring& aumid) {
  ComPtr<IShellLinkW> sl;
  if (FAILED(CoCreateInstance(CLSID_ShellLink, nullptr, CLSCTX_INPROC_SERVER, __uuidof(IShellLinkW), (void**)sl.GetAddressOf()))) return false;
  sl->SetPath(target.c_str());
  if (!args.empty()) sl->SetArguments(args.c_str());
  sl->SetWorkingDirectory(dirName(target).c_str());
  sl->SetDescription(desc.c_str());
  sl->SetIconLocation(target.c_str(), 0);
  if (!aumid.empty()) {
    ComPtr<IPropertyStore> ps;
    if (SUCCEEDED(sl.As(&ps))) {
      PROPVARIANT v;
      if (SUCCEEDED(InitPropVariantFromString(aumid.c_str(), &v))) {
        ps->SetValue(kPKEY_AppUserModel_ID, v);
        ps->Commit();
        PropVariantClear(&v);
      }
    }
  }
  ComPtr<IPersistFile> pf;
  return SUCCEEDED(sl.As(&pf)) && SUCCEEDED(pf->Save(lnk.c_str(), TRUE));
}

// ---------------------------------------------------------------- installed apps
std::vector<AppEntry> enumInstalledApps() {
  std::vector<AppEntry> out;
  ComPtr<IShellItem> folder;
  if (FAILED(SHGetKnownFolderItem(kFOLDERID_AppsFolder, KF_FLAG_DEFAULT, nullptr, __uuidof(IShellItem), (void**)folder.GetAddressOf()))) return out;
  ComPtr<IEnumShellItems> en;
  if (FAILED(folder->BindToHandler(nullptr, kBHID_EnumItems, __uuidof(IEnumShellItems), (void**)en.GetAddressOf()))) return out;
  for (;;) {
    ComPtr<IShellItem> it;
    ULONG got = 0;
    if (en->Next(1, &it, &got) != S_OK || !got) break;
    PWSTR p = nullptr;
    AppEntry e;
    if (SUCCEEDED(it->GetDisplayName(SIGDN_NORMALDISPLAY, &p))) e.name = takeCo(p);
    p = nullptr;
    if (SUCCEEDED(it->GetDisplayName(SIGDN_PARENTRELATIVEPARSING, &p))) e.aumid = takeCo(p);
    ComPtr<IShellItem2> i2;
    if (SUCCEEDED(it.As(&i2))) {
      p = nullptr;
      if (SUCCEEDED(i2->GetString(kPKEY_Link_TargetParsingPath, &p))) e.exe = takeCo(p);
    }
    if (e.name.empty() || e.aumid.empty()) continue;
    // Skip the help pages and uninstallers that Start menu folders are full of.
    std::wstring ext = fileExt(e.exe), low = toLower(e.name);
    if (ext == L".url" || ext == L".html" || ext == L".htm" || ext == L".chm" || ext == L".txt" || ext == L".pdf") continue;
    if (e.aumid.rfind(L"http", 0) == 0) continue;
    if (low.rfind(L"uninstall", 0) == 0) continue;
    out.push_back(std::move(e));
  }
  std::sort(out.begin(), out.end(), [](const AppEntry& a, const AppEntry& b) {
    return CompareStringEx(LOCALE_NAME_USER_DEFAULT, LINGUISTIC_IGNORECASE | SORT_DIGITSASNUMBERS, a.name.c_str(), -1, b.name.c_str(), -1, nullptr, nullptr, 0) == CSTR_LESS_THAN;
  });
  return out;
}

// ---------------------------------------------------------------- pin creation
static std::wstring displayNameFor(const std::wstring& path) {
  SHFILEINFOW fi{};
  if (SHGetFileInfoW(path.c_str(), 0, &fi, sizeof fi, SHGFI_DISPLAYNAME) && fi.szDisplayName[0]) {
    std::wstring n = fi.szDisplayName;
    std::wstring e = fileExt(n);
    if (e == L".exe" || e == L".lnk" || e == L".url") n = fileStem(n);
    return n;
  }
  return fileStem(path);
}

// A program's own description ("Visual Studio Code") beats its file name ("Code").
static std::wstring productNameFor(const std::wstring& exe) {
  DWORD dummy = 0, n = GetFileVersionInfoSizeW(exe.c_str(), &dummy);
  if (!n) return {};
  std::vector<uint8_t> buf(n);
  if (!GetFileVersionInfoW(exe.c_str(), 0, n, buf.data())) return {};
  struct Lang { WORD l, c; }* tr = nullptr;
  UINT cb = 0;
  if (!VerQueryValueW(buf.data(), L"\\VarFileInfo\\Translation", (void**)&tr, &cb) || cb < sizeof(Lang)) return {};
  wchar_t key[80];
  swprintf(key, 80, L"\\StringFileInfo\\%04x%04x\\FileDescription", tr->l, tr->c);
  wchar_t* val = nullptr;
  if (VerQueryValueW(buf.data(), key, (void**)&val, &cb) && cb > 1 && val) {
    std::wstring s = trim(val);
    if (s.size() > 1 && s.size() < 48) return s;
  }
  return {};
}

// Shortcuts are copied into our own folder: Windows deletes the original when an item is unpinned.
static std::wstring adoptLink(const std::wstring& lnk) {
  std::wstring dir = joinPath(dataDir(), L"links");
  SHCreateDirectoryExW(nullptr, dir.c_str(), nullptr);
  if (toLower(lnk).rfind(toLower(dir), 0) == 0) return lnk;
  std::wstring dst = joinPath(dir, fileStem(lnk) + L"-" + widen(newId()).substr(0, 8) + L".lnk");
  return CopyFileW(lnk.c_str(), dst.c_str(), FALSE) ? dst : lnk;
}

Pin pinFromPath(const std::wstring& pathIn) {
  Pin p;
  p.id = newId();
  std::wstring path = trim(pathIn);
  if (path.size() >= 2 && path.front() == L'"' && path.back() == L'"') path = path.substr(1, path.size() - 2);
  std::wstring ext = fileExt(path);
  if (ext == L".url") {
    wchar_t url[2048] = {};
    GetPrivateProfileStringW(L"InternetShortcut", L"URL", L"", url, 2048, path.c_str());
    if (url[0]) {
      p.kind = Pin::Kind::Url;
      p.target = url;
      p.name = fileStem(path);
      wchar_t ico[1024] = {};
      GetPrivateProfileStringW(L"InternetShortcut", L"IconFile", L"", ico, 1024, path.c_str());
      std::wstring icoPath = expandEnv(ico);
      if (!icoPath.empty() && fileExists(icoPath)) p.icon = icoPath;
      return p;
    }
  }
  p.kind = Pin::Kind::File;
  p.target = path;
  p.folder = dirExists(path);
  p.name = displayNameFor(path);
  if (ext == L".lnk") {
    p.name = fileStem(path);
  } else if (ext == L".exe") {
    std::wstring prod = productNameFor(path);
    if (!prod.empty()) p.name = prod;
  }
  if (p.name.empty()) p.name = fileStem(path);
  return p;
}

void adoptPin(Pin& p) {
  if (p.kind == Pin::Kind::File && fileExt(p.target) == L".lnk") p.target = adoptLink(p.target);
}

Pin pinFromApp(const AppEntry& a) {
  Pin p;
  p.id = newId();
  p.kind = Pin::Kind::App;
  p.name = a.name;
  p.target = a.aumid;
  return p;
}

Pin pinFromAppId(const std::wstring& aumid) {
  ComPtr<IShellItem> item;
  if (aumid.empty() || FAILED(SHCreateItemFromParsingName((L"shell:AppsFolder\\" + aumid).c_str(), nullptr, __uuidof(IShellItem), (void**)item.GetAddressOf()))) return {};
  AppEntry a;
  PWSTR p = nullptr;
  if (SUCCEEDED(item->GetDisplayName(SIGDN_NORMALDISPLAY, &p))) a.name = takeCo(p);
  p = nullptr;
  if (SUCCEEDED(item->GetDisplayName(SIGDN_PARENTRELATIVEPARSING, &p))) a.aumid = takeCo(p);
  if (a.name.empty() || toLower(a.aumid) != toLower(aumid)) return {};
  return pinFromApp(a);
}

Pin pinFromUrl(const std::wstring& urlIn, const std::wstring& name) {
  Pin p;
  p.id = newId();
  p.kind = Pin::Kind::Url;
  std::wstring u = trim(urlIn);
  if (u.find(L':') == std::wstring::npos) u = L"https://" + u;
  p.target = u;
  p.name = name;
  if (p.name.empty()) {
    size_t a = u.find(L"://");
    std::wstring host = a == std::wstring::npos ? u : u.substr(a + 3);
    size_t e = host.find_first_of(L"/?#");
    if (e != std::wstring::npos) host = host.substr(0, e);
    if (host.rfind(L"www.", 0) == 0) host = host.substr(4);
    p.name = host;
  }
  return p;
}

// ---------------------------------------------------------------- taskbar import
std::vector<Pin> importTaskbarPins() {
  std::vector<Pin> out;
  std::vector<std::wstring> seen;
  auto take = [&](const std::wstring& name, const std::wstring& parsing) {
    std::wstring low = toLower(parsing);
    if (parsing.empty() || std::find(seen.begin(), seen.end(), low) != seen.end()) return;
    seen.push_back(low);
    if (parsing.size() > 3 && parsing[1] == L':') {
      if (!fileExists(parsing) && !dirExists(parsing)) return;
      Pin p = pinFromPath(parsing);
      if (!name.empty()) p.name = name;
      if (fileExt(p.name) == L".lnk") p.name = fileStem(p.name);
      out.push_back(std::move(p));
      return;
    }
    // Store apps: "::{AppsFolder guid}\<AppUserModelID>" or "shell:AppsFolder\<id>"
    size_t slash = parsing.find(L'\\');
    if (slash == std::wstring::npos) return;
    if (low.find(L"4234d49b-0245-4df3-b780-3893943456e1") == std::wstring::npos && low.find(L"appsfolder") == std::wstring::npos) return;
    AppEntry a;
    a.name = name;
    a.aumid = parsing.substr(slash + 1);
    if (!a.name.empty()) out.push_back(pinFromApp(a));
  };

  // The taskbar keeps its order in a blob: repeated [byte kind][DWORD size][ITEMIDLIST].
  DWORD cb = 0;
  const wchar_t* key = L"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Taskband";
  if (RegGetValueW(HKEY_CURRENT_USER, key, L"Favorites", RRF_RT_REG_BINARY, nullptr, nullptr, &cb) == ERROR_SUCCESS && cb > 8 && cb < 4 * 1024 * 1024) {
    std::vector<uint8_t> buf(cb);
    if (RegGetValueW(HKEY_CURRENT_USER, key, L"Favorites", RRF_RT_REG_BINARY, nullptr, buf.data(), &cb) == ERROR_SUCCESS) {
      size_t i = 0;
      while (i + 5 < cb && buf[i] == 0) {
        uint32_t len;
        memcpy(&len, &buf[i + 1], 4);
        i += 5;
        if (len < 4 || i + len > cb) break;
        auto pidl = (PCIDLIST_ABSOLUTE)&buf[i];
        // Validate the item list stays inside its own block before handing it to the shell.
        size_t off = 0;
        bool good = false;
        while (off + 2 <= len) {
          uint16_t sz;
          memcpy(&sz, &buf[i + off], 2);
          if (sz == 0) { good = true; break; }
          if (sz < 2 || off + sz > len) break;
          off += sz;
        }
        if (good) {
          ComPtr<IShellItem> item;
          if (SUCCEEDED(SHCreateItemFromIDList(pidl, __uuidof(IShellItem), (void**)item.GetAddressOf()))) {
            PWSTR a = nullptr, b = nullptr;
            item->GetDisplayName(SIGDN_NORMALDISPLAY, &a);
            item->GetDisplayName(SIGDN_DESKTOPABSOLUTEPARSING, &b);
            std::wstring nm = takeCo(a), pr = takeCo(b);
            take(nm, pr);
          }
        }
        i += len;
      }
    }
  }
  // Anything the blob did not mention but whose shortcut is still in the pinned folder.
  PWSTR ad = nullptr;
  if (SUCCEEDED(SHGetKnownFolderPath(FOLDERID_RoamingAppData, 0, nullptr, &ad))) {
    std::wstring dir = joinPath(ad, L"Microsoft\\Internet Explorer\\Quick Launch\\User Pinned\\TaskBar");
    CoTaskMemFree(ad);
    WIN32_FIND_DATAW fd;
    HANDLE h = FindFirstFileW(joinPath(dir, L"*.lnk").c_str(), &fd);
    if (h != INVALID_HANDLE_VALUE) {
      do take(fileStem(fd.cFileName), joinPath(dir, fd.cFileName));
      while (FindNextFileW(h, &fd));
      FindClose(h);
    }
  }
  return out;
}

static bool samePin(const Pin& a, const Pin& b) {
  if (a.kind == Pin::Kind::Group || b.kind == Pin::Kind::Group) return false;
  if (a.kind == b.kind && toLower(a.target) == toLower(b.target) && a.args == b.args) return true;
  if (a.kind == Pin::Kind::Url || b.kind == Pin::Kind::Url) return false;
  MatchInfo x = resolveMatch(a), y = resolveMatch(b);
  if (!x.aumid.empty() && x.aumid == y.aumid) return true;
  if (a.args != b.args) return false;
  if (!x.other.empty() && x.other == y.other) return true;
  // The same program. Two different ids are two different apps even then (a browser and the sites installed from it).
  return !x.exe.empty() && x.exe == y.exe && (x.aumid.empty() || y.aumid.empty());
}
bool alreadyPinned(const std::vector<Pin>& pins, const Pin& p) { return !pinnedId(pins, p).empty(); }
std::string pinnedId(const std::vector<Pin>& pins, const Pin& p) {
  for (auto& q : pins) {
    if (samePin(q, p)) return q.id;
    for (auto& c : q.children)
      if (samePin(c, p)) return c.id;
  }
  return {};
}

// ---------------------------------------------------------------- launching
namespace {
struct LaunchJob {
  std::wstring file, args, dir;
  bool admin;
};
unsigned __stdcall launchThread(void* arg) {
  std::unique_ptr<LaunchJob> j((LaunchJob*)arg);
  CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED | COINIT_DISABLE_OLE1DDE);
  SHELLEXECUTEINFOW si{};
  si.cbSize = sizeof si;
  si.fMask = SEE_MASK_NOASYNC;
  si.lpVerb = j->admin ? L"runas" : nullptr;
  si.lpFile = j->file.c_str();
  si.lpParameters = j->args.empty() ? nullptr : j->args.c_str();
  si.lpDirectory = j->dir.empty() ? nullptr : j->dir.c_str();
  si.nShow = SW_SHOWNORMAL;
  if (!ShellExecuteExW(&si)) logf("launch failed: %lu", GetLastError());
  CoUninitialize();
  return 0;
}
void startLaunch(LaunchJob* j) {
  AllowSetForegroundWindow(ASFW_ANY);  // let the new program come to the front
  uintptr_t h = _beginthreadex(nullptr, 0, launchThread, j, 0, nullptr);
  if (h) CloseHandle((HANDLE)h);
  else delete j;
}
}  // namespace

void launchPin(const Pin& pin, bool admin) {
  if (pin.kind == Pin::Kind::Group || pin.target.empty()) return;
  auto* j = new LaunchJob;
  j->admin = admin || pin.admin;
  j->args = pin.args;
  j->dir = expandEnv(pin.workDir);
  switch (pin.kind) {
    case Pin::Kind::App: j->file = L"shell:AppsFolder\\" + pin.target; break;
    case Pin::Kind::Url: j->file = pin.target; break;
    default:
      j->file = expandEnv(pin.target);
      if (j->dir.empty() && fileExt(j->file) == L".exe") j->dir = dirName(j->file);
  }
  startLaunch(j);
}

void openPinLocation(const Pin& pin) {
  std::wstring path;
  if (pin.kind == Pin::Kind::File) {
    path = expandEnv(pin.target);
    if (fileExt(path) == L".lnk") {
      LinkInfo li;
      if (readLink(path, li) && !li.target.empty()) path = li.target;
    }
  } else if (pin.kind == Pin::Kind::App) {
    path = resolveMatch(pin).exe;
  }
  if (path.empty()) return;
  auto* j = new LaunchJob;
  j->admin = false;
  j->file = L"explorer.exe";
  j->args = L"/select,\"" + path + L"\"";
  startLaunch(j);
}

std::wstring pinSubtitle(const Pin& pin) {
  switch (pin.kind) {
    case Pin::Kind::App: return L"App";
    case Pin::Kind::Url: return pin.target;
    case Pin::Kind::Group: return std::to_wstring(pin.children.size()) + (pin.children.size() == 1 ? L" item" : L" items");
    default: {
      std::wstring t = expandEnv(pin.target);
      if (fileExt(t) == L".lnk") return L"Shortcut";
      return t;
    }
  }
}

// ---------------------------------------------------------------- matching
// Many apps are started through a small launcher (App\\app.exe) while the windows belong to a versioned
// copy below it (App\\app-1.2.3\\app.exe). Treat those as the same program. Both paths are lower case.
static bool sameProgram(const std::wstring& launcher, const std::wstring& running) {
  if (launcher.empty() || running.empty()) return false;
  if (launcher == running) return true;
  if (fileName(launcher) != fileName(running)) return false;
  std::wstring dir = dirName(launcher) + L"\\";
  return dir.size() > 4 && running.compare(0, dir.size(), dir) == 0;
}

static std::unordered_map<std::string, MatchInfo> g_matches;
static SRWLOCK g_matchLock = SRWLOCK_INIT;  // the taskbar row's helper asks from two threads

void forgetMatches() {
  AcquireSRWLockExclusive(&g_matchLock);
  g_matches.clear();
  ReleaseSRWLockExclusive(&g_matchLock);
}

MatchInfo resolveMatch(const Pin& pin) {
  std::string key = narrow(std::to_wstring((int)pin.kind) + L"|" + pin.target + L"|" + pin.args);
  MatchInfo m;
  AcquireSRWLockShared(&g_matchLock);
  auto it = g_matches.find(key);
  bool known = it != g_matches.end();
  if (known) m = it->second;
  ReleaseSRWLockShared(&g_matchLock);
  if (known) return m;
  if (pin.kind == Pin::Kind::App) {
    m.aumid = toLower(pin.target);
    ComPtr<IShellItem2> i2;
    if (SUCCEEDED(SHCreateItemFromParsingName((L"shell:AppsFolder\\" + pin.target).c_str(), nullptr, __uuidof(IShellItem2), (void**)i2.GetAddressOf()))) {
      PWSTR p = nullptr;
      if (SUCCEEDED(i2->GetString(kPKEY_Link_TargetParsingPath, &p))) m.exe = toLower(takeCo(p));
    }
    if (m.aumid == L"microsoft.windows.explorer") m.exe = toLower(expandEnv(L"%WINDIR%\\explorer.exe"));  // its windows carry no id
  } else if (pin.kind == Pin::Kind::File) {
    std::wstring t = expandEnv(pin.target);
    std::wstring ext = fileExt(t);
    bool plain = pin.args.empty();
    if (ext == L".exe") {
      if (plain) m.exe = toLower(t);
    } else if (ext == L".lnk") {
      LinkInfo li;
      if (readLink(t, li)) {
        m.aumid = toLower(li.aumid);
        if (fileExt(li.target) == L".exe" && li.args.empty()) m.exe = toLower(li.target);
        else if (fileExt(li.target) != L".exe" && li.args.empty()) m.other = toLower(li.target);
        // Squirrel installs point their shortcut at "Update.exe --processStart App.exe".
        size_t at = li.args.find(L"--processStart");
        if (at != std::wstring::npos && toLower(fileName(li.target)) == L"update.exe") {
          std::wstring rest = trim(li.args.substr(at + 14));
          std::wstring app = !rest.empty() && rest[0] == L'"' ? rest.substr(1, rest.find(L'"', 1) - 1) : rest.substr(0, rest.find(L' '));
          if (fileExt(app) == L".exe" && app.find_first_of(L"\\/") == std::wstring::npos) m.exe = toLower(joinPath(dirName(li.target), app));
        }
      }
    }
  }
  if (fileExt(m.exe) != L".exe") m.exe.clear();
  AcquireSRWLockExclusive(&g_matchLock);
  g_matches[key] = m;
  ReleaseSRWLockExclusive(&g_matchLock);
  return m;
}

// ---------------------------------------------------------------- running windows
namespace {
struct SnapCtx {
  std::vector<AppWindow>* out;
  HWND ig1, ig2;
  std::unordered_map<DWORD, std::pair<std::wstring, std::wstring>> procs;  // exe, aumid
};

}  // namespace

bool isAppWindow(HWND h) {
  if (!h || !IsWindowVisible(h)) return false;
  LONG_PTR ex = GetWindowLongPtrW(h, GWL_EXSTYLE);
  if ((ex & WS_EX_TOOLWINDOW) && !(ex & WS_EX_APPWINDOW)) return false;
  if (GetWindow(h, GW_OWNER) && !(ex & WS_EX_APPWINDOW)) return false;
  if ((ex & WS_EX_NOACTIVATE) && !(ex & WS_EX_APPWINDOW)) return false;
  DWORD cloaked = 0;
  if (SUCCEEDED(DwmGetWindowAttribute(h, DWMWA_CLOAKED, &cloaked, sizeof cloaked)) && cloaked) return false;
  if (GetWindowTextLengthW(h) == 0) return false;
  wchar_t cls[96] = {};
  GetClassNameW(h, cls, 96);
  static const wchar_t* skip[] = {L"Progman", L"WorkerW", L"Shell_TrayWnd", L"Shell_SecondaryTrayWnd", L"Windows.UI.Core.CoreWindow",
                                  L"XamlExplorerHostIslandWindow", L"TopLevelWindowForOverflowXamlIsland"};
  for (auto s : skip)
    if (!wcscmp(cls, s)) return false;
  return true;
}

namespace {

// Who a window belongs to, whether or not it is in sight.
bool describe(HWND h, SnapCtx* c, AppWindow& w) {
  w.hwnd = h;
  wchar_t t[512] = {};
  // Reads the cached caption; does not send a message, so a hung app cannot stall us.
  if (InternalGetWindowText(h, t, 512) <= 0) return false;
  w.title = t;
  w.minimized = IsIconic(h) != FALSE;
  DWORD pid = 0;
  GetWindowThreadProcessId(h, &pid);
  auto it = c->procs.find(pid);
  if (it == c->procs.end()) {
    std::pair<std::wstring, std::wstring> info;
    if (HANDLE p = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid)) {
      wchar_t path[1024];
      DWORD n = 1024;
      if (QueryFullProcessImageNameW(p, 0, path, &n)) info.first = toLower(path);
      wchar_t id[256];
      UINT32 idn = 256;
      if (GetApplicationUserModelId(p, &idn, id) == ERROR_SUCCESS) info.second = toLower(id);
      CloseHandle(p);
    }
    it = c->procs.emplace(pid, info).first;
  }
  w.exe = it->second.first;
  w.aumid = it->second.second;
  ComPtr<IPropertyStore> ps;
  if (SUCCEEDED(SHGetPropertyStoreForWindow(h, __uuidof(IPropertyStore), (void**)ps.GetAddressOf()))) {
    std::wstring id = propString(ps.Get(), kPKEY_AppUserModel_ID);
    if (!id.empty()) w.aumid = toLower(id);
  }
  return true;
}

BOOL CALLBACK enumProc(HWND h, LPARAM lp) {
  auto* c = (SnapCtx*)lp;
  AppWindow w;
  if (h != c->ig1 && h != c->ig2 && isAppWindow(h) && describe(h, c, w)) c->out->push_back(std::move(w));
  return TRUE;
}
}  // namespace

bool describeWindow(HWND h, AppWindow& out) {
  SnapCtx c{nullptr, nullptr, nullptr, {}};
  return IsWindow(h) && describe(h, &c, out);
}

void WindowList::snapshot(HWND ignore1, HWND ignore2) {
  wins.clear();
  foreground = GetForegroundWindow();
  SnapCtx c{&wins, ignore1, ignore2, {}};
  EnumWindows(enumProc, (LPARAM)&c);
}

std::vector<int> WindowList::matching(const Pin& pin) const {
  std::vector<int> out;
  if (pin.kind == Pin::Kind::Group || pin.kind == Pin::Kind::Url) return out;
  MatchInfo m = resolveMatch(pin);
  if (m.aumid.empty() && m.exe.empty()) return out;
  for (size_t i = 0; i < wins.size(); i++) {
    auto& w = wins[i];
    bool hit = !m.aumid.empty() && w.aumid == m.aumid;
    if (!hit && sameProgram(m.exe, w.exe)) hit = m.aumid.empty() || w.aumid.empty() || w.aumid == m.aumid;
    if (hit) out.push_back((int)i);
  }
  return out;
}

Pin pinFromWindow(HWND hwnd) {
  Pin p;
  if (!hwnd) return p;
  AppWindow w;
  if (!describeWindow(hwnd, w)) return p;
  // Prefer the Start menu entry: it carries the right name, icon and app id. By id is quick, by program means
  // going through the whole list.
  if (w.aumid.empty() && w.exe == toLower(expandEnv(L"%WINDIR%\\explorer.exe"))) {  // a folder window; others have an id
    p = pinFromAppId(L"Microsoft.Windows.Explorer");
    if (!p.target.empty()) return p;
  }
  if (!w.aumid.empty()) {
    p = pinFromAppId(w.aumid);
    if (!p.target.empty()) return p;
  }
  if (!w.aumid.empty() || !w.exe.empty()) {
    for (auto& a : enumInstalledApps()) {
      if ((!w.aumid.empty() && toLower(a.aumid) == w.aumid) || sameProgram(toLower(a.exe), w.exe)) return pinFromApp(a);
    }
  }
  if (!w.exe.empty() && fileName(w.exe) != L"applicationframehost.exe") {
    // The path as it is written on disk; the one above is lower case for comparing.
    std::wstring path = w.exe;
    DWORD pid = 0;
    GetWindowThreadProcessId(hwnd, &pid);
    if (HANDLE h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid)) {
      wchar_t full[1024];
      DWORD n = 1024;
      if (QueryFullProcessImageNameW(h, 0, full, &n) && toLower(full) == w.exe) path = full;
      CloseHandle(h);
    }
    return pinFromPath(path);
  }
  return p;
}

// Finding a window's Start menu entry walks the whole app list; done elsewhere so the resident stays small.
Pin pinFromWindowHelper(HWND hwnd) {
  Pin p;
  std::wstring out = joinPath(cacheDir(), L"pin-" + std::to_wstring(GetCurrentProcessId()) + L"-" + std::to_wstring(GetTickCount64()) + L".json");
  if (HANDLE h = startHelper(L"--pin-window " + std::to_wstring((uint64_t)(uintptr_t)hwnd) + L" --out \"" + out + L"\"")) {
    if (WaitForSingleObject(h, 20000) != WAIT_OBJECT_0) TerminateProcess(h, 1);
    CloseHandle(h);
    std::string text;
    if (readFile(out, text)) pinParse(text, p);
  }
  DeleteFileW(out.c_str());
  return p;
}
int runPinHelper(const std::wstring& hwnd, const std::wstring& outFile) {
  Pin p = pinFromWindow((HWND)(uintptr_t)wcstoull(hwnd.c_str(), nullptr, 10));
  return !p.target.empty() && !outFile.empty() && writeFileAtomic(outFile, pinText(p)) ? 0 : 1;
}

void focusWindow(HWND h) {
  if (!IsWindow(h)) return;
  if (IsIconic(h)) ShowWindowAsync(h, SW_RESTORE);
  if (SetForegroundWindow(h) && GetForegroundWindow() == h) return;
  // The foreground lock can refuse us, and a held Alt lifts it. The unassigned key in between
  // keeps the Alt release from opening anyone's menu bar. Only where the person's input goes to our own desktop.
  BOOL input = FALSE;
  if (!GetUserObjectInformationW(GetThreadDesktop(GetCurrentThreadId()), UOI_IO, &input, sizeof input, nullptr) || !input) return;
  auto key = [](WORD vk, bool up) {
    INPUT in{};
    in.type = INPUT_KEYBOARD;
    in.ki.wVk = vk;
    in.ki.dwFlags = up ? KEYEVENTF_KEYUP : 0;
    SendInput(1, &in, sizeof in);
  };
  key(VK_MENU, false);
  SetForegroundWindow(h);
  key(0xE8, false);
  key(0xE8, true);
  key(VK_MENU, true);
}

bool fullscreenAppRunning() {
  QUERY_USER_NOTIFICATION_STATE s;
  return SUCCEEDED(SHQueryUserNotificationState(&s)) && s == QUNS_RUNNING_D3D_FULL_SCREEN;
}

// ---------------------------------------------------------------- system bits
static const wchar_t* kRunKey = L"Software\\Microsoft\\Windows\\CurrentVersion\\Run";

bool autostartEnabled() {
  wchar_t v[1200];
  DWORD cb = sizeof v;
  if (RegGetValueW(HKEY_CURRENT_USER, kRunKey, kRunValue, RRF_RT_REG_SZ, nullptr, v, &cb) != ERROR_SUCCESS) return false;
  return toLower(v).find(toLower(modulePath())) != std::wstring::npos;
}
void setAutostart(bool on) {
  if (on) {
    std::wstring cmd = L"\"" + modulePath() + L"\" --background";
    RegSetKeyValueW(HKEY_CURRENT_USER, kRunKey, kRunValue, REG_SZ, cmd.c_str(), (DWORD)((cmd.size() + 1) * sizeof(wchar_t)));
  } else {
    RegDeleteKeyValueW(HKEY_CURRENT_USER, kRunKey, kRunValue);
  }
}

std::wstring pickFile(HWND owner, const wchar_t* title, bool folder, const wchar_t* filterName, const wchar_t* filterSpec) {
  ComPtr<IFileOpenDialog> d;
  if (FAILED(CoCreateInstance(CLSID_FileOpenDialog, nullptr, CLSCTX_INPROC_SERVER, __uuidof(IFileOpenDialog), (void**)d.GetAddressOf()))) return {};
  FILEOPENDIALOGOPTIONS o = 0;
  d->GetOptions(&o);
  d->SetOptions(o | FOS_FORCEFILESYSTEM | (folder ? FOS_PICKFOLDERS : 0) | FOS_NODEREFERENCELINKS);
  d->SetTitle(title);
  if (filterName && filterSpec) {
    COMDLG_FILTERSPEC fs[2] = {{filterName, filterSpec}, {L"All files", L"*.*"}};
    d->SetFileTypes(2, fs);
  }
  if (FAILED(d->Show(owner))) return {};
  ComPtr<IShellItem> it;
  PWSTR p = nullptr;
  if (SUCCEEDED(d->GetResult(&it)) && SUCCEEDED(it->GetDisplayName(SIGDN_FILESYSPATH, &p))) return takeCo(p);
  return {};
}

std::wstring pickSave(HWND owner, const wchar_t* title, const wchar_t* defName) {
  ComPtr<IFileSaveDialog> d;
  if (FAILED(CoCreateInstance(CLSID_FileSaveDialog, nullptr, CLSCTX_INPROC_SERVER, __uuidof(IFileSaveDialog), (void**)d.GetAddressOf()))) return {};
  d->SetTitle(title);
  d->SetFileName(defName);
  COMDLG_FILTERSPEC fs[1] = {{L"JSON", L"*.json"}};
  d->SetFileTypes(1, fs);
  d->SetDefaultExtension(L"json");
  if (FAILED(d->Show(owner))) return {};
  ComPtr<IShellItem> it;
  PWSTR p = nullptr;
  if (SUCCEEDED(d->GetResult(&it)) && SUCCEEDED(it->GetDisplayName(SIGDN_FILESYSPATH, &p))) return takeCo(p);
  return {};
}

std::wstring wallpaperPath() {
  wchar_t p[MAX_PATH * 2] = {};
  if (SystemParametersInfoW(SPI_GETDESKWALLPAPER, MAX_PATH * 2, p, 0) && p[0] && fileExists(p)) return p;
  return {};
}

void refreshEnvironment() {
  // Programs we launch inherit our variables, so pick up PATH changes made while running.
  using Fn = BOOL(WINAPI*)(void**, BOOL);
  static Fn fn = (Fn)(void*)GetProcAddress(GetModuleHandleW(L"shell32.dll"), "RegenerateUserEnvironment");
  void* env = nullptr;
  if (fn) fn(&env, TRUE);
}

}  // namespace rt
