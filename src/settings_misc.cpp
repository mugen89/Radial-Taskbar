// Settings: the Shortcut and General pages.
#include "app.h"
#include "install.h"
#include "settings.h"

namespace rt {

static constexpr UINT WM_RECORD = WM_APP + 60;

// ---------------------------------------------------------------- key caps
static std::vector<std::wstring> capsOf(const Hotkey& h) {
  std::vector<std::wstring> v;
  if (h.mods & MOD_WIN) v.push_back(L"\x01");  // drawn as the Windows logo
  if (h.mods & MOD_CONTROL) v.push_back(L"Ctrl");
  if (h.mods & MOD_ALT) v.push_back(L"Alt");
  if (h.mods & MOD_SHIFT) v.push_back(L"Shift");
  v.push_back(keyName(h.vk));
  return v;
}

static float capWidth(Ui& ui, const std::wstring& s, float size) {
  if (s == L"\x01") return size * 1.9f;
  return std::max(size * 1.35f, ui.textWidth(s, size * 0.56f, 600) + size * 0.72f);
}

float SettingsWindow::keycapsWidth(const Hotkey& h, float size) {
  float w = 0;
  auto caps = capsOf(h);
  for (size_t i = 0; i < caps.size(); i++) w += capWidth(ui, caps[i], size) + (i ? size * 0.28f : 0.f);
  return w;
}

void SettingsWindow::keycap(RectF& at, const std::wstring& s, float size, Color fill) {
  float w = capWidth(ui, s, size);
  RectF r = RectF::xywh(at.l, at.t, w, size);
  float cr = size * 0.22f, lip = std::max(1.5f, size * 0.07f), a = fill.a;
  ui.p->rrect(r.offset(0, lip), cr, (ui.pal.dark ? Color(0, 0, 0, 0.55f) : Color(0, 0, 0, 0.20f)).alpha(a));
  ui.p->rrect(r, cr, ui.pal.dark ? Color::hex(0x3A3C45).withA(a) : Color::hex(0xFFFFFF).withA(a));
  ui.p->rrectStroke(r.inset(0.5f), cr, ui.pal.strokeStrong.alpha(a), 1);
  if (s == L"\x01") {
    float q = size * 0.20f, g = size * 0.035f;
    for (int i = 0; i < 4; i++) {
      float x = r.cx() + ((i % 2) ? g : -g - q), y = r.cy() + ((i / 2) ? g : -g - q);
      ui.p->rrect(RectF::xywh(x, y, q, q), size * 0.02f, ui.pal.text.alpha(a));
    }
  } else if (s == L"`") {  // both legends, as printed on the key
    ui.text(RectF(r.l, r.t + size * 0.02f, r.r, r.t + size * 0.54f), L"~", size * 0.52f, ui.pal.text.alpha(a), 600, Align::Center);
    ui.text(RectF(r.l, r.t + size * 0.46f, r.r, r.b + size * 0.18f), L"`", size * 0.56f, ui.pal.text.alpha(a), 600, Align::Center);
  } else {
    ui.text(r.offset(0, -size * 0.02f), s, size * 0.56f, ui.pal.text.alpha(a), 600, Align::Center);
  }
  at.l += w + size * 0.28f;
}

void SettingsWindow::drawKeycaps(float x, float cy, const Hotkey& h, float size, float alpha) {
  RectF at(x, cy - size * 0.5f, x, cy + size * 0.5f);
  for (auto& s : capsOf(h)) keycap(at, s, size, Color(1, 1, 1, alpha));
}

// ---------------------------------------------------------------- recording
void SettingsWindow::startRecording() {
  if (recording_ || headless_) return;
  recording_ = true;
  triedTaken_ = false;
  app_.suspendHotkey(true);
  app_.hotkeys.beginRecord(hwnd_, WM_RECORD);
}

void SettingsWindow::stopRecording() {
  if (!recording_) return;
  recording_ = false;
  app_.hotkeys.endRecord();
  app_.suspendHotkey(false);
  ideasOk_ = false;
}

LRESULT SettingsWindow::onMessage(UINT m, WPARAM w, LPARAM l, bool& handled) {
  handled = false;
  if (m == WM_APP + 72) {  // pictures arrived
    handled = true;
    invalidate();
    return 0;
  }
  if (m == WM_APP_SHOW) {
    handled = true;
    show((int)(INT_PTR)w);
    return 0;
  }
  if (m == WM_COPYDATA) {  // the wheel changed something (a pin, the profile): this window owns the file
    std::wstring cmd, arg;
    if (splitCommand((void*)l, kCmdToSettings, cmd, arg)) {
      handled = true;
      ReplyMessage(TRUE);
      after([this, cmd, arg] {
        app_.applyRemote(cmd, arg);
        rev_++;
        invalidate();
      });
      return TRUE;
    }
  }
  if (m == WM_APP_RELOAD) {
    handled = true;
    after([this] {
      if (!dragging_ && app_.reloadFromDisk()) {
        rev_++;
        invalidate();
      }
    });
    return 0;
  }
  if (m == WM_RECORD && recording_) {
    handled = true;
    UINT vk = (UINT)w, mods = (UINT)l;
    if (vk == VK_ESCAPE && !mods) {
      stopRecording();
      invalidate();
      return 0;
    }
    bool fkey = vk >= VK_F1 && vk <= VK_F24;
    if (!mods && !fkey && vk != VK_PAUSE && vk != VK_SCROLL) {
      flash_ = L"Add Win, Ctrl, Alt or Shift to that key";
      flashAt_ = nowSec();
      invalidate();
      return 0;
    }
    tried_ = Hotkey{mods, vk, false};
    bool free = HotkeyManager::available(mods, vk);
    recording_ = false;
    app_.hotkeys.endRecord();
    if (free) {
      app_.cfg.hotkey = tried_;
      app_.suspendHotkey(false);
      app_.applyHotkey();
      flash_ = L"Shortcut set";
      flashAt_ = nowSec();
      changed();
    } else {
      triedTaken_ = true;
      app_.suspendHotkey(false);
    }
    ideasOk_ = false;
    invalidate();
    return 0;
  }
  if (m == WM_ACTIVATE && LOWORD(w) == WA_INACTIVE) stopRecording();
  return 0;
}

void SettingsWindow::refreshIdeas() {
  if (ideasOk_) return;
  ideas_ = suggestHotkeys(app_.cfg.hotkey);
  ideasOk_ = true;
}

// ---------------------------------------------------------------- shortcut page
void SettingsWindow::pageShortcut(RectF) {
  Config& k = app_.cfg;
  refreshIdeas();
  {
    float h = triedTaken_ ? 250.f : 196.f;
    RectF r = RectF::xywh(c_.x, c_.y + 4, c_.w, h);
    c_.y += h + 8;
    ui.card(r, 12);
    if (recording_) {
      float pulse = 0.5f + 0.5f * sinf((float)nowSec() * 5.f);
      ui.animating = true;
      ui.p->rrectStroke(r.inset(1.f), 11.5f, ui.pal.accent.alpha(0.35f + 0.65f * pulse), 2.f);
      ui.text(RectF(r.l, r.t + 46, r.r, r.t + 82), L"Press the new shortcut", 22.f, ui.pal.text, 600, Align::Center);
      ui.text(RectF(r.l, r.t + 82, r.r, r.t + 106), L"Hold Win, Ctrl, Alt or Shift and press a key. Esc cancels.", 13.f, ui.pal.dim, 400, Align::Center);
      if (ui.button(ui.id("recstop"), RectF::xywh(r.cx() - 60, r.t + 134, 120, 34), L"Cancel")) stopRecording();
    } else {
      const float size = 62;
      float kw = keycapsWidth(k.hotkey, size);
      drawKeycaps(r.cx() - kw * 0.5f, r.t + 62, k.hotkey, size, 1.f);
      bool ok = app_.hotkeyOk();
      std::wstring st = !ok ? L"Taken by another program. Pick one that is free below." : k.hotkey.takeOver ? L"Active, replacing what Windows does with it" : L"Active";
      Color sc = ok ? (ui.pal.dark ? Color::hex(0x6CCB8A) : Color::hex(0x107C41)) : ui.pal.danger;
      float tw = ui.textWidth(st, 13.f, 600);
      ui.glyph(RectF::xywh(r.cx() - tw * 0.5f - 24, r.t + 106, 20, 22), ok ? L"\xE73E" : L"\xE7BA", 13, sc);
      ui.text(RectF(r.l, r.t + 106, r.r, r.t + 128), st, 13.f, sc, 600, Align::Center);
      if (ui.button(ui.id("rec"), RectF::xywh(r.cx() - 90, r.t + 142, 180, 36), L"Record a shortcut", Btn::Accent, L"\xE765")) startRecording();
      if (triedTaken_) {
        RectF w(r.l + 14, r.t + 190, r.r - 14, r.b - 12);
        ui.p->rrect(w, 8, ui.pal.danger.withA(0.10f));
        ui.text(RectF(w.l + 14, w.t, w.r - 240, w.b), hotkeyText(tried_) + L" already does something in Windows or another program.", 13.f, ui.pal.text);
        if (ui.button(ui.id("force"), RectF(w.r - 222, w.t + 7, w.r - 96, w.b - 7), L"Use it anyway")) {
          k.hotkey = tried_;
          k.hotkey.takeOver = true;
          triedTaken_ = false;
          app_.applyHotkey();
          changed();
        }
        if (ui.button(ui.id("noforce"), RectF(w.r - 88, w.t + 7, w.r - 8, w.b - 7), L"Keep old", Btn::Subtle)) triedTaken_ = false;
        ui.tooltip(RectF(w.r - 222, w.t + 7, w.r - 96, w.b - 7), L"Installs a keyboard hook while the app runs, so your key wins");
      }
    }
  }

  section(L"One-handed ideas", L"Checked against this PC just now. All of them can be reached with the left hand.");
  {
    int cols = c_.w > 720 ? 3 : 2;
    float g = 8, w = (c_.w - g * (cols - 1)) / cols, h = 74;
    for (size_t i = 0; i < ideas_.size(); i++) {
      auto& d = ideas_[i];
      RectF r = RectF::xywh(c_.x + (float)(i % (size_t)cols) * (w + g), c_.y + (float)(i / (size_t)cols) * (h + g), w, h);
      uint32_t id = ui.id("idea", (int)i);
      Hotkey hk{d.mods, d.vk, false};
      bool on = k.hotkey.mods == d.mods && k.hotkey.vk == d.vk;
      if (d.free && ui.press(id, r) && !on) {
        k.hotkey = hk;
        triedTaken_ = false;
        app_.applyHotkey();
        ideasOk_ = false;
        changed();
      }
      bool hv = ui.hot(r) && d.free;
      if (hv) ui.cursor = LoadCursorW(nullptr, IDC_HAND);
      float a = ui.anim(id, hv ? 1.f : 0.f), s = ui.anim(id ^ 5u, on ? 1.f : 0.f);
      ui.p->rrect(r, 9, mix(ui.pal.card, ui.pal.cardHover, a));
      ui.p->rrectStroke(r.inset(0.5f), 9, ui.pal.stroke, 1);
      if (s > 0.01f) ui.p->rrectStroke(r.inset(1.f), 8.5f, ui.pal.accent.alpha(s), 2.f);
      drawKeycaps(r.l + 14, r.t + 26, hk, 27.f, d.free ? 1.f : 0.35f);
      ui.text(RectF(r.l + 14, r.t + 44, r.r - 8, r.b - 6), d.free ? d.note : L"In use on this PC", 11.5f, d.free ? ui.pal.dim : ui.pal.faint);
      V2 o{r.r - 22, r.t + 24};
      if (d.free) {
        ui.p->circle(o, 8, mix(ui.pal.control, ui.pal.accent, s));
        if (s < 0.98f) ui.p->circleStroke(o, 7.5f, ui.pal.faint.alpha(1 - s), 1.2f);
        ui.p->circle(o, 3.8f * s, ui.pal.onAccent.alpha(s));
      }
    }
    size_t rows = (ideas_.size() + (size_t)cols - 1) / (size_t)cols;
    c_.y += rows * (h + g);
  }

  section(L"How it opens");
  {
    struct O { const wchar_t* t; const wchar_t* d; };
    static const O o[] = {{L"Smart", L"Tap to keep it open and click. Or hold, flick toward an item and let go to launch it."},
                          {L"Hold and release", L"Like a weapon wheel: it closes as soon as you let go."},
                          {L"Tap to toggle", L"Stays open until you choose something or tap again."}};
    RectF r = RectF::xywh(c_.x, c_.y, c_.w, 3 * 52.f + 12);
    c_.y += r.h() + 4;
    ui.card(r, 8);
    for (int i = 0; i < 3; i++)
      if (ui.radio(ui.id("act", i), RectF(r.l + 10, r.t + 6 + i * 52.f, r.r - 10, r.t + 56 + i * 52.f), o[i].t, (int)k.activation == i, o[i].d) && (int)k.activation != i) {
        k.activation = (Activation)i;
        changed();
      }
  }

  section(L"While it is open", L"Everything works with the left hand alone.");
  {
    struct K { const wchar_t* keys[4]; const wchar_t* d; };
    static const K ks[] = {{{L"A", L"D"}, L"Turn left and right"},       {{L"W", L"S"}, L"Reach out (groups, outer ring) and back in"},
                           {{L"Space", L"F"}, L"Launch"},                {{L"Q", L"E"}, L"Previous and next profile"},
                           {{L"1", L"9"}, L"Launch by number"},          {{L"Tab"}, L"Next item, with Shift the previous one"},
                           {{L"Shift"}, L"Hold while launching to open a new window"}, {{L"Esc"}, L"Close"}};
    int n = (int)(sizeof ks / sizeof ks[0]);
    RectF r = RectF::xywh(c_.x, c_.y, c_.w, n * 34.f + 14);
    c_.y += r.h() + 4;
    ui.card(r, 8);
    for (int i = 0; i < n; i++) {
      RectF at(r.l + 16, r.t + 12 + i * 34.f, r.l + 16, r.t + 36 + i * 34.f);
      for (auto s : ks[i].keys)
        if (s) keycap(at, s, 23.f, Color(1, 1, 1, 1));
      ui.text(RectF(r.l + 150, r.t + 7 + i * 34.f, r.r - 12, r.t + 41 + i * 34.f), ks[i].d, 13.f, ui.pal.text);
    }
  }
}

// ---------------------------------------------------------------- general page
void SettingsWindow::pageGeneral(RectF) {
  Config& k = app_.cfg;
  if (nowSec() - autostartAt_ > 3.0) {
    autostart_ = autostartEnabled();
    fileMenu_ = fileMenuOn(modulePath());
    autostartAt_ = nowSec();
  }
  section(L"Startup");
  {
    RectF r = row(L"Start with Windows", L"Runs quietly in the background, ready for the shortcut", 48);
    if (ui.toggle(ui.id("auto"), r, autostart_)) {
      setAutostart(autostart_);
      autostartAt_ = nowSec();
    }
  }
  if (toggleRow("tray", L"Show the tray icon", L"Without it, start the app again to reach these settings", k.trayIcon)) app_.saveNow();

  section(L"Right-click to add", L"Puts \"Add to " RT_NAME L"\" where you already right-click.");
  toggleRow("tbmenu", L"On taskbar buttons", L"Shown right above the menu Windows opens", k.taskbarMenu);
  {
    RectF r = row(L"On files, folders and shortcuts", L"In Explorer and on the desktop, under Show more options", 48);
    if (ui.toggle(ui.id("filemenu"), r, fileMenu_)) {
      setFileMenu(fileMenu_, modulePath());
      autostartAt_ = nowSec();
    }
  }

  section(L"Websites");
  toggleRow("logos", L"Get logos for websites", L"Asks the site itself when you add it. You can always use a picture of your own", k.siteLogos);

  section(L"Launching");
  toggleRow("switch", L"Switch to a window that is already open", L"Like the taskbar. Shift-click or middle-click always opens a new one", k.switchToRunning);
  toggleRow("running", L"Mark running apps", nullptr, k.showRunning);
  toggleRow("fan", L"Extend running apps to show their windows", L"Hover an app with several windows to pick one", k.windowsFan);
  toggleRow("fs", L"Stay out of full-screen games", nullptr, k.blockFullscreen);

  section(L"Pointer");
  toggleRow("warp", L"Move the pointer to the wheel when it opens", L"One short flick then reaches every item", k.warpCursor);
  toggleRow("back", L"Put the pointer back afterwards", nullptr, k.restoreCursor);

  section(L"Resources");
  toggleRow("mem", L"Free memory when idle", L"Opening takes a moment longer after a pause", k.lowMemory);

  section(L"Your data");
  {
    RectF r = row(L"Backup", L"Pins, profiles and looks in one file", 250);
    if (ui.button(ui.id("exp"), RectF(r.l, r.t, r.l + 120, r.b), L"Export", Btn::Standard, L"\xEDE1")) {
      after([this] {
        std::wstring f = pickSave(hwnd_, L"Export settings", L"radial-taskbar.json");
        if (f.empty()) return;
        flash_ = writeFileAtomic(f, app_.cfg.exportText()) ? L"Exported" : L"Could not write that file";
        flashAt_ = nowSec();
      });
    }
    if (ui.button(ui.id("imp"), RectF(r.l + 130, r.t, r.r, r.b), L"Import", Btn::Standard, L"\xE8B5")) {
      after([this] {
        std::wstring f = pickFile(hwnd_, L"Import settings", false, L"JSON", L"*.json");
        if (f.empty()) return;
        std::string text;
        int profiles = 0, pins = 0;
        flashAt_ = nowSec();
        if (!readFile(f, text) || !Config::checkBackup(text, profiles, pins)) {
          flash_ = L"That file is not a Radial Taskbar backup";
          return;
        }
        std::wstring q = L"Replace your current pins, profiles and looks with this backup?\n\nIt holds " + std::to_wstring(profiles) + (profiles == 1 ? L" profile and " : L" profiles and ") +
                         std::to_wstring(pins) + (pins == 1 ? L" pin." : L" pins.") + L" Your current settings are kept beside it as config.json.before-import.";
        if (MessageBoxW(hwnd_, q.c_str(), L"Import settings", MB_OKCANCEL | MB_ICONQUESTION | MB_DEFBUTTON2) != IDOK) return;
        flash_ = app_.cfg.importText(text) ? L"Imported" : L"Could not read that backup";
        flashAt_ = nowSec();
        selected_.clear();
        forgetMatches();
        app_.applyHotkey();
        changed(true);
      });
    }
  }
  {
    RectF r = row(L"Settings folder", nullptr, 120);
    if (ui.button(ui.id("folder"), r, L"Open", Btn::Standard, L"\xE838")) {
      Pin p;
      p.kind = Pin::Kind::File;
      p.target = dataDir();
      launchPin(p);
    }
  }
  {
    RectF r = row(L"Reset look and layout", L"Keeps your pins and profiles", 120);
    if (ui.button(ui.id("reset"), r, L"Reset", Btn::Danger)) {
      after([this] {
        if (MessageBoxW(hwnd_, L"Reset the look, layout, effects and behaviour to their defaults?\nYour pins, profiles, saved styles and added skins stay.", L"Reset", MB_OKCANCEL | MB_ICONQUESTION | MB_DEFBUTTON2) != IDOK) return;
        Config d;
        d.profiles = app_.cfg.profiles;
        d.activeProfile = app_.cfg.activeProfile;
        d.customLooks = app_.cfg.customLooks;
        d.hotkey = app_.cfg.hotkey;
        d.firstRun = false;
        app_.cfg = d;
        app_.cfg.sanitize();
        changed(true);
      });
    }
  }
}

}  // namespace rt
