// Per-user installer. No administrator rights, no downloads: the program is embedded as a resource.
#include <process.h>

#include <atomic>

#include "install.h"
#include "shellutil.h"
#include "ui.h"
#include "zip.h"

using namespace rt;

namespace {

struct Options {
  std::wstring dir;
  bool autostart = true, startMenu = true, desktop = false, menus = true, sendTo = true, launch = true;
};

std::atomic<int> g_progress{0};  // 0..100
std::wstring g_error;

// The skins and their guide travel in one archive beside the program.
bool writeSkins(const std::wstring& dir) {
  HRSRC r = FindResourceW(nullptr, MAKEINTRESOURCEW(101), RT_RCDATA);
  HGLOBAL g = r ? LoadResource(nullptr, r) : nullptr;
  const void* data = g ? LockResource(g) : nullptr;
  DWORD size = r ? SizeofResource(nullptr, r) : 0;
  Archive a;
  Archive::Limits lim;
  lim.file = lim.total = 256u << 20;
  if (!data || !a.open(std::string((const char*)data, size), nullptr, lim)) return false;
  std::wstring skins = joinPath(dir, L"skins"), notes = joinPath(skins, kIncluded);
  SHCreateDirectoryExW(nullptr, skins.c_str(), nullptr);
  bool ok = true;
  std::string before, names;
  readFile(notes, before);  // what the version that is being replaced had put there
  for (auto& e : a.entries()) {
    std::string bytes;
    std::wstring name = widen(e.name);
    if (name.find(L'/') != std::wstring::npos || !a.read(e, bytes)) {
      ok = false;
      continue;
    }
    std::wstring to = joinPath(fileExt(name) == L".rskin" ? skins : dir, name), have;
    std::string old;
    if (readFile(to, old) && old == bytes) continue;
    ok &= writeFileAtomic(to, bytes);
  }
  for (auto& e : a.entries()) names += e.name + "\n";
  writeFileAtomic(notes, names);
  // Skins that no longer come with the program go; files somebody put there themselves stay.
  for (auto& n : includedSkins(before))
    if (!a.find(narrow(n))) DeleteFileW(joinPath(skins, n).c_str());
  return ok;
}

// One of the files this setup carries: 100 the program, 102 the uninstaller beside it.
bool writePayload(int id, const std::wstring& path, int from, int to) {
  HRSRC r = FindResourceW(nullptr, MAKEINTRESOURCEW(id), RT_RCDATA);
  HGLOBAL g = r ? LoadResource(nullptr, r) : nullptr;
  const void* data = g ? LockResource(g) : nullptr;
  DWORD size = r ? SizeofResource(nullptr, r) : 0;
  if (!data || size < 1024) {
    g_error = L"This setup file is damaged.";
    return false;
  }
  std::wstring tmp = path + L".new";
  HANDLE h = CreateFileW(tmp.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
  if (h == INVALID_HANDLE_VALUE) {
    g_error = L"Cannot write to that folder.";
    return false;
  }
  DWORD done = 0;
  bool ok = true;
  while (ok && done < size) {
    DWORD chunk = std::min<DWORD>(128 * 1024, size - done), wr = 0;
    ok = WriteFile(h, (const BYTE*)data + done, chunk, &wr, nullptr) && wr == chunk;
    done += wr;
    g_progress = from + (int)((to - from) * (double)done / size);
  }
  if (ok) ok = FlushFileBuffers(h) != FALSE;
  CloseHandle(h);
  if (ok) {
    // A just-closed copy can keep the old file busy for a moment.
    for (int i = 0; i < 25; i++) {
      ok = MoveFileExW(tmp.c_str(), path.c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH) != FALSE;
      if (ok) break;
      Sleep(160);
    }
  }
  if (!ok) {
    DeleteFileW(tmp.c_str());
    g_error = L"Could not replace the program file. Is it still running?";
  }
  return ok;
}

void setReg(HKEY k, const wchar_t* n, const std::wstring& v) { RegSetValueExW(k, n, 0, REG_SZ, (const BYTE*)v.c_str(), (DWORD)((v.size() + 1) * 2)); }
void setReg(HKEY k, const wchar_t* n, DWORD v) { RegSetValueExW(k, n, 0, REG_DWORD, (const BYTE*)&v, 4); }

bool install(const Options& o) {
  g_progress = 5;
  if (!quitRunningApp(6000)) {
    g_error = RT_NAME L" is running and did not close. Exit it from the tray and try again.";
    return false;
  }
  g_progress = 15;
  int e = SHCreateDirectoryExW(nullptr, o.dir.c_str(), nullptr);
  if (e != ERROR_SUCCESS && e != ERROR_ALREADY_EXISTS && e != ERROR_FILE_EXISTS) {
    g_error = L"Cannot create that folder.";
    return false;
  }
  // The test version with skins goes first: two copies would fight over the shortcut.
  if (betaThere() && !removeBeta(15000)) logf("setup: the test version could not be removed");
  g_progress = 18;
  std::wstring exe = joinPath(o.dir, kExeName);
  if (!writePayload(100, exe, 20, 66)) return false;
  if (!writePayload(102, joinPath(o.dir, kUninstaller), 66, 70)) logf("setup: no uninstaller beside the program");
  g_progress = 72;
  if (!writeSkins(o.dir)) logf("setup: not every skin could be written");  // the program works without them
  setSkinType(true, exe);
  g_progress = 80;

  if (o.startMenu) createShortcut(startMenuLink(), exe, L"", L"Open your pinned apps in a wheel", kAppUserModelId);
  if (o.desktop) createShortcut(desktopLink(), exe, L"", L"Open your pinned apps in a wheel", kAppUserModelId);
  if (o.sendTo) createShortcut(sendToLink(), exe, L"--pin", L"Pin to " RT_NAME);
  else DeleteFileW(sendToLink().c_str());
  if (o.menus || fileMenuOn()) setFileMenu(o.menus, exe);
  g_progress = 85;

  const wchar_t* runKey = L"Software\\Microsoft\\Windows\\CurrentVersion\\Run";
  if (o.autostart) {
    std::wstring cmd = L"\"" + exe + L"\" --background";
    RegSetKeyValueW(HKEY_CURRENT_USER, runKey, kRunValue, REG_SZ, cmd.c_str(), (DWORD)((cmd.size() + 1) * 2));
  } else {
    RegDeleteKeyValueW(HKEY_CURRENT_USER, runKey, kRunValue);
  }

  HKEY k;
  if (RegCreateKeyExW(HKEY_CURRENT_USER, kUninstallKey, 0, nullptr, 0, KEY_WRITE, nullptr, &k, nullptr) == ERROR_SUCCESS) {
    WIN32_FILE_ATTRIBUTE_DATA fa{};
    GetFileAttributesExW(exe.c_str(), GetFileExInfoStandard, &fa);
    SYSTEMTIME t;
    GetLocalTime(&t);
    wchar_t date[16];
    swprintf(date, 16, L"%04d%02d%02d", t.wYear, t.wMonth, t.wDay);
    setReg(k, L"DisplayName", kAppName);
    setReg(k, L"DisplayVersion", widen(RT_VERSION_STR));
    setReg(k, L"DisplayIcon", exe);
    setReg(k, L"Publisher", kAppName);
    setReg(k, L"InstallLocation", o.dir);
    setReg(k, L"InstallDate", date);
    setReg(k, L"UninstallString", L"\"" + exe + L"\" --uninstall");
    setReg(k, L"QuietUninstallString", L"\"" + exe + L"\" --uninstall --silent");
    setReg(k, L"EstimatedSize", (fa.nFileSizeLow + 1023) / 1024);
    setReg(k, L"NoModify", 1);
    setReg(k, L"NoRepair", 1);
    RegCloseKey(k);
  }
  SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, nullptr, nullptr);
  g_progress = 100;
  return true;
}

void launch(const Options& o) {
  std::wstring exe = joinPath(o.dir, kExeName);
  AllowSetForegroundWindow(ASFW_ANY);
  ShellExecuteW(nullptr, nullptr, exe.c_str(), nullptr, o.dir.c_str(), SW_SHOWNORMAL);
}

struct Job {
  Options o;
  std::atomic<int> state{0};  // 1 running, 2 done, 3 failed
};
unsigned __stdcall worker(void* p) {
  auto* j = (Job*)p;
  CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED | COINIT_DISABLE_OLE1DDE);
  bool ok = install(j->o);
  CoUninitialize();
  j->state = ok ? 2 : 3;
  return 0;
}

