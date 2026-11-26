#include "hotkey.h"

#include <process.h>

#include <atomic>

namespace rt {

namespace {
constexpr ULONG_PTR kMagic = 0x52544B31;  // marks our own injected keys

struct HookState {
  std::atomic<bool> hold{false}, takeOver{false}, suspended{false}, record{false};
  std::atomic<UINT> mods{0}, vk{0};
  HWND notify = nullptr;
  UINT hookMsg = 0, keyMsg = 0, recordMsg = 0;
  HWND recordTo = nullptr;
  HANDLE thread = nullptr;
  DWORD tid = 0;
  bool eatUp[256] = {};
  std::atomic<bool> down[256] = {};  // keys as the hook sees them, to tell a press from its auto-repeat
} g;

UINT modsNow() {
  auto dn = [](int vk) { return (GetAsyncKeyState(vk) & 0x8000) != 0; };
  return (dn(VK_LWIN) || dn(VK_RWIN) ? MOD_WIN : 0) | (dn(VK_CONTROL) ? MOD_CONTROL : 0) | (dn(VK_MENU) ? MOD_ALT : 0) | (dn(VK_SHIFT) ? MOD_SHIFT : 0);
}
bool modifierKey(UINT vk) {
  return vk == VK_LWIN || vk == VK_RWIN || vk == VK_SHIFT || vk == VK_LSHIFT || vk == VK_RSHIFT || vk == VK_CONTROL || vk == VK_LCONTROL ||
         vk == VK_RCONTROL || vk == VK_MENU || vk == VK_LMENU || vk == VK_RMENU;
}

// Checked on every key, so a stalled window can never leave keys captured after Win is released.
bool heldNow() {
  auto dn = [](int vk) { return (GetAsyncKeyState(vk) & 0x8000) != 0; };
  UINT m = g.mods;
  if (m & MOD_WIN) return dn(VK_LWIN) || dn(VK_RWIN);
  if (m & MOD_CONTROL) return dn(VK_CONTROL);
  if (m & MOD_ALT) return dn(VK_MENU);
  if (m & MOD_SHIFT) return dn(VK_SHIFT);
  UINT vk = g.vk & 0xFF;
  return g.takeOver ? g.down[vk].load() : dn((int)vk);  // a swallowed key never reaches the async state
}

bool steeringKey(UINT vk) {
  if (vk >= '1' && vk <= '9') return true;
  switch (vk) {
    case 'W': case 'A': case 'S': case 'D': case 'Q': case 'E': case 'F':
    case VK_LEFT: case VK_RIGHT: case VK_UP: case VK_DOWN:
    case VK_RETURN: case VK_SPACE: case VK_TAB: case VK_ESCAPE:
      return true;
  }
  return false;
}

// Stops Windows from opening Start when Win is released after a swallowed key.
void maskWinKey() {
  INPUT in[2]{};
  in[0].type = in[1].type = INPUT_KEYBOARD;
  in[0].ki.wVk = in[1].ki.wVk = 0xE8;  // unassigned
  in[0].ki.dwExtraInfo = in[1].ki.dwExtraInfo = kMagic;
  in[1].ki.dwFlags = KEYEVENTF_KEYUP;
  SendInput(2, in, sizeof(INPUT));
}

LRESULT CALLBACK hookProc(int code, WPARAM wp, LPARAM lp) {
  if (code == HC_ACTION) {
    auto* k = (KBDLLHOOKSTRUCT*)lp;
    bool down = wp == WM_KEYDOWN || wp == WM_SYSKEYDOWN;
    UINT vk = k->vkCode & 0xFF;
    if (k->dwExtraInfo != kMagic) {
      bool first = down && !g.down[vk];
      g.down[vk] = down;
      if (!down && g.eatUp[vk]) {
        g.eatUp[vk] = false;
        return 1;
      }
      bool swallow = false;
      if (g.record && !modifierKey(vk)) {
        if (down) {
          UINT m = modsNow();
          PostMessageW(g.recordTo, g.recordMsg, vk, (LPARAM)m);
          if (m & MOD_WIN) maskWinKey();
          g.eatUp[vk] = true;
          return 1;
        }
      }
      if (down && g.hold && heldNow() && vk == g.vk) {
        // The shortcut's own key. A fresh press moves on; its auto-repeat means nothing, and the release of
        // the press that opened the wheel must still reach Windows.
        if (!first) return 1;
        PostMessageW(g.notify, g.keyMsg, vk, (GetAsyncKeyState(VK_SHIFT) & 0x8000) ? 1 : 0);
        swallow = true;
      } else if (down && g.hold && heldNow() && steeringKey(vk)) {
        PostMessageW(g.notify, g.keyMsg, vk, ((GetAsyncKeyState(VK_SHIFT) & 0x8000) ? 1 : 0) | (first ? 0 : 2));
        swallow = true;
      } else if (down && g.takeOver && !g.suspended && vk == g.vk && HotkeyManager::modifiersDown(g.mods)) {
        if (first) {
          PostMessageW(g.notify, g.hookMsg, 0, 0);
          if (g.mods & MOD_WIN) maskWinKey();
        }
        swallow = true;
      }
      if (swallow) {
        g.eatUp[vk] = true;
        return 1;
      }
    }
  }
  return CallNextHookEx(nullptr, code, wp, lp);
}

unsigned __stdcall hookThread(void* ready) {
  MSG m;
  PeekMessageW(&m, nullptr, WM_USER, WM_USER, PM_NOREMOVE);  // make the queue exist
  HHOOK h = SetWindowsHookExW(WH_KEYBOARD_LL, hookProc, GetModuleHandleW(nullptr), 0);
  if (!h) logf("hotkey: keyboard hook refused (%lu)", GetLastError());
  SetEvent((HANDLE)ready);
  if (h) {
    while (GetMessageW(&m, nullptr, 0, 0) > 0) {}
    UnhookWindowsHookEx(h);
  }
  return 0;
}
}  // namespace

void HotkeyManager::init(HWND notify, UINT hookMsg, UINT keyMsg) {
  hwnd_ = notify;
  g.notify = notify;
  g.hookMsg = hookMsg;
  g.keyMsg = keyMsg;
}

void HotkeyManager::startHook() {
  if (g.thread) return;
  memset(g.eatUp, 0, sizeof g.eatUp);
  for (int i = 0; i < 256; i++) g.down[i] = (GetAsyncKeyState(i) & 0x8000) != 0;  // keys already held are not new presses
  HANDLE ready = CreateEventW(nullptr, TRUE, FALSE, nullptr);
  unsigned tid = 0;
  g.thread = (HANDLE)_beginthreadex(nullptr, 0, hookThread, ready, 0, &tid);
  g.tid = tid;
  if (g.thread) {
    SetThreadPriority(g.thread, THREAD_PRIORITY_HIGHEST);  // key events must never wait on drawing
    WaitForSingleObject(ready, 400);
  }
  CloseHandle(ready);
}

void HotkeyManager::stopHook() {
  if (!g.thread) return;
  PostThreadMessageW(g.tid, WM_QUIT, 0, 0);
  WaitForSingleObject(g.thread, 400);
  CloseHandle(g.thread);
  g.thread = nullptr;
}

bool HotkeyManager::modifiersDown(UINT mods) {
  auto dn = [](int vk) { return (GetAsyncKeyState(vk) & 0x8000) != 0; };
  bool win = dn(VK_LWIN) || dn(VK_RWIN), ctrl = dn(VK_CONTROL), alt = dn(VK_MENU), shift = dn(VK_SHIFT);
  return win == !!(mods & MOD_WIN) && ctrl == !!(mods & MOD_CONTROL) && alt == !!(mods & MOD_ALT) && shift == !!(mods & MOD_SHIFT);
}

bool HotkeyManager::holdKeysDown() const {
  auto dn = [](int vk) { return (GetAsyncKeyState(vk) & 0x8000) != 0; };
  if (hk_.mods & MOD_WIN) return dn(VK_LWIN) || dn(VK_RWIN);
  if (hk_.mods & MOD_CONTROL) return dn(VK_CONTROL);
  if (hk_.mods & MOD_ALT) return dn(VK_MENU);
  if (hk_.mods & MOD_SHIFT) return dn(VK_SHIFT);
  return g.takeOver ? g.down[hk_.vk & 0xFF].load() : dn((int)hk_.vk);
}

void HotkeyManager::remove() {
  for (int i = 1; i <= ids_; i++) UnregisterHotKey(hwnd_, i);
  ids_ = 0;
  g.takeOver = false;
  if (!g.hold && !g.record) stopHook();
}

bool HotkeyManager::apply(const Hotkey& h) {
  remove();
  hk_ = h;
  g.mods = h.mods;
  g.vk = h.vk;
  ok_ = false;
  if (suspended_) return true;
  // Register the same physical key under every installed keyboard layout, so switching
  // language does not lose the shortcut.
  std::vector<UINT> vks = {h.vk};
  HKL list[32];
  int n = GetKeyboardLayoutList(32, list);
  UINT scan = MapVirtualKeyW(h.vk, MAPVK_VK_TO_VSC);
  for (int i = 0; i < n && scan; i++) {
    UINT v = MapVirtualKeyExW(scan, MAPVK_VSC_TO_VK, list[i]);
    if (v && std::find(vks.begin(), vks.end(), v) == vks.end() && MapVirtualKeyExW(h.vk, MAPVK_VK_TO_VSC, list[i]) != scan) vks.push_back(v);
  }
  for (size_t i = 0; i < vks.size(); i++) {
    bool r = RegisterHotKey(hwnd_, ids_ + 1, h.mods | MOD_NOREPEAT, vks[i]) != FALSE;
    if (r) ids_++;
    if (i == 0) ok_ = r;
    if (!r && i == 0) break;
  }
  if (!ok_ && h.takeOver) {
    g.takeOver = true;
    startHook();
    ok_ = g.thread != nullptr;
  }
  logf("hotkey: mods=%u vk=%02X %s", h.mods, h.vk, ok_ ? (g.takeOver ? "taken over" : "registered") : "unavailable");
  return ok_;
}

void HotkeyManager::suspend(bool on) {
  if (on == suspended_) return;
  suspended_ = on;
  g.suspended = on;
  if (on) {
    for (int i = 1; i <= ids_; i++) UnregisterHotKey(hwnd_, i);
    ids_ = 0;
  } else {
    apply(Hotkey(hk_));
  }
}

bool HotkeyManager::available(UINT mods, UINT vk) {
  const int id = 0xBFF0;
  if (!RegisterHotKey(nullptr, id, mods | MOD_NOREPEAT, vk)) return false;
  UnregisterHotKey(nullptr, id);
  return true;
}

void HotkeyManager::beginHold() {
  g.hold = true;
  startHook();
}
void HotkeyManager::endHold() {
  g.hold = false;
  if (!g.takeOver && !g.record) stopHook();
}
void HotkeyManager::beginRecord(HWND target, UINT msg) {
  g.recordTo = target;
  g.recordMsg = msg;
  g.record = true;
  startHook();
}
void HotkeyManager::endRecord() {
  g.record = false;
  if (!g.takeOver && !g.hold) stopHook();
}
void HotkeyManager::shutdown() {
  remove();
  g.hold = false;
  stopHook();
}

std::vector<HotkeyIdea> suggestHotkeys(const Hotkey& cur) {
  static const HotkeyIdea ideas[] = {
      {MOD_WIN, VK_OEM_3, L"The key above Tab. Thumb on Win.", false},
      {MOD_WIN, VK_ESCAPE, L"Top left corner.", false},
      {MOD_WIN, VK_F2, L"Function row.", false},
      {MOD_WIN | MOD_ALT, 'Z', L"Thumb across Win and Alt.", false},
      {MOD_WIN | MOD_ALT, 'A', L"Thumb across Win and Alt, home row.", false},
      {MOD_WIN | MOD_ALT, 'Q', L"Thumb across Win and Alt, upper row.", false},
      {MOD_WIN | MOD_ALT, VK_SPACE, L"Three neighbours in the bottom row.", false},
      {MOD_WIN | MOD_SHIFT, 'Z', L"Little finger on Shift.", false},
      {MOD_WIN | MOD_SHIFT, 'Q', L"Little finger on Shift, upper row.", false},
      {MOD_WIN | MOD_CONTROL, 'A', L"Ctrl and Win side by side.", false},
      {MOD_WIN | MOD_CONTROL, 'Z', L"Ctrl and Win side by side.", false},
      {MOD_ALT, VK_OEM_3, L"No Win key needed.", false},
  };
  std::vector<HotkeyIdea> out;
  for (auto i : ideas) {
    i.free = (i.mods == cur.mods && i.vk == cur.vk) || HotkeyManager::available(i.mods, i.vk);
    out.push_back(i);
  }
  return out;
}

}  // namespace rt
