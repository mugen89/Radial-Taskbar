// Windows shell integration: shortcuts, installed apps, launching, running windows.
#pragma once
#include "common.h"
#include "config.h"

namespace rt {

struct LinkInfo {
  std::wstring target, args, workDir, aumid, icon;
  int iconIndex = 0;
  bool admin = false;
};
bool readLink(const std::wstring& lnk, LinkInfo& out);

struct AppEntry {
  std::wstring name, aumid, exe;
};
std::vector<AppEntry> enumInstalledApps();  // slow (shell enumeration): call off the UI thread

Pin pinFromPath(const std::wstring& path);
void adoptPin(Pin& p);  // when it is really added: keeps a copy of the shortcut it points to
Pin pinFromApp(const AppEntry& a);
Pin pinFromAppId(const std::wstring& aumid);           // empty target when the Start menu does not list it
Pin pinFromUrl(const std::wstring& url, const std::wstring& name = {});
Pin pinFromWindow(HWND hwnd);
Pin pinFromWindowHelper(HWND hwnd);                    // same, worked out by a short-lived copy of the program
int runPinHelper(const std::wstring& hwnd, const std::wstring& outFile);
std::vector<Pin> importTaskbarPins();
// True when an equivalent pin already exists in the list (or inside its groups).
bool alreadyPinned(const std::vector<Pin>& pins, const Pin& p);
std::string pinnedId(const std::vector<Pin>& pins, const Pin& p);  // the one that opens the same, in groups too

// Launches on a worker thread so a slow target can never freeze the wheel.
void launchPin(const Pin& pin, bool admin = false);
void openPinLocation(const Pin& pin);
std::wstring pinSubtitle(const Pin& pin);

// ---------------------------------------------------------------- running windows
struct AppWindow {
  HWND hwnd = nullptr;
  std::wstring title, exe, aumid;
  bool minimized = false;
};
struct MatchInfo {
  std::wstring exe, aumid, other;  // other: what a shortcut opens when it is not a program
};
MatchInfo resolveMatch(const Pin& pin);  // cached per pin
void forgetMatches();

class WindowList {
 public:
  std::vector<AppWindow> wins;  // front to back
  HWND foreground = nullptr;
  void snapshot(HWND ignore1 = nullptr, HWND ignore2 = nullptr);
  std::vector<int> matching(const Pin& pin) const;
};
void focusWindow(HWND h);
bool isAppWindow(HWND h);  // a window the taskbar would show
bool describeWindow(HWND h, AppWindow& out);
bool fullscreenAppRunning();

// ---------------------------------------------------------------- system bits
bool autostartEnabled();
void setAutostart(bool on);
std::wstring pickFile(HWND owner, const wchar_t* title, bool folder, const wchar_t* filterName = nullptr, const wchar_t* filterSpec = nullptr);
std::wstring pickSave(HWND owner, const wchar_t* title, const wchar_t* defName);
std::wstring wallpaperPath();
void refreshEnvironment();
bool createShortcut(const std::wstring& lnk, const std::wstring& target, const std::wstring& args, const std::wstring& desc,
                    const std::wstring& aumid = {});

constexpr const wchar_t* kAppUserModelId = RT_ID L".App";
constexpr const wchar_t* kRunValue = RT_ID;

}  // namespace rt