class SetupWindow final : public UiWindow {
 public:
  Job job;
  bool upgrade = false, beta = false;
  std::wstring oldVersion;
  bool closed = false;

  bool create(HINSTANCE inst) { return createWindow(inst, RT_ID L"Setup", RT_NAME L" Setup", 760, 480, 760, 480, false); }
  void show() {
    frame();
    ShowWindow(hwnd(), SW_SHOW);
    SetForegroundWindow(hwnd());
  }
  void preview(int step) {
    step_ = step;
    job.state = step == 2 ? 2 : 0;
    shown_ = 0.62f;
  }

 protected:
  bool onClose() override {
    if (job.state == 1) return false;
    closed = true;
    PostQuitMessage(0);
    return true;
  }

  void wheel(RectF r) {
    time_ += ui.dt;
    ui.animating = true;
    auto bg = ui.p->linear({r.l, r.t}, {r.r, r.b}, {{0, Color::hex(0x1A2440)}, {0.55f, Color::hex(0x221B44)}, {1, Color::hex(0x141A2E)}});
    ui.p->dc->FillRectangle(r.f(), bg.Get());
    V2 c{r.cx(), r.cy() - 6};
    float R = 112;
    auto halo = ui.p->radial(c, R * 1.7f, R * 1.7f, {{0, Color::hex(0x3E6BFF, 0.22f)}, {1, Color::hex(0x3E6BFF, 0)}});
    ui.p->dc->FillEllipse(D2D1::Ellipse(c.p(), R * 1.7f, R * 1.7f), halo.Get());
    const int n = 10;
    float want = floorf(fmodf(time_ * 1.15f, (float)n));
    lit_ += (wrapAngle((want - lit_) * kTau / n) * n / kTau) * (1.f - expf(-9.f * ui.dt));
    float in = easeOutCubic(saturate(time_ * 1.6f));
    for (int i = 0; i < n; i++) {
      float a = i * kTau / n;
      float d = fabsf(wrapAngle((i - lit_) * kTau / n)) / (kTau / n);
      float h = std::max(0.f, 1.f - d);
      float r0 = 52 + h * 3, r1 = lerp(70.f, R, in) + h * 13;
      auto g = wedgeGeo(c, r0, r1, a - kTau / n / 2, a + kTau / n / 2, 6, 11);
      Color ac = mix(Color::hex(0x2DD4FF), Color::hex(0x9A6BFF), 0.5f - 0.5f * cosf(a));
      ui.p->fill(g.Get(), Color(1, 1, 1, 0.09f * in));
      if (h > 0.01f) {
        ui.p->glow(g.Get(), ac.withA(0.6f * h), 8, 3);
        ui.p->fill(g.Get(), ac.withA(0.62f * h));
      }
      ui.p->stroke(g.Get(), mix(Color(1, 1, 1, 0.16f), ac, h).alpha(in), 1.2f);
      V2 q = polar(c, a, (r0 + r1) * 0.5f);
      float s = 8.f + 3.f * h;
      ui.p->rrect(RectF(q.x - s, q.y - s, q.x + s, q.y + s), s * 0.5f, Color(1, 1, 1, (0.30f + 0.65f * h) * in));
    }
    ui.p->circle(c, 43, Color(0, 0, 0, 0.25f));
    ui.p->circleStroke(c, 43, Color(1, 1, 1, 0.16f), 1.2f);
    ui.text(RectF(c.x - 60, c.y - 30, c.x + 60, c.y + 30), L"Win + `", 15.f, Color(1, 1, 1, 0.92f * in), 600, Align::Center);
  }

