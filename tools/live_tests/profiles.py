"""Profiles on the wheel, on the hidden desktop: locked ones are skipped, scrolling can be reversed, each can have its own skin."""
import ctypes as C, json, os, shutil, sys, time
import hid
hid.enter()
import live_util as L
S, u = L.S, L.u
EXE = os.path.join(S, "pr_h.exe")
shutil.copy(sys.argv[1] if len(sys.argv) > 1 else L.EXE, EXE)
HID, CLS = "RadialTaskbarHidden.alt", "RadialTaskbarOverlay.alt"
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


D = os.path.join(S, "data20h")


def cfg():
    try: return json.load(open(os.path.join(D, "config.json"), encoding="utf-8"))
    except Exception: return {}


def start(active, reverse=False):
    shutil.rmtree(D, ignore_errors=True); shutil.copytree(os.path.join(S, "data3h"), D)
    c = cfg()
    w = os.environ["WINDIR"]
    pin = lambda p, i: {"id": "%s%d" % (p, i), "kind": "file", "name": "N%d" % i, "target": w + "\\System32\\notepad.exe" if i % 2 else w + "\\explorer.exe"}
    c["profiles"] = [{"id": p, "name": p.upper(), "locked": p in "be", "skin": "neon" if p == "c" else "", "pins": [pin(p, i) for i in range(n)]} for p, n in (("a", 3), ("b", 4), ("c", 5), ("d", 6), ("e", 7))]
    c["activeProfile"] = active
    c["skin"] = ""
    c["profileSkins"] = True
    c.setdefault("layout", {}).update(type="radial", anchor="center")
    c.setdefault("behavior", {}).update(reverseScroll=reverse)
    json.dump(c, open(os.path.join(D, "config.json"), "w"))
    p = hid.Proc([EXE, "--background"], dict(os.environ, RADIALTASKBAR_DATA=D, RADIALTASKBAR_LOG=os.path.join(D, "log.txt"), RadialTaskbar_SKINS=L.SKINS))
    until(lambda: u.FindWindowW(HID, None), 10)
    time.sleep(0.8)
    return p


def wheel(notches):
    o = u.FindWindowW(CLS, None)
    d = (120 * notches) & 0xFFFF
    u.PostMessageW(o, 0x20A, d << 16, (400 << 16) | 400)
    time.sleep(0.9)


def opened():
    L.command("open\n", HID)
    return until(lambda: (lambda h: bool(h and u.IsWindowVisible(h)))(u.FindWindowW(CLS, None)), 4)


def active(want):
    return until(lambda: cfg().get("activeProfile") == want, 6)


# a, b (locked), c (its own skin), d, e (locked)
p = start(0)
check("the wheel opens", opened())
wheel(-1)
check("scrolling down skips the locked profile", active(2), str(cfg().get("activeProfile")))
wheel(-1)
check("and goes on to the next", active(3), str(cfg().get("activeProfile")))
wheel(-1)
check("past the locked last one, round to the first", active(0), str(cfg().get("activeProfile")))
wheel(1)
check("scrolling up goes back, skipping locked ones", active(3), str(cfg().get("activeProfile")))
o = u.FindWindowW(CLS, None)
u.PostMessageW(o, 0x100, ord("Q"), 0); time.sleep(0.8)
check("Q skips them too", active(2), str(cfg().get("activeProfile")))
log = open(os.path.join(D, "log.txt"), errors="replace").read()
check("the profile with its own skin brought it along", "overlay: skin asked" in log, "")
L.capture(o, os.path.join(S, "profile_own_skin.png"))
u.PostMessageW(o, 0x100, 0x1B, 0); time.sleep(0.5)
L.command("quit\n", HID); p.wait(8)

p = start(0, reverse=True)
opened()
wheel(-1)
check("reversed: scrolling down goes back", active(3), str(cfg().get("activeProfile")))
wheel(1)
check("reversed: scrolling up goes forward", active(0), str(cfg().get("activeProfile")))
u.PostMessageW(u.FindWindowW(CLS, None), 0x100, 0x1B, 0); time.sleep(0.5)
L.command("quit\n", HID); p.wait(8)

p = start(1)  # left on a locked one, say after editing it in the settings
check("the wheel opens", opened())
check("on the next profile that is not locked", active(2), str(cfg().get("activeProfile")))
u.PostMessageW(u.FindWindowW(CLS, None), 0x100, 0x1B, 0); time.sleep(0.5)
L.command("quit\n", HID)
check("program ends", p.wait(8) == 0)
print("FAILED:", bad)
