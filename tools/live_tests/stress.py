"""Every layout with styles and skins on the hidden desktop: random pointer, keys, wheel and clicks that launch nothing."""
import ctypes as C, ctypes.wintypes as W, json, math, os, random, re, shutil, sys, time
import hid
hid.enter()
import live_util as L
S = L.S
L.command.__defaults__ = ("RadialTaskbarHidden.alt",)
CLS = "RadialTaskbarOverlay.alt"
EXE = os.path.join(S, "st2_h.exe")
shutil.copy(L.EXE, EXE)
D = os.path.join(S, "data9h")
shutil.rmtree(D, ignore_errors=True); shutil.copytree(os.path.join(S, "data3h"), D)
BASE = json.load(open(os.path.join(D, "config.json")))
# targets that do nothing even if something is launched by mistake
for pr in BASE["profiles"]:
    for q in pr["pins"]:
        if q.get("kind") != "group": q["target"] = r"C:\does\not\exist\%s.exe" % q.get("id", "x")
        for k in q.get("children", []): k["target"] = r"C:\does\not\exist\%s.exe" % k.get("id", "x")
SK = L.SKINS
LAYOUTS = "radial flow strip orbit comb carousel globe cards corner galaxy board drum".split()
skins = ["" if s == "none" else s for s in sys.argv[1].split(",") if s] if len(sys.argv) > 1 else ["", "clockwork"]
opens = int(sys.argv[2]) if len(sys.argv) > 2 else 3
only = sys.argv[3].split(",") if len(sys.argv) > 3 else LAYOUTS
LOG = os.path.join(D, "log.txt")
bad = 0; allf = []
random.seed(7)
for layout in only:
    for sk in skins:
        c = json.loads(json.dumps(BASE))
        c["layout"] = {"type": layout, "anchor": random.choice(["center", "mouse"]), "labels": random.choice(["focused", "always"]), "showNumbers": random.random() < 0.5, "arc": random.choice([360, 360, 270, 180]),
                       "perRing": random.choice([6, 8, 10, 12]), "overflow": random.choice(["rings", "unfold", "pages"])}
        c["skin"] = sk
        json.dump(c, open(os.path.join(D, "config.json"), "w"))
        if os.path.exists(LOG): os.remove(LOG)
        p = hid.Proc([EXE, "--background"], dict(os.environ, RADIALTASKBAR_DATA=D, RADIALTASKBAR_LOG=LOG, RadialTaskbar_SKINS=SK))
        t0 = time.time()
        while not L.u.FindWindowW("RadialTaskbarHidden.alt", None) and time.time() - t0 < 15: time.sleep(0.05)
        time.sleep(0.4)
        for n in range(opens):
            L.command("open\n"); time.sleep(0.15)
            h = L.u.FindWindowW(CLS, None)
            r = W.RECT(); L.u.GetWindowRect(h, C.byref(r)); w, hh = max(10, r.right - r.left), max(10, r.bottom - r.top)
            for i in range(45):
                a = random.random()
                x, y = int(random.gauss(w / 2, w / 6)), int(random.gauss(hh / 2, hh / 6))
                lp = (max(0, y) << 16) | max(0, x)
                if a < 0.55: L.u.PostMessageW(h, 0x200, 0, lp)
                elif a < 0.80: L.u.PostMessageW(h, 0x100, random.choice([0x41, 0x44, 0x57, 0x53, 0x09]), 0)
                elif a < 0.88: L.u.PostMessageW(h, 0x20A, ((random.choice([120, -120, 40]) & 0xFFFF) << 16), lp)
                elif a < 0.94: L.u.PostMessageW(h, 0x100, random.choice([0x51, 0x45]), 0)
                else:
                    L.u.PostMessageW(h, 0x200, 0, lp); L.u.PostMessageW(h, 0x201, 1, lp); time.sleep(0.01)  # press, then leave: nothing is launched
                    L.u.PostMessageW(h, 0x200, 1, 0x00020002); L.u.PostMessageW(h, 0x202, 0, 0x00020002)
                time.sleep(0.014)
            L.u.PostMessageW(h, 0x100, 0x1B, 0); time.sleep(0.35)
        st = L.stats(p.pid)
        L.command("quit\n")
        try: rc = p.wait(8)
        except TimeoutError: rc = "HUNG"; p.kill()
        log = open(LOG, errors="replace").read() if os.path.exists(LOG) else ""
        fr = [(int(a), float(b), float(d)) for a, b, d in re.findall(r"overlay: (\d+) frames, ([\d.]+) ms average, ([\d.]+) ms worst", log)]
        op = [float(a) for a in re.findall(r"overlay: open ([\d.]+) ms", log)]
        fails = len(re.findall(r"failed|lost|rebuilding", log))
        avg = sum(a * b for a, b, _ in fr) / max(1, sum(a for a, _, _ in fr)); allf.append(avg)
        ok = rc == 0 and len(op) >= opens and not fails
        bad += not ok
        print("%-9s %-10s rc=%s opens=%d first=%.0fms later=%.0fms frame avg=%.1f worst=%.0f handles=%d priv=%.0fMB%s" %
              (layout, sk or "-", rc, len(op), op[0] if op else -1, sum(op[1:]) / max(1, len(op) - 1), avg, max([d for _, _, d in fr] or [0]), st[0], st[1], "" if ok else "  <<<<< %d fails in log" % fails), flush=True)
print("runs=%d bad=%d frames avg %.2f ms" % (len(allf), bad, sum(allf) / max(1, len(allf))))