  bool check(uint32_t id, RectF r, const wchar_t* label, bool& v) {
    bool c = ui.press(id, r);
    if (c) v = !v;
    bool h = ui.hot(r);
    if (h) ui.cursor = LoadCursorW(nullptr, IDC_HAND);
    float a = ui.anim(id, v ? 1.f : 0.f, 20.f), q = ui.anim(id ^ 3u, h ? 1.f : 0.f);
    RectF b = RectF::xywh(r.l, r.cy() - 10, 20, 20);
    ui.p->rrect(b, 5, mix(mix(ui.pal.control, ui.pal.controlHover, q), ui.pal.accent, a));
    if (a < 0.98f) ui.p->rrectStroke(b.inset(0.5f), 5, ui.pal.faint.alpha(1 - a), 1.2f);
    if (a > 0.02f) ui.glyph(b, L"\xE73E", 12.f, ui.pal.onAccent.alpha(a));
    ui.text(RectF(r.l + 30, r.t - 0.5f, r.r, r.b), label, 13.5f, ui.pal.text);
    return c;
  }

  void paint() override {
    RectF v = ui.view;
    wheel(RectF(v.l, v.t, v.l + 300, v.b));
    RectF r(v.l + 336, v.t + 34, v.r - 34, v.b - 28);
    if (job.state == 1) step_ = 1;
    if (job.state == 2 && step_ == 1) {
      step_ = 2;
      if (job.o.launch) launch(job.o);
    }
    if (job.state == 3) step_ = 3;

    if (step_ == 0) {
      ui.text(RectF(r.l, r.t, r.r, r.t + 38), RT_NAME, 27.f, ui.pal.text, 600);
      std::wstring now = widen(RT_VERSION_STR), sub;
      if (beta) sub = L"Replaces " RT_BETA_NAME L", the test version. Your pins, profiles and skins come along.";
      else if (upgrade && oldVersion == now) sub = L"Version " + now + L" is installed. Installing it again keeps your pins and looks.";
      else if (upgrade) sub = L"Replaces version " + oldVersion + L". Your pins and looks stay.";
      else sub = L"All your pinned apps, one press away.";
      ui.text(RectF(r.l, r.t + 38, r.r, r.t + 60), sub, 13.5f, ui.pal.dim);
      float y = r.t + 82;
      ui.text(RectF(r.l, y, r.r, y + 18), L"Install to", 12.f, ui.pal.dim, 600);
      RectF box(r.l, y + 22, r.r - 92, y + 56);
      ui.textBox(ui.id("dir"), box, job.o.dir);
      if (ui.button(ui.id("browse"), RectF(r.r - 84, box.t, r.r, box.b), L"Change")) {
        after([this] {
          std::wstring d = pickFile(hwnd(), L"Choose a folder", true);
          if (!d.empty()) job.o.dir = toLower(fileName(d)) == toLower(RT_NAME) ? d : joinPath(d, RT_NAME);
        });
      }
      y += 74;
      struct C { const char* id; const wchar_t* t; bool* v; };
      C cs[] = {{"c1", L"Start with Windows", &job.o.autostart}, {"c2", L"Add to the Start menu", &job.o.startMenu}, {"c3", L"Add a desktop shortcut", &job.o.desktop},
                {"c4", L"Add to the right-click menu of files and folders", &job.o.menus}, {"c5", L"Open it when finished", &job.o.launch}};
      for (auto& c : cs) {
        check(ui.id(c.id), RectF(r.l, y, r.r, y + 30), c.t, *c.v);
        y += 33;
      }
      ui.text(RectF(r.l, r.b - 34, r.r - 150, r.b), L"For you only. No administrator needed.", 12.f, ui.pal.faint);
      bool ok = trim(job.o.dir).size() > 3;
      if (ui.button(ui.id("go"), RectF(r.r - 140, r.b - 38, r.r, r.b), upgrade ? L"Update" : L"Install", Btn::Accent, nullptr, ok)) {
        job.o.dir = trim(job.o.dir);
        if (!upgrade) job.o.sendTo = job.o.menus;  // one question the first time, an update keeps what is there
        while (job.o.dir.size() > 3 && (job.o.dir.back() == L'\\' || job.o.dir.back() == L'/')) job.o.dir.pop_back();
        job.state = 1;
        uintptr_t t = _beginthreadex(nullptr, 0, worker, &job, 0, nullptr);
        if (t) CloseHandle((HANDLE)t);
        else job.state = 3;
      }
    } else if (step_ == 1) {
      ui.text(RectF(r.l, r.t + 120, r.r, r.t + 156), L"Installing", 22.f, ui.pal.text, 600);
      shown_ += (g_progress / 100.f - shown_) * (1.f - expf(-10.f * ui.dt));
      RectF bar(r.l, r.t + 172, r.r, r.t + 178);
      ui.p->rrect(bar, 3, ui.pal.text.withA(0.12f));
      ui.p->rrect(RectF(bar.l, bar.t, lerp(bar.l, bar.r, shown_), bar.b), 3, ui.pal.accent);
      ui.animating = true;
    } else if (step_ == 2) {
      float a = ui.anim(ui.id("donein"), 1.f, 7.f);
      V2 c{r.l + 28, r.t + 96};
      ui.p->circle(c, 26 * lerp(0.6f, 1.f, a), Color::hex(0x1FA463).withA(0.16f));
      ui.glyph(RectF(c.x - 26, c.y - 26, c.x + 26, c.y + 26), L"\xE73E", 24, Color::hex(0x1FA463));
      ui.text(RectF(r.l, r.t + 136, r.r, r.t + 172), upgrade ? L"Updated" : L"Ready", 26.f, ui.pal.text, 600);
      ui.text(RectF(r.l, r.t + 174, r.r, r.t + 250), upgrade || beta ? L"Your shortcut opens the wheel as before. Settings > News says what is new, Settings > Help how everything works." : L"Press Win + ` (the key above Tab) to open your wheel. Hold it, flick toward an app and let go. Skins are under Settings > Skins, and Settings > Help explains the rest.", 14.f, ui.pal.dim, 400, Align::Left, VAlign::Top, true);
      if (ui.button(ui.id("close"), RectF(r.r - 140, r.b - 38, r.r, r.b), L"Close", Btn::Accent)) PostMessageW(hwnd(), WM_CLOSE, 0, 0);
    } else {
      ui.glyph(RectF(r.l, r.t + 76, r.l + 44, r.t + 120), L"\xE7BA", 30, ui.pal.danger);
      ui.text(RectF(r.l, r.t + 130, r.r, r.t + 166), L"It did not finish", 22.f, ui.pal.text, 600);
      ui.text(RectF(r.l, r.t + 170, r.r, r.t + 250), g_error, 14.f, ui.pal.dim, 400, Align::Left, VAlign::Top, true);
      if (ui.button(ui.id("again"), RectF(r.r - 140, r.b - 38, r.r, r.b), L"Try again", Btn::Accent)) {
        job.state = 0;
        step_ = 0;
        g_progress = 0;
      }
    }
  }

