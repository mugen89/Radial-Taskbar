#include "install.h"

#include <commctrl.h>

#include "shellutil.h"

namespace rt {

std::wstring knownFolder(REFKNOWNFOLDERID id) {
  PWSTR p = nullptr;
  std::wstring s;
  if (SUCCEEDED(SHGetKnownFolderPath(id, KF_FLAG_CREATE, nullptr, &p))) s = p;
  CoTaskMemFree(p);
  return s;
}

std::wstring defaultInstallDir() { return joinPath(knownFolder(FOLDERID_LocalAppData), L"Programs\\" RT_NAME); }

static std::wstring regString(const wchar_t* name) {
  wchar_t v[1200];
  DWORD cb = sizeof v;
  if (RegGetValueW(HKEY_CURRENT_USER, kUninstallKey, name, RRF_RT_REG_SZ, nullptr, v, &cb) != ERROR_SUCCESS) return {};
  return v;
}
std::wstring installedDir() {
  std::wstring d = regString(L"InstallLocation");
  return !d.empty() && fileExists(joinPath(d, kExeName)) ? d : std::wstring();
}
std::wstring installedVersion() { return regString(L"DisplayVersion"); }

std::wstring startMenuLink() { return joinPath(knownFolder(FOLDERID_Programs), RT_NAME L".lnk"); }
std::wstring desktopLink() { return joinPath(knownFolder(FOLDERID_Desktop), RT_NAME L".lnk"); }
std::wstring sendToLink() { return joinPath(knownFolder(FOLDERID_SendTo), RT_NAME L".lnk"); }

// One verb for everything on disk: files, folders, shortcuts. A separate data folder is a separate copy of the
// program (used by the automated checks) and keeps a verb of its own.
static std::wstring fileMenuKey() {
  std::wstring k = L"Software\\Classes\\AllFilesystemObjects\\shell\\" RT_ID;
  if (GetEnvironmentVariableW(L"RADIALTASKBAR_DATA", nullptr, 0) > 0) k += L".alt";
  return k;
}
static std::wstring fileMenuCommand() {
  wchar_t v[1400];
  DWORD cb = sizeof v;
  return RegGetValueW(HKEY_CURRENT_USER, (fileMenuKey() + L"\\command").c_str(), nullptr, RRF_RT_REG_SZ, nullptr, v, &cb) == ERROR_SUCCESS ? std::wstring(v) : std::wstring();
}

bool fileMenuOn(const std::wstring& exe) {
  std::wstring c = fileMenuCommand();
  return !c.empty() && (exe.empty() || toLower(c).find(toLower(L"\"" + exe + L"\"")) != std::wstring::npos);
}

static void dropIfEmpty(const wchar_t* key) {
  HKEY k;
  DWORD subs = 1, vals = 1;
  if (RegOpenKeyExW(HKEY_CURRENT_USER, key, 0, KEY_READ, &k) != ERROR_SUCCESS) return;
  bool known = RegQueryInfoKeyW(k, nullptr, nullptr, nullptr, &subs, nullptr, nullptr, &vals, nullptr, nullptr, nullptr, nullptr) == ERROR_SUCCESS;
  RegCloseKey(k);
  if (known && !subs && !vals) RegDeleteKeyW(HKEY_CURRENT_USER, key);
}

void setFileMenu(bool on, const std::wstring& exe) {
  std::wstring key = fileMenuKey();
  if (on) {
    auto put = [&](const std::wstring& k, const wchar_t* name, const std::wstring& v) {
      RegSetKeyValueW(HKEY_CURRENT_USER, k.c_str(), name, REG_SZ, v.c_str(), (DWORD)((v.size() + 1) * sizeof(wchar_t)));
    };
    put(key, L"MUIVerb", L"Add to " RT_NAME);
    put(key, L"Icon", L"\"" + exe + L"\",0");
    put(key, L"MultiSelectModel", L"Document");
    put(key, L"NoWorkingDirectory", L"");
    put(key + L"\\command", nullptr, L"\"" + exe + L"\" --pin \"%1\"");
  } else {
    RegDeleteTreeW(HKEY_CURRENT_USER, key.c_str());
    dropIfEmpty(L"Software\\Classes\\AllFilesystemObjects\\shell");
    dropIfEmpty(L"Software\\Classes\\AllFilesystemObjects");
  }
  SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, nullptr, nullptr);
}

std::vector<std::wstring> includedSkins(const std::string& list) {
  std::vector<std::wstring> out;
  for (size_t at = 0; at < list.size();) {
    size_t e = std::min(list.find('\n', at), list.size());
    std::wstring n = trim(widen(list.substr(at, e - at)));
    if (n.size() < 80 && fileExt(n) == L".rskin" && n.find_first_of(L"\\/:") == std::wstring::npos) out.push_back(n);
    at = e + 1;
  }
  return out;
}

