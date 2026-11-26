import ctypes as C, ctypes.wintypes as W, json, os, tempfile
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXE = os.path.join(ROOT, "dist", "RadialTaskbar.exe")
SKINS = os.path.join(ROOT, "skins")
S = os.path.join(tempfile.gettempdir(), "rt2_live")      # everything a test writes goes here
if not os.path.exists(os.path.join(S, "data3h", "config.json")):
    os.makedirs(os.path.join(S, "data3h"), exist_ok=True)
    w = os.environ["WINDIR"]
    apps = [("Explorer", w + "\\explorer.exe")] + [(n, w + "\\System32\\" + n + ".exe") for n in "notepad taskmgr cmd mstsc charmap control magnify perfmon cleanmgr dxdiag winver".split()]
    pin = lambda p, i, n, t: {"id": "%s%d" % (p, i), "kind": "file", "name": n, "target": t}
    prof = lambda p, n, k: {"id": p, "name": n, "pins": [pin(p, i, *a) for i, a in enumerate(apps[:k])]}
    main = prof("a", "Main", 11)
    main["pins"][2] = {"id": "g", "kind": "group", "name": "Tools", "children": [pin("g", i, *a) for i, a in enumerate(apps[3:8])]}
    json.dump({"version": 2, "firstRun": False, "hotkey": {"mods": 14, "vk": 123}, "behavior": {"trayIcon": False, "taskbarMenu": False}, "profiles": [main, prof("b", "Games", 5), prof("c", "Home", 14)]},
              open(os.path.join(S, "data3h", "config.json"), "w"))
u, g, k, ps = C.windll.user32, C.windll.gdi32, C.windll.kernel32, C.windll.psapi
u.FindWindowW.restype = W.HWND
u.GetForegroundWindow.restype = W.HWND
u.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
u.SendMessageTimeoutW.argtypes = [W.HWND, W.UINT, W.WPARAM, C.c_void_p, W.UINT, W.UINT, C.c_void_p]
u.PrintWindow.argtypes = [W.HWND, W.HDC, W.UINT]
u.GetDC.restype = W.HDC; u.GetDC.argtypes = [W.HWND]
u.ReleaseDC.argtypes = [W.HWND, W.HDC]
g.CreateCompatibleDC.restype = W.HDC; g.CreateCompatibleDC.argtypes = [W.HDC]
g.CreateDIBSection.restype = W.HBITMAP
g.CreateDIBSection.argtypes = [W.HDC, C.c_void_p, W.UINT, C.POINTER(C.c_void_p), W.HANDLE, W.DWORD]
g.SelectObject.argtypes = [W.HDC, W.HGDIOBJ]; g.SelectObject.restype = W.HGDIOBJ
g.DeleteObject.argtypes = [W.HGDIOBJ]; g.DeleteDC.argtypes = [W.HDC]
k.OpenProcess.restype = W.HANDLE
u.SetProcessDpiAwarenessContext(C.c_void_p(-4))

class LII(C.Structure): _fields_ = [("cb", W.UINT), ("t", W.DWORD)]
def idle():
    l = LII(8, 0); u.GetLastInputInfo(C.byref(l)); return (k.GetTickCount() - l.t) / 1000.0
class CDS(C.Structure): _fields_ = [("d", C.c_void_p), ("n", W.DWORD), ("p", C.c_void_p)]
def command(text, cls="RadialTaskbarHidden.alt"):
    h = u.FindWindowW(cls, None)
    if not h: return False
    b = C.create_unicode_buffer(text)
    c = CDS(0x5254, C.sizeof(b), C.cast(b, C.c_void_p)); r = C.c_size_t()
    u.SendMessageTimeoutW(h, 0x4A, 0, C.byref(c), 2, 4000, C.byref(r)); return True
class PMC(C.Structure):
    _fields_ = [("cb", W.DWORD), ("pf", W.DWORD)] + [(n, C.c_size_t) for n in ("pws", "ws", "qpp", "qp", "qnp", "qnp2", "pfu", "ppfu", "priv")]
def stats(pid):
    h = k.OpenProcess(0x1000 | 0x0400, False, pid)
    n = W.DWORD(); k.GetProcessHandleCount(h, C.byref(n))
    m = PMC(); m.cb = C.sizeof(m); ps.GetProcessMemoryInfo(h, C.byref(m), m.cb)
    r = (n.value, m.priv / 1048576.0, u.GetGuiResources(h, 0), u.GetGuiResources(h, 1)); k.CloseHandle(h)
    return r
class BIH(C.Structure):
    _fields_ = [("biSize", W.DWORD), ("biWidth", W.LONG), ("biHeight", W.LONG), ("biPlanes", W.WORD), ("biBitCount", W.WORD),
                ("biCompression", W.DWORD), ("biSizeImage", W.DWORD), ("x", W.LONG), ("y", W.LONG), ("cu", W.DWORD), ("ci", W.DWORD)]
def capture(h, path, crop=None):
    r = W.RECT(); u.GetWindowRect(h, C.byref(r)); w, hh = r.right - r.left, r.bottom - r.top
    sdc = u.GetDC(None); mdc = g.CreateCompatibleDC(sdc)
    bi = BIH(C.sizeof(BIH), w, -hh, 1, 32, 0, 0, 0, 0, 0, 0); bits = C.c_void_p()
    bm = g.CreateDIBSection(sdc, C.byref(bi), 0, C.byref(bits), None, 0)
    old = g.SelectObject(mdc, bm)
    ok = u.PrintWindow(h, mdc, 2)
    im = Image.frombuffer("RGBA", (w, hh), C.string_at(bits, w * hh * 4), "raw", "BGRA", 0, 1).convert("RGB")
    g.SelectObject(mdc, old); g.DeleteObject(bm); g.DeleteDC(mdc); u.ReleaseDC(None, sdc)
    if crop: im = im.crop(crop)
    im.save(path); return ok
