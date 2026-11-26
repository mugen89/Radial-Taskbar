import ctypes as C, ctypes.wintypes as W
w=C.WinDLL('wtsapi32'); p=C.c_void_p(); n=W.DWORD()
w.WTSQuerySessionInformationW.argtypes=[W.HANDLE,W.DWORD,C.c_int,C.POINTER(C.c_void_p),C.POINTER(W.DWORD)]
w.WTSQuerySessionInformationW(None,0xFFFFFFFF,25,C.byref(p),C.byref(n))
v=C.cast(p,C.POINTER(C.c_int32))
class L(C.Structure): _fields_=[("cb",W.UINT),("t",W.DWORD)]
l=L(8,0); C.windll.user32.GetLastInputInfo(C.byref(l))
print('locked' if v[4]==0 else 'unlocked', 'idle %.0f s' % ((C.windll.kernel32.GetTickCount()-l.t)/1000))