 private:
  int step_ = 0;
  float time_ = 0, lit_ = 0, shown_ = 0;
};

}  // namespace

int WINAPI wWinMain(HINSTANCE inst, HINSTANCE, PWSTR, int) {
  SetDefaultDllDirectories(LOAD_LIBRARY_SEARCH_SYSTEM32 | LOAD_LIBRARY_SEARCH_USER_DIRS);
  OleInitialize(nullptr);
  int n = 0;
  LPWSTR* av = CommandLineToArgvW(GetCommandLineW(), &n);
  std::vector<std::wstring> args;
  for (int i = 1; av && i < n; i++) args.push_back(av[i]);
  LocalFree(av);
  auto has = [&](const wchar_t* s) { return std::find(args.begin(), args.end(), s) != args.end(); };
  auto val = [&](const wchar_t* s) {
    for (size_t i = 0; i + 1 < args.size(); i++)
      if (args[i] == s) return args[i + 1];
    return std::wstring();
  };

  auto winPtr = std::make_unique<SetupWindow>();
  SetupWindow& win = *winPtr;
  Options& o = win.job.o;
  o.dir = installedDir();
  win.upgrade = !o.dir.empty();
  if (win.upgrade) {
    win.oldVersion = installedVersion();
    wchar_t v[1200];
    DWORD cb = sizeof v;
    o.autostart = RegGetValueW(HKEY_CURRENT_USER, L"Software\\Microsoft\\Windows\\CurrentVersion\\Run", kRunValue, RRF_RT_REG_SZ, nullptr, v, &cb) == ERROR_SUCCESS;
    o.desktop = fileExists(desktopLink());
    o.sendTo = fileExists(sendToLink());
    o.menus = fileMenuOn();
  } else {
    o.dir = defaultInstallDir();
  }
  win.beta = betaThere();
  if (win.beta && !win.upgrade) {  // what the test version had, it keeps
    o.desktop = fileExists(joinPath(knownFolder(FOLDERID_Desktop), RT_BETA_NAME L".lnk"));
  }
  if (!val(L"--dir").empty()) o.dir = val(L"--dir");
  if (has(L"--no-autostart")) o.autostart = false;
  if (has(L"--no-launch")) o.launch = false;
  if (has(L"--no-startmenu")) o.startMenu = false;
  if (has(L"--no-menus")) o.menus = o.sendTo = false;
  if (has(L"--no-sendto")) o.sendTo = false;
  if (has(L"--desktop")) o.desktop = true;

  int rc = 0;
  if (has(L"--silent") || has(L"/S")) {
    rc = install(o) ? 0 : 1;
    if (rc == 0 && o.launch) launch(o);
  } else if (!val(L"--shot").empty()) {  // headless picture of a page, for checks
    if (gfx().ensure()) {
      auto t = gfx().target(760, 480);
      win.preview((int)wcstol(val(L"--step").c_str(), nullptr, 10));
      rc = win.renderTo(t.Get(), 760, 480, 100, has(L"--dark")) && savePng(t.Get(), val(L"--shot")) ? 0 : 1;
    }
  } else if (win.create(inst)) {
    win.show();
    MSG m;
    bool run = true;
    while (run) {
      HANDLE h = win.frameHandle();
      bool want = win.wantsFrame();
      DWORD r = MsgWaitForMultipleObjectsEx(want && h ? 1 : 0, &h, want && !h ? 8 : INFINITE, QS_ALLINPUT, MWMO_INPUTAVAILABLE);
      while (PeekMessageW(&m, nullptr, 0, 0, PM_REMOVE)) {
        if (m.message == WM_QUIT) { run = false; break; }
        TranslateMessage(&m);
        DispatchMessageW(&m);
      }
      if (run && win.wantsFrame() && (r == WAIT_TIMEOUT || (want && h && r == WAIT_OBJECT_0))) win.frame(true);
    }
  }
  winPtr.reset();
  gfx().shutdown();
  OleUninitialize();
  return rc;
}