static const wchar_t* const kSkinExt = L"Software\\Classes\\.rskin";
static const wchar_t* const kSkinType = L"Software\\Classes\\" RT_ID L".Skin";

void setSkinType(bool on, const std::wstring& exe) {
  auto put = [](const std::wstring& k, const std::wstring& v) { RegSetKeyValueW(HKEY_CURRENT_USER, k.c_str(), nullptr, REG_SZ, v.c_str(), (DWORD)((v.size() + 1) * sizeof(wchar_t))); };
  if (on) {
    put(kSkinExt, RT_ID L".Skin");
    put(kSkinType, L"Radial Taskbar skin");
    put(std::wstring(kSkinType) + L"\\DefaultIcon", L"\"" + exe + L"\",0");
    put(std::wstring(kSkinType) + L"\\shell\\open\\command", L"\"" + exe + L"\" --add-skin \"%1\"");
  } else {
    RegDeleteTreeW(HKEY_CURRENT_USER, kSkinType);
    wchar_t v[128];
    DWORD cb = sizeof v;
    if (RegGetValueW(HKEY_CURRENT_USER, kSkinExt, nullptr, RRF_RT_REG_SZ, nullptr, v, &cb) == ERROR_SUCCESS && !wcscmp(v, RT_ID L".Skin")) RegDeleteTreeW(HKEY_CURRENT_USER, kSkinExt);
  }
  SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, nullptr, nullptr);
}

bool skinTypeIs(const std::wstring& dir) {
  wchar_t v[1400];
  DWORD cb = sizeof v;
  return RegGetValueW(HKEY_CURRENT_USER, (std::wstring(kSkinType) + L"\\shell\\open\\command").c_str(), nullptr, RRF_RT_REG_SZ, nullptr, v, &cb) == ERROR_SUCCESS &&
         toLower(v).find(toLower(dir)) != std::wstring::npos;
}

