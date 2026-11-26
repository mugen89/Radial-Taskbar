// Drives the real keyboard-hook procedure with invented keyboard states.
#include "common.h"
#include "config.h"

#include <process.h>

#include <atomic>
#include <map>

static std::map<int, bool> keyDown;  // what Windows' async key state would say
static SHORT fakeAsync(int vk) { return keyDown[vk] ? (SHORT)0x8000 : 0; }
struct Posted { UINT msg; WPARAM w; LPARAM l; };
static std::vector<Posted> posted;
static int masks = 0;
static BOOL fakePost(HWND, UINT m, WPARAM w, LPARAM l) { posted.push_back({m, w, l}); return TRUE; }
static UINT fakeSend(UINT n, LPINPUT, int) { masks++; return n; }
static LRESULT fakeNext(HHOOK, int, WPARAM, LPARAM) { return 7777; }  // "reached Windows"
#define GetAsyncKeyState fakeAsync
#define PostMessageW fakePost
#define SendInput fakeSend
#define CallNextHookEx fakeNext
#include "../src/hotkey.cpp"
#undef PostMessageW

using namespace rt;

static int bad = 0;
static void check(const char* n, bool ok) {
  printf("%s %s\n", ok ? "ok  " : "FAIL", n);
  if (!ok) bad++;
}
// One hardware event; true when it got through to Windows.
static bool reached(UINT vk, bool down) {
  KBDLLHOOKSTRUCT k{};
  k.vkCode = vk;
  bool r = hookProc(HC_ACTION, down ? WM_KEYDOWN : WM_KEYUP, (LPARAM)&k) == 7777;
  if (r) keyDown[(int)vk] = down;  // the system state only sees what we let through
  return r;
}
static void fresh(UINT mods, UINT vk, bool takeOver) {
  keyDown.clear();
  posted.clear();
  masks = 0;
  memset(g.eatUp, 0, sizeof g.eatUp);
  for (auto& d : g.down) d = false;
  g.mods = mods;
  g.vk = vk;
  g.takeOver = takeOver;
  g.hold = false;
  g.record = false;
  g.suspended = false;
  g.hookMsg = 1;
  g.keyMsg = 2;
}
static void hold() {
  for (int i = 0; i < 256; i++) g.down[i] = keyDown[i];
  g.hold = true;
}
static size_t keys() {
  size_t n = 0;
  for (auto& p : posted) n += p.msg == 2;
  return n;
}

int main() {
  // Win+` held: RegisterHotKey took the first press, then the keyboard auto-repeats
  fresh(MOD_WIN, VK_OEM_3, false);
  keyDown[VK_LWIN] = keyDown[VK_OEM_3] = true;
  hold();
  for (int i = 0; i < 40; i++) reached(VK_OEM_3, true);
  check("auto-repeat of the shortcut key steers nothing", keys() == 0);
  check("its release reaches Windows", reached(VK_OEM_3, false) && !keyDown[VK_OEM_3]);
  check("a fresh press while Win is held cycles once", !reached(VK_OEM_3, true) && keys() == 1 && posted.back().w == VK_OEM_3);
  for (int i = 0; i < 20; i++) reached(VK_OEM_3, true);
  check("holding it again does not spin", keys() == 1);
  check("that press was ours, so its release is too", !reached(VK_OEM_3, false));

  // steering keys
  posted.clear();
  check("D is taken (no Win+D)", !reached('D', true) && keys() == 1 && posted.back().l == 0);
  reached('D', true);
  check("repeat of D is marked as a repeat", keys() == 2 && posted.back().l == 2);
  check("release of D swallowed", !reached('D', false));
  check("unrelated key passes", reached('L', true));
  keyDown[VK_SHIFT] = true;
  reached(VK_TAB, true);
  check("Shift reported", posted.back().l == 1);
  keyDown[VK_SHIFT] = false;
  reached(VK_TAB, false);

  // Win is up but the window is stalled and has not ended the hold
  posted.clear();
  reached(VK_LWIN, false);
  check("after Win is up, D belongs to Windows again", reached('D', true) && keys() == 0);
  reached('D', false);

  // a shortcut that is also a steering key
  fresh(MOD_WIN | MOD_ALT, 'Q', false);
  keyDown[VK_LWIN] = keyDown[VK_MENU] = keyDown['Q'] = true;
  hold();
  for (int i = 0; i < 10; i++) reached('Q', true);
  check("Win+Alt+Q: repeats do not flip profiles", keys() == 0);

  // single key through RegisterHotKey
  fresh(0, VK_F9, false);
  keyDown[VK_F9] = true;
  hold();
  for (int i = 0; i < 10; i++) reached(VK_F9, true);
  check("F9: still held", heldNow());
  check("F9: release is seen by Windows and ends the hold", reached(VK_F9, false) && !heldNow());
  check("F9: after that W passes", reached('W', true));

  // single key taken over by the hook itself
  fresh(0, VK_F9, true);
  check("F9 taken over: press swallowed and reported once", !reached(VK_F9, true) && posted.size() == 1 && posted[0].msg == 1);
  g.hold = true;
  for (int i = 0; i < 10; i++) reached(VK_F9, true);
  check("F9 taken over: repeats silent, still held", posted.size() == 1 && heldNow());
  check("F9 taken over: release swallowed, hold over", !reached(VK_F9, false) && !heldNow());

  // taking over Win+E: Start must not open and Windows must not see E
  fresh(MOD_WIN, 'E', true);
  keyDown[VK_LWIN] = true;
  check("Win+E taken over: swallowed, reported, Start masked", !reached('E', true) && posted.size() == 1 && masks == 1);
  for (int i = 0; i < 5; i++) reached('E', true);
  check("Win+E taken over: repeats swallowed silently", posted.size() == 1 && masks == 1);
  check("Win+E taken over: release swallowed", !reached('E', false));
  keyDown[VK_LWIN] = false;
  check("plain E is not touched", reached('E', true));

  // recording a new shortcut
  fresh(MOD_WIN, VK_OEM_3, false);
  g.record = true;
  g.recordMsg = 3;
  keyDown[VK_LWIN] = true;
  check("recording takes Win+E instead of Explorer", !reached('E', true) && posted.size() == 1 && posted[0].msg == 3 && posted[0].l == MOD_WIN);
  check("modifiers pass while recording", reached(VK_LCONTROL, true));

  if (bad) printf("FAILED %d\n", bad);
  else printf("all good\n");
  return bad;
}
