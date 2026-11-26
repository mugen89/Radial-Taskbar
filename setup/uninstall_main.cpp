// Uninstall.exe in the program's folder. It hands over to the program itself, which asks first and then removes
// everything, this file included.
#include <windows.h>
#include <shellapi.h>

#include "product.h"

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
  wchar_t dir[4096], exe[4200];
  DWORD n = GetModuleFileNameW(nullptr, dir, 4096);
  if (!n || n >= 4096) return 1;
  for (DWORD i = n; i-- > 0;)
    if (dir[i] == L'\\') {
      dir[i] = 0;
      break;
    }
  lstrcpynW(exe, dir, 4096);
  lstrcatW(exe, L"\\" RT_EXE);
  if (GetFileAttributesW(exe) == INVALID_FILE_ATTRIBUTES) {
    MessageBoxW(nullptr, RT_NAME L" is not in this folder any more.", L"Uninstall " RT_NAME, MB_ICONINFORMATION);
    return 2;
  }
  return (INT_PTR)ShellExecuteW(nullptr, nullptr, exe, L"--uninstall", dir, SW_SHOWNORMAL) > 32 ? 0 : 3;
}
