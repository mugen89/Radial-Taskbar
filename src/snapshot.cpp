#include "snapshot.h"
#include "backfx.h"
#include "update.h"

#include "app.h"
#include "scene.h"
#include "live.h"
#include "settings.h"
#include "taskrow.h"
#include "zip.h"

namespace rt {

bool Args::has(const wchar_t* n) const {
  for (auto& s : v)
    if (s == n) return true;
  return false;
}
std::wstring Args::get(const wchar_t* n, const wchar_t* def) const {
  for (size_t i = 0; i + 1 < v.size(); i++)
    if (v[i] == n) return v[i + 1];
  return def;
}
int Args::num(const wchar_t* n, int def) const {
  std::wstring s = get(n);
  return s.empty() ? def : (int)wcstol(s.c_str(), nullptr, 10);
}
float Args::real(const wchar_t* n, float def) const {
  std::wstring s = get(n);
  return s.empty() ? def : (float)wcstod(s.c_str(), nullptr);
}
Args parseArgs() {
  Args a;
  int n = 0;
  LPWSTR* p = CommandLineToArgvW(GetCommandLineW(), &n);
  for (int i = 1; p && i < n; i++) a.v.push_back(p[i]);
  LocalFree(p);
  return a;
}

ComPtr<ID2D1Bitmap1> demoWallpaper(int w, int h, bool light) {
  auto& g = gfx();
  auto t = g.target(w, h);
  if (!t) return {};
  ID2D1DeviceContext* dc = g.aux.Get();
  dc->SetTarget(t.Get());
  dc->SetTransform(D2D1::Matrix3x2F::Identity());
  dc->BeginDraw();
  Painter p;
  p.attach(dc);
  float W = (float)w, H = (float)h;
  Color base = light ? Color::hex(0xDCE6F2) : Color::hex(0x101B33);
  dc->Clear(base.f());
  auto blob = [&](float x, float y, float r, Color c) {
    auto b = p.radial({x * W, y * H}, r * W, r * W, {{0, c}, {1, c.withA(0)}});
    dc->FillRectangle(D2D1::RectF(0, 0, W, H), b.Get());
  };
  if (light) {
    blob(0.15f, 0.2f, 0.5f, Color::hex(0xFFB38A, 0.9f));
    blob(0.85f, 0.15f, 0.5f, Color::hex(0x8AC6FF, 0.9f));
    blob(0.7f, 0.9f, 0.55f, Color::hex(0xB59CFF, 0.8f));
    blob(0.2f, 0.95f, 0.45f, Color::hex(0x9BE8C9, 0.8f));
  } else {
    blob(0.15f, 0.2f, 0.5f, Color::hex(0x2456B8, 0.9f));
    blob(0.85f, 0.15f, 0.5f, Color::hex(0x7A2E8F, 0.85f));
    blob(0.72f, 0.9f, 0.55f, Color::hex(0x0E8C8C, 0.8f));
    blob(0.2f, 0.95f, 0.45f, Color::hex(0xB84A2B, 0.65f));
  }
  // a couple of fake windows so blur and refraction have detail to work with
  auto window = [&](float x, float y, float ww, float hh, bool dark) {
    RectF r = RectF::xywh(x * W, y * H, ww * W, hh * H);
    Color bg = dark ? Color::hex(0x1E1F26) : Color::hex(0xFAFAFC);
    p.rrect(r.offset(0, 8), 10, Color(0, 0, 0, 0.25f));
    p.rrect(r, 10, bg);
    p.rrect(RectF(r.l, r.t, r.r, r.t + 34), 10, dark ? Color::hex(0x2A2C36) : Color::hex(0xEDEFF4));
    for (int i = 0; i < 3; i++) p.circle({r.l + 20 + i * 20.f, r.t + 17}, 5, i == 0 ? Color::hex(0xFF5F57) : i == 1 ? Color::hex(0xFEBC2E) : Color::hex(0x28C840));
    uint32_t seed = 12345;
    for (float ly = r.t + 56; ly < r.b - 16; ly += 22) {
      float lx = r.l + 24;
      while (lx < r.r - 60) {
        seed = seed * 1664525u + 1013904223u;
        float len = 18.f + (seed >> 24) * 0.30f;
        Color c = fromHsv({((seed >> 8) & 255) / 255.f, 0.5f, dark ? 0.8f : 0.55f}, 0.75f);
        if ((seed & 3) == 0) c = dark ? Color(1, 1, 1, 0.5f) : Color(0, 0, 0, 0.45f);
        p.rrect(RectF::xywh(lx, ly, std::min(len, r.r - 24 - lx), 8), 4, c);
        lx += len + 12;
      }
    }
  };
  window(0.05f, 0.10f, 0.42f, 0.62f, true);
  window(0.50f, 0.26f, 0.44f, 0.60f, false);
  dc->EndDraw();
  dc->SetTarget(nullptr);
  return t;
}

static Pin sysPin(const wchar_t* name, const wchar_t* path) {
  Pin p;
  p.id = newId();
  p.kind = Pin::Kind::File;
  p.name = name;
  p.target = expandEnv(path);
  return p;
}

// "--pictures a.png;b.png" gives the first items these pictures instead of their icons.
static void demoPictures(const Args& a, std::vector<Pin>& pins) {
  std::wstring list = a.get(L"--pictures");
  size_t at = 0, i = 0;
  while (at < list.size() && i < pins.size()) {
    size_t e = list.find(L';', at);
    if (e == std::wstring::npos) e = list.size();
    pins[i].icon = list.substr(at, e - at);
    pins[i].iconShape = (PicShape)clampi(a.num(L"--picshape", 0), 0, 3);
    if (!pins[i].icon.empty()) i++;
    at = e + 1;
  }
}

static std::vector<Pin> demoPins(int n, bool groups) {
  static const std::pair<const wchar_t*, const wchar_t*> list[] = {
      {L"File Explorer", L"%WINDIR%\\explorer.exe"}, {L"Notepad", L"%WINDIR%\\System32\\notepad.exe"},
      {L"Task Manager", L"%WINDIR%\\System32\\Taskmgr.exe"}, {L"Command Prompt", L"%WINDIR%\\System32\\cmd.exe"},
      {L"PowerShell", L"%WINDIR%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"}, {L"Remote Desktop", L"%WINDIR%\\System32\\mstsc.exe"},
      {L"Character Map", L"%WINDIR%\\System32\\charmap.exe"}, {L"Snipping Tool", L"%WINDIR%\\System32\\SnippingTool.exe"},
      {L"Control Panel", L"%WINDIR%\\System32\\control.exe"}, {L"Magnifier", L"%WINDIR%\\System32\\Magnify.exe"},
      {L"Registry Editor", L"%WINDIR%\\regedit.exe"}, {L"Performance", L"%WINDIR%\\System32\\perfmon.exe"},
      {L"Disk Cleanup", L"%WINDIR%\\System32\\cleanmgr.exe"}, {L"Defragment", L"%WINDIR%\\System32\\dfrgui.exe"},
      {L"DirectX Diagnostics", L"%WINDIR%\\System32\\dxdiag.exe"}, {L"System Information", L"%WINDIR%\\System32\\msinfo32.exe"},
      {L"Management Console", L"%WINDIR%\\System32\\mmc.exe"}, {L"On-Screen Keyboard", L"%WINDIR%\\System32\\osk.exe"},
      {L"Narrator", L"%WINDIR%\\System32\\Narrator.exe"}, {L"Resource Monitor", L"%WINDIR%\\System32\\resmon.exe"},
      {L"Windows", L"%WINDIR%"}, {L"Fonts", L"%WINDIR%\\Fonts"}, {L"ODBC", L"%WINDIR%\\System32\\odbcad32.exe"},
      {L"About Windows", L"%WINDIR%\\System32\\winver.exe"}};
  std::vector<Pin> out;
  int total = (int)(sizeof list / sizeof list[0]);
  for (int i = 0; i < n; i++) out.push_back(sysPin(list[i % total].first, list[i % total].second));
  if (groups && n >= 4) {
    Pin g;
    g.id = newId();
    g.kind = Pin::Kind::Group;
    g.name = L"Tools";
    for (int i = 0; i < 6; i++) g.children.push_back(sysPin(list[(i + 4) % total].first, list[(i + 4) % total].second));
    out[2] = g;
    Pin g2 = g;
    g2.id = newId();
    g2.name = L"Design";
    g2.children.resize(3);
    out[(size_t)n - 2] = g2;
    out[1] = pinFromUrl(L"https://example.com", L"Example site");
  }
  return out;
}

int runSnapshot(const Args& a) {
  std::wstring out = a.get(L"--snapshot");
  if (out.empty() || !gfx().ensure()) return 2;
  Config cfg;
  std::wstring lay = a.get(L"--layout", L"radial");
  for (int i = 0; i < kLayoutCount; i++)
    if (lay == widen(layoutId((LayoutType)i))) cfg.layout = (LayoutType)i;
  if (auto* k = findLook(narrow(a.get(L"--look", L"glass")))) cfg.style = k->style;
  std::wstring shape = a.get(L"--shape");
  const wchar_t* shapes[] = {L"wedge", L"blade", L"orb", L"hex", L"petal", L"none"};
  for (int i = 0; i < 6; i++)
    if (shape == shapes[i]) cfg.style.shape = (SlotShape)i;
  cfg.perRing = a.num(L"--perring", cfg.perRing);
  std::wstring ov = a.get(L"--overflow", L"rings");
  cfg.overflow = ov == L"unfold" ? Overflow::Unfold : ov == L"pages" ? Overflow::Pages : Overflow::Rings;
  cfg.showNumbers = a.has(L"--numbers");
  cfg.arc = a.real(L"--arc", 360.f);
  cfg.arcAt = a.num(L"--arcat", 0);
  if (a.has(L"--labels")) cfg.labels = Labels::Always;
  cfg.scale = a.real(L"--scale", cfg.scale);
  cfg.iconSize = a.real(L"--icon", cfg.iconSize);
  std::wstring edge = a.get(L"--edge");
  if (edge == L"left") { cfg.flowSide = FlowSide::Left; cfg.stripEdge = StripEdge::Left; }
  if (edge == L"right") cfg.stripEdge = StripEdge::Right;
  if (edge == L"top") cfg.stripEdge = StripEdge::Top;
  if (edge == L"center") cfg.stripEdge = StripEdge::Center;

  Profile prof;
  prof.name = L"Work";
  prof.color = cfg.style.accent;
  prof.pins = a.has(L"--taskbar") ? importTaskbarPins() : demoPins(a.num(L"--items", 10), a.has(L"--groups"));
  demoPictures(a, prof.pins);
  cfg.profiles.push_back(prof);
  static const wchar_t* names[] = {L"Work", L"Games", L"Home", L"Design", L"Music", L"Studio", L"Servers", L"Travel", L"Reading", L"Finance", L"Photos", L"Misc"};
  static const uint32_t cols[] = {0x4CA8FF, 0xFF8A4C, 0x35D6A0, 0xC58BFF, 0xFFD24C, 0xFF6B9A, 0x5CE1E6, 0x9BE15D};
  for (int i = 1; i < a.num(L"--profiles", 1); i++) {
    Profile q;
    q.name = names[i % 12];
    q.color = Color::hex(cols[i % 8]);
    q.pins = demoPins(4 + i, false);
    cfg.profiles.push_back(q);
  }

  int W = a.num(L"--w", 900), H = a.num(L"--h", 900);
  auto wall = demoWallpaper(W, H, a.has(L"--light"));
  auto frame = gfx().target(W, H);
  if (!wall || !frame) return 3;

  auto L = makeLayout(cfg.layout);
  if (a.has(L"--skin")) {
    cfg.skin = narrow(a.get(L"--skin"));
    Config::Tune u;
    u.hue = a.real(L"--hue", 0);
    u.sat = a.real(L"--sat", 1);
    u.light = a.real(L"--light-tune", 1);
    cfg.tunes[cfg.skin] = u;
    live().staged = true;
    cfg.profiles[0].color = Color::hex(0x4CA8FF);
  }
  dressLayout(*L, cfg, false);
  if (a.has(L"--skin")) {
    if (!L->skin) {
      logf("skin not found");
      return 5;
    }
    if (a.has(L"--strict") && !L->skin->problems.empty()) return 6;
  }
  L->model = buildModel(cfg, nullptr);
  // a few invented running states
  for (size_t i = 0; i < L->model.items.size(); i++) {
    auto& it = L->model.items[i];
    if (it.isGroup()) continue;
    if (i == 0) { it.windows = 1; it.active = true; it.sub = L"Open"; }
    if (i == 3) { it.windows = 2; it.sub = L"2 windows"; }
    if (i == 5) { it.windows = 1; it.sub = L"Open"; }
  }
  L->env.vw = (float)W;
  L->env.vh = (float)H;
  L->env.s = cfg.scale;
  L->env.anchor = {W * 0.5f, H * 0.5f};
  L->env.work = RectF(0, 0, (float)W, (float)H - (a.has(L"--taskbararea") ? 48.f : 0.f));
  L->env.anchorIsMouse = a.has(L"--mouse");
  if (L->env.anchorIsMouse) L->env.anchor = {a.real(L"--mx", W * 0.3f), a.real(L"--my", H * 0.6f)};
  L->sticky = !a.has(L"--hold");
  for (auto& it : L->model.items) {
    icons().request(it.iconKey);
    for (auto& k : it.kids) icons().request(k.iconKey);
  }
  icons().waitIdle(8000);
  L->build();
  L->beginOpen();

  // artwork arrives on a worker: draw once to find out what is needed, then wait for it
  auto settleArt = [&] {
    if (!L->view) return;
    ID2D1DeviceContext* dc = gfx().dc.Get();
    for (int i = 0; i < 3; i++) {
      dc->SetTarget(frame.Get());
      dc->BeginDraw();
      painter().attach(dc);
      L->draw(painter(), nullptr);
      dc->EndDraw();
      dc->SetTarget(nullptr);
      skinArt().wait(20000);
    }
  };
  float t = a.real(L"--t", 1.4f), dt = 1.f / 60.f;
  float hoverAt = a.real(L"--hoverat", 0.5f);
  int hover = a.num(L"--hover", -1), kid = a.num(L"--kid", -1);
  bool hovered = false, kidded = false;
  for (float now = 0; now < t; now += dt) {
    if (hover >= 0 && !hovered && now >= std::min(hoverAt, t * 0.5f)) {
      L->select(hover);
      if (cfg.layout == LayoutType::Radial || a.has(L"--byptr")) L->pointer(L->spot({hover, -1}));
      hovered = true;
    }
    if (a.has(L"--px")) L->pointer({a.real(L"--px", 0), a.real(L"--py", 0)});
    if (kid >= 0 && hovered && !kidded && now >= hoverAt + 0.5f) {
      L->openKids();
      for (int i = 0; i < 12; i++) L->key(NavKey::Left);
      for (int i = 0; i < kid; i++) L->key(NavKey::Right);
      kidded = true;
    }
    L->tick(dt);
  }
  settleArt();
  if (L->view)
    for (int i = 0; i < 30 && skinArt().pending(); i++) skinArt().tick(dt);
  if (a.has(L"--closing")) {
    L->beginClose(hover >= 0, L->pick());
    for (float now = 0; now < a.real(L"--closing", 0.08f); now += dt) L->tick(dt);
  }

  Backdrop bd;
  RectF area = L->bounds();
  if (wantsBackdrop(L->st)) {
    // Same path as the real overlay: material is built from the picture behind the bounds.
    int bw = (int)ceilf(area.w()), bh = (int)ceilf(area.h());
    auto part = gfx().target(bw, bh);
    ID2D1DeviceContext* ax = gfx().aux.Get();
    ax->SetTarget(part.Get());
    ax->SetTransform(D2D1::Matrix3x2F::Identity());
    ax->BeginDraw();
    D2D1_RECT_F dst = D2D1::RectF(0, 0, (float)bw, (float)bh);
    D2D1_RECT_F src = D2D1::RectF(area.l, area.t, area.l + bw, area.t + bh);
    ax->DrawBitmap(wall.Get(), &dst, 1.f, D2D1_INTERPOLATION_MODE_LINEAR, &src);
    ax->EndDraw();
    ax->SetTarget(nullptr);
    double t0 = nowSec();
    bd = makeBackdrop(part.Get(), area, *L);
    logf("backdrop %.1f ms", (nowSec() - t0) * 1000.0);
  }

  ID2D1DeviceContext* dc = gfx().dc.Get();
  dc->SetTarget(frame.Get());
  dc->SetTransform(D2D1::Matrix3x2F::Identity());
  dc->SetDpi(96, 96);
  if (int n = a.num(L"--bench", 0)) {  // what one frame costs, drawing only
    painter().attach(dc);
    double sum = 0, worst = 0;
    for (int i = -10; i < n; i++) {
      L->tick(0.f);  // a frame always follows a tick
      double b0 = nowSec();
      dc->BeginDraw();
      dc->Clear(D2D1::ColorF(0, 0, 0, 0));
      L->draw(painter(), bd.bmp ? &bd : nullptr);
      dc->EndDraw();
      double ms = (nowSec() - b0) * 1000.0;
      if (i >= 0) {
        sum += ms;
        worst = std::max(worst, ms);
      }
    }
    logf("bench %.2f ms average, %.2f worst", sum / n, worst);
  }
  BackFx fx;
  BackFxSpec spec = L->skin ? L->skin->screen : BackFxSpec{};
  if (a.has(L"--backfx")) {
    spec = {};
    spec.kind = narrow(a.get(L"--backfx"));
    backFxDefaults(spec);
  }
  if (spec.on() && fx.begin(spec, W, H, 1.f, L->env.anchor))
    for (int i = 0; i < 80; i++) fx.step(0.05f);  // a few seconds in, so the screen is full
  dc->BeginDraw();
  dc->DrawBitmap(wall.Get());
  Painter& p = painter();
  p.attach(dc);
  auto dimBr = p.solid(Color(0, 0, 0, L->st.dim * L->fade()));
  dc->FillRectangle(D2D1::RectF(0, 0, (float)W, (float)H), dimBr);
  if (fx.active()) fx.draw(dc, 1.f);
  double t0 = nowSec();
  L->draw(p, bd.bmp ? &bd : nullptr);
  HRESULT hr = dc->EndDraw();
  fx.end();
  logf("draw %.1f ms hr=%08lx", (nowSec() - t0) * 1000.0, hr);
  dc->SetTarget(nullptr);
  return SUCCEEDED(hr) && savePng(frame.Get(), out) ? 0 : 4;
}

int runDiagnose(const Args& a) {
  Config cfg;
  cfg.load();
  WindowList wl;
  wl.snapshot();
  std::string out = "PINS\n";
  for (auto& p : cfg.profile().pins) {
    MatchInfo m = resolveMatch(p);
    out += narrow(p.name) + " | exe=" + narrow(m.exe) + " | id=" + narrow(m.aumid) + " | windows=" + std::to_string(wl.matching(p).size()) + "\n";
  }
  out += "RUNNING\n";
  for (auto& w : wl.wins) out += narrow(w.exe) + " | id=" + narrow(w.aumid) + "\n";
  if (a.has(L"--taskbar")) out += describeTaskButtons(cfg);
  return writeFileAtomic(a.get(L"--diagnose"), out) ? 0 : 1;
}

static void say(const std::string& line);

int runCheckUpdate(const Args& a) {
  if (a.has(L"--as-version")) Updater::current = a.get(L"--as-version");
  Updater u;
  auto wait = [&] {
    for (int i = 0; i < 2400; i++) {
      auto n = u.now();
      if (n.state != Updater::State::Checking && n.state != Updater::State::Downloading) return n;
      Sleep(50);
    }
    return u.now();
  };
  u.check();
  auto n = wait();
  static const char* names[] = {"idle", "checking", "newest already", "available", "downloading", "ready", "failed"};
  say(std::string("check: ") + names[(int)n.state] + ", newest " + narrow(n.version) + ", setup " + std::to_string(n.size) + " bytes" + (n.error.empty() ? "" : ", " + narrow(n.error)));
  if (!n.notes.empty()) say("notes:\n" + narrow(n.notes));
  if (a.has(L"--download") && n.state == Updater::State::Available) {
    u.download();
    n = wait();
    say(std::string("download: ") + names[(int)n.state] + ", " + narrow(n.file) + ", " + std::to_string(n.got) + " bytes" + (n.error.empty() ? "" : ", " + narrow(n.error)));
  }
  return n.state == Updater::State::Failed ? 1 : 0;
}

int runDumpLooks(const Args& a) {
  std::wstring dir = a.get(L"--dump-looks");
  for (auto& k : builtinLooks()) writeFileAtomic(joinPath(dir, L"look_" + widen(k.id) + L".json"), styleText(k.style));
  return 0;
}

static void say(const std::string& line) {
  static bool tried = false;
  if (!tried) {
    tried = true;
    AttachConsole(ATTACH_PARENT_PROCESS);  // a program with windows has no console of its own
  }
  HANDLE h = GetStdHandle(STD_OUTPUT_HANDLE);
  DWORD n = 0;
  std::string t = line + "\r\n";
  if (h && h != INVALID_HANDLE_VALUE) WriteFile(h, t.data(), (DWORD)t.size(), &n, nullptr);
}

int runCheckSkin(const Args& a) {
  std::wstring path = a.get(L"--check-skin");
  std::string err, text;
  auto f = SkinFiles::open(path, &err);
  if (!f) {
    say("cannot open it: " + err);
    return 2;
  }
  if (!f->read("skin.json", text, SkinFiles::kJsonMost)) {
    say("there is no skin.json in it");
    return 2;
  }
  Skin t;
  if (!parseSkin(text, t, &err)) {
    say(err);
    return 3;
  }
  auto have = f->list();
  auto there = [&](const std::string& n) {
    for (auto& h : have)
      if (CompareStringOrdinal(widen(h).c_str(), -1, widen(n).c_str(), -1, TRUE) == CSTR_EQUAL) return true;
    return false;
  };
  std::vector<std::string> bad = t.problems, used{"skin.json", "preview.jpg", "preview.png", "readme.txt", "license.txt", "ofl.txt"};
  auto need = [&](const std::string& n) {
    if (n.empty()) return;
    used.push_back(n);
    if (!there(n)) bad.push_back("the file \"" + n + "\" is missing");
  };
  for (auto& im : t.images) {
    need(im.file);
    need(im.mask);
  }
  for (auto& q : t.fonts) need(q.file);
  for (auto& q : t.sounds) need(q.second);
  size_t total = 0;
  for (auto& n : have) {
    std::string b;
    if (f->read(n, b)) total += b.size();
    bool known = false;
    for (auto& u : used) known |= CompareStringOrdinal(widen(u).c_str(), -1, widen(n).c_str(), -1, TRUE) == CSTR_EQUAL;
    if (!known) say("not used: " + n);
  }
  for (auto& b : bad) say("problem: " + b);
  say(narrow(t.name) + ": " + std::to_string(t.images.size()) + " images, " + std::to_string(have.size()) + " files, " + std::to_string(total / 1024) + " KB, " +
      (bad.empty() ? "no problems" : std::to_string(bad.size()) + " problems"));
  return bad.empty() ? 0 : 4;
}

int runFuzzSkin(const Args& a) {
  std::string id = narrow(a.get(L"--fuzz-skin"));
  int rounds = a.num(id.empty() ? L"" : widen(id).c_str(), 200);
  const SkinInfo* info = skins().info(id);
  std::string base, err;
  auto f = info ? SkinFiles::open(info->path, &err) : nullptr;
  if (!f || !f->read("skin.json", base) || !gfx().ensure()) return 2;
  live().staged = true;
  uint32_t seed = (uint32_t)a.num(L"--seed", 4711);
  auto rnd = [&] {
    seed ^= seed << 13;
    seed ^= seed >> 17;
    seed ^= seed << 5;
    return seed;
  };
  auto frame = gfx().target(600, 600);
  Config cfg;
  Profile prof;
  prof.pins = demoPins(9, true);
  cfg.profiles.push_back(prof);
  cfg.profiles.push_back(prof);
  for (auto& p : prof.pins) icons().request(IconCache::keyFor(p));
  icons().waitIdle(6000);
  static const char* const odd[] = {"1e30", "-1e30", "0", "-1", "99999", "0.00001", "\"1/0\"", "\"time*1e9\"", "\"hot\"", "\"noise(time)\"", "\"pow(9,99)\"", "true", "null", "[]", "\"\"", "[1,2]", "\"sel-9999\"", "-0.5", "1000000"};
  int drawn = 0, refused = 0;
  double worst = 0;
  for (int r = 0; r < rounds; r++) {
    std::string s = base;
    for (int k = (int)(rnd() % 12) + 1; k-- > 0;) {
      // replace one number or one quoted formula by something odd
      size_t at = rnd() % s.size();
      while (at < s.size() && !(s[at] >= '0' && s[at] <= '9')) at++;
      if (at >= s.size()) continue;
      size_t from = at, to = at;
      while (from > 0 && strchr("0123456789.-", s[from - 1])) from--;
      while (to < s.size() && strchr("0123456789.-", s[to])) to++;
      s.replace(from, to - from, odd[rnd() % (sizeof odd / sizeof *odd)]);
    }
    auto t = std::make_shared<Skin>();
    t->path = info->path;
    t->stamp = 1;
    t->id = "fuzz";
    if (!parseSkin(s, *t, &err)) {
      refused++;
      continue;
    }
    cfg.layout = (LayoutType)(rnd() % kLayoutCount);
    if (rnd() % 3) cfg.layout = LayoutType::Radial;
    auto L = makeLayout(cfg.layout);
    L->cfg = cfg;
    L->st = t->style;
    L->skin = t;
    skinArt().use(t, {}, false);
    L->view = std::make_unique<SkinView>(*L, t);
    if (t->wheel.hub > 0) L->cfg.hubRadius = t->wheel.hub;
    if (t->wheel.thickness > 0) L->cfg.ringThickness = t->wheel.thickness;
    L->model = buildModel(cfg, nullptr);
    L->env.vw = L->env.vh = 600;
    L->env.s = 1;
    L->env.anchor = {300, 300};
    L->env.work = RectF(0, 0, 600, 600);
    L->build();
    L->beginOpen();
    double t0 = nowSec();
    for (int k = 0; k < 14; k++) {
      L->pointer({(float)(rnd() % 600), (float)(rnd() % 600)});
      if (k == 6) L->key(NavKey::Right);
      if (k == 8) L->openKids();
      if (k == 11) L->beginClose(true, L->pick());
      L->tick(k == 4 ? 0.5f : 0.016f);
      gfx().dc->SetTarget(frame.Get());
      gfx().dc->BeginDraw();
      gfx().dc->Clear(D2D1::ColorF(0, 0, 0, 0));
      painter().attach(gfx().dc.Get());
      L->draw(painter(), nullptr);
      HRESULT hr = gfx().dc->EndDraw();
      gfx().dc->SetTarget(nullptr);
      if (FAILED(hr)) {
        say("round " + std::to_string(r) + ": drawing failed");
        writeFileAtomic(L"fuzz-failed.json", s);
        return 5;
      }
      if (k == 1) skinArt().wait(3000);
    }
    double ms = (nowSec() - t0) * 1000 / 14;
    if (ms > worst) {
      worst = ms;
      if (ms > 120) writeFileAtomic(L"fuzz-slow.json", s);
    }
    drawn++;
  }
  say(id + ": " + std::to_string(drawn) + " drawn, " + std::to_string(refused) + " refused, slowest frame on average " + std::to_string((int)worst) + " ms");
  return 0;
}

int runPackSkin(const Args& a) {
  std::wstring dir, file;
  for (size_t i = 0; i + 2 < a.v.size(); i++)
    if (a.v[i] == L"--pack-skin") {
      dir = a.v[i + 1];
      file = a.v[i + 2];
    }
  std::string err;
  auto f = dir.empty() ? nullptr : SkinFiles::open(dir, &err);
  if (!f) {
    say("usage: --pack-skin <folder> <file.rskin>");
    return 2;
  }
  auto names = f->list();
  std::sort(names.begin(), names.end());
  std::vector<std::pair<std::string, std::string>> all;
  for (auto& n : names) {
    std::string b;
    if (f->read(n, b)) all.push_back({n, std::move(b)});
  }
  std::string zip = makeZip(all);
  if (!writeFileAtomic(file, zip)) {
    say("the file could not be written");
    return 3;
  }
  say(narrow(fileName(file)) + ": " + std::to_string(all.size()) + " files, " + std::to_string(zip.size() / 1024) + " KB");
  return 0;
}

int runSettingsShot(const Args& a) {
  std::wstring out = a.get(L"--settings-shot");
  if (out.empty() || !gfx().ensure()) return 2;
  Preview::demoOnly = true;
  App app;
  if (auto* k = findLook(narrow(a.get(L"--look", L"glass")))) app.cfg.style = k->style;
  std::wstring lay = a.get(L"--layout", L"radial");
  for (int i = 0; i < kLayoutCount; i++)
    if (lay == widen(layoutId((LayoutType)i))) app.cfg.layout = (LayoutType)i;
  app.cfg.skin = narrow(a.get(L"--skin"));
  app.cfg.helpLang = narrow(a.get(L"--lang"));
  live().staged = true;
  Profile p;
  p.name = L"Work";
  p.id = "w";
  p.pins = demoPins(a.num(L"--items", 11), true);
  if (a.has(L"--picture"))
    for (auto& x : p.pins)
      if (x.kind == Pin::Kind::Url) {
        x.icon = a.get(L"--picture");
        x.iconShape = (PicShape)clampi(a.num(L"--picshape", 0), 0, 3);
        x.name = L"YouTube";
        x.target = L"https://www.youtube.com";
      }
  app.cfg.profiles.push_back(p);
  Profile q;
  q.name = L"Home";
  q.id = "h";
  q.color = Color::hex(0xFF8A4C);
  app.cfg.profiles.push_back(q);
  // more profiles, a locked one, one with a skin of its own: for pictures of the profile pages
  static const wchar_t* more[] = {L"Free Form", L"Projects", L"Design work", L"Games", L"Study", L"Travel", L"Music", L"Photos", L"Writing", L"Tools"};
  for (int i = 2; i < clampi(a.num(L"--profiles", 2), 2, 12); i++) {
    Profile r;
    r.name = more[i - 2];
    r.id = "p" + std::to_string(i);
    r.color = Color::hex(0x35D6A0 + 0x101010u * (uint32_t)i);
    r.pins = demoPins(3 + i, false);
    app.cfg.profiles.push_back(r);
  }
  if (int l = a.num(L"--lock", -1); l >= 0 && l < (int)app.cfg.profiles.size()) app.cfg.profiles[(size_t)l].locked = true;
  if (a.has(L"--own-skin") && app.cfg.profiles.size() > 1) app.cfg.profiles[1].skin = narrow(a.get(L"--own-skin"));
  for (auto& pin : app.cfg.profile().pins) {
    icons().request(IconCache::keyFor(pin));
    for (auto& c : pin.children) icons().request(IconCache::keyFor(c));
  }
  float w = a.real(L"--w", 1180), h = a.real(L"--h", 740), s = a.real(L"--dpi", 1.f);
  auto t = gfx().target((int)(w * s), (int)(h * s));
  SettingsWindow win(app);
  win.setPage(a.num(L"--page", 0));
  if (a.has(L"--select-pin")) win.selectFirstPin(false);
  if (a.has(L"--select-group")) win.selectFirstPin(true);
  if (a.has(L"--select-url")) win.selectUrl();
  if (a.has(L"--url-form")) win.openUrlForm(a.get(L"--url-form"), a.get(L"--picture"));
  if (a.has(L"--apps")) win.loadAppsNow();
  if (a.has(L"--scroll")) win.scrollPage(a.real(L"--scroll", 0));
  bool ok = win.renderTo(t.Get(), w, h, 3, a.has(L"--dark"));
  icons().waitIdle(6000);
  skinArt().wait(8000);
  if (a.has(L"--bench")) {  // how long a frame takes, page by page
    for (int pg = 0; pg < SettingsWindow::kPageCount; pg++)
      for (int change = -1; change < 2; change++) {
        win.setPage(pg);
        win.renderTo(t.Get(), w, h, 30, a.has(L"--dark"));
        skinArt().wait(8000);
        win.renderTo(t.Get(), w, h, 30, a.has(L"--dark"));
        UiWindow::Times q;
        q.pageToo = change >= 0;
        for (int i = 0; i < 60; i++) {
          if (change > 0) win.touch();
          win.renderTo(t.Get(), w, h, 1, a.has(L"--dark"), &q);
        }
        char line[160];
        snprintf(line, sizeof line, "page %d %-9s record %6.2f  submit %6.2f  gpu %6.2f  worst %6.2f ms", pg, change > 0 ? "changing" : change < 0 ? "idle" : "mouse", q.record * 1000 / q.n, q.submit * 1000 / q.n, q.gpu * 1000 / q.n, q.worst * 1000);
        say(line);
      }
    return 0;
  }
  ok = win.renderTo(t.Get(), w, h, a.num(L"--frames", 90), a.has(L"--dark"));
  return ok && savePng(t.Get(), out) ? 0 : 4;
}

}  // namespace rt
