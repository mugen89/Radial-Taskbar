// Headless rendering for checks and documentation: no window, no screen capture.
#pragma once
#include "common.h"

namespace rt {

struct Args {
  std::vector<std::wstring> v;
  bool has(const wchar_t* name) const;
  std::wstring get(const wchar_t* name, const wchar_t* def = L"") const;
  int num(const wchar_t* name, int def) const;
  float real(const wchar_t* name, float def) const;
};
Args parseArgs();

// A made-up desktop used wherever the real one should not be shown.
ComPtr<ID2D1Bitmap1> demoWallpaper(int w, int h, bool light);

int runSnapshot(const Args& a);
int runSettingsShot(const Args& a);
int runDumpLooks(const Args& a);
int runCheckSkin(const Args& a);  // --check-skin <folder or file>
int runFuzzSkin(const Args& a);   // --fuzz-skin <id> <rounds>
int runPackSkin(const Args& a);   // --pack-skin <folder> <file>
int runDiagnose(const Args& a);  // how pins match running programs; no window titles
int runCheckUpdate(const Args& a);  // --check-update [--as-version 0.9.0] [--download]: what the News button would find

}  // namespace rt
