"""Opens the wheel with a skin on the hidden desktop; prints opening times, frame times and memory."""
import ctypes as C, ctypes.wintypes as W, json, math, os, random, shutil, sys, time
import hid
hid.enter()
import live_util as L
S = L.S
L.command.__defaults__ = ("RadialTaskbarHidden.alt",)
CLS = "RadialTaskbarOverlay.alt"
skin = sys.argv[1] if len(sys.argv) > 1 else "clockwork"
layout = sys.argv[2] if len(sys.argv) > 2 else "radial"
n = int(sys.argv[3]) if len(sys.argv) > 3 else 6
EXE = os.path.join(S, "so_h.exe")
shutil.copy(L.EXE, EXE)
D = os.path.join(S, "data8h"); shutil.rmtree(D, ignore_errors=True); shutil.copytree(os.path.join(S, "data3h"), D)
c = json.load(open(os.path.join(D, "config.json")))
c["layout"] = {"type": layout, "anchor": "center"}; c["skin"] = skin if skin != "none" else ""
json.dump(c, open(os.path.join(D, "config.json"), "w"))
LOG = os.path.join(D, "log.txt")
env = dict(os.environ, RADIALTASKBAR_DATA=D, RADIALTASKBAR_LOG=LOG, RadialTaskbar_SKINS=L.SKINS)
p = hid.Proc([EXE, "--background"], env)
time.sleep(2.2)
random.seed(1)
for k in range(n):
    L.command("open\n"); time.sleep(0.5)
    h = L.u.FindWindowW(CLS, None)
    r = W.RECT(); L.u.GetWindowRect(h, C.byref(r)); w, hh = r.right - r.left, r.bottom - r.top
    for i in range(60):
        x, y = w // 2 + random.randint(-300, 300), hh // 2 + random.randint(-300, 300)
        L.u.PostMessageW(h, 0x200, 0, (y << 16) | x); time.sleep(0.016)
    st = L.stats(p.pid)
    L.u.PostMessageW(h, 0x100, 0x1B, 0); time.sleep(0.6)
    print("open %d: handles %d, private %.1f MB" % (k + 1, st[0], st[1]), flush=True)
time.sleep(33)
print("after 33 s: handles %d, private %.1f MB" % L.stats(p.pid)[:2])
L.command("quit\n"); print("exit", p.wait(6))
for l in open(LOG, errors="replace"):
    if "overlay" in l or "skin" in l: print(l.rstrip())
