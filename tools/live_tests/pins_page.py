"""The Pins page on the hidden desktop: adding straight into a group, moving a pinned app into it, dragging an item to
another profile, the right-click menu, and locking from the toolbar."""
import ctypes as C, ctypes.wintypes as W, json, os, shutil, sys, time
import hid
hid.enter()
import live_util as L
S, u = L.S, L.u
EXE = os.path.join(S, "pp_h.exe")
shutil.copy(sys.argv[1] if len(sys.argv) > 1 else L.EXE, EXE)
bad = []


def check(n, ok, more=""):
    print(("ok   " if ok else "FAIL ") + n, more, flush=True)
    if not ok: bad.append(n)


def until(f, sec=8):
    t = time.time()
    while time.time() - t < sec:
        if f(): return True
        time.sleep(0.1)
    return False


D = os.path.join(S, "data21h")
shutil.rmtree(D, ignore_errors=True); os.makedirs(D)
w = os.environ["WINDIR"]
conf = {"version": 2, "firstRun": False, "profileSkins": True, "behavior": {"trayIcon": False, "taskbarMenu": False}, "activeProfile": 0,
        "profiles": [{"id": "m", "name": "Main", "pins": [{"id": "x", "kind": "file", "name": "Explorer", "target": w + "\\explorer.exe"},
                                                          {"id": "g", "kind": "group", "name": "Tools", "children": []},
                                                          {"id": "n", "kind": "file", "name": "Charmap", "target": w + "\\System32\\charmap.exe"}]},
                     {"id": "o", "name": "Other", "pins": []}]}
json.dump(conf, open(os.path.join(D, "config.json"), "w"))


def cfg():
    try: return json.load(open(os.path.join(D, "config.json"), encoding="utf-8"))
    except Exception: return {}


def pins(i=0): return cfg().get("profiles", [{}, {}])[i].get("pins", [])


env = dict(os.environ, RADIALTASKBAR_DATA=D, RADIALTASKBAR_LOG=os.path.join(D, "log.txt"), RadialTaskbar_SKINS=L.SKINS)
s = hid.Proc([EXE, "--settings-window", "--page", "0"], env)
check("settings open", until(lambda: u.FindWindowW("RadialTaskbarSettings.alt", None), 15))
h = u.FindWindowW("RadialTaskbarSettings.alt", None)
u.SetWindowPos.argtypes = [W.HWND, W.HWND, C.c_int, C.c_int, C.c_int, C.c_int, W.UINT]
dpi = u.GetDpiForWindow(h) / 96.0
wr, cr = W.RECT(), W.RECT(); u.GetWindowRect(h, C.byref(wr)); u.GetClientRect(h, C.byref(cr))
u.SetWindowPos(h, None, 30, 30, int(1180 * dpi) + (wr.right - wr.left) - cr.right, int(780 * dpi) + (wr.bottom - wr.top) - cr.bottom, 0x14)
time.sleep(1.0)


def lp(x, y): return (int(y * dpi) << 16) | int(x * dpi)


def click(x, y, wait=0.5, right=False):
    u.PostMessageW(h, 0x200, 0, lp(x, y)); time.sleep(0.08)
    u.PostMessageW(h, 0x204 if right else 0x201, 2 if right else 1, lp(x, y)); time.sleep(0.08)
    u.PostMessageW(h, 0x205 if right else 0x202, 0, lp(x, y)); time.sleep(wait)


def typed(text):
    for ch in text:
        u.PostMessageW(h, 0x102, ord(ch), 0); time.sleep(0.03)
    time.sleep(0.6)


def drag(x0, y0, x1, y1):
    u.PostMessageW(h, 0x200, 0, lp(x0, y0)); time.sleep(0.08)
    u.PostMessageW(h, 0x201, 1, lp(x0, y0)); time.sleep(0.1)
    for i in range(1, 13):
        u.PostMessageW(h, 0x200, 1, lp(x0 + (x1 - x0) * i / 12, y0 + (y1 - y0) * i / 12)); time.sleep(0.05)
    time.sleep(0.3)
    u.PostMessageW(h, 0x202, 0, lp(x1, y1)); time.sleep(0.8)


