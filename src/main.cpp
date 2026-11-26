#include "app.h"
#include "icons.h"
#include "install.h"
#include "sitelogo.h"
#include "taskrow.h"
#include "snapshot.h"
#include "skinart.h"

using namespace rt;

int WINAPI wWinMain(HINSTANCE inst, HINSTANCE, PWSTR, int) {
  // Only ever load system DLLs from System32, never from the folder we are run from.
  SetDefaultDllDirectories(LOAD_LIBRARY_SEARCH_SYSTEM32 | LOAD_LIBRARY_SEARCH_USER_DIRS);
  OleInitialize(nullptr);
  Args args = parseArgs();
  gfx().onRelease.push_back([] { icons().dropDevice(); });
  gfx().onRelease.push_back([] { skinArt().dropDevice(); });
  int rc = 0;
  if (args.has(L"--snapshot") || args.has(L"--settings-shot") || args.has(L"--fuzz-skin")) {
    icons().start(nullptr, 0);
    rc = args.has(L"--snapshot") ? runSnapshot(args) : args.has(L"--fuzz-skin") ? runFuzzSkin(args) : runSettingsShot(args);
    icons().stop();
  } else if (args.has(L"--icon-worker")) {
    rc = runIconHelper(args.get(L"--icon-worker"));
  } else if (args.has(L"--logo-worker")) {
    rc = runLogoHelper(args.get(L"--logo-worker"));
  } else if (args.has(L"--settings-window") || args.has(L"--add-skin")) {
    App app;
    rc = app.runSettings(inst, args);
  } else if (args.has(L"--pin-window")) {
    rc = runPinHelper(args.get(L"--pin-window"), args.get(L"--out"));
  } else if (args.has(L"--taskbar-row")) {
    rc = runTaskbarRow(inst, args);
  } else if (args.has(L"--row-shot")) {
    rc = runRowShot(args);
  } else if (args.has(L"--diagnose")) {
    rc = runDiagnose(args);
  } else if (args.has(L"--check-update")) {
    rc = runCheckUpdate(args);
  } else if (args.has(L"--check-skin")) {
    rc = runCheckSkin(args);
  } else if (args.has(L"--pack-skin")) {
    rc = runPackSkin(args);
  } else if (args.has(L"--dump-looks")) {
    rc = runDumpLooks(args);
  } else if (args.has(L"--uninstall")) {
    rc = runUninstall(args.v);
  } else if (args.has(L"--uninstall-run")) {
    rc = runUninstallStage2(args.get(L"--uninstall-run"), args.has(L"--silent"), args.has(L"--purge"));
  } else {
    App app;
    rc = app.run(inst, args);
  }
  gfx().shutdown();
  OleUninitialize();
  return rc;
}
