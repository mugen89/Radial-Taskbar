// Global shortcut. Uses RegisterHotKey, which costs nothing while idle. A keyboard hook exists only
// while the wheel is held open (so WASD can steer it with Win down), or permanently when the person
// explicitly chose to take over a shortcut Windows already uses.
#pragma once
#include "common.h"
#include "config.h"

namespace rt {

class HotkeyManager {
 public:
  void init(HWND notify, UINT hookMsg, UINT keyMsg);
  bool apply(const Hotkey& h);   // false: the combination is taken
  void remove();
  void suspend(bool on);         // while a new shortcut is being recorded
  bool ok() const { return ok_; }
  const Hotkey& current() const { return hk_; }

  static bool available(UINT mods, UINT vk);
  static bool modifiersDown(UINT mods);
  bool holdKeysDown() const;     // is the person still holding the shortcut?

  void beginHold();              // forward steering keys to the overlay
  void endHold();
  void shutdown();

  // While recording, every key goes to `target` as `msg` (wParam: key, lParam: modifiers) instead of Windows.
  void beginRecord(HWND target, UINT msg);
  void endRecord();

 private:
  void startHook();
  void stopHook();
  HWND hwnd_ = nullptr;
  Hotkey hk_;
  bool ok_ = false, suspended_ = false;
  int ids_ = 0;
};

// One-handed combinations worth offering, checked live against this PC.
struct HotkeyIdea {
  UINT mods, vk;
  const wchar_t* note;
  bool free;
};
std::vector<HotkeyIdea> suggestHotkeys(const Hotkey& current);

}  // namespace rt
