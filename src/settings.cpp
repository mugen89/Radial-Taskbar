#include "settings.h"
#include "backfx.h"

#include <commdlg.h>

#include "app.h"
#include "snapshot.h"

namespace rt {

// ================================================================ preview
bool Preview::demoOnly = false;

// The wallpaper is read in the background and kept; resizing the window only scales it.
void Preview::wallpaper(int w, int h, bool again) {
  constexpr uint64_t kKey = 1;
  auto& g = gfx();
  if (again || (!wall_ && !wallFull_)) wallPath_ = demoOnly || !loader ? std::wstring() : wallpaperPath();
  const std::wstring& path = wallPath_;
  if (path.empty()) {
    if (again || !wall_) wall_ = demoWallpaper(w, h, systemUsesLightTheme());
    return;
  }
  PictureLoader::Picture p;
  if (loader->take(kKey, p)) {
    wallFull_ = p.w ? g.bitmap(p.px.data(), p.w, p.h, p.w * 4, true) : demoWallpaper(w, h, systemUsesLightTheme());
    again = true;
    rev_ = -1;
  }
  if (!wallFull_ || w > wallW_ * 1.3f || h > wallH_ * 1.3f) {
    if (!loader->waiting(kKey)) {
      wallW_ = w + w / 8;
      wallH_ = h + h / 8;
      loader->ask(kKey, [path](std::string& b) { return readFile(path, b); }, wallW_, wallH_, true);
    }
  }
  if (!again && wall_) return;
  wall_ = g.target(w, h);
  if (!wall_) return;
  g.aux->SetTarget(wall_.Get());
  g.aux->SetTransform(D2D1::Matrix3x2F::Identity());
  g.aux->BeginDraw();
  g.aux->Clear(D2D1::ColorF(0.16f, 0.18f, 0.24f, 1));
  if (wallFull_) {
    D2D1_SIZE_F z = wallFull_->GetSize();
    float k = std::max(w / z.width, h / z.height);
    D2D1_RECT_F d = D2D1::RectF((w - z.width * k) * 0.5f, (h - z.height * k) * 0.5f, (w + z.width * k) * 0.5f, (h + z.height * k) * 0.5f);
    g.aux->DrawBitmap(wallFull_.Get(), &d, 1.f, D2D1_INTERPOLATION_MODE_HIGH_QUALITY_CUBIC, nullptr, nullptr);
  }
  g.aux->EndDraw();
  g.aux->SetTarget(nullptr);
}

void Preview::drop() {
  layout_.reset();
  bd_ = {};
  wall_.Reset();
  wallFull_.Reset();
  scene_.Reset();
  rev_ = -1;
}

void Preview::rebuild(const Config& cfg, int sampleCount, bool settle) {
  Config c = cfg;
  if (c.profile().pins.size() > 80) c.profile().pins.resize(80);
  if (sampleCount > 0) {
    std::vector<Pin> base;
    for (auto& p : c.profile().pins)
      if (p.kind != Pin::Kind::Group) base.push_back(p);
    if (base.size() < 4) {
      for (auto path : {L"%WINDIR%\\explorer.exe", L"%WINDIR%\\System32\\notepad.exe", L"%WINDIR%\\System32\\Taskmgr.exe", L"%WINDIR%\\regedit.exe"}) {
        Pin p;
        p.kind = Pin::Kind::File;
        p.target = expandEnv(path);
        p.name = fileStem(p.target);
        base.push_back(p);
      }
    }
    std::vector<Pin> out;
    for (int i = 0; i < sampleCount; i++) out.push_back(base[(size_t)i % base.size()]);
    c.profile().pins = out;
  }
  LayoutType lt = c.layoutNow();  // the profile in use may have an arrangement of its own
  layout_ = makeLayout(lt);
  dressLayout(*layout_, c, false);
  layout_->model = buildModel(c, nullptr);
  if (!layout_->model.items.empty()) {  // show what running marks look like
    auto& a = layout_->model.items[0];
    if (!a.isGroup()) { a.windows = 1; a.active = true; a.sub = L"Open"; }
    if (layout_->model.items.size() > 2 && !layout_->model.items[2].isGroup()) layout_->model.items[2].windows = 2;
  }
  auto& e = layout_->env;
  e.vw = (float)w_;
  e.vh = (float)h_;
  float fit = lt == LayoutType::Radial ? 0.92f : lt == LayoutType::Flow ? 0.72f : lt == LayoutType::Strip ? 0.60f : lt == LayoutType::Corner ? 0.8f : 0.72f;
  e.s = scale_ * c.scale * fit;
  e.work = RectF(0, 0, e.vw, e.vh);
  e.anchor = {e.vw * 0.5f, e.vh * 0.5f};
  e.anchorIsMouse = false;
  e.preview = true;
  layout_->sticky = false;
  layout_->build();
  layout_->beginOpen();
  if (settle)
    for (int i = 0; i < 40; i++) layout_->tick(1.f / 30.f);
  bd_ = {};
  if (wantsBackdrop(layout_->st) && wall_) {
    RectF area(0, 0, e.vw, e.vh);
    bd_ = makeBackdrop(wall_.Get(), area, *layout_);
  }
  if (demoItem_ >= (int)layout_->model.items.size()) demoItem_ = 0;
  if (settle && !hovering_ && !layout_->model.items.empty()) {
    layout_->select(demoItem_);
    for (int i = 0; i < 10; i++) layout_->tick(1.f / 30.f);
  }
}

bool Preview::draw(Ui& ui, RectF r, float scale, const Config& cfg, int revision, int sampleCount) {
  auto& g = gfx();
  int w = std::max(8, (int)lroundf(r.w() * scale)), h = std::max(8, (int)lroundf(r.h() * scale));
  scale_ = scale;
  bool fresh = !layout_ || gen_ != g.generation || w != w_ || h != h_;
  if (gen_ != g.generation) {
    wall_.Reset();
    wallFull_.Reset();
    scene_.Reset();
  }
  wallpaper(w, h, w != w_ || h != h_ || gen_ != g.generation);
  if (fresh) {
    w_ = w;
    h_ = h;
    gen_ = g.generation;
  }
  if (fresh || revision != rev_ || sampleCount != samples_ || replay_) {
    rebuild(cfg, sampleCount, !replay_);
    rev_ = revision;
    samples_ = sampleCount;
    if (replay_) demo_ = -0.9f;
    replay_ = false;
  }

  bool over = ui.hot(r);
  if (over) {
    hovering_ = true;
    V2 q{(ui.mouse.x - r.l) * scale, (ui.mouse.y - r.t) * scale};
    layout_->pointer(q);
    if (ui.wheel != 0) {
      layout_->wheel(ui.wheel);
      ui.wheel = 0;
    }
  } else {
    if (hovering_) layout_->clearHover();
    hovering_ = false;
    demo_ += ui.dt;
    if (demo_ > 1.25f && !layout_->model.items.empty()) {
      demo_ = 0;
      demoItem_ = (demoItem_ + 1) % (int)layout_->model.items.size();
      layout_->select(demoItem_);
    }
  }
  layout_->tick(ui.dt);

  // The scene works in pixels and has a picture of its own: rounding its corners is cheaper that way than with a layer.
  ID2D1DeviceContext* dc = ui.p->dc;
  if (!scene_ || fresh) scene_ = g.target(w, h);
  if (!scene_) return false;
  FLOAT dx, dy;
  dc->GetDpi(&dx, &dy);
  D2D1_MATRIX_3X2_F old;
  dc->GetTransform(&old);
  ComPtr<ID2D1Image> target;
  dc->GetTarget(&target);
  dc->SetTarget(scene_.Get());
  dc->SetDpi(96, 96);
  dc->SetTransform(D2D1::Matrix3x2F::Identity());
  if (wall_) {
    dc->SetPrimitiveBlend(D2D1_PRIMITIVE_BLEND_COPY);
    dc->DrawBitmap(wall_.Get(), nullptr, 1.f, D2D1_INTERPOLATION_MODE_NEAREST_NEIGHBOR, nullptr, nullptr);
    dc->SetPrimitiveBlend(D2D1_PRIMITIVE_BLEND_SOURCE_OVER);
  } else {
    dc->Clear(D2D1::ColorF(0, 0, 0, 1));
  }
  dc->FillRectangle(D2D1::RectF(0, 0, (float)w, (float)h), ui.p->solid(Color(0, 0, 0, layout_->st.dim * layout_->fade())));
  layout_->draw(*ui.p, bd_.bmp ? &bd_ : nullptr);
  dc->SetTarget(target.Get());
  dc->SetDpi(dx, dy);
  dc->SetTransform(old);
  if (auto br = ui.p->image(scene_.Get(), {r.l, r.t}, 1.f / scale)) ui.p->rrect(r, 12.f, br.Get());
  ui.p->rrectStroke(r.inset(0.5f), 12.f, ui.pal.strokeStrong, 1);
  return !ui.hwnd || GetForegroundWindow() == ui.hwnd;
}

// ================================================================ window
constexpr UINT kPicturesMsg = WM_APP + 72;

SettingsWindow::SettingsWindow(App& app) : app_(app) { preview_.loader = &loader_; }

void SettingsWindow::dropDevice() {
  preview_.drop();
  thumbs_.clear();
  skinPics_.clear();
  UiWindow::dropDevice();
}

void SettingsWindow::show(int page) {
  if (page >= 0) page_ = page;
  if (!hwnd_) {
    if (!createWindow(app_.instance(), settingsWindowClass().c_str(), RT_NAME, 1180, 780, 960, 640, true)) return;
    loader_.notify(hwnd_, kPicturesMsg);
    updater_.notify(hwnd_, kPicturesMsg);  // both only ask for a new frame
  }
  autostartAt_ = -10;
  ideasOk_ = false;
  if (IsIconic(hwnd_)) ShowWindow(hwnd_, SW_RESTORE);
  invalidate();
  frame();
  ShowWindow(hwnd_, SW_SHOW);
  SetForegroundWindow(hwnd_);
}

bool SettingsWindow::onClose() {
  stopRecording();
  naming_ = -1;
  addingUrl_ = namingLook_ = false;
  dropDraft();
  selected_.clear();
  ui.closePopup();
  preview_.drop();
  app_.settingsClosed();
  return true;
}

void SettingsWindow::changed(bool pins) {
  rev_++;
  app_.saveSoon();
  if (pins) app_.pinsChanged();
  invalidate();
}

// ---------------------------------------------------------------- frame layout
void SettingsWindow::paint() {
  RectF v = ui.view;
  sidebar(RectF(v.l, v.t, v.l + kSide, v.b));
  RectF body(v.l + kSide, v.t, v.r, v.b);
  previewOn_ = false;
  static const wchar_t* titles[] = {L"Pins", L"Layout", L"Skins", L"Look", L"Effects", L"Shortcut", L"General", L"News", L"Help", L"About", L"Profiles"};
  static const wchar_t* subs[] = {
      L"Everything on your wheel. Drag to reorder, drop files or links anywhere on this window to add them.",
      L"Choose how your pins are arranged and where they appear.",
      L"A skin replaces the whole look: artwork, motion, lettering and sounds.",
      L"Start from a style, then change anything you like.",
      L"Motion, light and feedback.",
      L"One hand, one press.",
      L"Behaviour, startup and your data.",
      L"Updates, and what changed in each version.",
      L"How to use " RT_NAME L", from the first press to your own skins.",
      L"Who makes it, and how to reach us.",
      L"A skin and an arrangement for every profile, and how you move between them."};
  bool bg = page_ == kHelp && app_.cfg.helpLang == "bg";
  header(RectF(body.l + 28, body.t + 18, body.r - 28, body.t + 82), bg ? L"\x041F\x043E\x043C\x043E\x0449" : titles[page_],
         bg ? L"\x041A\x0430\x043A \x0441\x0435 \x0438\x0437\x043F\x043E\x043B\x0437\x0432\x0430 " RT_NAME L": \x043E\x0442 \x043F\x044A\x0440\x0432\x043E\x0442\x043E \x043D\x0430\x0442\x0438\x0441\x043A\x0430\x043D\x0435 \x0434\x043E \x0441\x043E\x0431\x0441\x0442\x0432\x0435\x043D\x0438\x0442\x0435 \x0432\x0438 \x0441\x043A\x0438\x043D\x043E\x0432\x0435." : subs[page_]);
  RectF area(body.l + 28, body.t + 92, body.r - 20, body.b - 16);
  bool withPreview = page_ == kLayout || page_ == kSkins || page_ == kLook || page_ == kEffects;
  if (withPreview) {
    float pw = clampf(area.w() * 0.46f, 330.f, 560.f);
    RectF pr(area.r - 8 - pw, area.t, area.r - 8, area.b);
    previewPanel(pr);
    area.r = pr.l - 16;
  }
  if (page_ == kPins) {
    pagePins(area);
  } else {
    float off = ui.beginScroll(ui.id("page", page_), area, contentH_[page_]);
    c_ = {area.l, area.t + off, area.w() - 14};
    float start = c_.y;
    switch (page_) {
      case kLayout: pageLayout(area); break;
      case kSkins: pageSkins(area); break;
      case kLook: pageLook(area); break;
      case kEffects: pageEffects(area); break;
      case kShortcut: pageShortcut(area); break;
      case kGeneral: pageGeneral(area); break;
      case kNews: pageNews(area); break;
      case kHelp: pageHelp(area); break;
      case kAbout: pageAbout(area); break;
      case kProfiles: pageProfiles(area); break;
    }
    float hh = c_.y - start + 24;
    if (fabsf(hh - contentH_[page_]) > 0.5f) ui.animating = true;
    contentH_[page_] = hh;
    ui.endScroll();
  }
}

void SettingsWindow::paintLive() {
  if (previewOn_) {
    if (auto now = skins().get(app_.cfg.skinNow()); now != skinSeen_) {
      skinSeen_ = now;
      rev_++;
    }
    if (preview_.draw(ui, previewBox_, scale_, app_.cfg, rev_, sample_)) liveBusy_ = true;
  }
  // short confirmation line
  double age = nowSec() - flashAt_;
  if (age < 2.4) {
    liveBusy_ = true;
    RectF body(ui.view.l + kSide, ui.view.t, ui.view.r, ui.view.b);
    float a = (float)(std::min(1.0, age * 8.0) * saturate((float)(2.4 - age) * 4.f));
    float w = ui.textWidth(flash_, 13.5f, 600) + 36;
    RectF r = RectF::xywh(body.cx() - w * 0.5f, body.b - 64 + (1 - a) * 10, w, 36);
    ui.p->rrect(r.offset(0, 3), 18, Color(0, 0, 0, 0.18f * a));
    ui.p->rrect(r, 18, (ui.pal.dark ? Color::hex(0x3A3C45) : Color::hex(0x24262C)).withA(a));
    ui.text(r, flash_, 13.5f, Color(1, 1, 1, a), 600, Align::Center);
  }
}

void SettingsWindow::drawFailed() {
  if (!previewOn_ || app_.cfg.skinNow().empty()) return;
  skins().distrust(app_.cfg.skinNow());
  say(L"This skin cannot be drawn");
  rev_++;
}

// Little pictures that take long to draw are drawn once and kept.
void SettingsWindow::thumb(uint32_t key, RectF r, float margin, const std::function<void()>& draw) {
  auto& g = gfx();
  if (thumbsGen_ != g.generation || thumbsDark_ != ui.pal.dark || thumbsScale_ != scale_) {
    thumbs_.clear();
    thumbsGen_ = g.generation;
    thumbsDark_ = ui.pal.dark;
    thumbsScale_ = scale_;
  }
  RectF all = r.inset(-margin);
  int w = (int)ceilf(all.w() * scale_), h = (int)ceilf(all.h() * scale_);
  uint32_t slot = ui.id("thumb", (int)(key ^ (uint32_t)(w * 4099 + h * 17)));
  ComPtr<ID2D1Bitmap1> t;
  if (auto it = thumbs_.find(slot); it != thumbs_.end()) t = it->second;
  if (!t && w > 0 && h > 0 && w < 4096 && h < 4096 && (t = g.target(w, h)) != nullptr) {
    if (thumbs_.size() > 240) thumbs_.clear();  // sizes nobody uses any more
    thumbs_[slot] = t;
    ID2D1DeviceContext* was = ui.p->dc;
    g.aux->SetTarget(t.Get());
    g.aux->SetDpi(96.f * scale_, 96.f * scale_);
    g.aux->BeginDraw();
    g.aux->SetTransform(D2D1::Matrix3x2F::Translation(-all.l, -all.t));
    g.aux->Clear(D2D1::ColorF(0, 0, 0, 0));
    ui.p->attach(g.aux.Get());
    draw();
    ui.p->attach(was);
    g.aux->EndDraw();
    g.aux->SetTransform(D2D1::Matrix3x2F::Identity());
    g.aux->SetDpi(96, 96);
    g.aux->SetTarget(nullptr);
  }
  ID2D1Bitmap1* b = t.Get();
  if (!b) {
    draw();
    return;
  }
  float x = roundf(all.l * scale_) / scale_, y = roundf(all.t * scale_) / scale_;
  D2D1_RECT_F d = D2D1::RectF(x, y, x + w / scale_, y + h / scale_);
  ui.p->dc->DrawBitmap(b, &d, 1.f, D2D1_INTERPOLATION_MODE_NEAREST_NEIGHBOR, nullptr, nullptr);
}

void SettingsWindow::sidebar(RectF r) {
  ui.p->dc->FillRectangle(r.f(), ui.p->solid(ui.pal.panel));
  ui.p->dc->FillRectangle(D2D1::RectF(r.r - 1, r.t, r.r, r.b), ui.p->solid(ui.pal.stroke));
  // wordmark: a tiny wheel with one lit slot
  V2 c{r.l + 38, r.t + 44};
  thumb(ui.id("mark"), RectF::xywh(c.x - 20, c.y - 20, 40, 40), 2, [&] {
    for (int i = 0; i < 8; i++) {
      float a = i * kTau / 8;
      bool lit = i == 1;
      auto g = wedgeGeo(c, 7.f, lit ? 18.5f : 17.f, a - kTau / 16, a + kTau / 16, 2.4f, 1.8f);
      if (lit) {
        auto br = ui.p->linear({c.x, c.y - 18}, {c.x + 18, c.y}, {{0, Color::hex(0x2DD4FF)}, {1, Color::hex(0x805CFF)}});
        ui.p->fill(g.Get(), br.Get());
      } else {
        ui.p->fill(g.Get(), ui.pal.text.withA(0.30f));
      }
    }
  });
  ui.text(RectF(r.l + 66, r.t + 26, r.r, r.t + 46), L"Radial", 16.f, ui.pal.text, 600);
  ui.text(RectF(r.l + 66, r.t + 44, r.r, r.t + 62), L"Taskbar", 13.f, ui.pal.dim, 400);

  struct N { int page; const wchar_t* icon; const wchar_t* label; };
  static const N nav[] = {{kPins, L"\xE718", L"Pins"},         {kProfiles, L"\xE77B", L"Profiles"}, {kLayout, L"\xE8A9", L"Layout"},
                          {kSkins, L"\xE771", L"Skins"},       {kLook, L"\xE790", L"Look"},         {kEffects, L"\xE945", L"Effects"},
                          {kShortcut, L"\xE765", L"Shortcut"}, {kGeneral, L"\xE713", L"General"},   {kNews, L"\xE789", L"News"},
                          {kHelp, L"\xE9CE", L"Help"},         {kAbout, L"\xE946", L"About"}};
  const int count = (int)(sizeof nav / sizeof nav[0]), apart = 8;  // News, Help and About sit a little apart
  float top = r.t + 92, step = clampf((r.b - 104 - top - 12) / count, 30.f, 42.f), ih = step - 4;
  auto yOf = [&](int i) { return top + i * step + (i >= apart ? 12.f : 0.f); };
  int at = 0;
  for (int i = 0; i < count; i++)
    if (nav[i].page == page_) at = i;
  float pos = ui.anim(ui.id("navy"), yOf(at), 20.f);
  ui.p->rrect(RectF::xywh(r.l + 12, pos, r.w() - 25, ih), 7, ui.pal.dark ? Color(1, 1, 1, 0.075f) : Color(0, 0, 0, 0.050f));
  ui.p->rrect(RectF::xywh(r.l + 12, pos + ih * 0.5f - 9, 3, 18), 1.5f, ui.pal.accent);
  ui.divider(RectF(r.l + 24, yOf(apart) - 9, r.r - 25, yOf(apart) - 8));
  bool news = updater_.now().state == Updater::State::Available;
  for (int i = 0; i < count; i++) {
    RectF n = RectF::xywh(r.l + 12, yOf(i), r.w() - 25, ih);
    int pg = nav[i].page;
    uint32_t id = ui.id("nav", pg);
    if (ui.press(id, n) && page_ != pg) {
      page_ = pg;
      stopRecording();
      ui.clearFocus();
      if (pg == kShortcut) ideasOk_ = false;
    }
    bool h = ui.hot(n);
    if (h) ui.cursor = LoadCursorW(nullptr, IDC_HAND);
    float a = ui.anim(id, h && pg != page_ ? 1.f : 0.f);
    ui.p->rrect(n, 7, (ui.pal.dark ? Color(1, 1, 1, 0.05f) : Color(0, 0, 0, 0.03f)).alpha(a));
    ui.glyph(RectF::xywh(n.l + 10, n.t, 24, n.h()), nav[i].icon, 16.f, pg == page_ ? ui.pal.accent : ui.pal.dim);
    ui.text(RectF(n.l + 44, n.t - 0.5f, n.r, n.b), nav[i].label, 14.f, pg == page_ ? ui.pal.text : ui.pal.dim, pg == page_ ? 600 : 400);
    if (pg == kNews && news) ui.p->circle({n.l + 44 + ui.textWidth(L"News", 14.f, pg == page_ ? 600 : 400) + 9, n.cy() - 1}, 4, ui.pal.accent);
  }
  // open button with the current shortcut
  RectF b(r.l + 14, r.b - 92, r.r - 15, r.b - 54);
  if (ui.button(ui.id("openwheel"), b, L"Open it now", Btn::Accent, L"\xE768")) app_.openWheel();
  float kw = keycapsWidth(app_.cfg.hotkey, 20.f);
  drawKeycaps(r.l + (r.w() - kw) * 0.5f, r.b - 30, app_.cfg.hotkey, 20.f, app_.hotkeyOk() ? 0.9f : 0.4f);
}

void SettingsWindow::header(RectF r, const wchar_t* title, const wchar_t* sub) {
  ui.text(RectF(r.l, r.t, r.r, r.t + 38), title, 27.f, ui.pal.text, 600);
  ui.text(RectF(r.l, r.t + 38, r.r, r.t + 60), sub, 13.5f, ui.pal.dim);
}

void SettingsWindow::previewPanel(RectF r) {
  RectF box(r.l, r.t, r.r, r.b - 48);
  previewOn_ = true;
  previewBox_ = box;
  RectF bar(r.l, r.b - 38, r.r, r.b - 4);
  std::vector<std::wstring> opts = {L"My pins", L"12", L"24", L"36"};
  int idx = sample_ == 0 ? 0 : sample_ == 12 ? 1 : sample_ == 24 ? 2 : 3;
  float sw = std::min(230.f, bar.w() - 130);
  if (ui.segmented(ui.id("sample"), RectF(bar.l, bar.t, bar.l + sw, bar.b), idx, opts)) sample_ = idx == 0 ? 0 : idx * 12;
  ui.tooltip(RectF(bar.l, bar.t, bar.l + sw, bar.b), L"Fill the preview with sample items to see how rings and rows behave");
  if (ui.button(ui.id("replay"), RectF(bar.r - 112, bar.t, bar.r, bar.b), L"Replay", Btn::Standard, L"\xE72C")) preview_.replay();
}

// ---------------------------------------------------------------- rows
void SettingsWindow::section(const wchar_t* title, const wchar_t* note) {
  c_.y += 14;
  ui.text(RectF::xywh(c_.x + 2, c_.y, c_.w, 22), title, 14.f, ui.pal.text, 600);
  c_.y += 26;
  if (note) {
    ui.text(RectF::xywh(c_.x + 2, c_.y - 3, c_.w, 18), note, 12.5f, ui.pal.dim);
    c_.y += 20;
  }
}

RectF SettingsWindow::row(const wchar_t* title, const wchar_t* desc, float ctlW, float h) {
  if (h <= 0) h = desc ? 60.f : 48.f;
  RectF r = RectF::xywh(c_.x, c_.y, c_.w, h);
  c_.y += h + 4;
  ui.card(r, 8);
  float tr = r.r - 14 - ctlW - (ctlW > 0 ? 12 : 0);
  if (desc) {
    ui.text(RectF(r.l + 16, r.t + 9, tr, r.t + 31), title, 13.5f, ui.pal.text, 400);
    ui.text(RectF(r.l + 16, r.t + 30, tr, r.b - 6), desc, 12.f, ui.pal.dim, 400, Align::Left, VAlign::Top);
  } else {
    ui.text(RectF(r.l + 16, r.t - 0.5f, tr, r.b), title, 13.5f, ui.pal.text, 400);
  }
  return RectF(r.r - 14 - ctlW, r.cy() - 16, r.r - 14, r.cy() + 16);
}

bool SettingsWindow::sliderRow(const char* key, const wchar_t* title, float& v, float lo, float hi, float step, const wchar_t* fmt, float show, const wchar_t* desc) {
  float w = clampf(c_.w * 0.56f, 190.f, 340.f);
  RectF r = row(title, desc, w);
  bool ch = ui.slider(ui.id(key), r, v, lo, hi, step, fmt, show);
  if (ch) changed();
  return ch;
}

bool SettingsWindow::toggleRow(const char* key, const wchar_t* title, const wchar_t* desc, bool& v) {
  RectF r = row(title, desc, 48);
  bool ch = ui.toggle(ui.id(key), r, v);
  if (ch) changed();
  return ch;
}

// ---------------------------------------------------------------- layout page
void SettingsWindow::layoutThumb(RectF r, int kind, bool on, float hv) {
  Color fg = ui.pal.text.withA(on ? 0.50f : 0.34f), ac = ui.pal.accent;
  V2 c = r.center();
  if (kind == 0) {
    float R = std::min(r.w(), r.h()) * 0.5f - 2;
    for (int i = 0; i < 8; i++) {
      float a = i * kTau / 8;
      bool lit = i == 1 && (on || hv > 0.1f);
      auto g = wedgeGeo(c, R * 0.44f, lit ? R * lerp(0.97f, 1.07f, hv) : R * 0.93f, a - kTau / 16, a + kTau / 16, 3.f, 3.f);
      ui.p->fill(g.Get(), lit ? ac : fg);
    }
    ui.p->circle(c, R * 0.32f, fg.alpha(0.7f));
  } else if (kind == 1) {
    std::vector<V2> rim;
    for (int i = 0; i <= 40; i++) {
      float t = i / 40.f, dy = (t - 0.5f) * r.h();
      float q = dy / (r.h() * 0.24f);
      float w = (16.f + 10.f * sinf(t * kPi) + 12.f * expf(-q * q)) * smooth01(std::min(t, 1 - t) * 5.f);
      rim.push_back({r.r - w, c.y + dy});
    }
    rim.push_back({r.r, r.b});
    rim.push_back({r.r, r.t});
    auto g = polyGeo(rim, true, false);
    ui.p->fill(g.Get(), fg.alpha(0.40f));
    for (int i = -2; i <= 2; i++) {
      float k = 1.f - abs(i) * 0.30f, rr = 3.6f + 5.4f * k * k;
      bool lit = i == 0 && (on || hv > 0.1f);
      ui.p->circle({r.r - 12.f - 10.f * k, c.y + i * r.h() * 0.18f}, rr, lit ? ac : fg);
    }
    ui.p->rrect(RectF::xywh(r.r - 92, c.y - 5, 40, 10), 5, fg.alpha(0.6f));
  } else if (kind == 2) {
    RectF b = RectF::xywh(r.l + 4, r.b - 30, r.w() - 8, 24);
    ui.p->rrect(b, 9, fg.alpha(0.40f));
    for (int i = 0; i < 6; i++) {
      float d = fabsf(i - 2.f), k = expf(-d * d / 1.6f);
      float h = 11.f + 13.f * k;
      float x = b.l + 17 + i * (b.w() - 34) / 5.f;
      bool lit = i == 2 && (on || hv > 0.1f);
      ui.p->rrect(RectF::xywh(x - h * 0.5f, b.b - 6 - h, h, h), h * 0.28f, lit ? ac : fg);
    }
  } else {
    auto tile = [&](V2 q, float h, bool lit, float a = 1.f) {
      ui.p->rrect(RectF::xywh(q.x - h, q.y - h, h * 2, h * 2), h * 0.36f, (lit ? ac : fg).alpha(a));
    };
    bool live = on || hv > 0.1f;
    float R = std::min(r.w(), r.h()) * 0.5f - 2;
    switch ((LayoutType)kind) {
      case LayoutType::Orbit:
        for (int k = 1; k <= 2; k++) ui.p->dc->DrawEllipse(D2D1::Ellipse(c.p(), R * (0.62f + 0.48f * k), R * (0.36f + 0.30f * k)), ui.p->solid(fg.alpha(0.45f)), 1.2f);
        ui.p->circle(c, R * 0.30f, live ? ac : fg);
        for (int i = 0; i < 4; i++) { float a = 0.5f + i * kTau / 4; ui.p->circle({c.x + sinf(a) * R * 1.10f, c.y - cosf(a) * R * 0.66f}, 5.5f - cosf(a) * 2.f, fg); }
        for (int i = 0; i < 6; i++) { float a = 0.2f + i * kTau / 6; ui.p->circle({c.x + sinf(a) * R * 1.58f, c.y - cosf(a) * R * 0.96f}, 5.f - cosf(a) * 2.f, fg); }
        break;
      case LayoutType::Comb:
        for (int y = -1; y <= 1; y++)
          for (int x = -2; x <= 2; x++) {
            if (y && x == 2) continue;
            V2 q{c.x + (x + (y ? 0.5f : 0.f)) * 24.f, c.y + y * 21.f};
            bool lit = !x && !y && live;
            auto g = hexGeo(q, lit ? 14.5f : 11.f, 0, 2);
            ui.p->fill(g.Get(), lit ? ac : fg);
          }
        break;
      case LayoutType::Carousel:
        for (int i : {4, -4, 3, -3, 2, -2, 1, -1, 0}) { float a = i * 0.56f, d = 0.5f + 0.5f * cosf(a); tile({c.x + sinf(a) * r.w() * 0.42f, c.y + (d - 0.5f) * R * 1.0f}, lerp(3.5f, 13.f, d), !i && live, lerp(0.35f, 1.f, d)); }
        break;
      case LayoutType::Globe:
        ui.p->circleStroke(c, R * 0.98f, fg.alpha(0.5f), 1.2f);
        ui.p->dc->DrawEllipse(D2D1::Ellipse(c.p(), R * 0.45f, R * 0.98f), ui.p->solid(fg.alpha(0.3f)), 1.f);
        ui.p->dc->DrawEllipse(D2D1::Ellipse(c.p(), R * 0.98f, R * 0.32f), ui.p->solid(fg.alpha(0.3f)), 1.f);
        for (int i = 0; i < 11; i++) { float y = 1 - 2 * (i + 0.5f) / 11, a = i * 2.4f, q = sqrtf(1 - y * y), z = cosf(a) * q; tile({c.x + sinf(a) * q * R * 0.95f, c.y - y * R * 0.95f}, lerp(2.5f, 8.5f, 0.5f + 0.5f * z), i == 5 && live, lerp(0.3f, 1.f, 0.5f + 0.5f * z)); }
        break;
      case LayoutType::Cards:
        for (int k = 0; k < 5; k++) {
          int i = k < 2 ? k : k < 4 ? k + 1 : 2;  // the middle one last
          float a = (i - 2) * 0.185f;
          V2 o{c.x, c.y + 134}, q = polar(o, a, 130 + (i == 2 && live ? 9.f : 0.f));
          D2D1_MATRIX_3X2_F m;
          ui.p->dc->GetTransform(&m);
          ui.p->dc->SetTransform(D2D1::Matrix3x2F::Rotation(a * 180 / kPi, q.p()) * *D2D1::Matrix3x2F::ReinterpretBaseType(&m));
          RectF k2 = RectF::xywh(q.x - 14, q.y - 21, 28, 42);
          ui.p->rrect(k2, 5, ui.pal.card);
          ui.p->rrect(k2, 5, i == 2 && live ? ac : fg.alpha(0.75f));
          ui.p->rrectStroke(k2, 5, ui.pal.card, 1.4f);
          ui.p->dc->SetTransform(m);
        }
        break;
      case LayoutType::Corner: {
        V2 o{r.l + 8, r.b - 2};
        auto g = wedgeGeo(o, 1, r.h() - 4, 0, kPi / 2, 0, 0);
        ui.p->fill(g.Get(), fg.alpha(0.35f));
        for (int k = 0; k < 2; k++)
          for (int i = 0; i < 2 + k; i++) ui.p->circle(polar(o, kPi / 2 * (i + 0.5f) / (2 + k), 34.f + 27.f * k), 8.f, k == 1 && i == 1 && live ? ac : fg);
        break;
      }
      case LayoutType::Galaxy:
        for (int i = 0; i < 17; i++) { float a = i * 2.4f, q = R * 0.285f * sqrtf(i + 0.3f); ui.p->circle(polar(c, a, q), lerp(7.f, 3.6f, i / 16.f), i == 0 && live ? ac : fg); }
        break;
      case LayoutType::Board: {
        RectF b = RectF::xywh(c.x - 50, r.t + 4, 100, r.h() - 8);
        ui.p->rrect(b, 8, fg.alpha(0.32f));
        for (int y = 0; y < 3; y++)
          for (int x = 0; x < 4; x++) tile({b.l + 17 + x * 22.f, b.t + 15 + y * 21.f}, 7.f, x == 1 && y == 1 && live);
        break;
      }
      case LayoutType::Drum: {
        RectF b = RectF::xywh(c.x - 48, r.t + 1, 96, r.h() - 2);
        ui.p->rrect(b, 8, fg.alpha(0.28f));
        for (int i = -2; i <= 2; i++) {
          float k = cosf(i * 0.58f), y = c.y + sinf(i * 0.58f) * 39.f;
          tile({b.l + 16, y}, 7.5f * k, !i && live, 0.4f + 0.6f * k);
          ui.p->rrect(RectF::xywh(b.l + 30, y - 3.5f * k, 52 - abs(i) * 8.f, 7.f * k), 3.f, (!i && live ? ac : fg).alpha(0.4f + 0.6f * k));
        }
        break;
      }
      default: break;
    }
  }
}

namespace {
struct Arrangement { const wchar_t* name; const wchar_t* desc; };
const Arrangement kArrangements[kLayoutCount] = {{L"Radial wheel", L"Weapon-wheel style"}, {L"Side flow", L"Wave on an edge"}, {L"Line strip", L"A magnifying bar"},
                                                 {L"Orbit", L"Planets round a sun"}, {L"Honeycomb", L"Cells under a lens"}, {L"Carousel", L"A ring in depth"},
                                                 {L"Globe", L"A ball that rolls"}, {L"Hand of cards", L"Fanned from below"}, {L"Corner fan", L"A quarter wheel"},
                                                 {L"Galaxy", L"A turning spiral"}, {L"Board", L"A grid with names"}, {L"Drum", L"A list on a roller"}};
}  // namespace

const wchar_t* layoutTitle(LayoutType t) { return kArrangements[clampi((int)t, 0, kLayoutCount - 1)].name; }

void SettingsWindow::pageLayout(RectF) {
  Config& k = app_.cfg;
  LayoutType lay = k.layoutNow();  // the profile in use may have an arrangement of its own
  const auto& opts = kArrangements;
  section(L"Arrangement");
  if (k.profiles.size() > 1) {  // what a click on a tile changes, as on the Skins page
    Profile& p = k.profile();
    bool own = p.layout >= 0;
    std::wstring d = own ? L"A tile you click is for \x201C" + p.name + L"\x201D only" : L"For every profile that uses it";
    RectF b = row(own ? L"Its own arrangement" : L"The main arrangement", d.c_str(), own ? 236 : 150);
    if (own) {
      if (ui.button(ui.id("laymain"), RectF(b.l, b.t, b.l + 110, b.b), L"Use main")) {
        p.layout = -1;
        changed();
      }
      if (ui.button(ui.id("laytoprof"), RectF(b.l + 118, b.t, b.r, b.b), L"Profiles")) page_ = kProfiles;
    } else if (ui.button(ui.id("laytoprof"), b, L"Per profile", Btn::Standard, L"\xE77B")) {
      page_ = kProfiles;
    }
    c_.y += 8;
  }
  float gap = 8, h = 148;
  int cols = c_.w > 620 ? 4 : 3;
  float w = (c_.w - gap * (cols - 1)) / cols, top = c_.y;
  for (int i = 0; i < kLayoutCount; i++) {
    RectF r = RectF::xywh(c_.x + (i % cols) * (w + gap), top + (i / cols) * (h + gap), w, h);
    uint32_t id = ui.id("layout", i);
    bool on = (int)lay == i;
    if (ui.press(id, r) && !on) {
      k.chooseLayout((LayoutType)i);
      changed();
    }
    bool hv = ui.hot(r);
    if (hv) ui.cursor = LoadCursorW(nullptr, IDC_HAND);
    float a = ui.anim(id, hv ? 1.f : 0.f), s = ui.anim(id ^ 5u, on ? 1.f : 0.f);
    ui.p->rrect(r, 10, mix(ui.pal.card, ui.pal.cardHover, a));
    ui.p->rrectStroke(r.inset(0.5f), 10, ui.pal.stroke, 1);
    if (s > 0.01f) ui.p->rrectStroke(r.inset(1.f), 9.5f, ui.pal.accent.alpha(s), 2.f);
    {
      RectF q(r.l + 14, r.t + 12, r.r - 14, r.t + 92);
      if (a > 0.f && a < 1.f) layoutThumb(q, i, on, a);
      else thumb(ui.id("layoutpic", i * 4 + on * 2 + (a > 0.5f)), q, 6, [&] { layoutThumb(q, i, on, a); });
    }
    // radio dot
    V2 o{r.l + 20, r.b - 34};
    ui.p->circle(o, 8, mix(ui.pal.control, ui.pal.accent, s));
    if (s < 0.98f) ui.p->circleStroke(o, 7.5f, ui.pal.faint.alpha(1 - s), 1.2f);
    ui.p->circle(o, 3.8f * s, ui.pal.onAccent.alpha(s));
    ui.text(RectF(r.l + 34, r.b - 46, r.r - 6, r.b - 24), opts[i].name, 13.5f, ui.pal.text, 600);
    ui.text(RectF(r.l + 34, r.b - 26, r.r - 6, r.b - 8), opts[i].desc, 11.5f, ui.pal.dim);
  }
  c_.y = top + ((kLayoutCount + cols - 1) / cols) * (h + gap) - 4;

  section(L"Where it opens");
  {
    RectF r = RectF::xywh(c_.x, c_.y, c_.w, 48);
    c_.y += 52;
    ui.card(r, 8);
    bool edge = lay == LayoutType::Flow || lay == LayoutType::Corner, place = lay == LayoutType::Strip || lay == LayoutType::Cards;
    const wchar_t* a = lay == LayoutType::Flow ? L"On its edge" : lay == LayoutType::Corner ? L"In its corner" : place ? L"In its place" : L"Centre of the screen";
    const wchar_t* b = lay == LayoutType::Flow ? L"Edge nearest the mouse" : edge ? L"Corner nearest the mouse" : L"At the mouse pointer";
    float half = (r.w() - 20) / 2;
    if (ui.radio(ui.id("anc", 0), RectF(r.l + 8, r.t + 6, r.l + 8 + half, r.b - 6), a, k.anchor == Anchor::Center) && k.anchor != Anchor::Center) {
      k.anchor = Anchor::Center;
      changed();
    }
    if (ui.radio(ui.id("anc", 1), RectF(r.l + 12 + half, r.t + 6, r.r - 8, r.b - 6), b, k.anchor == Anchor::Mouse) && k.anchor != Anchor::Mouse) {
      k.anchor = Anchor::Mouse;
      changed();
    }
  }
  if (k.anchor == Anchor::Center) segRow("mon", L"Screen", nullptr, k.monitor, {L"With the mouse", L"Main screen"}, 250);

  if (lay == LayoutType::Radial) {
    section(L"Rings", L"Set how many items fit in one ring and what happens after that.");
    float per = (float)k.perRing;
    if (sliderRow("per", L"Items per ring", per, 3, 20, 1, L"%.0f")) k.perRing = (int)lroundf(per);
    struct O { const wchar_t* t; const wchar_t* d; };
    static const O ov[] = {{L"Add an outer ring", L"Everything is visible at once"},
                           {L"Unfold when I reach out", L"The outer ring extends as the pointer moves outward"},
                           {L"Turn pages", L"Scroll the mouse wheel to rotate to the next set"}};
    RectF r = RectF::xywh(c_.x, c_.y, c_.w, 30 + 3 * 50.f);
    c_.y += r.h() + 4;
    ui.card(r, 8);
    ui.text(RectF(r.l + 16, r.t + 6, r.r, r.t + 28), L"When a ring is full", 13.5f, ui.pal.text);
    for (int i = 0; i < 3; i++) {
      if (ui.radio(ui.id("ovf", i), RectF(r.l + 12, r.t + 28 + i * 50.f, r.r - 12, r.t + 76 + i * 50.f), ov[i].t, (int)k.overflow == i, ov[i].d) && (int)k.overflow != i) {
        k.overflow = (Overflow)i;
        changed();
      }
    }
    {
      int part = k.arc > 350 ? 0 : k.arc > 250 ? 1 : k.arc > 170 ? 2 : 3, was = part;
      RectF q = row(L"Part of a circle", nullptr, clampf(c_.w * 0.58f, 230.f, 330.f));
      if (ui.segmented(ui.id("arc"), q, part, {L"Full", L"Three quarters", L"Half", L"Third"}) && part != was) {
        static const float arcs[] = {360, 270, 180, 120};
        k.arc = arcs[part];
        changed();
      }
      if (part) {
        RectF f = row(L"Facing", nullptr, 250);
        if (ui.segmented(ui.id("arcat"), f, k.arcAt, {L"Up", L"Right", L"Down", L"Left"})) changed();
      }
    }
    section(L"Size");
    sliderRow("scale", L"Overall size", k.scale, 0.6f, 2.2f, 0.05f, L"%.0f%%", 100.f);
    sliderRow("icon", L"Icon size", k.iconSize, 24, 96, 2, L"%.0f px");
    sliderRow("hubr", L"Centre size", k.hubRadius, 50, 180, 2, L"%.0f px");
    sliderRow("ringt", L"Ring thickness", k.ringThickness, 48, 140, 2, L"%.0f px");
    section(L"Details");
    segRow("hub", L"Centre shows", nullptr, k.hub, {L"Clock", L"Profile", L"Nothing"}, 240);
    toggleRow("hubp", L"Profiles around the centre", L"Click one to switch, or turn the mouse wheel", k.hubProfiles);
  } else if (lay == LayoutType::Flow) {
    section(L"Flow");
    if (k.anchor == Anchor::Center) segRow("side", L"Side", nullptr, k.flowSide, {L"Right", L"Left"}, 200);
    sliderRow("curve", L"Curve", k.flowCurve, 0, 1, 0.05f, L"%.0f%%", 100.f);
    sliderRow("mag", L"Magnify under the pointer", k.flowMagnify, 1, 2.4f, 0.05f, L"%.0f%%", 100.f);
    sliderRow("fsp", L"Spacing", k.flowSpacing, 4, 60, 1, L"%.0f px");
    section(L"Size");
    sliderRow("scale", L"Overall size", k.scale, 0.6f, 2.2f, 0.05f, L"%.0f%%", 100.f);
    sliderRow("icon", L"Icon size", k.iconSize, 24, 96, 2, L"%.0f px");
    section(L"Details");
  } else if (lay != LayoutType::Strip) {
    LayoutType t = lay;
    section(opts[(int)t].name);
    if (t == LayoutType::Corner && k.anchor == Anchor::Center) {
      RectF f = row(L"Corner", nullptr, clampf(c_.w * 0.62f, 250.f, 350.f));
      if (ui.segmented(ui.id("cornerat"), f, k.cornerAt, {L"Lower left", L"Lower right", L"Upper left", L"Upper right"})) changed();
    }
    if (t == LayoutType::Board) {
      float col = (float)k.columns;
      if (sliderRow("cols", L"Columns", col, 0, 14, 1, L"%.0f", 1.f, L"0 finds a good number")) k.columns = (int)lroundf(col);
    }
    sliderRow("spread", L"Spacing", k.spread, 0.7f, 1.6f, 0.05f, L"%.0f%%", 100.f);
    sliderRow("lens", L"Grow under the pointer", k.lens, 1, 2.2f, 0.05f, L"%.0f%%", 100.f);
    if (t == LayoutType::Orbit || t == LayoutType::Galaxy || t == LayoutType::Globe || t == LayoutType::Carousel)
      sliderRow("drift", L"Movement", k.drift, 0, 1, 0.05f, L"%.0f%%", 100.f, L"How fast it turns by itself");
    section(L"Size");
    sliderRow("scale", L"Overall size", k.scale, 0.6f, 2.2f, 0.05f, L"%.0f%%", 100.f);
    sliderRow("icon", L"Icon size", k.iconSize, 24, 96, 2, L"%.0f px");
    section(L"Details");
    if (t == LayoutType::Orbit || t == LayoutType::Corner) segRow("hub", t == LayoutType::Orbit ? L"The sun shows" : L"The corner shows", nullptr, k.hub, {L"Clock", L"Profile", L"Nothing"}, 240);
  } else {
    section(L"Strip");
    if (k.anchor == Anchor::Center) segRow("edge", L"Place", nullptr, k.stripEdge, {L"Bottom", L"Top", L"Left", L"Right", L"Middle"}, 330);
    sliderRow("smag", L"Magnify under the pointer", k.stripMagnify, 1, 2.4f, 0.05f, L"%.0f%%", 100.f);
    sliderRow("ssp", L"Spacing", k.stripSpacing, 2, 60, 1, L"%.0f px");
    section(L"Size");
    sliderRow("scale", L"Overall size", k.scale, 0.6f, 2.2f, 0.05f, L"%.0f%%", 100.f);
    sliderRow("icon", L"Icon size", k.iconSize, 24, 96, 2, L"%.0f px");
    section(L"Details");
  }
  segRow("labels", L"Names", nullptr, k.labels, {L"On focus", L"Always"}, 200);
  toggleRow("nums", L"Number badges", L"Press 1 to 9 to launch directly", k.showNumbers);
}

// ---------------------------------------------------------------- skins page
ID2D1Bitmap1* SettingsWindow::skinPreview(const SkinInfo& k, float width) {
  auto& g = gfx();
  if (skinPicsGen_ != g.generation) {
    skinPics_.clear();
    skinPicsGen_ = g.generation;
  }
  int want = width * scale_ <= 330 ? 320 : width * scale_ <= 500 ? 480 : 640;
  auto& pic = skinPics_[k.path];
  if (k.preview.empty()) return nullptr;
  auto read = [path = k.path, entry = k.preview](std::string& b) {
    auto f = SkinFiles::open(path);
    return f && f->read(entry, b);
  };
  PictureLoader::Picture p;
  uint64_t key = 1469598103934665603ull;
  for (wchar_t c : k.path) key = (key ^ c) * 1099511628211ull;
  if (headless_) {
    std::string bytes;
    if (!pic.tried && read(bytes) && PictureLoader::decode(bytes, want, want, false, p) && p.w) pic.bmp = g.bitmap(p.px.data(), p.w, p.h, p.w * 4, true);
    pic.tried = true;
  } else if (loader_.take(key, p)) {
    if (p.w) {
      pic.bmp = g.bitmap(p.px.data(), p.w, p.h, p.w * 4, true);
      if (!pic.shownAt) pic.shownAt = nowSec();
    }
  } else if (pic.asked < want && !loader_.waiting(key)) {
    pic.asked = want;
    loader_.ask(key, read, want, want, false);
  }
  return pic.bmp.Get();
}

void SettingsWindow::chooseSkin(const std::string& id) {
  if (app_.cfg.skinNow() == id) return;
  app_.cfg.chooseSkin(id);
  changed();
  preview_.replay();
}

void SettingsWindow::skinCard(RectF r, const SkinInfo* k) {
  Config& cfg = app_.cfg;
  std::string key = k ? k->id : std::string();
  uint32_t id = ui.id(key + "#skin");
  bool on = cfg.skinNow() == key, broken = k && !k->error.empty();
  RectF del(r.r - 30, r.t + 8, r.r - 8, r.t + 30);
  bool mine = k && !k->builtin, overDel = k && ui.hot(del);
  if (!overDel && ui.press(id, r) && !broken) chooseSkin(key);
  bool hv = ui.hot(r);
  if (hv) {
    if (!broken) ui.cursor = LoadCursorW(nullptr, IDC_HAND);
    if (k) ui.tooltip(r, broken ? widen(k->error) : k->about);
  }
  float a = ui.anim(id, hv ? 1.f : 0.f), s = ui.anim(id ^ 9u, on ? 1.f : 0.f);
  ui.p->rrect(r, 10, mix(ui.pal.card, ui.pal.cardHover, a));
  ui.p->rrectStroke(r.inset(0.5f), 10, ui.pal.stroke, 1);
  RectF pic(r.l + 6, r.t + 6, r.r - 6, r.b - 46);
  ID2D1Bitmap1* b = k ? skinPreview(*k, pic.w()) : nullptr;
  float in = 1;
  if (b && !headless_) {  // pictures that arrive later fade in
    in = saturate((float)(nowSec() - skinPics_[k->path].shownAt) * 5.f);
    if (in < 1) ui.animating = true;
  }
  if (k && (!b || in < 1)) {
    auto bg = ui.p->linear({pic.l, pic.t}, {pic.r, pic.b}, {{0, Color::hex(0x3A4660)}, {1, Color::hex(0x22283A)}});
    ui.p->rrect(pic, 7, bg.Get());
    if (broken || k->preview.empty()) ui.glyph(pic, broken ? L"\xE783" : L"\xE771", 30.f, Color(1, 1, 1, 0.6f));
  }
  if (b) {
    D2D1_SIZE_F z = b->GetSize();
    float q = std::max(pic.w() / z.width, pic.h() / z.height) * lerp(1.f, 1.04f, a);
    auto br = ui.p->image(b, {pic.cx() - z.width * q * 0.5f, pic.cy() - z.height * q * 0.5f}, q, in);
    ui.p->rrect(pic, 7, br.Get());
  } else if (!k) {
    if (a > 0.f && a < 1.f) drawLookThumb(pic, cfg.style, a);
    else thumb(ui.id("noskinpic", rev_ * 2 + (a > 0.5f)), pic, 2, [&] { drawLookThumb(pic, cfg.style, a); });
  }
  if (s > 0.01f) ui.p->rrectStroke(r.inset(1.f), 9.5f, ui.pal.accent.alpha(s), 2.f);
  std::wstring name = k ? k->name : L"No skin", sub = k ? (broken ? L"Cannot be used" : !k->tags.empty() ? std::wstring() : k->author) : L"Your style from the Look page";
  if (k && !broken)
    for (size_t i = 0; i < k->tags.size() && i < 3; i++) sub += (i ? L" \x00B7 " : L"") + k->tags[i];
  ui.text(RectF(r.l + 10, r.b - 43, r.r - 8, r.b - 22), name, 13.f, broken ? ui.pal.dim : ui.pal.text, on ? 600 : 500);
  ui.text(RectF(r.l + 10, r.b - 24, r.r - 8, r.b - 6), sub, 11.f, ui.pal.dim);
  if (mine) {
    ui.p->rrect(RectF(pic.l + 6, pic.t + 6, pic.l + 52, pic.t + 24), 9, Color(0, 0, 0, 0.55f));
    ui.text(RectF(pic.l + 6, pic.t + 6, pic.l + 52, pic.t + 24), L"Yours", 11.f, Color(1, 1, 1, 0.95f), 600, Align::Center);
  }
  if (k && (hv || overDel)) {
    ui.p->rrect(del, 6, Color(0, 0, 0, 0.5f));
    if (ui.iconButton(id ^ 77u, del, L"\xE74D", mine ? L"Delete this skin (it goes to the recycle bin)" : L"Remove it from the list. It can be brought back below", true, 12.f)) {
      std::string gone = k->id;
      if (mine) after([this, gone] { removeSkin(gone); });
      else after([this, gone] { hideSkin(gone); });
    }
  }
}

void SettingsWindow::pageSkins(RectF) {
  Config& k = app_.cfg;
  // somebody may have copied a file into the folder
  if (nowSec() - skinListAt_ > 1.5 && !headless_) {
    skinListAt_ = nowSec();
    if (skins().refreshIfChanged()) skinPics_.clear();
  }
  std::vector<SkinInfo> list = skins().list();  // a copy: removing one must not move what we iterate
  // one among many: every word has to occur in its name, its tags or what it says about itself
  std::vector<const SkinInfo*> shown;
  std::wstring want = toLower(trim(skinSearch_));
  int hiddenCount = 0;
  for (auto& q : list) {
    if (k.hidden(q.id)) {
      hiddenCount++;
      continue;
    }
    std::wstring hay = toLower(q.name + L" " + q.about + L" " + q.author);
    for (auto& t : q.tags) hay += L" " + toLower(t);
    bool fits = true;
    for (size_t i = 0; i < want.size() && fits;) {
      size_t e = std::min(want.find(L' ', i), want.size());
      if (e > i) fits = hay.find(want.substr(i, e - i)) != std::wstring::npos;
      i = e + 1;
    }
    if (fits) shown.push_back(&q);
  }
  {
    float bw = 126, iw = 136;
    RectF r = RectF::xywh(c_.x, c_.y + 8, c_.w, 36);
    c_.y += 44;
    RectF imp(r.r - iw, r.t, r.r, r.b);
    if (ui.button(ui.id("skinimport"), imp, L"Import skin", Btn::Accent, L"\xE710")) after([this] { pickSkinFiles(); });
    ui.tooltip(imp, L"Add .rskin files. Double-clicking one, or dropping it on this window, works too");
    r.r = imp.l - 8;
    if (list.size() > 10) ui.textBox(ui.id("skinsearch"), RectF(r.l, r.t, r.r - bw - 8, r.b), skinSearch_, L"Find by name or mood", L"\xE721");
    if (list.size() > 10 && ui.button(ui.id("skinluck"), RectF(r.r - bw, r.t, r.r, r.b), L"Surprise me", Btn::Standard, L"\xE8B1")) {
      std::vector<std::string> other;
      for (auto* q : shown)
        if (q->error.empty() && q->id != k.skinNow()) other.push_back(q->id);
      if (!other.empty()) chooseSkin(other[(size_t)((uint64_t)(nowSec() * 997.0) % other.size())]);
    }
  }
  if (k.profiles.size() > 1) {  // what a click on a card changes
    Profile& p = k.profile();
    bool own = !p.skin.empty();
    std::wstring d = own ? L"A card you click is for \x201C" + p.name + L"\x201D only" : L"For every profile that uses it";
    RectF b = row(own ? L"Its own skin" : L"The main skin", d.c_str(), own ? 236 : 150);
    if (own) {
      if (ui.button(ui.id("usemain"), RectF(b.l, b.t, b.l + 110, b.b), L"Use main")) {
        p.skin.clear();
        changed();
        preview_.replay();
      }
      if (ui.button(ui.id("toprofiles"), RectF(b.l + 118, b.t, b.r, b.b), L"Profiles")) page_ = kProfiles;
    } else if (ui.button(ui.id("toprofiles"), b, L"Per profile", Btn::Standard, L"\xE77B")) {
      page_ = kProfiles;
    }
  }
  bool plain = want.empty();  // the card for no skin
  size_t cards = shown.size() + plain;
  int cols = std::max(2, (int)floorf((c_.w + 10) / 190.f));
  float w = (c_.w - 10.f * (cols - 1)) / cols, h = (w - 12) * 0.75f + 52;
  c_.y += 8;
  float top = c_.y;
  for (size_t i = 0; i < cards; i++) {
    RectF r = RectF::xywh(c_.x + (float)(i % (size_t)cols) * (w + 10), top + (float)(i / (size_t)cols) * (h + 10), w, h);
    if (r.b < -200 || r.t > ui.view.b + 200) continue;
    skinCard(r, plain ? (i ? shown[i - 1] : nullptr) : shown[i]);
  }
  c_.y = top + (float)((cards + (size_t)cols - 1) / (size_t)cols) * (h + 10);
  if (!cards) {
    ui.text(RectF::xywh(c_.x + 2, c_.y, c_.w, 40), L"No skin fits that", 13.5f, ui.pal.dim);
    c_.y += 44;
  }

  {
    RectF r = RectF::xywh(c_.x, c_.y, c_.w, 52);
    c_.y += 56;
    ui.card(r, 8);
    float bw = 118;
    if (ui.button(ui.id("skinadd"), RectF(r.l + 10, r.t + 10, r.l + 10 + bw, r.b - 10), L"Import skin", Btn::Standard, L"\xE710")) after([this] { pickSkinFiles(); });
    if (ui.button(ui.id("skinfolder"), RectF(r.l + 18 + bw, r.t + 10, r.l + 18 + bw * 2, r.b - 10), L"Open folder", Btn::Standard, L"\xE838")) {
      SHCreateDirectoryExW(nullptr, SkinStore::userDir().c_str(), nullptr);
      ShellExecuteW(hwnd_, nullptr, SkinStore::userDir().c_str(), nullptr, nullptr, SW_SHOWNORMAL);
    }
    float tx = r.l + 30 + bw * 2;
    if (hiddenCount > 0) {
      std::wstring t = L"Bring back " + std::to_wstring(hiddenCount) + (hiddenCount == 1 ? L" removed skin" : L" removed skins");
      float w = std::min(ui.textWidth(t, 13.5f) + 32, r.r - 10 - tx);
      if (w > 60 && ui.button(ui.id("skinback"), RectF(r.r - 10 - w, r.t + 10, r.r - 10, r.b - 10), t)) {
        k.hiddenSkins.clear();
        skinPics_.clear();
        changed();
      }
    } else if (c_.w > 420) {
      ui.text(RectF(tx, r.t, r.r - 10, r.b), L"or drop a .rskin file here", 12.f, ui.pal.dim);
    }
  }

  auto now = preview_.skin();
  const SkinInfo* info = nullptr;
  for (auto& q : list)
    if (q.id == k.skinNow()) info = &q;
  if (!k.skinNow().empty() && !info) {
    RectF r = RectF::xywh(c_.x, c_.y, c_.w, 48);
    c_.y += 52;
    ui.card(r, 8);
    ui.text(RectF(r.l + 16, r.t, r.r - 12, r.b), L"The chosen skin is not there any more. Your style is used instead.", 13.f, ui.pal.text);
  }
  if (info && info->error.empty()) {
    section(L"Colours");
    Config::Tune u = k.tune();
    bool ch = false;
    float sw = clampf(c_.w * 0.56f, 190.f, 340.f);
    ch |= ui.slider(ui.id("hue"), row(L"Hue", nullptr, sw), u.hue, -180, 180, 5, L"%.0f\x00B0");
    ch |= ui.slider(ui.id("sat"), row(L"Saturation", nullptr, sw), u.sat, 0, 2, 0.05f, L"%.0f%%", 100.f);
    ch |= ui.slider(ui.id("lum"), row(L"Brightness", nullptr, sw), u.light, 0.4f, 1.8f, 0.05f, L"%.0f%%", 100.f);
    if (!u.plain()) {
      RectF r = row(L"Back to how it was made", nullptr, 90);
      if (ui.button(ui.id("untune"), r, L"Reset")) {
        u = {};
        ch = true;
      }
    }
    if (ch) {
      if (u.plain()) k.tunes.erase(k.skinNow());
      else k.tunes[k.skinNow()] = u;
      changed();
    }
    section(L"Sound and pointer");
    toggleRow("snd", L"Interface sounds", now && !now->sounds.empty() ? L"This skin brings its own" : nullptr, k.sounds);
    if (k.sounds) sliderRow("vol", L"Volume", k.volume, 0.05f, 1, 0.05f, L"%.0f%%", 100.f);
    if (now && now->cursor.image >= 0) toggleRow("skincur", L"The skin's own pointer", nullptr, k.skinCursor);

    section(L"Make your own", L"Every skin can be taken apart. SKINS.md beside the program explains all of it.");
    {
      RectF r = RectF::xywh(c_.x, c_.y, c_.w, 52);
      c_.y += 56;
      ui.card(r, 8);
      std::string id = k.skinNow();
      float x = r.l + 10;
      auto next = [&](float bw) {
        RectF q(x, r.t + 10, x + bw, r.b - 10);
        x += bw + 8;
        return q;
      };
      if (info->folder && !info->builtin) {
        if (ui.button(ui.id("skinopen"), next(124), L"Edit its files", Btn::Standard, L"\xE70F")) ShellExecuteW(hwnd_, nullptr, info->path.c_str(), nullptr, nullptr, SW_SHOWNORMAL);
      }
      if (ui.button(ui.id("skincopy"), next(160), L"Make a copy to edit", Btn::Standard, L"\xE8C8")) after([this, id] { copySkin(id); });
      if (ui.button(ui.id("skinshare"), next(96), L"Share", Btn::Standard, L"\xE72D")) after([this, id] { shareSkin(id); });
      if (fileExists(joinPath(dirName(modulePath()), L"SKINS.md")) && x + 90 < r.r &&
          ui.button(ui.id("skinguide"), next(88), L"Guide", Btn::Standard, L"\xE897"))
        if (std::wstring md = joinPath(dirName(modulePath()), L"SKINS.md"); (INT_PTR)ShellExecuteW(hwnd_, L"open", md.c_str(), nullptr, nullptr, SW_SHOWNORMAL) <= 32)
          ShellExecuteW(hwnd_, L"open", L"notepad.exe", (L"\"" + md + L"\"").c_str(), nullptr, SW_SHOWNORMAL);  // nothing opens .md files here
    }
    if (now && !now->problems.empty()) {
      size_t n = std::min<size_t>(now->problems.size(), 8);
      RectF r = RectF::xywh(c_.x, c_.y, c_.w, 34 + 20.f * n);
      c_.y += r.h() + 4;
      ui.card(r, 8);
      ui.text(RectF(r.l + 16, r.t + 4, r.r, r.t + 28), n == 1 ? L"One thing in skin.json needs a look" : std::to_wstring(now->problems.size()) + L" things in skin.json need a look", 13.f, ui.pal.text, 600);
      for (size_t i = 0; i < n; i++) ui.text(RectF(r.l + 16, r.t + 28 + 20.f * i, r.r - 12, r.t + 48 + 20.f * i), widen(now->problems[i]), 12.f, ui.pal.dim);
    }
  }
}

void SettingsWindow::pickSkinFiles() {
  std::vector<wchar_t> buf(32768, L'\0');
  OPENFILENAMEW o{};
  o.lStructSize = sizeof o;
  o.hwndOwner = hwnd_;
  o.lpstrFilter = L"Skins (*.rskin)\0*.rskin;*.zip\0";
  o.lpstrFile = buf.data();
  o.nMaxFile = (DWORD)buf.size();
  o.Flags = OFN_EXPLORER | OFN_FILEMUSTEXIST | OFN_ALLOWMULTISELECT | OFN_NOCHANGEDIR;
  if (!GetOpenFileNameW(&o)) return;
  std::vector<std::wstring> files;
  std::wstring first = buf.data();
  const wchar_t* q = buf.data() + first.size() + 1;
  if (!*q) files.push_back(first);
  for (; *q; q += wcslen(q) + 1) files.push_back(joinPath(first, q));
  addSkins(files, false);
}

void SettingsWindow::addSkins(const std::vector<std::wstring>& files, bool ask) {
  std::string last, err;
  int added = 0;
  std::wstring bad;
  for (auto& f : files) {
    if (ask) {  // double-clicked somewhere: say what it is before taking it in
      std::string text, e;
      auto sf = SkinFiles::open(f, &e);
      Skin t;
      if (!sf || !sf->read("skin.json", text, SkinFiles::kJsonMost) || !parseSkin(text, t, &e)) {
        MessageBoxW(hwnd_, (fileName(f) + L"\n\n" + widen(e.empty() ? "There is no skin.json in it." : e)).c_str(), L"This skin cannot be used", MB_ICONWARNING);
        continue;
      }
      std::wstring line = L"Add the skin \"" + (t.name.empty() ? fileStem(f) : t.name) + L"\"" + (t.author.empty() ? L"" : L" by " + t.author) + L" and use it?";
      if (!t.about.empty()) line += L"\n\n" + t.about;
      if (MessageBoxW(hwnd_, line.c_str(), RT_NAME, MB_OKCANCEL | MB_ICONQUESTION) != IDOK) continue;
    }
    std::string id;
    if (skins().install(f, id, &err)) {
      last = id;
      added++;
    } else if (bad.empty()) {
      bad = fileName(f) + L": " + widen(err);
    }
  }
  skinPics_.clear();
  if (added) {
    page_ = kSkins;
    app_.cfg.chooseSkin(last);
    changed();
    preview_.replay();
  }
  if (!bad.empty()) say(bad);
  else if (added > 1) say(std::to_wstring(added) + L" skins added");
  else if (added)
    if (auto* i = skins().info(last)) say(i->name + L" added");
  invalidate();
}

void SettingsWindow::copySkin(const std::string& id) {
  const SkinInfo* i = skins().info(id);
  if (!i) return;
  std::wstring folder, name = i->name.rfind(L"My ", 0) == 0 ? i->name + L" 2" : L"My " + i->name;
  std::string err;
  if (!skins().copyToFolder(id, name, folder, &err)) {
    say(widen(err));
    return;
  }
  for (auto& q : skins().list())
    if (toLower(q.path) == toLower(folder)) chooseSkin(q.id);
  ShellExecuteW(hwnd_, nullptr, folder.c_str(), nullptr, nullptr, SW_SHOWNORMAL);
  say(name + L" is yours to change");
}

void SettingsWindow::shareSkin(const std::string& id) {
  const SkinInfo* i = skins().info(id);
  if (!i) return;
  wchar_t buf[1024];
  wcsncpy(buf, (widen(id) + L".rskin").c_str(), 1023);
  buf[1023] = 0;
  OPENFILENAMEW o{};
  o.lStructSize = sizeof o;
  o.hwndOwner = hwnd_;
  o.lpstrFilter = L"Skin (*.rskin)\0*.rskin\0";
  o.lpstrFile = buf;
  o.nMaxFile = 1024;
  o.lpstrDefExt = L"rskin";
  o.Flags = OFN_OVERWRITEPROMPT | OFN_NOCHANGEDIR;
  if (!GetSaveFileNameW(&o)) return;
  std::string err;
  say(skins().pack(id, buf, &err) ? L"Saved " + fileName(buf) : widen(err));
}

void SettingsWindow::removeSkin(const std::string& id) {
  const SkinInfo* i = skins().info(id);
  if (!i) return;
  std::wstring line = L"Remove \"" + i->name + L"\"? It goes to the recycle bin.";
  if (MessageBoxW(hwnd_, line.c_str(), RT_NAME, MB_OKCANCEL | MB_ICONQUESTION) != IDOK) return;
  std::string err;
  for (auto& pr : app_.cfg.profiles)
    if (pr.skin == id) pr.skin.clear();
  if (app_.cfg.skin == id) app_.cfg.skin.clear();
  changed();
  if (!skins().remove(id, &err)) say(widen(err));
  skinPics_.clear();
  invalidate();
}

// One that came with the program cannot be deleted (an update would bring it back), so it leaves the list instead.
void SettingsWindow::hideSkin(const std::string& id) {
  const SkinInfo* i = skins().info(id);
  if (!i) return;
  std::wstring line = L"Remove \"" + i->name + L"\" from the list?\n\nIt came with " RT_NAME L", so it is only put away: \"Bring back\" at the bottom of the Skins page shows it again.";
  if (MessageBoxW(hwnd_, line.c_str(), RT_NAME, MB_OKCANCEL | MB_ICONQUESTION) != IDOK) return;
  Config& k = app_.cfg;
  if (!k.hidden(id)) k.hiddenSkins.push_back(id);
  for (auto& pr : k.profiles)
    if (pr.skin == id) pr.skin.clear();
  if (k.skin == id) k.skin.clear();
  say(L"Removed " + i->name + L" from the list");
  changed();
  preview_.replay();
}

bool SettingsWindow::skinBanner(const wchar_t* what) {
  const SkinInfo* i = skins().info(app_.cfg.skinNow());
  if (!i) return false;
  RectF r = RectF::xywh(c_.x, c_.y + 8, c_.w, 60);
  c_.y += 72;
  ui.card(r, 8);
  ui.p->rrect(RectF(r.l, r.t + 8, r.l + 3, r.b - 8), 1.5f, ui.pal.accent);
  ui.text(RectF(r.l + 16, r.t + 9, r.r - 150, r.t + 31), L"The skin " + i->name + L" is in charge", 13.5f, ui.pal.text, 600);
  ui.text(RectF(r.l + 16, r.t + 30, r.r - 150, r.b - 8), what, 12.f, ui.pal.dim);
  if (ui.button(ui.id("noskin"), RectF(r.r - 138, r.t + 14, r.r - 12, r.b - 14), L"Turn it off")) chooseSkin({});
  return true;
}

// ---------------------------------------------------------------- look page
void SettingsWindow::drawLookThumb(RectF r, const Style& st, float hv) {
  Painter& p = *ui.p;
  // One colourful backdrop for every thumbnail, so tint and transparency can be compared.
  auto bg = p.linear({r.l, r.t}, {r.r, r.b}, {{0, Color::hex(0x5B8FE0)}, {0.5f, Color::hex(0x8F76D6)}, {1, Color::hex(0xE08A8F)}});
  p.rrect(r, 8, bg.Get());
  p.rrect(r, 8, Color(0, 0, 0, st.dim * 0.85f));
  V2 c = r.center();
  float R = std::min(r.w(), r.h()) * 0.5f - 6, ri = R * 0.42f;
  int n = 7;
  float gap = std::max(1.2f, st.gap * 0.32f);
  auto slot = [&](int i, float grow) -> Geo {
    float a = i * kTau / n, w = kTau / n, rm = (ri + R) * 0.5f;
    switch (st.shape) {
      case SlotShape::Wedge: return wedgeGeo(c, ri, R + grow, a - w / 2, a + w / 2, gap, st.corner * 0.26f);
      case SlotShape::Blade: return bladeGeo(c, ri, R + grow, a - w / 2, a + w / 2, gap, st.corner * 0.3f, 0.05f);
      case SlotShape::Orb: return circleGeo(polar(c, a, rm), std::min((R - ri) * 0.5f, rm * sinf(w / 2) - gap * 0.5f) + grow * 0.4f);
      case SlotShape::Hex: return hexGeo(polar(c, a, rm), std::min((R - ri) * 0.55f, rm * sinf(w / 2) * 1.05f - gap * 0.4f) + grow * 0.4f, a, 1.5f);
      case SlotShape::Petal: return petalGeo(c, ri, R + 3 + grow, a, rm * tanf(w / 2) - gap * 0.25f);
      default: return {};
    }
  };
  float op = st.material == Material::Outline ? st.opacity * 0.8f : st.material == Material::Liquid ? std::max(0.28f, st.opacity) : std::max(st.opacity, 0.5f);
  for (int i = 0; i < n; i++) {
    bool lit = i == 1;
    Geo g = slot(i, lit ? 2.f + 2.f * hv : 0.f);
    Color ac = st.accent;
    V2 ic = polar(c, i * kTau / n, (ri + R) * 0.5f);
    if (g) {
      p.fill(g.Get(), st.base.withA(op));
      if (lit) p.fill(g.Get(), ac.withA(0.55f));
      p.stroke(g.Get(), lit ? ac : st.border.withA(std::max(0.14f, st.borderOpacity)), lit ? 1.4f : 1.f);
    }
    p.circle(ic, 3.1f, lit ? Color(1, 1, 1, 0.95f) : st.text.withA(0.62f));
  }
  if (st.shape != SlotShape::None) {
    p.circle(c, ri - gap - 1, st.base.withA(op));
    p.circleStroke(c, ri - gap - 1, st.border.withA(std::max(0.14f, st.borderOpacity)), 1.f);
  }
  if (st.ticks)
    for (int i = 0; i < 24; i++) p.line(polar(c, i * kTau / 24, R + 2.5f), polar(c, i * kTau / 24, R + 4.5f), st.border.withA(0.6f), 1, false);
  if (st.rim != RimStyle::Off) {
    auto br = p.linear({c.x - R, c.y}, {c.x + R, c.y}, {{0, st.accent}, {1, st.accent2}});
    auto g = circleGeo(c, R + 3.f);
    p.stroke(g.Get(), br.Get(), 1.4f);
  }
}

void SettingsWindow::lookCard(RectF r, const Look& k, bool custom) {
  Config& cfg = app_.cfg;
  uint32_t id = ui.id(k.id, custom ? 2 : 1);
  bool on = cfg.style.look == k.id;
  RectF del(r.r - 28, r.t + 6, r.r - 6, r.t + 28);
  bool overDel = custom && ui.hot(del);
  if (!overDel && ui.press(id, r)) {
    cfg.style = k.style;
    cfg.style.look = k.id;
    cfg.chooseSkin({});  // choosing a style means wanting to see it
    changed();
    preview_.replay();
  }
  bool hv = ui.hot(r);
  if (hv) {
    ui.cursor = LoadCursorW(nullptr, IDC_HAND);
    if (!k.blurb.empty()) ui.tooltip(r, k.blurb);
  }
  float a = ui.anim(id, hv ? 1.f : 0.f), s = ui.anim(id ^ 9u, on ? 1.f : 0.f);
  ui.p->rrect(r, 10, mix(ui.pal.card, ui.pal.cardHover, a));
  ui.p->rrectStroke(r.inset(0.5f), 10, ui.pal.stroke, 1);
  {
    RectF q(r.l + 6, r.t + 6, r.r - 6, r.b - 30);
    if (a > 0.f && a < 1.f) drawLookThumb(q, k.style, a);
    else thumb(ui.id(k.id, custom * 2 + (a > 0.5f)), q, 2, [&] { drawLookThumb(q, k.style, a); });
  }
  if (s > 0.01f) ui.p->rrectStroke(r.inset(1.f), 9.5f, ui.pal.accent.alpha(s), 2.f);
  ui.text(RectF(r.l + 8, r.b - 28, r.r - 8, r.b - 3), k.name, 12.5f, ui.pal.text, on ? 600 : 400, Align::Center);
  if (custom && (hv || overDel)) {
    if (ui.iconButton(id ^ 77u, del, L"\xE74D", L"Delete this style", true, 12.f)) {
      std::string gone = k.id;
      for (size_t i = 0; i < cfg.customLooks.size(); i++)
        if (cfg.customLooks[i].id == gone) {
          cfg.customLooks.erase(cfg.customLooks.begin() + (ptrdiff_t)i);
          break;
        }
      changed();
    }
  }
}

void SettingsWindow::pageLook(RectF) {
  Config& k = app_.cfg;
  Style& s = k.style;
  auto grid = [&](const std::vector<const Look*>& list, bool custom) {
    int cols = std::max(2, (int)floorf((c_.w + 8) / 132.f));
    float w = (c_.w - 8.f * (cols - 1)) / cols, h = 122;
    for (size_t i = 0; i < list.size(); i++) {
      RectF r = RectF::xywh(c_.x + (float)(i % (size_t)cols) * (w + 8), c_.y + (float)(i / (size_t)cols) * (h + 8), w, h);
      lookCard(r, *list[i], custom);
    }
    size_t rows = (list.size() + (size_t)cols - 1) / (size_t)cols;
    c_.y += rows * (h + 8);
  };
  skinBanner(L"Choose a style to go back to styles.");
  for (const wchar_t* grp : {L"Stylized", L"Gamey", L"Minimal"}) {
    section(grp);
    std::vector<const Look*> list;
    for (auto& q : builtinLooks())
      if (q.group == grp) list.push_back(&q);
    grid(list, false);
  }
  if (!k.customLooks.empty()) {
    section(L"Yours");
    std::vector<Look> copy = k.customLooks;  // a delete inside the loop must not move what we iterate
    std::vector<const Look*> list;
    for (auto& q : copy) list.push_back(&q);
    grid(list, true);
  }

  // save / reset
  {
    const Look* base = findLook(s.look);
    for (auto& q : k.customLooks)
      if (q.id == s.look) base = &q;
    bool mod = base && !sameLook(base->style, s);
    c_.y += 4;
    RectF r = RectF::xywh(c_.x, c_.y, c_.w, 48);
    c_.y += 52;
    ui.card(r, 8);
    if (namingLook_) {
      bool enter = false;
      ui.textBox(ui.id("skinname"), RectF(r.l + 10, r.t + 8, r.r - 190, r.b - 8), lookName_, L"Name your style", nullptr, &enter);
      bool ok = ui.button(ui.id("skinsave"), RectF(r.r - 180, r.t + 8, r.r - 98, r.b - 8), L"Save", Btn::Accent, nullptr, !trim(lookName_).empty());
      if (ui.button(ui.id("skincancel"), RectF(r.r - 92, r.t + 8, r.r - 10, r.b - 8), L"Cancel")) namingLook_ = false;
      if ((ok || enter) && !trim(lookName_).empty()) {
        Look q;
        q.id = "my-" + newId();
        q.name = trim(lookName_);
        q.group = L"Yours";
        q.style = s;
        q.style.look = q.id;
        s.look = q.id;
        k.customLooks.push_back(q);
        namingLook_ = false;
        changed();
      }
    } else {
      std::wstring nm = base ? base->name : L"Custom";
      ui.text(RectF(r.l + 16, r.t, r.r - 260, r.b), mod ? nm + L" (changed)" : nm, 13.5f, ui.pal.text, 600);
      if (ui.button(ui.id("skinreset"), RectF(r.r - 246, r.t + 8, r.r - 146, r.b - 8), L"Reset", Btn::Standard, L"\xE7A7", mod)) {
        Style z = base->style;
        s = z;
        changed();
      }
      if (ui.button(ui.id("skinas"), RectF(r.r - 138, r.t + 8, r.r - 10, r.b - 8), L"Save as mine", Btn::Standard, L"\xE74E")) {
        namingLook_ = true;
        lookName_ = nm + L" 2";
        ui.focusOn(ui.id("skinname"));
      }
    }
  }

  section(L"Shape and material");
  {
    RectF r = RectF::xywh(c_.x, c_.y, c_.w, 96);
    c_.y += 100;
    ui.card(r, 8);
    static const wchar_t* names[] = {L"Wedge", L"Blade", L"Orb", L"Hex", L"Petal", L"None"};
    float w = (r.w() - 20) / 6;
    for (int i = 0; i < 6; i++) {
      RectF q = RectF::xywh(r.l + 10 + i * w, r.t + 8, w - 4, r.h() - 16);
      uint32_t id = ui.id("shape", i);
      bool on = (int)s.shape == i;
      if (ui.press(id, q) && !on) {
        s.shape = (SlotShape)i;
        changed();
      }
      bool h = ui.hot(q);
      if (h) ui.cursor = LoadCursorW(nullptr, IDC_HAND);
      float a = ui.anim(id, on ? 1.f : (h ? 0.45f : 0.f));
      ui.p->rrect(q, 7, ui.pal.accent.withA(0.13f * a));
      if (on) ui.p->rrectStroke(q.inset(0.5f), 7, ui.pal.accent, 1.4f);
      V2 c{q.cx(), q.t + 28};
      Color fg = mix(ui.pal.dim, ui.pal.accent, on ? 1.f : 0.f);
      V2 o{c.x, c.y + 62};
      Geo g;
      switch (i) {
        case 0: g = wedgeGeo(o, 46, 80, -0.27f, 0.27f, 0, 6); break;
        case 1: g = bladeGeo(o, 46, 80, -0.27f, 0.27f, 0, 8, 0.07f); break;
        case 2: g = circleGeo(c, 17); break;
        case 3: g = hexGeo(c, 18.5f, 0, 3); break;
        case 4: g = petalGeo({c.x, c.y + 40}, 22, 60, 0, 16); break;
        default: break;
      }
      if (g) ui.p->stroke(g.Get(), fg, 1.7f);
      else
        for (int d = -1; d <= 1; d++) ui.p->circle({c.x + d * 11.f, c.y}, 3, fg);
      ui.text(RectF(q.l, q.b - 24, q.r, q.b - 4), names[i], 12.f, on ? ui.pal.text : ui.pal.dim, on ? 600 : 400, Align::Center);
    }
  }
  segRow("mat", L"Material", nullptr, s.material, {L"Frosted", L"Liquid", L"Solid", L"Outline"}, 300);

  section(L"Colours");
  {
    RectF r = RectF::xywh(c_.x, c_.y, c_.w, 82);
    c_.y += 86;
    ui.card(r, 8);
    struct C { const wchar_t* n; Color* c; bool off; };
    C cs[] = {{L"Panel", &s.base, false}, {L"Accent", &s.accent, s.systemAccent}, {L"Accent 2", &s.accent2, s.systemAccent}, {L"Text", &s.text, false}, {L"Border", &s.border, false}};
    float w = (r.w() - 24) / 5;
    for (int i = 0; i < 5; i++) {
      RectF q = RectF::xywh(r.l + 12 + i * w, r.t + 12, w - 8, 34);
      if (cs[i].off) {
        Style e = effectiveStyle(k);
        ui.p->rrect(q, 7, (i == 1 ? e.accent : e.accent2).withA(0.55f));
        ui.tooltip(q, L"Following Windows");
      } else if (ui.colorBox(ui.id("col", i), q, *cs[i].c)) {
        changed();
      }
      ui.text(RectF(q.l - 4, q.b + 4, q.r + 4, q.b + 26), cs[i].n, 12.f, ui.pal.dim, 400, Align::Center);
    }
  }
  toggleRow("sysacc", L"Use the Windows accent colour", nullptr, s.systemAccent);

  section(L"Surface");
  sliderRow("op", L"Opacity", s.opacity, 0, 1, 0.02f, L"%.0f%%", 100.f);
  if (s.material == Material::Frosted || s.material == Material::Liquid) sliderRow("blur", L"Blur", s.blur, 0, 60, 1, L"%.0f px");
  if (s.material == Material::Liquid && !k.onlyLayout(LayoutType::Flow)) sliderRow("refr", L"Edge refraction", s.refraction, 0, 1, 0.05f, L"%.0f%%", 100.f);
  sliderRow("corner", s.shape == SlotShape::Blade ? L"Corner cut" : L"Corner rounding", s.corner, 0, 40, 1, L"%.0f px");
  if (k.anyLayout(LayoutType::Radial)) sliderRow("gap", L"Gap between slots", s.gap, 0, 30, 1, L"%.0f px");
  sliderRow("bw", L"Border width", s.borderWidth, 0, 6, 0.2f, L"%.1f px");
  sliderRow("bo", L"Border strength", s.borderOpacity, 0, 1, 0.02f, L"%.0f%%", 100.f);
  sliderRow("shadow", L"Shadow", s.shadow, 0, 1, 0.05f, L"%.0f%%", 100.f);

  section(L"Icons and text");
  segRow("tone", L"Icon colour", L"Muted and tinted icons light up on focus", s.tone, {L"Original", L"Muted", L"Tinted"}, 250);
  {
    static const char* fonts[] = {"Segoe UI Variable Display", "Bahnschrift", "Segoe UI", "Calibri", "Trebuchet MS", "Verdana", "Georgia", "Cambria", "Consolas", "Cascadia Code", "Comic Sans MS", "Impact"};
    std::vector<std::wstring> names;
    std::vector<std::string> ids;
    int idx = -1;
    for (auto f : fonts)
      if (gfx().hasFont(widen(f))) {
        if (s.font == f) idx = (int)ids.size();
        ids.push_back(f);
        names.push_back(!strcmp(f, "Segoe UI Variable Display") ? L"Segoe UI Variable" : widen(f));
      }
    if (idx < 0) {
      ids.push_back(s.font);
      names.push_back(widen(s.font));
      idx = (int)ids.size() - 1;
    }
    RectF r = row(L"Font", nullptr, 210);
    if (ui.combo(ui.id("font"), r, idx, names)) {
      s.font = ids[(size_t)idx];
      changed();
    }
  }
}

// ---------------------------------------------------------------- effects page
void SettingsWindow::pageEffects(RectF) {
  Config& k = app_.cfg;
  Style& s = k.style;
  skinBanner(L"These settings belong to your style and are used without a skin.");
  section(L"Opening");
  if (segRow("open", L"Animation", nullptr, s.open, {L"Bloom", L"Spin", L"Unfold", L"Zoom", L"Fade"}, 320)) preview_.replay();
  if (sliderRow("speed", L"Speed", s.speed, 0.4f, 2.5f, 0.05f, L"%.2fx") && !ui.down) preview_.replay();
  section(L"Focus");
  bool wheel = k.anyLayout(LayoutType::Radial);  // the other layouts swell with their own magnify setting
  if (wheel) sliderRow("grow", L"Extension on focus", s.hoverGrow, 0, 40, 1, L"%.0f px");
  if (wheel) sliderRow("zoom", L"Icon zoom", s.iconZoom, 1, 1.8f, 0.02f, L"%.0f%%", 100.f);
  sliderRow("glow", L"Glow", s.glow, 0, 1, 0.05f, L"%.0f%%", 100.f);
  if (wheel) toggleRow("ptr", L"Direction needle", L"An arrow on the centre that points at your choice", s.pointer);
  section(L"Atmosphere");
  sliderRow("dim", L"Darken the desktop", s.dim, 0, 0.85f, 0.01f, L"%.0f%%", 100.f);
  sliderRow("tilt", L"3D tilt", s.tilt, 0, 1, 0.05f, L"%.0f%%", 100.f, L"Leans toward the pointer");
  segRow("rim", L"Rim light", nullptr, s.rim, {L"Off", L"Solid", L"Spinning"}, 250);
  segRow("part", L"Particles", nullptr, s.particles, {L"Off", L"Embers", L"Stars"}, 250);
  if (wheel) {
    toggleRow("ticks", L"HUD tick ring", nullptr, s.ticks);
    toggleRow("scan", L"Scan lines", nullptr, s.scan);
    toggleRow("pulse", L"Radar pulse", nullptr, s.pulse);
  }
  toggleRow("burst", L"Spark burst on launch", nullptr, s.burst);
  section(L"Background", L"Screensaver-like motion over the darkened desktop while the wheel is open.");
  toggleRow("bfx", L"Animate the background", nullptr, k.backFx);
  if (k.backFx) {
    auto& kinds = backFxKinds();
    std::vector<std::wstring> opts{L"The skin's own"};
    int idx = 0;
    for (size_t i = 0; i < kinds.size(); i++) {
      opts.push_back(kinds[i].second);
      if (kinds[i].first == k.backFxKind) idx = (int)i + 1;
    }
    RectF r = row(L"Effect", idx == 0 ? L"Shown with skins that have one" : L"With every skin, and without one", 220);
    if (ui.combo(ui.id("bfxkind"), r, idx, opts) && idx >= 0) {
      k.backFxKind = idx == 0 ? std::string("skin") : kinds[(size_t)idx - 1].first;
      changed();
    }
  }
  section(L"Sound");
  toggleRow("snd", L"Interface sounds", L"Short ticks while you move and a chime on launch", k.sounds);
  if (k.sounds) sliderRow("vol", L"Volume", k.volume, 0.05f, 1, 0.05f, L"%.0f%%", 100.f);
  section(L"Comfort");
  toggleRow("rm", L"Reduce motion", L"Keeps fades, drops movement", k.reduceMotion);
}

}  // namespace rt
