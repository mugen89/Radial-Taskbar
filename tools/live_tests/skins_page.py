"""The Skins page, adding by double-click, and taking over the test version's settings, on the hidden desktop."""
import ctypes as C, ctypes.wintypes as W, json, os, shutil, subprocess, sys, time, zipfile
import hid
hid.enter()
import live_util as L
S = L.S
u = L.u
L.command.__defaults__ = ("RadialTaskbarHidden.alt",)
EXE = os.path.join(S, "sl_h.exe")
shutil.copy(L.EXE, EXE)
SK = L.SKINS
bad = []


def check(n, ok, more=""):
    print(("ok   " if ok else "FAIL ") + n, more, flush=True)
    if not ok: bad.append(n)


def fresh(name):
    d = os.path.join(S, name); shutil.rmtree(d, ignore_errors=True); os.makedirs(d); return d


def env(d, **k):
    return dict(os.environ, RADIALTASKBAR_DATA=d, RADIALTASKBAR_LOG=os.path.join(d, "log.txt"), RadialTaskbar_SKINS=SK, **k)


def until(f, sec=8):
    t = time.time()
    while time.time() - t < sec:
        if f(): return True
        time.sleep(0.1)
    return False


def cfg(d):
    try: return json.load(open(os.path.join(d, "config.json"), encoding="utf-8"))
    except Exception: return {}


# ---- the test version's settings are taken over once; the first version's, already in our folder, stay as a copy
beta = fresh("betaprobe"); os.makedirs(os.path.join(beta, "images")); os.makedirs(os.path.join(beta, "links")); os.makedirs(os.path.join(beta, "skins", "mine"))
open(os.path.join(beta, "images", "yt.png"), "wb").write(b"\x89PNG-not-really")
open(os.path.join(beta, "links", "a.lnk"), "wb").write(b"L" * 100)
open(os.path.join(beta, "skins", "probe2.rskin"), "wb").write(b"PK-not-really")
open(os.path.join(beta, "skins", "mine", "skin.json"), "w").write('{"id": "mine", "name": "Mine"}')
conf = {"version": 2, "firstRun": False, "hotkey": {"mods": 8, "vk": 192}, "layout": {"type": "radial", "scale": 1.4}, "style": {"skin": "tactical", "accent": "#FFB000"},
        "behavior": {"taskbarMenu": True}, "activeProfile": 0, "skin": "neon", "skinPerProfile": True,
        "profiles": [{"id": "a", "name": "Main", "skin": "neon", "pins": [{"id": "1", "kind": "url", "name": "Tube", "target": "https://example.com", "icon": os.path.join(beta, "images", "yt.png")},
                                                                       {"id": "2", "kind": "file", "name": "A", "target": os.path.join(beta, "links", "a.lnk")}]},
                     {"id": "b", "name": "sites", "skin": "clockwork", "pins": [{"id": "g", "kind": "group", "name": "G", "children": [{"id": "3", "kind": "file", "name": "B", "target": os.path.join(beta, "links", "a.lnk")}]}]}]}
