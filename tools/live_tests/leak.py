import ctypes as C, ctypes.wintypes as W, json, math, os, random, shutil, sys, time
import hid
hid.enter()
import live_util as L
S = L.S
L.command.__defaults__ = ("RadialTaskbarHidden.alt",)
EXE = os.path.join(S, "leak3_h.exe")
shutil.copy(L.EXE, EXE)
skin, rounds = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 80
D = os.path.join(S, "data11h"); shutil.rmtree(D, ignore_errors=True); shutil.copytree(os.path.join(S, "data3h"), D)
c = json.load(open(os.path.join(D, "config.json")))
c["layout"] = {"type": "radial", "anchor": "center"}; c["skin"] = "" if skin == "none" else skin
json.dump(c, open(os.path.join(D, "config.json"), "w"))
random.seed(3)
SK = L.SKINS
p = hid.Proc([EXE, "--background"], dict(os.environ, RADIALTASKBAR_DATA=D, RADIALTASKBAR_LOG=os.path.join(D, "log.txt"), RadialTaskbar_SKINS=SK))
time.sleep(2.5)
for n in range(1, rounds + 1):
    L.command("open\n"); time.sleep(0.12)
    h = L.u.FindWindowW("RadialTaskbarOverlay.alt", None)
    r = W.RECT(); L.u.GetWindowRect(h, C.byref(r)); w, hh = r.right - r.left, r.bottom - r.top
    for i in range(26):
        a = random.random()
        if a < 0.6:
            x, y = w // 2 + random.randint(-330, 330), hh // 2 + random.randint(-330, 330)
            L.u.PostMessageW(h, 0x200, 0, (y << 16) | x)
        elif a < 0.85: L.u.PostMessageW(h, 0x100, random.choice([0x41, 0x44, 0x57, 0x53]), 0)
        elif a < 0.93: L.u.PostMessageW(h, 0x100, random.choice([0x51, 0x45]), 0)
        else:
            t = random.uniform(-1.6, 1.6); l = (int(hh // 2 - 70 * math.cos(t)) << 16) | int(w // 2 + 70 * math.sin(t))
            L.u.PostMessageW(h, 0x200, 0, l); L.u.PostMessageW(h, 0x201, 1, l); L.u.PostMessageW(h, 0x202, 0, l)
        time.sleep(0.012)
    L.u.PostMessageW(h, 0x100, 0x1B, 0); time.sleep(0.3)
    if n in (2, 5, 10, 20, 30, 40, 50, 60, 70, 80): print("%3d openings: handles %d, private %.1f MB, gdi %d, user %d" % ((n,) + L.stats(p.pid)), flush=True)
time.sleep(34)
print("idle 34 s   : handles %d, private %.1f MB, gdi %d, user %d" % L.stats(p.pid))
L.command("quit\n"); print("exit", p.wait(6))