def menu():  # the popup menu of this process, if one is up
    found = []
    ENUM = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)

    def one(hw, _):
        b = C.create_unicode_buffer(32); u.GetClassNameW(hw, b, 32)
        if b.value == "#32768" and u.IsWindowVisible(hw): found.append(hw)
        return True
    hid.u.EnumDesktopWindows.argtypes = [W.HANDLE, ENUM, W.LPARAM]
    hid.u.EnumDesktopWindows(hid.u.GetThreadDesktop(hid.k.GetCurrentThreadId()), ENUM(one), 0)
    return found


# the layout of the page at 1180 x 780: profiles at y 111, the list rows from y 168 every 46, the add panel on the right
ROW = lambda i: 168 + i * 46
time.sleep(3.0)  # the installed apps are being looked up
# 1: an app added while no group is open goes to the profile
click(950, 265); typed("Calcul")
click(950, 310, wait=1.0)
check("an app from the list lands in the profile", until(lambda: any(p.get("kind") == "app" and "Calculator" in p.get("name", "") for p in pins())), str([p.get("name") for p in pins()]))
# 2: open the group: the panel to add into it is right there
click(400, ROW(1)); time.sleep(0.8)
L.capture(h, os.path.join(S, "pins_group_live.png"))
# the search is the same one, still set to "Calcul"
click(950, 452, wait=1.2)
grp = [p for p in pins() if p.get("id") == "g"]
check("an app already pinned moves into the open group", until(lambda: [c.get("name") for p in pins() if p.get("id") == "g" for c in p.get("children", [])] == ["Calculator"] and not any(p.get("kind") == "app" for p in pins())),
      str([(p.get("name"), [c.get("name") for c in p.get("children", [])]) for p in pins()]))
click(1081, 731); time.sleep(0.5)  # Done
# 3: drag Explorer onto the other profile
tabs = (280, 111), (364, 111)
drag(400, ROW(0), tabs[1][0], tabs[1][1])
check("dragged onto another profile, it moves there", until(lambda: [p.get("name") for p in pins(1)] == ["Explorer"] and not any(p.get("id") == "x" for p in pins())), str([p.get("name") for p in pins(1)]))
# 4: the right-click menu: copy to the other profile
click(400, ROW(2), right=True, wait=0.8)  # Charmap: Tools and its open item are above it
check("right-click opens the item's menu", until(lambda: bool(menu()), 3))
m = menu()
if m:
    for vk in (0x28, 0x28, 0x28, 0x28):  # Edit, Move into group, Move to profile, Copy to profile
        u.PostMessageW(m[0], 0x100, vk, 0); time.sleep(0.15)
    u.PostMessageW(m[0], 0x100, 0x27, 0); time.sleep(0.4)  # into the submenu
    m2 = menu()
    u.PostMessageW(m2[-1], 0x100, 0x0D, 0); time.sleep(1.0)
check("Copy to profile copies it", until(lambda: [p.get("name") for p in pins(1)] == ["Explorer", "Charmap"] and any(p.get("name") == "Charmap" for p in pins())),
      str([p.get("name") for p in pins(1)]))
copies = [p for p in pins(1) if p.get("name") == "Charmap"] + [p for p in pins() if p.get("name") == "Charmap"]
check("and the copy has an id of its own", len(copies) == 2 and copies[0].get("id") != copies[1].get("id"))
# 5: lock the profile in use from the toolbar: refused while it is the only unlocked one... it is not: Other is unlocked
click(997, 111, wait=0.8)
check("the padlock locks the profile in use", until(lambda: cfg()["profiles"][0].get("locked") is True))
click(364, 111, wait=0.6)  # to Other
click(997, 111, wait=0.8)
check("the last one that is not locked cannot be locked", not cfg()["profiles"][1].get("locked"))
L.capture(h, os.path.join(S, "pins_live.png"))
u.PostMessageW(h, 0x10, 0, 0)
check("settings close", s.wait(8) == 0)
print("FAILED:", bad)