json.dump(conf, open(os.path.join(beta, "config.json"), "w"))
before = open(os.path.join(beta, "config.json")).read()
D = fresh("data10h")
open(os.path.join(D, "config.json"), "w").write('{"firstRun": false, "profiles": [{"id": "old", "name": "First version", "pins": []}]}')
p = hid.Proc([EXE, "--background"], env(D, RadialTaskbar_BETA=beta))
check("starts", until(lambda: u.FindWindowW("RadialTaskbarHidden.alt", None)))
until(lambda: "sites" in open(os.path.join(D, "config.json")).read())
c = cfg(D)
check("profiles and pins taken over", [x["name"] for x in c.get("profiles", [])] == ["Main", "sites"] and len(c["profiles"][0]["pins"]) == 2)
pin = c["profiles"][0]["pins"]
check("pictures and shortcuts are copies of our own", pin[0]["icon"].startswith(D) and os.path.exists(pin[0]["icon"]) and pin[1]["target"].startswith(D) and c["profiles"][1]["pins"][0]["children"][0]["target"].startswith(D))
check("looks, layout and shortcut taken over", c["style"]["accent"].upper() == "#FFB000" and abs(c["layout"]["scale"] - 1.4) < 0.01 and c["hotkey"]["mods"] == 8 and c["behavior"]["taskbarMenu"] is True)
check("the first profile's skin is the main one, the other keeps its own", c.get("skin") == "neon" and not c["profiles"][0].get("skin") and c["profiles"][1].get("skin") == "clockwork", str([c.get("skin")] + [x.get("skin") for x in c["profiles"]]))
check("added skins come along, folders too", os.path.exists(os.path.join(D, "skins", "probe2.rskin")) and os.path.exists(os.path.join(D, "skins", "mine", "skin.json")))
check("the first version's settings stay as a copy", "First version" in open(os.path.join(D, "config.json.first-version")).read() and os.path.exists(os.path.join(D, "taken-over.txt")))
check("nothing changed over there", open(os.path.join(beta, "config.json")).read() == before and os.path.exists(os.path.join(beta, "images", "yt.png")))
os.remove(os.path.join(D, "skins", "probe2.rskin")); shutil.rmtree(os.path.join(D, "skins", "mine"))
L.command("quit\n"); p.wait(8)
conf["profiles"][0]["name"] = "Changed later"; json.dump(conf, open(os.path.join(beta, "config.json"), "w"))
p = hid.Proc([EXE, "--background"], env(D, RadialTaskbar_BETA=beta))
check("starts again", until(lambda: u.FindWindowW("RadialTaskbarHidden.alt", None)))
time.sleep(1.5)
check("and takes over only once", "Changed later" not in open(os.path.join(D, "config.json")).read() and cfg(D)["profiles"][0]["name"] == "Main")

# ---- the Skins page
s = hid.Proc([EXE, "--settings-window", "--page", "2"], env(D))
check("settings open", until(lambda: u.FindWindowW("RadialTaskbarSettings.alt", None), 15))
h = u.FindWindowW("RadialTaskbarSettings.alt", None)
time.sleep(2.0)
u.SetWindowPos.argtypes = [W.HWND, W.HWND, C.c_int, C.c_int, C.c_int, C.c_int, W.UINT]
dpi = u.GetDpiForWindow(h) / 96.0
wr, cr = W.RECT(), W.RECT(); u.GetWindowRect(h, C.byref(wr)); u.GetClientRect(h, C.byref(cr))
u.SetWindowPos(h, None, 50, 50, int(1180 * dpi) + (wr.right - wr.left) - cr.right, int(780 * dpi) + (wr.bottom - wr.top) - cr.bottom, 0x14)
time.sleep(0.6)


def click(x, y, wait=0.5):
    lp = (int(y * dpi) << 16) | int(x * dpi)
    u.PostMessageW(h, 0x200, 0, lp); time.sleep(0.06); u.PostMessageW(h, 0x201, 1, lp); time.sleep(0.06); u.PostMessageW(h, 0x202, 0, lp); time.sleep(wait)


click(590, 300)
check("a click on a card chooses the skin", until(lambda: cfg(D).get("skin")), cfg(D).get("skin"))
first = cfg(D).get("skin")
click(350, 300)
check("and No skin turns it off", until(lambda: not cfg(D).get("skin")))
click(590, 300); until(lambda: cfg(D).get("skin"))
time.sleep(1.0)
L.capture(h, os.path.join(S, "skins_live.png"))

# ---- a file from somewhere else, by double-click
zf = os.path.join(S, "probe skin.rskin")
with zipfile.ZipFile(zf, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("skin.json", json.dumps({"id": "probe", "name": "Probe skin", "author": "Somebody", "about": "Only for the check", "style": {"accent": "#00FF88"},
                                        "hub": [{"shape": "circle", "size": 1, "fill": "accent/50"}]}))
a = hid.Proc([EXE, "--add-skin", zf], env(D))
dlg = []
ENUM = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)


def find(hw, lp):
    b = C.create_unicode_buffer(64); u.GetClassNameW(hw, b, 64)
    pid = W.DWORD(); u.GetWindowThreadProcessId(hw, C.byref(pid))
    if b.value == "#32770" and pid.value == s.pid: dlg.append(hw)
    return True


