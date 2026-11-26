// The resident part: tray icon, shortcut, settings file, single instance.
// The settings window runs in a second, short-lived process (same exe), so the memory that file
// dialogs and shell extensions pull in is given back the moment it closes. The two talk through
// the settings file plus a few window messages.
#pragma once
#include "common.h"
#include "config.h"
#include "hotkey.h"
#include "overlay.h"
#include "snapshot.h"
#include "taskrow.h"

namespace rt {

class SettingsWindow;

// A question to a website that has not been answered yet.
struct LogoAsk {
  uint32_t serial = 0;
  std::string pin;
  std::wstring url, was;   // was: the picture at that moment. A newer choice is never replaced by the answer
  bool isImage = false, started = false;
};

class App {
 public:
  enum class Role { Resident, Settings };

  App();
  ~App();
  int run(HINSTANCE inst, const Args& args);
  int runSettings(HINSTANCE inst, const Args& args);

  Config cfg;
  HotkeyManager hotkeys;
  Overlay overlay;
  Role role = Role::Resident;

  HWND hiddenWindow() const { return hwnd_; }
  HINSTANCE instance() const { return inst_; }

  void saveSoon();
  void saveNow(bool wait = false);  // writes on a worker unless told to wait
  void pinsChanged();              // warm icons and tell whoever is showing pins
  void openSettings(int page = -1);
  void settingsClosed();
  void overlayHidden();
  void pinWindow(HWND h);          // pin the program that owns a window
  bool addPin(Pin p, bool quiet = false, const std::string& profileId = {});  // no id: the profile in use
  void applyHotkey();
  void notify(const std::wstring& title, const std::wstring& text);
  void updateTray();
  void quit();

  // for the settings window, whichever process it lives in
  bool hotkeyOk();
  void suspendHotkey(bool on);
  void openWheel();
  bool reloadFromDisk();
  bool applyRemote(const std::wstring& cmd, const std::wstring& arg);  // a change made on the wheel

  // changes the wheel can make
  void setProfile(int index);
  void setSkin(const std::string& id);
  bool unpin(const std::string& id);
  bool ungroup(const std::string& id);

  // pictures for websites: looked up by a helper process, the answer arrives later
  void fetchLogo(const std::string& pinId, const std::wstring& url, const std::wstring& was = {}, bool isImage = false);
  void cancelLogo(const std::string& pinId);
  void wantLogo(const Pin& p);     // when it is a new website without a picture and the person allows it
  bool logoBusy(const std::string& pinId) const;

 private:
  static LRESULT CALLBACK proc(HWND h, UINT m, WPARAM w, LPARAM l);
  LRESULT handle(UINT m, WPARAM w, LPARAM l);
  bool makeHiddenWindow(const std::wstring& cls);
  void firstRun();
  bool takeOverBeta();
  void trayMenu();
  bool runCommand(const std::wstring& cmd, const std::wstring& arg);
  void restIfIdle();
  void saved(bool ok, uint32_t seq);
  void warmIcons();
  // While the settings window is open it owns the file: hand it the change instead of saving over it.
  void persist(const std::wstring& cmd, const std::wstring& arg);

  HINSTANCE inst_ = nullptr;
  HWND hwnd_ = nullptr;
  UINT taskbarCreated_ = 0;
  bool dirty_ = false, trayOn_ = false, quitting_ = false;
  std::unique_ptr<SettingsWindow> settings_;
  TaskbarWatch watch_;
  double lastUse_ = 0, okAt_ = -10;
  uint32_t changes_ = 0, savingChanges_ = 0;  // so a save that was under way cannot pass for a newer change

  std::vector<LogoAsk> logos_;     // waiting and running, oldest first
  int logosRunning_ = 0;
  uint32_t logoSerial_ = 0;
  bool askingAll_ = false;         // the one round of questions after an update
  void startLogos();
  void logoAnswered(void* result);
  bool applyLogo(const std::string& pinId, const std::wstring& was, const std::wstring& image, const std::wstring& siteName);
  Pin* pinById(const std::string& id);
  bool ok_ = true;
};

std::wstring instanceSuffix();
std::wstring settingsWindowClass();
std::wstring hiddenWindowClass();
bool sendCommand(const std::wstring& cmd, const std::wstring& arg = {}, bool block = false);  // to the resident process
bool splitCommand(const void* copyData, ULONG_PTR tag, std::wstring& cmd, std::wstring& arg);
constexpr ULONG_PTR kCmdToResident = 0x5254, kCmdToSettings = 0x5255;

enum AppMessages : UINT {
  WM_APP_TRAY = WM_APP + 1,
  WM_APP_ICON,       // an icon finished loading
  WM_APP_HOTKEY,     // from the hook
  WM_APP_KEY,        // steering key from the hook
  WM_APP_PIN,        // lParam: Pin* to add (from a worker)
  WM_APP_APPS,       // installed apps list is ready
  WM_APP_QUERY,      // asks the resident whether its shortcut works
  WM_APP_RELOAD,     // to the settings window: the file changed
  WM_APP_SHOW,       // to the settings window: come to the front, wParam = page
  WM_APP_SAVED,      // the settings file was written: wParam ok, lParam which save
  WM_APP_LOGO,       // a website answered: lParam LogoResult*
};

}  // namespace rt