std::wstring betaDir() {
  wchar_t v[1200];
  DWORD cb = sizeof v;
  if (RegGetValueW(HKEY_CURRENT_USER, L"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\" RT_BETA_ID, L"InstallLocation", RRF_RT_REG_SZ, nullptr, v, &cb) != ERROR_SUCCESS) return {};
  return fileExists(joinPath(v, RT_BETA_EXE)) ? std::wstring(v) : std::wstring();
}

bool betaThere() { return !betaDir().empty() || FindWindowW(RT_BETA_ID L"Hidden", nullptr); }

// Its own uninstaller knows what it put where. It runs on in a copy in the temp folder, so we wait for the result.
bool removeBeta(DWORD waitMs) {
  double end = nowSec() + waitMs / 1000.0;
  if (!quitApp(RT_BETA_ID, waitMs / 2)) return false;
  std::wstring dir = betaDir();
  if (dir.empty()) return true;
  std::wstring exe = joinPath(dir, RT_BETA_EXE), cmd = L"\"" + exe + L"\" --uninstall --silent";
  STARTUPINFOW si{};
  si.cb = sizeof si;
  PROCESS_INFORMATION pi{};
  if (!CreateProcessW(exe.c_str(), cmd.data(), nullptr, nullptr, FALSE, 0, nullptr, dir.c_str(), &si, &pi)) return false;
  WaitForSingleObject(pi.hProcess, 5000);
  CloseHandle(pi.hThread);
  CloseHandle(pi.hProcess);
  while (!betaDir().empty() && nowSec() < end) Sleep(150);
  return betaDir().empty();
}

static void deleteFiles(const std::wstring& dir, const wchar_t* pattern) {
  WIN32_FIND_DATAW f;
  HANDLE h = FindFirstFileW(joinPath(dir, pattern).c_str(), &f);
  if (h == INVALID_HANDLE_VALUE) return;
  do DeleteFileW(joinPath(dir, f.cFileName).c_str());
  while (FindNextFileW(h, &f));
  FindClose(h);
}

static void closeSettings(const wchar_t* id, double end);

bool quitApp(const wchar_t* id, DWORD waitMs) {
  double end = nowSec() + waitMs / 1000.0;
  std::wstring hidden = std::wstring(id) + L"Hidden";
  closeSettings(id, end);
  for (;;) {
    HWND h = FindWindowW(hidden.c_str(), nullptr);
    if (!h) return true;
    DWORD pid = 0;
    GetWindowThreadProcessId(h, &pid);
    HANDLE p = OpenProcess(SYNCHRONIZE, FALSE, pid);
    std::wstring msg = L"quit\n";
    COPYDATASTRUCT cd{0x5254, (DWORD)((msg.size() + 1) * sizeof(wchar_t)), msg.data()};
    DWORD_PTR res = 0;
    SendMessageTimeoutW(h, WM_COPYDATA, 0, (LPARAM)&cd, SMTO_ABORTIFHUNG, 2000, &res);
    bool gone = false;
    if (p) {
      double left = std::max(0.0, end - nowSec());
      gone = WaitForSingleObject(p, (DWORD)(left * 1000.0)) == WAIT_OBJECT_0;
      CloseHandle(p);
    } else {
      Sleep(400);
    }
    if (!gone && nowSec() >= end) return FindWindowW(hidden.c_str(), nullptr) == nullptr;
  }
}

// The settings window is its own process and keeps the exe in use too.
static void closeSettings(const wchar_t* id, double end) {
  std::wstring cls = std::wstring(id) + L"Settings";
  for (int i = 0; i < 2; i++) {
    HWND s = FindWindowW(cls.c_str(), nullptr);
    if (!s) return;
    DWORD pid = 0;
    GetWindowThreadProcessId(s, &pid);
    HANDLE p = OpenProcess(SYNCHRONIZE, FALSE, pid);
    PostMessageW(s, WM_CLOSE, 0, 0);
    if (p) {
      WaitForSingleObject(p, (DWORD)(std::max(0.2, end - nowSec()) * 1000.0));
      CloseHandle(p);
    }
  }
}

// ---------------------------------------------------------------- uninstall
static bool isOurs(const std::wstring& lnk) {
  LinkInfo li;
  return fileExists(lnk) && readLink(lnk, li) && toLower(fileName(li.target)) == toLower(kExeName);
}

int runUninstall(const std::vector<std::wstring>& args) {
  bool silent = false, purge = false;
  for (auto& a : args) {
    if (a == L"--silent") silent = true;
    if (a == L"--purge") purge = true;
  }
  std::wstring dir = dirName(modulePath());
  if (!silent) {
    TASKDIALOG_BUTTON btn[] = {{IDOK, L"Uninstall"}};
    TASKDIALOGCONFIG c{};
    c.cbSize = sizeof c;
    c.hInstance = GetModuleHandleW(nullptr);
    c.dwFlags = TDF_ALLOW_DIALOG_CANCELLATION | TDF_POSITION_RELATIVE_TO_WINDOW;
    c.dwCommonButtons = TDCBF_CANCEL_BUTTON;
    c.pszWindowTitle = kAppName;
    c.pszMainIcon = MAKEINTRESOURCEW(1);
    c.pszMainInstruction = L"Uninstall " RT_NAME L"?";
    c.pszContent = L"The program, its shortcuts and its startup entry will be removed.";
    c.pszVerificationText = L"Also delete my pins, profiles, styles and skins";
    c.pButtons = btn;
    c.cButtons = 1;
    int pressed = 0;
    BOOL checked = FALSE;
    if (FAILED(TaskDialogIndirect(&c, &pressed, nullptr, &checked)) || pressed != IDOK) return 0;
    purge = checked != FALSE;
  }
  // A running program cannot delete itself, so a copy in the temp folder finishes the job.
  std::wstring tmp = joinPath(knownFolder(FOLDERID_LocalAppData), L"Temp\\" RT_ID L"-Uninstall");
  SHCreateDirectoryExW(nullptr, tmp.c_str(), nullptr);
  std::wstring exe = joinPath(tmp, kExeName);
  if (!CopyFileW(modulePath().c_str(), exe.c_str(), FALSE)) return 1;
  std::wstring cmd = L"\"" + exe + L"\" --uninstall-run \"" + dir + L"\"" + (silent ? L" --silent" : L"") + (purge ? L" --purge" : L"");
  STARTUPINFOW si{};
  si.cb = sizeof si;
  PROCESS_INFORMATION pi{};
  if (!CreateProcessW(exe.c_str(), cmd.data(), nullptr, nullptr, FALSE, 0, nullptr, tmp.c_str(), &si, &pi)) return 1;
  CloseHandle(pi.hThread);
  CloseHandle(pi.hProcess);
  return 0;
}

int runUninstallStage2(const std::wstring& dir, bool silent, bool purge) {
  // Only ever remove a folder that really holds this program.
  if (dir.size() < 4 || !fileExists(joinPath(dir, kExeName))) return 2;
  if (!quitRunningApp(6000)) {
    if (!silent) MessageBoxW(nullptr, RT_NAME L" is still running. Close it and try again.", kAppName, MB_ICONWARNING);
    return 3;
  }
  wchar_t run[1200];
  DWORD cb = sizeof run;
  const wchar_t* runKey = L"Software\\Microsoft\\Windows\\CurrentVersion\\Run";
  if (RegGetValueW(HKEY_CURRENT_USER, runKey, kRunValue, RRF_RT_REG_SZ, nullptr, run, &cb) == ERROR_SUCCESS && toLower(run).find(toLower(dir)) != std::wstring::npos)
    RegDeleteKeyValueW(HKEY_CURRENT_USER, runKey, kRunValue);
  for (auto& l : {startMenuLink(), desktopLink(), sendToLink()})
    if (isOurs(l)) DeleteFileW(l.c_str());
  if (toLower(fileMenuCommand()).find(toLower(dir)) != std::wstring::npos) setFileMenu(false, L"");
  if (skinTypeIs(dir)) setSkinType(false, L"");
  std::wstring skinDir = joinPath(dir, L"skins");
  std::string list;
  if (readFile(joinPath(skinDir, kIncluded), list)) {  // only what came with the program
    for (auto& n : includedSkins(list)) DeleteFileW(joinPath(skinDir, n).c_str());
    DeleteFileW(joinPath(skinDir, kIncluded).c_str());
  } else {
    deleteFiles(skinDir, L"*.rskin");
  }
  RemoveDirectoryW(skinDir.c_str());
  DeleteFileW(joinPath(dir, L"SKINS.md").c_str());
  for (int i = 0; i < 20 && !DeleteFileW(joinPath(dir, kUninstaller).c_str()) && GetLastError() != ERROR_FILE_NOT_FOUND; i++) Sleep(150);  // it may still be closing

  std::wstring exe = joinPath(dir, kExeName);
  bool gone = false;
  for (int i = 0; i < 40 && !gone; i++) {  // the first stage may still be exiting
    gone = DeleteFileW(exe.c_str()) || GetLastError() == ERROR_FILE_NOT_FOUND;
    if (!gone) Sleep(150);
  }
  RemoveDirectoryW(dir.c_str());  // only succeeds when nothing else is in there
  if (gone) RegDeleteTreeW(HKEY_CURRENT_USER, kUninstallKey);

  // The icon cache is not the person's data: always clean it up.
  std::wstring cd = cacheDir();
  if (toLower(fileName(cd)) == toLower(RT_ID)) {
    sweepCache(true);
    deleteFiles(joinPath(cd, L"skins"), L"*.px*");
    RemoveDirectoryW(joinPath(cd, L"skins").c_str());
    WIN32_FIND_DATAW cf;
    std::wstring ic = joinPath(cd, L"icons");
    HANDLE ch = FindFirstFileW(joinPath(ic, L"*.rti").c_str(), &cf);
    if (ch != INVALID_HANDLE_VALUE) {
      do DeleteFileW(joinPath(ic, cf.cFileName).c_str());
      while (FindNextFileW(ch, &cf));
      FindClose(ch);
    }
    RemoveDirectoryW(ic.c_str());
    RemoveDirectoryW(cd.c_str());
  }

  if (purge) {
    std::wstring d = dataDir();
    if (toLower(fileName(d)) == toLower(RT_ID)) {
      if (std::wstring sk = joinPath(d, L"skins"); dirExists(sk)) {  // perhaps made by hand: the recycle bin, not gone for good
        sk.push_back(L'\0');
        SHFILEOPSTRUCTW op{};
        op.wFunc = FO_DELETE;
        op.pFrom = sk.c_str();
        op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI;
        SHFileOperationW(&op);
      }
      for (const wchar_t* f : {L"config.json", L"config.json.bak", L"config.json.broken", L"config.json.before-import"}) DeleteFileW(joinPath(d, f).c_str());
      WIN32_FIND_DATAW fd;
      struct { const wchar_t* dir; const wchar_t* files; } kept[] = {{L"links", L"*.lnk"}, {L"images", L"*.png"}};
      for (auto& k : kept) {
        std::wstring sub = joinPath(d, k.dir);
        HANDLE h = FindFirstFileW(joinPath(sub, k.files).c_str(), &fd);
        if (h != INVALID_HANDLE_VALUE) {
          do DeleteFileW(joinPath(sub, fd.cFileName).c_str());
          while (FindNextFileW(h, &fd));
          FindClose(h);
        }
        RemoveDirectoryW(sub.c_str());
      }
      RemoveDirectoryW(d.c_str());
    }
  }
  if (!silent)
    MessageBoxW(nullptr, gone ? RT_NAME L" was removed." : L"Some files are in use and could not be removed.", kAppName, gone ? MB_ICONINFORMATION : MB_ICONWARNING);
  return gone ? 0 : 4;
}

}  // namespace rt