def dialog():
    dlg.clear()
    hid.u.EnumDesktopWindows.argtypes = [W.HANDLE, ENUM, W.LPARAM]
    hid.u.EnumDesktopWindows(hid.u.GetThreadDesktop(hid.k.GetCurrentThreadId()), ENUM(find), 0)
    return bool(dlg)


check("the question comes up in the open settings window", until(dialog, 8))
if dlg:
    u.PostMessageW(dlg[0], 0x111, 1, 0)  # OK
check("the skin was copied", until(lambda: os.path.exists(os.path.join(D, "skins", "probe.rskin"))))
check("and is in use", until(lambda: cfg(D).get("skin") == "probe"), cfg(D).get("skin"))
check("the helper process is gone", a.wait(6) == 0)
# the resident part uses it too
time.sleep(1.5)
L.command("open\n"); time.sleep(0.8)
o = u.FindWindowW("RadialTaskbarOverlay.alt", None)
check("the wheel opens with it", bool(o and u.IsWindowVisible(o)))
u.PostMessageW(o, 0x100, 0x1B, 0); time.sleep(0.5)
# an edited file is noticed
with zipfile.ZipFile(zf, "w") as z: z.writestr("skin.json", json.dumps({"id": "probe", "name": "Probe two", "style": {"accent": "#FF0088"}}))
shutil.copy(zf, os.path.join(D, "skins", "probe.rskin")); time.sleep(1.2)
L.command("open\n"); time.sleep(0.6); u.PostMessageW(o, 0x100, 0x1B, 0); time.sleep(0.4)
# junk by double-click
jf = os.path.join(S, "junk.rskin"); open(jf, "wb").write(b"hello" * 50)
hid.Proc([EXE, "--add-skin", jf], env(D))
check("junk is refused with a message", until(dialog, 8))
if dlg: u.PostMessageW(dlg[0], 0x111, 2, 0); time.sleep(0.2); u.PostMessageW(dlg[0], 0x111, 1, 0)
time.sleep(0.8)
check("nothing was added", not os.path.exists(os.path.join(D, "skins", "junk.rskin")))
# the skins that are handed out as files, one after the other
IMP = os.path.join(L.ROOT, "dist", "skins to import")
for f in sorted(os.listdir(IMP)):
    i = f.rsplit(".", 1)[0]
    b = hid.Proc([EXE, "--add-skin", os.path.join(IMP, f)], env(D))
    check(f + ": the question comes up", until(dialog, 8))
    if dlg: u.PostMessageW(dlg[0], 0x111, 1, 0)
    check(f + ": copied and in use", until(lambda: os.path.exists(os.path.join(D, "skins", f)) and cfg(D).get("skin") == i), cfg(D).get("skin"))
    b.wait(6); time.sleep(1.6)
    L.command("open\n"); time.sleep(1.0)
    check(f + ": the wheel opens with it", bool(u.IsWindowVisible(o)))
    L.capture(o, os.path.join(S, "import_%s.png" % i))
    u.PostMessageW(o, 0x100, 0x1B, 0); time.sleep(0.5)
# one of them leaves again through the gallery's own file
os.remove(os.path.join(D, "skins", "winter.rskin")); time.sleep(0.5)
shutil.copy(zf, os.path.join(D, "skins", "probe.rskin")); time.sleep(0.3)
b = hid.Proc([EXE, "--add-skin", zf], env(D)); until(dialog, 8)
if dlg: u.PostMessageW(dlg[0], 0x111, 1, 0)
until(lambda: cfg(D).get("skin") == "probe"); b.wait(6)
# the skin disappears while it is in use
os.remove(os.path.join(D, "skins", "probe.rskin")); time.sleep(2.2)
L.command("open\n"); time.sleep(0.6)
check("the wheel still opens when its skin is gone", bool(u.IsWindowVisible(o)))
u.PostMessageW(o, 0x100, 0x1B, 0); time.sleep(0.5)
u.PostMessageW(h, 0x10, 0, 0)
check("settings close", s.wait(8) == 0)
L.command("quit\n")
check("program ends", p.wait(8) == 0)
log = open(os.path.join(D, "log.txt"), errors="replace").read()
print("\n".join(l for l in log.splitlines() if "skin" in l or "fail" in l)[-1500:])
print("FAILED:", bad)
