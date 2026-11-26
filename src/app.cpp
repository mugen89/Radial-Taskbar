#include "app.h"

#include <process.h>

#include <atomic>

#include "icons.h"
#include "install.h"
#include "picture.h"
#include "settings.h"
#include "sitelogo.h"
#include "skin.h"

namespace rt {

namespace {
enum Timers : UINT_PTR { kSaveTimer = 1, kRestTimer, kWarmTimer, kRetryTimer, kReadTimer, kResumeTimer, kLogoTimer, kSkinTimer };
enum Menu : UINT { kMenuOpen = 1, kMenuSettings, kMenuAutostart, kMenuQuit, kMenuProfile0 = 100, kMenuSkin0 = 1000 };

struct PinJob {
  HWND target, notify;
};
unsigned __stdcall pinThread(void* p) {
  std::unique_ptr<PinJob> j((PinJob*)p);
  auto* pin = new Pin(pinFromWindowHelper(j->target));
  if (!PostMessageW(j->notify, WM_APP_PIN, 0, (LPARAM)pin)) delete pin;
  return 0;
}

struct LogoResult {
  uint32_t serial;
  std::wstring url;
  bool isImage;
  HWND notify;
  SiteInfo info;
};
unsigned __stdcall logoThread(void* p) {
  auto* r = (LogoResult*)p;
  askSite(r->url, r->isImage, r->info);
  if (!PostMessageW(r->notify, WM_APP_LOGO, 0, (LPARAM)r)) delete r;
  return 0;
}

// Scanners hold freshly written files for a moment, so the write (and its retries) must not be felt.
SRWLOCK g_saveLock = SRWLOCK_INIT;
std::atomic<uint32_t> g_saveSeq{0};
struct SaveJob {
  std::string text;
  uint32_t seq;
  HWND notify;
};
unsigned __stdcall saveThread(void* p) {
  std::unique_ptr<SaveJob> j((SaveJob*)p);
  AcquireSRWLockExclusive(&g_saveLock);
  bool current = j->seq == g_saveSeq;  // a newer save makes this one pointless
  bool ok = !current || writeFileAtomic(Config::path(), j->text, true);
  ReleaseSRWLockExclusive(&g_saveLock);
  if (current) PostMessageW(j->notify, WM_APP_SAVED, ok, (LPARAM)j->seq);
  return 0;
}

// Runs a message loop that also paces one or two frame-latency waitable swap chains.
template <class Frames>
void pump(Frames&& frames) {
  MSG msg;
  for (;;) {
    HANDLE waits[2];
    DWORD n = 0, timeout = INFINITE;
    frames.collect(waits, n, timeout);
    DWORD r = MsgWaitForMultipleObjectsEx(n, waits, timeout, QS_ALLINPUT, MWMO_INPUTAVAILABLE);
    while (PeekMessageW(&msg, nullptr, 0, 0, PM_REMOVE)) {
      if (msg.message == WM_QUIT) return;
      TranslateMessage(&msg);
      DispatchMessageW(&msg);
    }
    if (r == WAIT_TIMEOUT || r < WAIT_OBJECT_0 + n) frames.draw();
  }
}
}  // namespace

std::wstring instanceSuffix() {
  // A separate data folder means a separate instance (used by the automated checks).
  return GetEnvironmentVariableW(L"RADIALTASKBAR_DATA", nullptr, 0) > 0 ? L".alt" : L"";
}
std::wstring settingsWindowClass() { return RT_ID L"Settings" + instanceSuffix(); }
std::wstring hiddenWindowClass() { return RT_ID L"Hidden" + instanceSuffix(); }

static bool sendTo(HWND other, ULONG_PTR tag, const std::wstring& cmd, const std::wstring& arg, UINT flags) {
  if (!other) return false;
  DWORD pid = 0;
  GetWindowThreadProcessId(other, &pid);
  AllowSetForegroundWindow(pid);
  std::wstring payload = cmd + L"\n" + arg;
  COPYDATASTRUCT cd{tag, (DWORD)((payload.size() + 1) * sizeof(wchar_t)), payload.data()};
  DWORD_PTR res = 0;
  return SendMessageTimeoutW(other, WM_COPYDATA, 0, (LPARAM)&cd, SMTO_ABORTIFHUNG | flags, 3000, &res) != 0 && res;
}
bool sendCommand(const std::wstring& cmd, const std::wstring& arg, bool block) {
  return sendTo(FindWindowW(hiddenWindowClass().c_str(), nullptr), kCmdToResident, cmd, arg, block ? SMTO_BLOCK : 0);
}
bool splitCommand(const void* copyData, ULONG_PTR tag, std::wstring& cmd, std::wstring& arg) {
  auto* cd = (const COPYDATASTRUCT*)copyData;
  if (!cd || cd->dwData != tag || cd->cbData < 2 || cd->cbData > 262144 || !cd->lpData) return false;
  std::wstring s((const wchar_t*)cd->lpData, cd->cbData / sizeof(wchar_t));
  while (!s.empty() && s.back() == 0) s.pop_back();
  size_t nl = s.find(L'\n');
  cmd = s.substr(0, nl);
  arg = nl == std::wstring::npos ? L"" : s.substr(nl + 1);
  return true;
}

static HWND findSettings() { return FindWindowW(settingsWindowClass().c_str(), nullptr); }

App::App() : overlay(*this) {}
App::~App() = default;

bool App::makeHiddenWindow(const std::wstring& cls) {
  WNDCLASSEXW wc{};
  wc.cbSize = sizeof wc;
  wc.lpfnWndProc = proc;
  wc.hInstance = inst_;
  wc.lpszClassName = cls.c_str();
  wc.hIcon = LoadIconW(inst_, MAKEINTRESOURCEW(1));
  RegisterClassExW(&wc);
  // A real (never shown) top-level window, so it hears TaskbarCreated and settings broadcasts.
  hwnd_ = CreateWindowExW(WS_EX_TOOLWINDOW, cls.c_str(), RT_NAME, WS_POPUP, 0, 0, 0, 0, nullptr, nullptr, inst_, this);
  return hwnd_ != nullptr;
}

// ---------------------------------------------------------------- the resident process
int App::run(HINSTANCE inst, const Args& args) {
  inst_ = inst;
  std::wstring cmd, arg;
  if (args.has(L"--quit")) cmd = L"quit";
  else if (args.has(L"--open")) cmd = L"open";
  else if (args.has(L"--settings")) cmd = L"settings";
  else if (args.has(L"--pin")) {
    cmd = L"pin";
    bool on = false;
    for (auto& a : args.v) {  // Send To passes every selected file
      if (on) arg += (arg.empty() ? L"" : L"\n") + a;
      if (a == L"--pin") on = true;
    }
  }

  HANDLE mutex = CreateMutexW(nullptr, TRUE, (L"Local\\" RT_ID L".Instance" + instanceSuffix()).c_str());
  if (GetLastError() == ERROR_ALREADY_EXISTS) {
    if (cmd.empty() && !args.has(L"--background")) cmd = L"settings";
    if (!cmd.empty()) sendCommand(cmd, arg);
    if (mutex) CloseHandle(mutex);
    return 0;
  }
  if (cmd == L"quit") {
    ReleaseMutex(mutex);
    CloseHandle(mutex);
    return 0;
  }

  SetThreadPriority(GetCurrentThread(), THREAD_PRIORITY_ABOVE_NORMAL);  // answer the shortcut promptly on a busy PC
  SetCurrentProcessExplicitAppUserModelID(kAppUserModelId);
  taskbarCreated_ = RegisterWindowMessageW(L"TaskbarCreated");
  if (!makeHiddenWindow(hiddenWindowClass())) return 1;

  Config::Load st = cfg.load();
  bool loaded = st == Config::Load::Ok;
  if (st != Config::Load::Unreadable && takeOverBeta()) {
    st = Config::Load::Ok;
    loaded = true;
  }
  if (st == Config::Load::Unreadable) {  // something is holding the file: run, but never write over it
    cfg.locked = true;
    cfg.sanitize();
    SetTimer(hwnd_, kReadTimer, 3000, nullptr);
  } else if (!loaded || cfg.firstRun) {
    firstRun();
  }
  icons().start(hwnd_, WM_APP_ICON, 144, IconCache::Mode::Helper);
  hotkeys.init(hwnd_, WM_APP_HOTKEY, WM_APP_KEY);
  if (!overlay.create(inst)) return 1;
  hotkeys.apply(cfg.hotkey);
  updateTray();
  watch_.apply(cfg.taskbarMenu);
  SetTimer(hwnd_, kWarmTimer, 1200, nullptr);
  if (loaded && cfg.version < Config::kVersion) SetTimer(hwnd_, kLogoTimer, 4000, nullptr);

  bool background = args.has(L"--background");
  if (!hotkeys.ok()) {
    SetTimer(hwnd_, kRetryTimer, 20000, nullptr);
    notify(L"Shortcut is taken", hotkeyText(cfg.hotkey) + L" is used by another program. Choose another one in Settings.");
  } else if (st == Config::Load::Missing) {
    notify(RT_NAME L" is ready", L"Press " + hotkeyText(cfg.hotkey) + L" to open it.");
  }
  if (!cmd.empty()) runCommand(cmd, arg);
  else if (!background) openSettings(st == Config::Load::Missing ? SettingsWindow::kSkins : -1);  // the first thing to see

  struct Frames {
    Overlay& o;
    void collect(HANDLE* w, DWORD& n, DWORD& t) {
      if (!o.wantsFrame()) return;
      if (o.frameHandle()) w[n++] = o.frameHandle();
      else t = 8;
    }
    void draw() {
      if (o.wantsFrame()) o.frame();
    }
  };
  pump(Frames{overlay});

  if (dirty_) saveNow(true);
  if (HWND s = findSettings()) PostMessageW(s, WM_CLOSE, 0, 0);
  watch_.apply(false);
  hotkeys.shutdown();
  if (trayOn_) {
    NOTIFYICONDATAW ni{};
    ni.cbSize = sizeof ni;
    ni.hWnd = hwnd_;
    ni.uID = 1;
    Shell_NotifyIconW(NIM_DELETE, &ni);
  }
  overlay.destroy();
  icons().stop();
  gfx().release();
  DestroyWindow(hwnd_);
  hwnd_ = nullptr;
  ReleaseMutex(mutex);
  CloseHandle(mutex);
  return 0;
}

static void copyTree(const std::wstring& from, const std::wstring& to, int depth = 0) {
  WIN32_FIND_DATAW f;
  HANDLE h = depth < 6 ? FindFirstFileW(joinPath(from, L"*").c_str(), &f) : INVALID_HANDLE_VALUE;
  if (h == INVALID_HANDLE_VALUE) return;
  SHCreateDirectoryExW(nullptr, to.c_str(), nullptr);
  do {
    std::wstring n = f.cFileName;
    if (n == L"." || n == L".." || (f.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT)) continue;
    if (f.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) copyTree(joinPath(from, n), joinPath(to, n), depth + 1);
    else CopyFileW(joinPath(from, n).c_str(), joinPath(to, n).c_str(), TRUE);
  } while (FindNextFileW(h, &f));
  FindClose(h);
}

// Radial Taskbar 2 was the test version with skins. What was set up there comes along once: pins, profiles, looks,
// skins, and the pictures and shortcuts the pins use. The first version kept its settings in our folder: a copy stays.
bool App::takeOverBeta() {
  wchar_t env[1024];
  DWORD n = GetEnvironmentVariableW(RT_ID L"_BETA", env, 1024);
  std::wstring from;
  if (n > 0 && n < 1024) from = env;  // for the checks
  else if (instanceSuffix().empty()) from = joinPath(knownFolder(FOLDERID_RoamingAppData), RT_BETA_ID);
  std::wstring mark = joinPath(dataDir(), L"taken-over.txt");
  std::string text;
  Json j;
  if (from.empty() || fileExists(mark) || !readFile(joinPath(from, L"config.json"), text) || !Json::parse(text, j) || !j.isObj() || !j.find("profiles")) return false;
  std::wstring own = Config::path();
  if (fileExists(own)) CopyFileW(own.c_str(), (own + L".first-version").c_str(), FALSE);
  std::string chosen = cfg.firstRun ? cfg.skin : std::string();  // opened by double-click before the very first start
  cfg = Config();
  cfg.fromJson(j);
  auto take = [&](std::wstring& path, const wchar_t* sub, const std::wstring& to) {
    if (path.empty() || toLower(dirName(path)) != toLower(joinPath(from, sub))) return;
    SHCreateDirectoryExW(nullptr, to.c_str(), nullptr);
    std::wstring copy = joinPath(to, fileName(path));
    if (CopyFileW(path.c_str(), copy.c_str(), FALSE)) path = copy;
  };
  auto each = [&](Pin& p) {
    take(p.icon, L"images", imagesDir());
    take(p.target, L"links", linksDir());
  };
  for (auto& pr : cfg.profiles)
    for (auto& p : pr.pins) {
      each(p);
      for (auto& c : p.children) each(c);
    }
  copyTree(joinPath(from, L"skins"), SkinStore::userDir());  // folders made for editing included
  cfg.firstRun = false;
  if (!chosen.empty()) cfg.chooseSkin(chosen);
  writeFileAtomic(mark, "The settings of " + narrow(RT_BETA_NAME) + " were taken over from " + narrow(from) + "\n");
  logf("config: took over %zu profiles from the test version", cfg.profiles.size());
  return cfg.save();
}

void App::firstRun() {
  cfg.sanitize();
  Profile& p = cfg.profile();
  if (p.pins.empty()) {
    for (auto& q : importTaskbarPins())
      if (!alreadyPinned(p.pins, q)) {
        adoptPin(q);
        p.pins.push_back(q);
      }
    if (p.pins.size() < 3) {
      // An empty wheel teaches nothing; start with a few things everyone has.
      auto add = [&](const wchar_t* name, const wchar_t* path) {
        Pin q = pinFromPath(expandEnv(path));
        q.name = name;
        if (!alreadyPinned(p.pins, q)) p.pins.push_back(q);
      };
      add(L"File Explorer", L"%WINDIR%\\explorer.exe");
      add(L"Notepad", L"%WINDIR%\\System32\\notepad.exe");
      add(L"Task Manager", L"%WINDIR%\\System32\\Taskmgr.exe");
      p.pins.push_back(pinFromUrl(L"ms-settings:", L"Windows Settings"));
    }
  }
  cfg.firstRun = false;
  cfg.save();
}

void App::warmIcons() {
  std::vector<std::wstring> keys;
  for (auto& pr : cfg.profiles)
    for (auto& p : pr.pins) {
      keys.push_back(IconCache::keyFor(p));
      for (auto& c : p.children) keys.push_back(IconCache::keyFor(c));
    }
  for (auto& k : keys) icons().request(k);
  if (role == Role::Resident) icons().keepOnly(std::move(keys));  // the settings window also shows apps that are not pinned
}

// ---------------------------------------------------------------- the settings process
int App::runSettings(HINSTANCE inst, const Args& args) {
  inst_ = inst;
  role = Role::Settings;
  int page = args.num(L"--page", -1);
  std::wstring addSkin = args.get(L"--add-skin");
  HANDLE mutex = CreateMutexW(nullptr, TRUE, (L"Local\\" RT_ID L".Settings" + instanceSuffix()).c_str());
  if (GetLastError() == ERROR_ALREADY_EXISTS) {
    HWND s = findSettings();
    for (int i = 0; i < 30 && !s; i++) {  // the other one may still be starting
      Sleep(100);
      s = findSettings();
    }
    if (s) {
      if (!addSkin.empty()) sendTo(s, kCmdToSettings, L"addskin", addSkin, 0);
      DWORD pid = 0;
      GetWindowThreadProcessId(s, &pid);
      AllowSetForegroundWindow(pid);
      PostMessageW(s, WM_APP_SHOW, (WPARAM)(INT_PTR)page, 0);
    }
    if (mutex) CloseHandle(mutex);
    return 0;
  }
  SetCurrentProcessExplicitAppUserModelID(kAppUserModelId);
  if (!makeHiddenWindow(RT_ID L"SettingsHost" + instanceSuffix())) return 1;
  if (cfg.load() == Config::Load::Unreadable) {
    MessageBoxW(nullptr, L"Your settings file is in use by another program right now. Please try again in a moment.", RT_NAME, MB_ICONINFORMATION);
    return 1;
  }
  cfg.sanitize();
  icons().start(hwnd_, WM_APP_ICON, 96);
  hotkeys.init(hwnd_, WM_APP_HOTKEY, WM_APP_KEY);
  settings_ = std::make_unique<SettingsWindow>(*this);
  settings_->show(addSkin.empty() ? page : SettingsWindow::kSkins);
  if (!addSkin.empty()) settings_->addSkins({addSkin}, true);

  struct Frames {
    SettingsWindow& s;
    void collect(HANDLE* w, DWORD& n, DWORD& t) {
      if (!s.wantsFrame()) return;
      if (s.frameHandle()) w[n++] = s.frameHandle();
      else t = 8;
    }
    void draw() {
      if (s.wantsFrame()) s.frame(true);
    }
  };
  pump(Frames{*settings_});

  if (dirty_) saveNow(true);
  if (!dirty_) sweepKept(cfg);
  hotkeys.shutdown();
  settings_.reset();
  icons().stop();
  gfx().release();
  DestroyWindow(hwnd_);
  hwnd_ = nullptr;
  ReleaseMutex(mutex);
  CloseHandle(mutex);
  return 0;
}

bool App::hotkeyOk() {
  if (role == Role::Resident) return hwnd_ ? hotkeys.ok() : true;
  if (nowSec() - okAt_ > 0.8) {
    okAt_ = nowSec();
    // It may be busy reading a skin: the answer comes later, this window does not wait for it.
    auto answer = [](HWND, UINT, ULONG_PTR p, LRESULT r) {
      auto* a = (App*)p;
      bool ok = (r & 1) != 0;
      if (ok != a->ok_ && a->settings_) a->settings_->invalidate();
      a->ok_ = ok;
    };
    HWND other = FindWindowW(hiddenWindowClass().c_str(), nullptr);
    if (!other || !SendMessageCallbackW(other, WM_APP_QUERY, 0, 0, answer, (ULONG_PTR)this)) ok_ = false;
  }
  return ok_;
}

void App::suspendHotkey(bool on) {
  if (role == Role::Resident) hotkeys.suspend(on);
  else sendCommand(on ? L"suspend" : L"resume");
}

void App::openWheel() {
  if (role == Role::Resident) {
    overlay.open(false);
    return;
  }
  if (dirty_) saveNow(true);
  if (!sendCommand(L"open")) {  // the resident part is not running: start it
    std::wstring cmd = L"\"" + modulePath() + L"\" --open";
    STARTUPINFOW si{};
    si.cb = sizeof si;
    PROCESS_INFORMATION pi{};
    if (CreateProcessW(modulePath().c_str(), cmd.data(), nullptr, nullptr, FALSE, 0, nullptr, nullptr, &si, &pi)) {
      AllowSetForegroundWindow(pi.dwProcessId);
      CloseHandle(pi.hThread);
      CloseHandle(pi.hProcess);
    }
  }
}

bool App::reloadFromDisk() {
  Config n;
  Config::Load st = n.load(5);
  if (st == Config::Load::Unreadable && role == Role::Resident) SetTimer(hwnd_, kReadTimer, 1500, nullptr);  // busy: look again soon
  if (st != Config::Load::Ok) return false;
  if (!cfg.locked && n.toJson().dump() == cfg.toJson().dump()) return true;
  bool key = !(n.hotkey == cfg.hotkey);
  cfg = std::move(n);
  dirty_ = false;
  forgetMatches();
  warmIcons();
  if (role == Role::Resident) {
    if (key || !hotkeys.ok()) hotkeys.apply(cfg.hotkey);
    updateTray();
    watch_.apply(cfg.taskbarMenu);
    overlay.reload();
    if (!cfg.skinNow().empty()) SetTimer(hwnd_, kSkinTimer, 900, nullptr);  // once the sliders have come to rest
  }
  return true;
}

// ---------------------------------------------------------------- actions
void App::saveSoon() {
  if (!hwnd_) return;
  changes_++;
  dirty_ = true;
  SetTimer(hwnd_, kSaveTimer, role == Role::Settings ? 250 : 500, nullptr);
}

void App::persist(const std::wstring& cmd, const std::wstring& arg) {
  HWND s = role == Role::Resident ? findSettings() : nullptr;
  if (!s || !sendTo(s, kCmdToSettings, cmd, arg, 0)) saveSoon();
}

static bool eachPinList(Config& c, const std::function<bool(std::vector<Pin>&)>& f) {
  for (auto& p : c.profiles)
    if (f(p.pins)) return true;
  return false;
}

void App::setProfile(int index) {
  cfg.activeProfile = clampi(index, 0, (int)cfg.profiles.size() - 1);
  persist(L"profile", std::to_wstring(cfg.activeProfile));
}
void App::setSkin(const std::string& id) {
  cfg.chooseSkin(id);
  persist(L"skin", widen(id));
}
bool App::unpin(const std::string& id) {
  if (!eachPinList(cfg, [&](std::vector<Pin>& v) { return removePin(v, id); })) return false;
  persist(L"unpin", widen(id));
  pinsChanged();
  return true;
}
bool App::ungroup(const std::string& id) {
  if (!eachPinList(cfg, [&](std::vector<Pin>& v) { return ungroupPin(v, id); })) return false;
  persist(L"ungroup", widen(id));
  pinsChanged();
  return true;
}

bool App::applyRemote(const std::wstring& cmd, const std::wstring& arg) {
  std::string id = narrow(arg);
  if (cmd == L"addskin") {
    if (settings_) settings_->addSkins({arg}, true);
    return true;
  }
  if (cmd == L"profile") {
    cfg.activeProfile = clampi((int)wcstol(arg.c_str(), nullptr, 10), 0, (int)cfg.profiles.size() - 1);
  } else if (cmd == L"skin") {
    cfg.chooseSkin(id);
  } else if (cmd == L"unpin") {
    if (!eachPinList(cfg, [&](std::vector<Pin>& v) { return removePin(v, id); })) return false;
  } else if (cmd == L"ungroup") {
    if (!eachPinList(cfg, [&](std::vector<Pin>& v) { return ungroupPin(v, id); })) return false;
  } else if (cmd == L"setlogo") {  // what a website answered to the resident part
    Json j;
    if (!Json::parse(id, j) || !j.isObj()) return false;
    if (!applyLogo(j.str("id"), widen(j.str("was")), widen(j.str("image")), widen(j.str("name")))) {
      sendCommand(L"reload", {}, true);  // something newer was chosen here: the resident must not keep its version
      return false;
    }
  } else if (cmd == L"addpin") {
    Pin p;
    std::string where;
    if (!pinParse(id, p, &where)) return false;
    Profile& to = cfg.profileById(where);
    if (alreadyPinned(to.pins, p)) return false;
    to.pins.push_back(std::move(p));
  } else {
    return false;
  }
  saveNow();
  pinsChanged();
  return true;
}

void App::saveNow(bool wait) {
  KillTimer(hwnd_, kSaveTimer);
  if (cfg.locked) return;
  auto* j = new SaveJob{cfg.toJson().dump(), ++g_saveSeq, hwnd_};
  savingChanges_ = changes_;
  dirty_ = true;
  if (!wait) {
    if (uintptr_t t = _beginthreadex(nullptr, 0, saveThread, j, 0, nullptr)) {
      CloseHandle((HANDLE)t);
      return;
    }
  }
  std::unique_ptr<SaveJob> own(j);
  AcquireSRWLockExclusive(&g_saveLock);
  bool ok = writeFileAtomic(Config::path(), own->text, true);
  ReleaseSRWLockExclusive(&g_saveLock);
  saved(ok, own->seq);
}

void App::saved(bool ok, uint32_t seq) {
  if (seq != g_saveSeq) return;  // something newer is on its way
  if (!ok) {                     // keep it pending and try again rather than lose it
    logf("config: save failed, will retry");
    if (!quitting_) SetTimer(hwnd_, kSaveTimer, 2000, nullptr);
    return;
  }
  dirty_ = changes_ != savingChanges_;  // something may have changed while this one was being written
  if (role == Role::Settings) sendCommand(L"reload", {}, true);
  else if (HWND s = findSettings()) PostMessageW(s, WM_APP_RELOAD, 0, 0);  // only when handing over failed
}

void App::pinsChanged() {
  warmIcons();
  if (settings_) settings_->invalidate();
}

void App::openSettings(int page) {
  if (dirty_) saveNow(true);
  if (HWND s = findSettings()) {
    DWORD pid = 0;
    GetWindowThreadProcessId(s, &pid);
    AllowSetForegroundWindow(pid);
    PostMessageW(s, WM_APP_SHOW, (WPARAM)(INT_PTR)page, 0);
    return;
  }
  std::wstring exe = modulePath(), cmd = L"\"" + exe + L"\" --settings-window";
  if (page >= 0) cmd += L" --page " + std::to_wstring(page);
  STARTUPINFOW si{};
  si.cb = sizeof si;
  PROCESS_INFORMATION pi{};
  if (CreateProcessW(exe.c_str(), cmd.data(), nullptr, nullptr, FALSE, 0, nullptr, nullptr, &si, &pi)) {
    AllowSetForegroundWindow(pi.dwProcessId);
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
  } else {
    logf("settings: could not start (%lu)", GetLastError());
  }
}

void App::settingsClosed() {
  if (dirty_) saveNow(true);
  // A logo that is still on its way would be lost with this process: the resident part asks again.
  if (role == Role::Settings) {
    for (auto& a : logos_)
      if (!a.isImage) sendCommand(L"logo", widen(a.pin), true);
    PostQuitMessage(0);
  }
}

void App::overlayHidden() {
  lastUse_ = nowSec();
  SetTimer(hwnd_, kRestTimer, 5000, nullptr);
  warmIcons();  // anything that failed earlier gets another chance
}

// Gives memory back once nothing has been on screen for a while.
void App::restIfIdle() {
  if (overlay.visible()) return;
  double idle = nowSec() - lastUse_;
  if (idle < 24.0) return;  // the timer ticks every 5 s and may come a hair early
  KillTimer(hwnd_, kRestTimer);
  if (!cfg.lowMemory) return;
  overlay.dropDevice();
  skinArt().dropDevice();
  skinArt().rest();
  gfx().release();
  struct { ULONG version, flags; } opt{1, 0};  // HEAP_OPTIMIZE_RESOURCES_INFORMATION
  HeapSetInformation(nullptr, (HEAP_INFORMATION_CLASS)3, &opt, sizeof opt);  // hand cached heap pages back
  SetProcessWorkingSetSize(GetCurrentProcess(), (SIZE_T)-1, (SIZE_T)-1);
  logf("app: idle for %.0f s, memory given back", idle);
}

bool App::addPin(Pin p, bool quiet, const std::string& profileId) {
  if (p.target.empty() && p.kind != Pin::Kind::Group) return false;
  if (cfg.locked) {
    if (!quiet) notify(L"Not pinned", L"Your settings file is in use by another program right now. Please try again in a moment.");
    return false;
  }
  Profile& to = cfg.profileById(profileId);
  if (p.kind != Pin::Kind::Group && alreadyPinned(to.pins, p)) {
    if (!quiet) notify(L"Already pinned", p.name + L" is already in " + to.name + L".");
    return false;
  }
  adoptPin(p);
  std::wstring name = p.name, into = to.name, text = widen(pinText(p, to.id));
  Pin copy = p;
  to.pins.push_back(std::move(p));
  if (role == Role::Resident) persist(L"addpin", text);
  else saveSoon();
  pinsChanged();
  wantLogo(copy);
  overlay.reload();
  if (!quiet && !overlay.visible()) notify(L"Pinned", name + L" was added to " + into + L".");
  return true;
}

// ---------------------------------------------------------------- website pictures
Pin* App::pinById(const std::string& id) {
  for (auto& pr : cfg.profiles)
    if (Pin* p = findPin(pr.pins, id)) return p;
  return nullptr;
}

void App::wantLogo(const Pin& p) {
  if (cfg.siteLogos && p.kind == Pin::Kind::Url && p.icon.empty() && isWebAddress(p.target)) fetchLogo(p.id, p.target);
}

bool App::logoBusy(const std::string& id) const {
  for (auto& a : logos_)
    if (a.pin == id) return true;
  return false;
}

void App::fetchLogo(const std::string& id, const std::wstring& url, const std::wstring& was, bool isImage) {
  if (!hwnd_ || !isWebAddress(url) || logoBusy(id)) return;
  logos_.push_back({++logoSerial_, id, url, was, isImage, false});
  startLogos();
}

// The answer to a cancelled question is dropped when it arrives.
void App::cancelLogo(const std::string& id) {
  logos_.erase(std::remove_if(logos_.begin(), logos_.end(), [&](const LogoAsk& a) { return a.pin == id; }), logos_.end());
}

void App::startLogos() {
  for (auto& a : logos_) {
    if (logosRunning_ >= 2) return;  // each one is a process of its own
    if (a.started) continue;
    auto* r = new LogoResult{a.serial, a.url, a.isImage, hwnd_, {}};
    uintptr_t t = _beginthreadex(nullptr, 0, logoThread, r, 0, nullptr);
    if (!t) {
      delete r;
      return;
    }
    CloseHandle((HANDLE)t);
    a.started = true;
    logosRunning_++;
  }
}

void App::logoAnswered(void* result) {
  std::unique_ptr<LogoResult> r((LogoResult*)result);
  logosRunning_--;
  auto it = std::find_if(logos_.begin(), logos_.end(), [&](const LogoAsk& a) { return a.serial == r->serial; });
  if (it != logos_.end()) {
    LogoAsk ask = *it;
    logos_.erase(it);
    bool done = settings_ && settings_->logoArrived(ask, r->info.image, r->info.name);
    if (!done && applyLogo(ask.pin, ask.was, r->info.image, r->info.name)) {
      if (role == Role::Resident) {
        Json j = Json::object();
        j.set("id", ask.pin);
        j.set("was", narrow(ask.was));
        j.set("image", narrow(r->info.image));
        j.set("name", narrow(r->info.name));
        persist(L"setlogo", widen(j.dump()));
      } else {
        saveSoon();
      }
      pinsChanged();
      if (Pin* p = pinById(ask.pin)) overlay.pinChanged(*p);
    }
  }
  startLogos();
  if (logos_.empty() && askingAll_) {
    askingAll_ = false;
    cfg.version = Config::kVersion;
    if (!findSettings()) saveSoon();
  }
}

bool App::applyLogo(const std::string& id, const std::wstring& was, const std::wstring& image, const std::wstring& siteName) {
  Pin* p = pinById(id);
  if (!p) return false;
  bool ch = false;
  if (!image.empty() && p->icon == was && p->icon != image) {
    p->icon = image;
    ch = true;
  }
  // The address stands in for a name until the site has told us its own.
  if (!siteName.empty() && p->kind == Pin::Kind::Url && toLower(p->name) == siteHost(p->target)) {
    p->name = siteName;
    ch = true;
  }
  return ch;
}

void App::pinWindow(HWND h) {
  auto* j = new PinJob{h, hwnd_};
  uintptr_t t = _beginthreadex(nullptr, 0, pinThread, j, 0, nullptr);
  if (t) CloseHandle((HANDLE)t);
  else delete j;
}

void App::applyHotkey() {
  if (role == Role::Settings) {
    saveNow(true);  // the resident must see it before we ask whether it works
    okAt_ = -10;
    return;
  }
  hotkeys.apply(cfg.hotkey);
  updateTray();
  saveSoon();
}

bool App::runCommand(const std::wstring& cmd, const std::wstring& arg) {
  if (cmd == L"open") overlay.open(false);
  else if (cmd == L"settings") openSettings();
  else if (cmd == L"quit") quit();
  else if (cmd == L"reload") reloadFromDisk();
  else if (cmd == L"suspend") {  // a new shortcut is being recorded
    hotkeys.suspend(true);
    SetTimer(hwnd_, kResumeTimer, 45000, nullptr);  // in case nobody tells us it is over
  } else if (cmd == L"resume") {
    KillTimer(hwnd_, kResumeTimer);
    hotkeys.suspend(false);
  }
  else if (cmd == L"logo") {
    if (Pin* p = pinById(narrow(arg))) wantLogo(*p);
  }
  else if (cmd == L"addpin") {  // from the row beside a taskbar menu, which shows how it went
    Pin p;
    std::string where;
    if (!pinParse(narrow(arg), p, &where)) return false;
    if (alreadyPinned(cfg.profileById(where).pins, p)) return true;  // there already is what was wanted
    return addPin(std::move(p), true, where);
  } else if (cmd == L"unpin") {
    if (cfg.locked || !unpin(narrow(arg))) return false;
    overlay.reload();
  }
  else if (cmd == L"pin" && !arg.empty()) {
    size_t at = 0;
    while (at <= arg.size()) {
      size_t nl = arg.find(L'\n', at);
      std::wstring one = arg.substr(at, nl == std::wstring::npos ? std::wstring::npos : nl - at);
      if (!one.empty()) addPin(pinFromPath(one));
      if (nl == std::wstring::npos) break;
      at = nl + 1;
    }
  }
  return true;
}

void App::quit() {
  if (quitting_) return;
  quitting_ = true;
  PostQuitMessage(0);
}

// ---------------------------------------------------------------- tray
void App::updateTray() {
  if (role != Role::Resident || !hwnd_) return;
  NOTIFYICONDATAW ni{};
  ni.cbSize = sizeof ni;
  ni.hWnd = hwnd_;
  ni.uID = 1;
  if (!cfg.trayIcon) {
    if (trayOn_) Shell_NotifyIconW(NIM_DELETE, &ni);
    trayOn_ = false;
    return;
  }
  ni.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP | NIF_SHOWTIP;
  ni.uCallbackMessage = WM_APP_TRAY;
  ni.hIcon = (HICON)LoadImageW(inst_, MAKEINTRESOURCEW(1), IMAGE_ICON, GetSystemMetrics(SM_CXSMICON), GetSystemMetrics(SM_CYSMICON), LR_SHARED);
  std::wstring tip = RT_NAME;
  if (hotkeys.ok()) tip += L"  (" + hotkeyText(cfg.hotkey) + L")";
  lstrcpynW(ni.szTip, tip.c_str(), 128);
  if (!trayOn_) {
    trayOn_ = Shell_NotifyIconW(NIM_ADD, &ni) != FALSE;
    ni.uVersion = NOTIFYICON_VERSION_4;
    Shell_NotifyIconW(NIM_SETVERSION, &ni);
  } else {
    Shell_NotifyIconW(NIM_MODIFY, &ni);
  }
}

void App::notify(const std::wstring& title, const std::wstring& text) {
  if (!trayOn_) return;
  NOTIFYICONDATAW ni{};
  ni.cbSize = sizeof ni;
  ni.hWnd = hwnd_;
  ni.uID = 1;
  ni.uFlags = NIF_INFO;
  ni.dwInfoFlags = NIIF_NONE | NIIF_NOSOUND;
  lstrcpynW(ni.szInfoTitle, title.c_str(), 64);
  lstrcpynW(ni.szInfo, text.c_str(), 256);
  Shell_NotifyIconW(NIM_MODIFY, &ni);
}

void App::trayMenu() {
  HMENU m = CreatePopupMenu();
  std::wstring open = L"Open wheel";
  if (hotkeys.ok()) open += L"\t" + hotkeyText(cfg.hotkey);
  AppendMenuW(m, MF_STRING, kMenuOpen, open.c_str());
  SetMenuDefaultItem(m, kMenuOpen, FALSE);
  if (cfg.unlockedCount() > 1) {
    HMENU sub = CreatePopupMenu();
    for (size_t i = 0; i < cfg.profiles.size(); i++)
      if (!cfg.profiles[i].locked) AppendMenuW(sub, MF_STRING | ((int)i == cfg.activeProfile ? MF_CHECKED : 0), kMenuProfile0 + i, cfg.profiles[i].name.c_str());
    AppendMenuW(m, MF_POPUP, (UINT_PTR)sub, L"Profile");
  }
  std::vector<std::string> skinIds{std::string()};
  if (HMENU sub = CreatePopupMenu()) {
    AppendMenuW(sub, MF_STRING | (cfg.skinNow().empty() ? MF_CHECKED : 0), kMenuSkin0, L"No skin");
    AppendMenuW(sub, MF_SEPARATOR, 0, nullptr);
    skins().refreshIfChanged();
    for (auto& k : skins().list()) {
      if (!k.error.empty() || skinIds.size() > 60 || cfg.hidden(k.id)) continue;
      AppendMenuW(sub, MF_STRING | (skinIds.size() % 17 == 0 ? MF_MENUBARBREAK : 0) | (cfg.skinNow() == k.id ? MF_CHECKED : 0), kMenuSkin0 + skinIds.size(), k.name.c_str());
      skinIds.push_back(k.id);
    }
    AppendMenuW(m, MF_POPUP, (UINT_PTR)sub, L"Skin");
  }
  AppendMenuW(m, MF_STRING, kMenuSettings, L"Settings");
  AppendMenuW(m, MF_SEPARATOR, 0, nullptr);
  AppendMenuW(m, MF_STRING | (autostartEnabled() ? MF_CHECKED : 0), kMenuAutostart, L"Start with Windows");
  AppendMenuW(m, MF_SEPARATOR, 0, nullptr);
  AppendMenuW(m, MF_STRING, kMenuQuit, L"Exit");
  POINT p;
  GetCursorPos(&p);
  SetForegroundWindow(hwnd_);
  UINT cmd = (UINT)TrackPopupMenuEx(m, TPM_RETURNCMD | TPM_RIGHTBUTTON | TPM_BOTTOMALIGN, p.x, p.y, hwnd_, nullptr);
  PostMessageW(hwnd_, WM_NULL, 0, 0);
  DestroyMenu(m);
  switch (cmd) {
    case 0: break;
    case kMenuOpen: overlay.open(false); break;
    case kMenuSettings: openSettings(); break;
    case kMenuAutostart: setAutostart(!autostartEnabled()); break;
    case kMenuQuit: quit(); break;
    default:
      if (cmd >= kMenuSkin0) {
        if (cmd - kMenuSkin0 < skinIds.size()) setSkin(skinIds[cmd - kMenuSkin0]);
        SetTimer(hwnd_, kSkinTimer, 300, nullptr);
      } else if (cmd >= kMenuProfile0 && cmd - kMenuProfile0 < cfg.profiles.size()) {
        setProfile((int)(cmd - kMenuProfile0));
      }
  }
}

// ---------------------------------------------------------------- messages
LRESULT CALLBACK App::proc(HWND h, UINT m, WPARAM w, LPARAM l) {
  if (m == WM_NCCREATE) SetWindowLongPtrW(h, GWLP_USERDATA, (LONG_PTR)((CREATESTRUCTW*)l)->lpCreateParams);
  auto* self = (App*)GetWindowLongPtrW(h, GWLP_USERDATA);
  return self && self->hwnd_ ? self->handle(m, w, l) : DefWindowProcW(h, m, w, l);
}

LRESULT App::handle(UINT m, WPARAM w, LPARAM l) {
  if (m == taskbarCreated_ && taskbarCreated_) {  // Explorer restarted
    trayOn_ = false;
    updateTray();
    return 0;
  }
  switch (m) {
    case WM_HOTKEY:
    case WM_APP_HOTKEY:
      if (cfg.blockFullscreen && !overlay.visible() && fullscreenAppRunning()) return 0;
      overlay.hotkeyAgain();
      return 0;
    case WM_APP_KEY: overlay.steer((UINT)w, (l & 1) != 0, (l & 2) != 0); return 0;
    case WM_APP_QUERY: return hotkeys.ok() ? 1 : 0;
    case WM_APP_SAVED: saved(w != 0, (uint32_t)l); return 0;
    case WM_APP_ICON:
      icons().drain();
      overlay.invalidate();
      if (settings_) settings_->invalidate();
      return 0;
    case WM_APP_PIN: {
      std::unique_ptr<Pin> p((Pin*)l);
      if (p->target.empty()) notify(L"Nothing to pin", L"That window does not belong to a program that can be pinned.");
      else addPin(*p);
      return 0;
    }
    case WM_APP_APPS:
      if (settings_) settings_->appsReady((void*)l);
      return 0;
    case WM_APP_LOGO: logoAnswered((void*)l); return 0;
    case WM_APP_TRAY:
      switch (LOWORD(l)) {
        case WM_CONTEXTMENU: trayMenu(); break;
        case NIN_SELECT:
        case NIN_KEYSELECT: overlay.open(false); break;
      }
      return 0;
    case WM_COPYDATA: {
      std::wstring cmd, arg;
      if (role == Role::Resident && splitCommand((void*)l, kCmdToResident, cmd, arg)) {
        if (cmd == L"addpin" || cmd == L"unpin") return runCommand(cmd, arg);  // whoever asked shows the result
        ReplyMessage(TRUE);
        runCommand(cmd, arg);
      }
      return TRUE;
    }
    case WM_TIMER:
      if (w == kSaveTimer) saveNow();
      else if (w == kRestTimer) restIfIdle();
      else if (w == kRetryTimer) {  // the program that held the shortcut may be gone
        if (!hotkeys.ok()) hotkeys.apply(cfg.hotkey);
        if (hotkeys.ok()) {
          KillTimer(hwnd_, kRetryTimer);
          updateTray();
        }
      } else if (w == kLogoTimer) {
        KillTimer(hwnd_, kLogoTimer);
        // Websites pinned by an earlier version have no logo yet: they are asked once. Noted as done when all answered.
        if (cfg.locked || cfg.version >= Config::kVersion) return 0;
        for (auto& pr : cfg.profiles)
          for (auto& p : pr.pins) {
            wantLogo(p);
            for (auto& c : p.children) wantLogo(c);
          }
        askingAll_ = !logos_.empty();
        if (!askingAll_) {
          cfg.version = Config::kVersion;
          if (!findSettings()) saveSoon();
        }
      } else if (w == kResumeTimer) {
        KillTimer(hwnd_, kResumeTimer);
        hotkeys.suspend(false);
      } else if (w == kReadTimer) {  // the settings file was busy at start
        if (reloadFromDisk()) KillTimer(hwnd_, kReadTimer);
      } else if (w == kSkinTimer) {
        KillTimer(hwnd_, kSkinTimer);
        overlay.prepare();
        lastUse_ = nowSec();
        SetTimer(hwnd_, kRestTimer, 5000, nullptr);
      } else if (w == kWarmTimer) {
        KillTimer(hwnd_, kWarmTimer);
        sweepCache(false);
        sweepSkinCache(false);
        warmIcons();
        gfx().prewarm();
        overlay.prepare();
        lastUse_ = nowSec();
        SetTimer(hwnd_, kRestTimer, 5000, nullptr);
      }
      return 0;
    case WM_SETTINGCHANGE:
      if (l && !wcscmp((const wchar_t*)l, L"Environment")) refreshEnvironment();
      if (settings_) settings_->themeChanged();
      return 0;
    case WM_DWMCOLORIZATIONCOLORCHANGED:
      if (settings_) settings_->themeChanged();
      return 0;
    case WM_QUERYENDSESSION: return TRUE;
    case WM_ENDSESSION:
      if (w && dirty_) saveNow(true);
      return 0;
    case WM_CLOSE:
      quit();
      return 0;
  }
  return DefWindowProcW(hwnd_, m, w, l);
}

}  // namespace rt
