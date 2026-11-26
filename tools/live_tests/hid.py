"""Runs test copies on a hidden desktop of their own: nothing appears on the person's screen, and windows are only
looked up there, so a test can never meet the person's real windows."""
import ctypes as C, ctypes.wintypes as W, os

u = C.WinDLL("user32", use_last_error=True)
k = C.WinDLL("kernel32", use_last_error=True)
NAME = "rt_hidden_test"
u.CreateDesktopW.restype = W.HANDLE
u.CreateDesktopW.argtypes = [W.LPCWSTR, W.LPCWSTR, C.c_void_p, W.DWORD, W.DWORD, C.c_void_p]
u.SetThreadDesktop.argtypes = [W.HANDLE]
u.GetThreadDesktop.restype = W.HANDLE
u.GetThreadDesktop.argtypes = [W.DWORD]


class SI(C.Structure):
    _fields_ = [("cb", W.DWORD), ("r", W.LPWSTR), ("lpDesktop", W.LPWSTR), ("lpTitle", W.LPWSTR), ("x", W.DWORD), ("y", W.DWORD), ("xs", W.DWORD), ("ys", W.DWORD),
                ("xc", W.DWORD), ("yc", W.DWORD), ("fa", W.DWORD), ("flags", W.DWORD), ("show", W.WORD), ("r2", W.WORD), ("r3", C.c_void_p), ("i", W.HANDLE), ("o", W.HANDLE),
                ("e", W.HANDLE)]


class PI(C.Structure):
    _fields_ = [("hProcess", W.HANDLE), ("hThread", W.HANDLE), ("pid", W.DWORD), ("tid", W.DWORD)]


k.CreateProcessW.argtypes = [W.LPCWSTR, W.LPWSTR, C.c_void_p, C.c_void_p, W.BOOL, W.DWORD, C.c_void_p, W.LPCWSTR, C.POINTER(SI), C.POINTER(PI)]
k.WaitForSingleObject.argtypes = [W.HANDLE, W.DWORD]
k.GetExitCodeProcess.argtypes = [W.HANDLE, C.POINTER(W.DWORD)]
k.TerminateProcess.argtypes = [W.HANDLE, W.UINT]


def enter():
    """Puts the calling thread on the hidden desktop. Must come before anything that makes a window."""
    h = u.CreateDesktopW(NAME, None, None, 0, 0x10000000, None)
    if not h:
        raise OSError("CreateDesktop %d" % C.get_last_error())
    if not u.SetThreadDesktop(h):
        raise OSError("SetThreadDesktop %d" % C.get_last_error())
    b = C.create_unicode_buffer(64)
    u.GetUserObjectInformationW.argtypes = [W.HANDLE, C.c_int, C.c_void_p, W.DWORD, C.c_void_p]
    u.GetUserObjectInformationW(u.GetThreadDesktop(k.GetCurrentThreadId()), 2, b, 128, None)
    assert b.value == NAME, b.value
    return h


class Proc:
    def __init__(self, args, env):
        cmd = C.create_unicode_buffer(" ".join('"%s"' % a if " " in a or not a.startswith("-") else a for a in args))
        block = C.create_unicode_buffer("\0".join("%s=%s" % kv for kv in sorted(env.items(), key=lambda q: q[0].upper())) + "\0\0")
        si = SI()
        si.cb = C.sizeof(SI)
        si.lpDesktop = "WinSta0\\" + NAME
        pi = PI()
        if not k.CreateProcessW(None, cmd, None, None, False, 0x400, block, None, C.byref(si), C.byref(pi)):
            raise OSError("CreateProcess %d" % C.get_last_error())
        self.h, self.pid = pi.hProcess, pi.pid

    def poll(self):
        if k.WaitForSingleObject(self.h, 0) != 0:
            return None
        c = W.DWORD()
        k.GetExitCodeProcess(self.h, C.byref(c))
        return c.value

    def wait(self, sec):
        if k.WaitForSingleObject(self.h, int(sec * 1000)) != 0:
            raise TimeoutError()
        return self.poll()

    def kill(self):
        k.TerminateProcess(self.h, 99)
