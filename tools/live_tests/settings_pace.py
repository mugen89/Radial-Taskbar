"""How fast the settings window opens and draws while the mouse moves, pages scroll and sliders are dragged.
python -X utf8 settings_pace.py [skin] [exe]"""
import ctypes as C, ctypes.wintypes as W, json, os, re, shutil, sys, time
import hid
hid.enter()
import live_util as L
S, u = L.S, L.u
skin = sys.argv[1] if len(sys.argv) > 1 else "vinyl"
src = sys.argv[2] if len(sys.argv) > 2 else L.EXE
EXE = os.path.join(S, "sp_h.exe")
shutil.copy(src, EXE)
D = os.path.join(S, "data11h"); shutil.rmtree(D, ignore_errors=True); shutil.copytree(os.path.join(S, "data3h"), D)
c = json.load(open(os.path.join(D, "config.json")))
c["layout"] = {"type": "radial", "anchor": "center"}; c["skin"] = "" if skin == "none" else skin
json.dump(c, open(os.path.join(D, "config.json"), "w"))
LOG = os.path.join(D, "log.txt")
env = dict(os.environ, RADIALTASKBAR_DATA=D, RADIALTASKBAR_LOG=LOG, RadialTaskbar_SKINS=L.SKINS)
res = hid.Proc([EXE, "--background"], env)
time.sleep(2.5)
t0 = time.perf_counter()
p = hid.Proc([EXE, "--settings-window", "--page", "0"], env)
h = None
while time.perf_counter() - t0 < 20:
    h = u.FindWindowW("RadialTaskbarSettings.alt", None)
    if h and u.IsWindowVisible(h): break
    time.sleep(0.005)
print("window visible after %.0f ms" % ((time.perf_counter() - t0) * 1000))
time.sleep(1.5)
u.SetWindowPos.argtypes = [W.HWND, W.HWND, C.c_int, C.c_int, C.c_int, C.c_int, W.UINT]
dpi = u.GetDpiForWindow(h) / 96.0
wr, cr = W.RECT(), W.RECT(); u.GetWindowRect(h, C.byref(wr)); u.GetClientRect(h, C.byref(cr))
u.SetWindowPos(h, None, 50, 50, int(1180 * dpi) + (wr.right - wr.left) - cr.right, int(780 * dpi) + (wr.bottom - wr.top) - cr.bottom, 0x14)
time.sleep(0.4)


def at(x, y): return (int(y * dpi) << 16) | (int(x * dpi) & 0xFFFF)
def move(x, y): u.PostMessageW(h, 0x200, 0, at(x, y))
def reply(limit=2.0):
    """How long the window needs to answer: what a person feels as lag."""
    t = time.perf_counter(); r = C.c_size_t()
    ok = u.SendMessageTimeoutW(h, 0, 0, None, 2, int(limit * 1000), C.byref(r))
    return (time.perf_counter() - t) * 1000 if ok else limit * 1000


def phase(name, f, n=150):
    mark = os.path.getsize(LOG)
    lag = []
    for i in range(n):
        f(i)
        lag.append(reply())
        time.sleep(0.012)
    lines = open(LOG, errors="replace").read()[mark:].splitlines()
    draws = [l[l.index("ui:"):] for l in lines if "ui: 100 frames" in l]
    lag.sort()
    print("%-26s answers: middle %5.1f ms, 95%% %5.1f, worst %5.1f | %s" % (name, lag[len(lag) // 2], lag[int(len(lag) * 0.95)], lag[-1], (draws[-1] if draws else "")), flush=True)


def nav(i):
    move(100, 110 + i * 42); u.PostMessageW(h, 0x201, 1, at(100, 110 + i * 42)); time.sleep(0.05); u.PostMessageW(h, 0x202, 0, at(100, 110 + i * 42)); time.sleep(0.9)


def wheel(i):
    r = W.RECT(); u.GetWindowRect(h, C.byref(r))
    pt = W.POINT(int(360 * dpi), int(400 * dpi)); u.ClientToScreen(h, C.byref(pt))
    u.PostMessageW(h, 0x20A, ((120 if (i // 24) % 2 else -120) & 0xFFFF) << 16, ((pt.y & 0xFFFF) << 16) | (pt.x & 0xFFFF))


names = ["Pins", "Layout", "Skins", "Look", "Effects", "Shortcut", "General"]
for pg, name in enumerate(names):
    nav(pg)
    phase(name + ": mouse", lambda i: move(260 + (i * 13) % 420, 120 + (i * 29) % 600))
    phase(name + ": scroll", wheel, 100)
# dragging a slider: Effects page, the glow slider
nav(4)
u.PostMessageW(h, 0x20A, (2400 & 0xFFFF) << 16, 0); time.sleep(0.5)
move(500, 330); time.sleep(0.1)
u.PostMessageW(h, 0x201, 1, at(500, 330))
phase("Effects: dragging", lambda i: move(470 + 100 * abs(((i / 40.0) % 2) - 1), 330))
u.PostMessageW(h, 0x202, 0, at(500, 330)); time.sleep(0.4)
nav(2)
print("settings process: handles %d, private %.1f MB" % L.stats(p.pid)[:2])
L.capture(h, os.path.join(S, "pace_skins.png"))
for pg in (1, 3):
    nav(pg); time.sleep(0.4); L.capture(h, os.path.join(S, "pace_%d.png" % pg))
u.PostMessageW(h, 0x10, 0, 0); print("settings exit", p.wait(6))
L.command("quit\n", "RadialTaskbarHidden.alt"); print("exit", res.wait(6))
