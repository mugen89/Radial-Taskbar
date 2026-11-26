// "Add to Radial Taskbar" beside the menu of a taskbar button.
// Windows does not let other programs put entries into that menu, so a matching row is shown right above it.
// The resident part only hears that such a menu opened (one foreground notification). A copy of the program finds out
// which button it belongs to and shows the row. It stays warm for two minutes after its last use, then goes away.
#pragma once
#include "common.h"
#include "config.h"
#include "shellutil.h"
#include "snapshot.h"

namespace rt {

class TaskbarWatch {
 public:
  void apply(bool on);
  ~TaskbarWatch() { apply(false); }

 private:
  static void CALLBACK onForeground(HWINEVENTHOOK, DWORD, HWND hwnd, LONG obj, LONG child, DWORD, DWORD);
  HWINEVENTHOOK hook_ = nullptr;
};

// One button on the taskbar, as the taskbar itself describes it.
struct TaskButton {
  HWND hwnd = nullptr;      // set when the button stands for one window
  std::wstring appId;       // otherwise the app's id, which can also be a path
  std::wstring name;
  RECT rc{};
};
std::vector<TaskButton> listTaskButtons();                       // slow: call off the UI thread, COM initialised
std::string pinnedAs(const std::vector<Pin>& pins, const TaskButton& b);  // id of the pin for it, if there is one
Pin pinFromTaskButton(const TaskButton& b);
bool isOurButton(const TaskButton& b);

int runTaskbarRow(HINSTANCE inst, const Args& args);             // "--taskbar-row"
int runRowShot(const Args& args);                                // "--row-shot": headless picture for checks
std::string describeTaskButtons(const Config& cfg);              // for --diagnose

}  // namespace rt
