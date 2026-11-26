"""Skins that want to do harm, in the real program on the hidden desktop: memory, a lying sound file, impossible slowness."""
import ctypes as C, io, json, os, shutil, struct, sys, time, wave, zipfile
import hid
hid.enter()
import live_util as L
from PIL import Image
S = L.S
EXE = os.path.join(S, "ho_h.exe")
shutil.copy(sys.argv[1] if len(sys.argv) > 1 else L.EXE, EXE)
CLS = "RadialTaskbarOverlay.alt"
L.command.__defaults__ = ("RadialTaskbarHidden.alt",)
bad = []


def check(n, ok, more=""):
    print(("ok   " if ok else "FAIL ") + n, more, flush=True)
    if not ok: bad.append(n)


def png(w, h):
    b = io.BytesIO(); Image.new("RGB", (w, h), (90, 20, 30)).save(b, "PNG", optimize=True); return b.getvalue()


def skin(folder, sid, j, files=()):
    os.makedirs(folder, exist_ok=True)
    p = os.path.join(folder, sid + ".rskin")
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("skin.json", json.dumps(dict({"id": sid, "name": sid, "author": "nobody"}, **j)))
        for n, d in files: z.writestr(n, d)


def start(name, sounds=False):
    d = os.path.join(S, "data14h"); shutil.rmtree(d, ignore_errors=True); shutil.copytree(os.path.join(S, "data3h"), d)
    c = json.load(open(os.path.join(d, "config.json"))); c["layout"] = {"type": "radial", "anchor": "center"}; c["skin"] = name
    c.setdefault("behavior", {}).update(sounds=sounds, volume=0.05)
    json.dump(c, open(os.path.join(d, "config.json"), "w"))
    return d


def run(d):
    return hid.Proc([EXE, "--background"], dict(os.environ, RADIALTASKBAR_DATA=d, RADIALTASKBAR_LOG=os.path.join(d, "log.txt"), RadialTaskbar_SKINS=os.path.join(d, "none")))


def opened(p, n=2, stay=1.5):
    seen = 0
    for _ in range(n):
        L.command("open\n"); time.sleep(stay)
        h = L.u.FindWindowW(CLS, None)
        seen += bool(h and L.u.IsWindowVisible(h))
        if h: L.u.PostMessageW(h, 0x100, 0x1B, 0); time.sleep(0.7)
    return seen


# 1: a hundred and twenty pictures of 4096 by 4096
big = png(4096, 4096)
d = start("bomb")
skin(os.path.join(d, "skins"), "bomb", {"images": {"i%d" % k: {"file": "big.png", "sharp": True, "cols": 1 + k % 3} for k in range(119)}, "back": [{"image": "i%d" % k, "size": 1} for k in range(119)]}, [("big.png", big)])
p = run(d); worst = 0
for _ in range(60):
    time.sleep(0.2); worst = max(worst, L.stats(p.pid)[1])
check("120 huge pictures at start: alive, memory bounded", p.poll() is None and worst < 1400, "%.0f MB at most (%d KB file)" % (worst, len(big) // 1024))
n = opened(p); m = L.stats(p.pid)[1]
check("and the wheel opens", n == 2 and p.poll() is None, "%.0f MB" % m)
L.command("quit\n"); p.wait(8)

# 2: a sound that claims to be 64 MB long, and one that is fine
w = io.BytesIO()
with wave.open(w, "wb") as f: f.setnchannels(1); f.setsampwidth(2); f.setframerate(22050); f.writeframes(b"\0\1" * 800)
good = w.getvalue()
lie = bytearray(good[:60]); lie[4:8] = struct.pack("<I", 64 << 20); lie[40:44] = struct.pack("<I", 64 << 20)
for name, data in (("lie", bytes(lie)), ("honest", good)):
    d = start(name, True)
    skin(os.path.join(d, "skins"), name, {"sounds": {k: "s.wav" for k in ("open", "move", "launch", "close")}, "hub": [{"shape": "circle", "size": 1, "fill": "accent"}]}, [("s.wav", data)])
    p = run(d); time.sleep(2)
    n = opened(p, 3, 0.8)
    check("a skin with a sound (%s): alive" % name, p.poll() is None and n == 3)
    L.command("quit\n"); p.wait(8)

# 3: thousands of stars with formulas, and layers that are never shown
for name, j in (("stars", {"back": [{"shape": "star", "count": 100, "inner": "0.3+0.1*sin(time+j)", "outer": "0.8+0.1*noise(time)", "curve": True, "size": 1, "fill": "accent/20", "copies": 120} for _ in range(10)]}),
                ("letters", {"back": [{"text": "lorem ipsum dolor sit amet " * 8, "px": 14, "box": [1.5, 1], "wrap": True, "copies": 120, "y": "0.01*j", "shadow": {"x": 1, "y": 1, "blur": 6, "color": "black"}} for _ in range(4)]}),
                ("unseen", {"slot": {"under": [{"shape": "circle", "size": 1, "fill": "accent", "copies": 120, "when": "sin(j)+noise(time*j)>9"} for _ in range(190)], "over": [{"shape": "circle", "size": 1, "fill": "accent", "copies": 120, "when": "0"} for _ in range(190)]}})):
    d = start(name); skin(os.path.join(d, "skins"), name, j)
    p = run(d); time.sleep(2)
    t = time.perf_counter(); n = opened(p, 2, 2.0)
    r = C.c_size_t(); t0 = time.perf_counter(); L.u.SendMessageTimeoutW(L.u.FindWindowW("RadialTaskbarHidden.alt", None), 0, 0, None, 2, 4000, C.byref(r)); lag = (time.perf_counter() - t0) * 1000
    log = open(os.path.join(d, "log.txt"), errors="replace").read()
    fr = [l.split("overlay:")[1].strip() for l in log.splitlines() if " frames, " in l]
    check("%s: the wheel opens, the program answers" % name, n == 2 and p.poll() is None and lag < 500, "%.0f ms | %s%s" % (lag, fr[-1] if fr else "", " | left out" if "left out" in log else ""))
    L.command("quit\n"); p.wait(8)
print("FAILED:", bad)
