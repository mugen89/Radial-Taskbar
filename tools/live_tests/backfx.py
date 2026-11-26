"""The background effects and the profile the wheel always opens on, in the real program on the hidden desktop."""
import json, os, re, shutil, sys, time
import hid
hid.enter()
import live_util as L
S, u = L.S, L.u
EXE = os.path.join(S, "bf_h.exe")
shutil.copy(sys.argv[1] if len(sys.argv) > 1 else L.EXE, EXE)
HID, CLS = "RadialTaskbarHidden.alt", "RadialTaskbarOverlay.alt"
D = os.path.join(S, "data22h")
bad = []


def check(n, ok, more=""):
    print(("ok   " if ok else "FAIL ") + n, more, flush=True)
    if not ok: bad.append(n)


def until(f, sec=6):
    t = time.time()
    while time.time() - t < sec:
        if f(): return True
        time.sleep(0.1)
    return False


def cfg():
    try: return json.load(open(os.path.join(D, "config.json"), encoding="utf-8"))
    except Exception: return {}


def run(kind, start="", skin=""):
    shutil.rmtree(D, ignore_errors=True); shutil.copytree(os.path.join(S, "data3h"), D)
    c = cfg()
    c["layout"] = {"type": "radial", "anchor": "center"}
    c["skin"] = skin
    c["activeProfile"] = 0
    c.setdefault("behavior", {}).update(backFx=True, backFxKind=kind, startProfile=start)
    json.dump(c, open(os.path.join(D, "config.json"), "w"))
    p = hid.Proc([EXE, "--background"], dict(os.environ, RADIALTASKBAR_DATA=D, RADIALTASKBAR_LOG=os.path.join(D, "log.txt"), RadialTaskbar_SKINS=L.SKINS))
    until(lambda: u.FindWindowW(HID, None), 10)
    time.sleep(0.8)
    return p


def frames():
    log = open(os.path.join(D, "log.txt"), errors="replace").read()
    m = re.findall(r"overlay: (\d+) frames, ([\d.]+) ms average, ([\d.]+) ms worst", log)
    return m[-1] if m else None


for kind in ("rain", "stars", "petals"):
    p = run(kind)
    L.command("open\n", HID)
    opened = until(lambda: (lambda h: bool(h and u.IsWindowVisible(h)))(u.FindWindowW(CLS, None)), 4)
    time.sleep(2.0)  # it keeps moving while the wheel stays open
    o = u.FindWindowW(CLS, None)
    L.capture(o, os.path.join(S, "backfx_%s.png" % kind))
    u.PostMessageW(o, 0x100, 0x1B, 0); time.sleep(0.8)
    f = frames()
    check(kind + ": opens, keeps drawing while open, closes", opened and f is not None and int(f[0]) > 60, str(f))
    L.command("quit\n", HID); p.wait(8)

p = run("none", start="c")  # the Home profile is the third one
L.command("open\n", HID)
check("the wheel opens on the chosen profile", until(lambda: cfg().get("activeProfile") == 2), str(cfg().get("activeProfile")))
o = u.FindWindowW(CLS, None)
u.PostMessageW(o, 0x20A, (0xFF88) << 16, (400 << 16) | 400); time.sleep(0.9)  # on to the next one
check("scrolling still moves on", until(lambda: cfg().get("activeProfile") == 0), str(cfg().get("activeProfile")))
u.PostMessageW(o, 0x100, 0x1B, 0); time.sleep(0.8)
L.command("open\n", HID)
check("and the next opening starts there again", until(lambda: cfg().get("activeProfile") == 2), str(cfg().get("activeProfile")))
f = frames()
check("without an effect it rests when nothing moves", f is not None and int(f[0]) < 200, str(f))
u.PostMessageW(u.FindWindowW(CLS, None), 0x100, 0x1B, 0); time.sleep(0.6)
L.command("quit\n", HID)
check("program ends", p.wait(8) == 0)
print("FAILED:", bad)
