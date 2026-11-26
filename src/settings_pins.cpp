// Settings: the Pins page (profiles, ordering, groups, adding and editing).
#include <process.h>

#include "app.h"
#include "picture.h"
#include "settings.h"
#include "sitelogo.h"

namespace rt {

namespace {
constexpr float kRowH = 46.f;

unsigned __stdcall appsThread(void* arg) {
  CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED | COINIT_DISABLE_OLE1DDE);
  auto* list = new std::vector<AppEntry>(enumInstalledApps());
  if (!PostMessageW((HWND)arg, WM_APP_APPS, 0, (LPARAM)list)) delete list;
  CoUninitialize();
  return 0;
}

Color tile(const std::wstring& name) {
  uint32_t h = 2166136261u;
  for (wchar_t c : name) h = (h ^ (uint32_t)c) * 16777619u;
  return fromHsv({(h % 360) / 360.f, 0.55f, 0.82f});
}

const uint32_t kProfileColors[] = {0x4CA8FF, 0xFF8A4C, 0x35D6A0, 0xC58BFF, 0xFFD24C, 0xFF6B9A, 0x5CE1E6, 0x9BE15D};
}  // namespace

// ---------------------------------------------------------------- data
void SettingsWindow::ensureApps() {
  if (appsLoaded_ || appsLoading_ || headless_) return;
  appsLoading_ = true;
  uintptr_t t = _beginthreadex(nullptr, 0, appsThread, app_.hiddenWindow(), 0, nullptr);
  if (t) CloseHandle((HANDLE)t);
  else appsLoading_ = false;
}

void SettingsWindow::appsReady(void* list) {
  std::unique_ptr<std::vector<AppEntry>> p((std::vector<AppEntry>*)list);
  apps_ = std::move(*p);
  appsLoaded_ = true;
  appsLoading_ = false;
  foundFor_ = L"\x01";
  invalidate();
}

void SettingsWindow::loadAppsNow() {
  apps_ = enumInstalledApps();
  appsLoaded_ = true;
}

void SettingsWindow::selectFirstPin(bool group) {
  for (auto& p : app_.cfg.profile().pins) {
    if ((p.kind == Pin::Kind::Group) == group) {
      selected_ = p.id;
      expanded_[p.id] = true;
      return;
    }
  }
}

void SettingsWindow::selectUrl() {
  for (auto& p : app_.cfg.profile().pins)
    if (p.kind == Pin::Kind::Url) selected_ = p.id;
}

void SettingsWindow::openUrlForm(const std::wstring& url, const std::wstring& picture) {
  addingUrl_ = true;
  newDraft();
  urlBuf_ = url;
  draft_.icon = picture;
}

void SettingsWindow::newDraft() {
  dropDraft();
  urlBuf_.clear();
  urlName_.clear();
  draft_.id = "draft-" + newId();
  draft_.kind = Pin::Kind::Url;
}

void SettingsWindow::dropDraft() {
  if (!draft_.id.empty()) app_.cancelLogo(draft_.id);
  draft_ = {};
}

bool SettingsWindow::appPinned(const AppEntry& a) {
  if (pinnedRev_ != rev_ || pinnedTargets_.empty()) {
    pinnedRev_ = rev_;
    pinnedMatch_.clear();
    pinnedTargets_.assign(1, L"\x01");
    auto take = [&](const Pin& p) {
      if (p.kind == Pin::Kind::App) pinnedTargets_.push_back(toLower(p.target));
      if (p.kind == Pin::Kind::File) pinnedMatch_.push_back(resolveMatch(p));
    };
    for (auto& p : app_.cfg.profile().pins) {
      take(p);
      for (auto& c : p.children) take(c);
    }
  }
  std::wstring id = toLower(a.aumid), exe = toLower(a.exe);
  for (auto& t : pinnedTargets_)
    if (t == id) return true;
  for (auto& m : pinnedMatch_) {
    if (!m.aumid.empty() && m.aumid == id) return true;
    if (!m.exe.empty() && m.exe == exe) return true;
  }
  return false;
}

void SettingsWindow::addPins(std::vector<Pin> list) {
  int n = 0, movedIn = 0, there = 0;
  std::wstring last, groupName;
  for (auto& p : list) {
    std::wstring nm = p.name;
    auto& pins = app_.cfg.profile().pins;
    // New items go into the group being edited, if any.
    Pin* sel = selected_.empty() ? nullptr : findPin(pins, selected_);
    if (sel && sel->kind == Pin::Kind::Group && p.kind != Pin::Kind::Group) {
      std::string gid = sel->id;
      groupName = sel->name;
      if (alreadyPinned(sel->children, p)) {
        there++;
        continue;
      }
      // Somewhere else in this profile already: it moves in rather than being there twice.
      if (std::string other = pinnedId(pins, p); !other.empty()) {
        Pin moved;
        if (removePin(pins, other, &moved))
          if (Pin* g = findPin(pins, gid)) {
            g->children.push_back(std::move(moved));
            expanded_[gid] = true;
            movedIn++;
            n++;
            last = nm;
          }
        continue;
      }
      adoptPin(p);
      Pin copy = p;
      sel->children.push_back(std::move(p));
      expanded_[gid] = true;
      app_.wantLogo(copy);
      n++;
      last = nm;
    } else if (app_.addPin(std::move(p), true)) {
      n++;
      last = nm;
    }
  }
  if (n == 0) say(there ? L"Already in " + groupName : list.size() == 1 ? L"Already pinned" : L"Nothing new to add");
  else if (n == 1 && movedIn) say(L"Moved " + last + L" into " + groupName);
  else if (n == 1) say(groupName.empty() ? L"Added " + last : L"Added " + last + L" to " + groupName);
  else say(L"Added " + std::to_wstring(n) + L" items");
  changed(true);
}

void SettingsWindow::say(const std::wstring& line) {
  flash_ = line;
  flashAt_ = nowSec();
  invalidate();
}

void SettingsWindow::onDrop(const DropData& d, V2 at) {
  std::vector<std::wstring> skinFiles;
  auto isSkin = [](const std::wstring& f) { return fileExt(f) == L".rskin" || fileExists(joinPath(f, L"skin.json")); };
  for (auto& f : d.files)
    if (isSkin(f)) skinFiles.push_back(f);
  if (!skinFiles.empty()) {
    addSkins(skinFiles, false);
    if (skinFiles.size() == d.files.size()) return;
  }
  bool files = !d.files.empty(), here = page_ == kPins && !pictureFor_.empty() && pictureZone_.contains(at);
  // What is dropped on the open editor is meant for that item.
  if (here) {
    const std::string id = pictureFor_;
    std::string bytes;
    if (d.files.size() == 1 && isPictureFile(d.files[0])) {
      if (readFile(d.files[0], bytes)) takePicture(id, bytes, fileStem(d.files[0]));
      else say(L"That file could not be read");
      return;
    }
    if (!d.picture.empty()) {
      takePicture(id, d.picture, d.pictureName);
      return;
    }
    if (!files && !d.url.empty()) {
      Pin* p = pinById(id);
      if (p && isPictureFile(d.url.substr(0, d.url.find_first_of(L"?#")))) {
        app_.cancelLogo(id);
        app_.fetchLogo(id, d.url, p->icon, true);
      } else if (isDraft(id)) {  // an address for the website being added
        urlBuf_ = d.url;
        if (trim(urlName_).empty()) urlName_ = d.title;
      } else {
        say(L"That is not a picture");
      }
      return;
    }
  }
  std::vector<Pin> list;
  for (auto& f : d.files)
    if (!isSkin(f)) list.push_back(pinFromPath(f));
  if (!files && !d.url.empty() && d.picture.empty()) list.push_back(pinFromUrl(d.url, d.title));  // a link from a browser
  if (list.empty()) {
    say(L"Open an item first, then drop the picture on it");
    return;
  }
  page_ = kPins;
  addPins(std::move(list));
}

void SettingsWindow::drawPinIcon(const Pin& pin, V2 c, float size, float alpha) {
  float h = size * 0.5f;
  RectF r(c.x - h, c.y - h, c.x + h, c.y + h);
  if (pin.kind == Pin::Kind::Group && pin.icon.empty()) {
    ui.p->rrect(r, size * 0.26f, ui.pal.text.withA(0.09f * alpha));
    ui.p->rrectStroke(r.inset(0.5f), size * 0.26f, ui.pal.strokeStrong.alpha(alpha), 1);
    float q = size * 0.34f, o = size * 0.205f;
    for (size_t i = 0; i < std::min<size_t>(4, pin.children.size()); i++)
      drawPinIcon(pin.children[i], {c.x + ((i % 2) ? o : -o), c.y + ((i / 2) ? o : -o)}, q, alpha);
    if (pin.children.empty()) ui.glyph(r, L"\xE8B7", size * 0.45f, ui.pal.dim.alpha(alpha));
    return;
  }
  D2D1_RECT_F crop{};
  std::wstring key = IconCache::keyFor(pin);
  if (auto* b = icons().get(key, IconTone::Original, Color(), &crop)) {
    ui.p->bitmap(b, r, alpha, &crop);
    return;
  }
  if (!key.empty() && !icons().failed(key)) return;
  Color t = tile(pin.name);
  ui.p->rrect(r, size * 0.26f, t.withA(alpha));
  std::wstring ch = pin.name.empty() ? L"?" : pin.name.substr(0, 1);
  CharUpperBuffW(ch.data(), 1);
  ui.text(r, ch, size * 0.5f, Color(1, 1, 1, alpha), 600, Align::Center);
}

// ---------------------------------------------------------------- pictures
void SettingsWindow::spinner(V2 c, float r) {
  float t = (float)fmod(nowSec(), 60.0) * 5.2f;
  auto g = arcGeo(c, r, t, t + 1.9f + 1.1f * sinf(t * 0.6f));
  ui.p->stroke(g.Get(), ui.pal.accent, std::max(1.6f, r * 0.16f), true);
  ui.animating = true;
}

void SettingsWindow::takePicture(const std::string& id, const std::string& bytes, const std::wstring& name) {
  Pin* p = pinById(id);
  if (!p) return;
  std::wstring stored = keepPicture(bytes, name);
  if (stored.empty()) {
    say(L"That picture could not be read");
    return;
  }
  app_.cancelLogo(id);  // this is the one that was wanted
  p->icon = stored;
  say(L"Picture set");
  if (!isDraft(id)) changed(true);
}

void SettingsWindow::choosePicture(const std::string& id) {
  std::wstring f = pickFile(hwnd_, L"Choose a picture or an icon", false, L"Pictures, icons and programs", kPictureFilter);
  Pin* p = f.empty() ? nullptr : pinById(id);
  if (!p) return;
  if (isPictureFile(f)) {
    std::string bytes;
    if (!readFile(f, bytes)) say(L"That file could not be read");
    else takePicture(id, bytes, fileStem(f));
    return;
  }
  app_.cancelLogo(id);
  p->icon = f;  // the icon inside a program stays where it is
  if (isDraft(id)) invalidate();
  else changed(true);
}

void SettingsWindow::pastePicture(const std::string& id) {
  std::string bytes;
  std::wstring link;
  if (!pinById(id)) return;
  bool got = clipboardPicture(hwnd_, bytes, link);
  Pin* p = pinById(id);  // looked up afterwards: reading the clipboard can run other programs' code
  if (!p) return;
  if (!got) {
    say(L"Copy a picture first, then paste it here");
  } else if (!bytes.empty()) {
    takePicture(id, bytes, p->name.empty() ? L"picture" : p->name);
  } else {
    app_.cancelLogo(id);
    app_.fetchLogo(id, link, p->icon, true);
  }
}

void SettingsWindow::askForLogo(const std::string& id) {
  Pin* p = pinById(id);
  if (!p) return;
  std::wstring url = isDraft(id) ? pinFromUrl(urlBuf_).target : p->target;
  if (isWebAddress(url) && siteHost(url).size() > 1) app_.fetchLogo(id, url, p->icon);
  else say(isDraft(id) ? L"Type the address of the site first" : L"Only web addresses have a logo to get");
}

// True when the answer was for the website being typed in, which is not in the settings yet.
bool SettingsWindow::logoArrived(const LogoAsk& ask, const std::wstring& image, const std::wstring& name) {
  invalidate();
  Pin* p = pinById(ask.pin);
  bool draft = isDraft(ask.pin);
  bool current = p && (!draft || ask.isImage || ask.url == pinFromUrl(urlBuf_).target);  // the address may be another one by now
  if (image.empty() && current) say(ask.isImage ? L"There is no picture at that address" : L"That site did not offer a logo. Add a picture instead");
  if (!draft) {
    if (!image.empty()) rev_++;
    return false;
  }
  if (current) {
    if (!image.empty() && p->icon == ask.was) p->icon = image;
    if (trim(urlName_).empty() && !ask.isImage) urlName_ = name;
  }
  return true;
}

// The picture itself: click to choose one, the little cross to go back to the original icon.
void SettingsWindow::pictureWell(RectF well, const Pin& pin) {
  const std::string id = pin.id;
  bool url = pin.kind == Pin::Kind::Url, busy = app_.logoBusy(id), has = !pin.icon.empty();
  uint32_t wid = ui.id("picwell");
  RectF del = RectF::xywh(well.r - 15, well.t - 7, 22, 22);
  bool onDel = (has || busy) && ui.hot(del);
  bool h = ui.hot(well) && !onDel;
  float a = ui.anim(wid, h ? 1.f : 0.f);
  if (h) ui.cursor = LoadCursorW(nullptr, IDC_HAND);
  ui.p->rrect(well, 12, mix(ui.pal.control, ui.pal.controlHover, a));
  ui.p->rrectStroke(well.inset(0.5f), 12, mix(ui.pal.strokeStrong, ui.pal.accent, a * 0.7f), 1);
  float da0 = ui.anim(wid ^ 7u, dragOver_ && pictureZone_.contains(dragAt_) ? 1.f : 0.f);
  if (da0 > 0.01f) ui.p->rrectStroke(well.inset(-2.f), 14, ui.pal.accent.alpha(da0), 2.f);
  if (busy) spinner(well.center(), 18);
  else drawPinIcon(pin, well.center(), 50);
  if (!onDel && ui.press(wid, well) && !busy) after([this, id] { choosePicture(id); });
  if (has || busy) {
    uint32_t did = ui.id("picdel");
    float da = ui.anim(did, onDel ? 1.f : 0.f);
    ui.p->circle(del.center(), 10, mix(ui.pal.popup, ui.pal.danger, da));
    ui.p->circleStroke(del.center(), 9.5f, ui.pal.strokeStrong, 1);
    ui.glyph(del, L"\xE711", 8.5f, mix(ui.pal.dim, ui.pal.dark ? Color(0, 0, 0) : Color(1, 1, 1), da));
    if (onDel) ui.cursor = LoadCursorW(nullptr, IDC_HAND);
    ui.tooltip(del, busy ? L"Stop looking" : url ? L"Remove the picture" : L"Back to the original icon");
    if (ui.press(did, del)) after([this, id, busy] {
      Pin* p = pinById(id);
      if (busy) app_.cancelLogo(id);
      if (busy || !p) return;
      p->icon.clear();
      p->iconShape = PicShape::Auto;
      if (!isDraft(id)) changed(true);
    });
  }
}

// The picture of an item with every way to change it: choose, paste, drop, or the website's own logo.
float SettingsWindow::picturePanel(float x, float y, float w, const Pin& pin) {
  const std::string id = pin.id;
  bool draft = isDraft(id), url = pin.kind == Pin::Kind::Url, busy = app_.logoBusy(id), has = !pin.icon.empty();
  ui.text(RectF(x, y, x + w, y + 18), L"Picture", 12.f, ui.pal.dim, 600);
  y += 20;
  RectF well = RectF::xywh(x, y, 72, 72);
  pictureWell(well, pin);
  float bx = well.r + 14, bw = x + w - bx;
  int n = url ? 3 : 2;
  float one = (bw - 6.f * (n - 1)) / n;
  struct B { const wchar_t* g; const wchar_t* t; };
  static const B bs[] = {{L"\xEB9F", L"Choose"}, {L"\xE77F", L"Paste"}, {L"\xE774", L"From site"}};
  for (int i = 0; i < n; i++) {
    RectF b = RectF::xywh(bx + i * (one + 6), y, one, 34);
    bool icon = one > 92.f;
    static const wchar_t* tips[] = {L"A picture, an icon or a program", L"A picture you copied, or its address (Ctrl+V)", L"Get the logo and name from the website"};
    ui.tooltip(b, tips[i]);
    if (ui.button(ui.id("picb", i), b, bs[i].t, Btn::Standard, icon ? bs[i].g : nullptr, !busy)) {
      after([this, id, i] {
        if (i == 0) choosePicture(id);
        else if (i == 1) pastePicture(id);
        else askForLogo(id);
      });
    }
  }
  RectF low = RectF::xywh(bx, y + 41, bw, 31);
  if (has && !busy) {
    int s = (int)pin.iconShape;
    if (ui.segmented(ui.id("picshape"), low, s, {L"Auto", L"As is", L"Tile", L"Circle"})) after([this, id, s] {
      Pin* p = pinById(id);
      if (!p) return;
      p->iconShape = (PicShape)s;
      if (!isDraft(id)) changed(true);
    });
  } else {
    const wchar_t* t = busy ? L"Looking for the logo..." : url && draft && app_.cfg.siteLogos ? L"Leave it empty to use the site's own logo." : L"Or drop a picture here, or press Ctrl+V.";
    ui.text(low, t, 12.f, ui.pal.dim, 400, Align::Left, VAlign::Middle, true);
  }
  return 20 + 72 + 10;
}

// ---------------------------------------------------------------- page
void SettingsWindow::pagePins(RectF r) {
  pictureFor_.clear();
  float barBottom = profileBar(RectF(r.l, r.t, r.r - 8, r.t + 38));
  RectF body(r.l, barBottom + 12, r.r - 8, r.b);
  float rw = clampf(body.w() * 0.43f, 330.f, 460.f);
  RectF left(body.l, body.t, body.r - rw - 14, body.b), right(body.r - rw, body.t, body.r, body.b);
  pinList(left);
  Pin* sel = selected_.empty() ? nullptr : findPin(app_.cfg.profile().pins, selected_);
  if (sel) editPanel(right, *sel);
  else addPanel(right);
  if (!pictureFor_.empty() && !ui.anyFocus()) {
    for (auto& k : ui.keys)
      if (k.vk == 'V' && k.ctrl) after([this, id = pictureFor_] { pastePicture(id); });
  }
}

// The profiles wrap onto more lines when there are many; the tools for the one in use stay at the right.
float SettingsWindow::profileBar(RectF r) {
  Config& k = app_.cfg;
  const float lineH = 34.f, step = 42.f, top = r.t + 2;
  int i = k.activeProfile, n = (int)k.profiles.size();
  bool locked = k.profile().locked, onlyOpen = !locked && k.unlockedCount() < 2;  // the wheel needs one
  float bx = r.r - 34;
  auto tool = [&](const char* key, const wchar_t* g, const wchar_t* tip, bool en) {
    RectF b(bx, top + 1, bx + 32, top + lineH - 1);
    bx -= 34;
    return ui.iconButton(ui.id(key), b, g, tip, en);
  };
  if (tool("pdel", L"\xE74D", onlyOpen && n > 1 ? L"The wheel needs one profile that is not locked" : L"Delete profile", n > 1 && !onlyOpen))
    after([this] { removeProfile(app_.cfg.activeProfile); });
  if (tool("pright", L"\xE76C", L"Move right", i + 1 < n)) {
    std::swap(k.profiles[(size_t)i], k.profiles[(size_t)i + 1]);
    k.activeProfile++;
    changed(true);
  }
  if (tool("pleft", L"\xE76B", L"Move left", i > 0)) {
    std::swap(k.profiles[(size_t)i], k.profiles[(size_t)i - 1]);
    k.activeProfile--;
    changed(true);
  }
  if (tool("pcopy", L"\xE8C8", L"Duplicate profile", true)) {
    Profile q = k.profile();
    q.id = newId();
    q.name += L" copy";
    for (auto& p : q.pins) {
      p.id = newId();
      for (auto& c : p.children) c.id = newId();
    }
    k.profiles.insert(k.profiles.begin() + i + 1, q);
    k.activeProfile = i + 1;
    changed(true);
  }
  if (locked) ui.p->rrect(RectF(bx, top + 1, bx + 32, top + lineH - 1), 6, ui.pal.accent.withA(0.16f));
  if (tool("plock", locked ? L"\xE72E" : L"\xE785",
           locked ? L"Locked: the wheel skips it. Click to unlock" : onlyOpen ? L"The wheel needs one profile that is not locked" : L"Lock: keep it off the wheel until you unlock it", locked || !onlyOpen))
    setLocked(i, !locked);
  if (tool("pname", L"\xE8AC", L"Rename profile", true)) {
    naming_ = i;
    nameBuf_ = k.profile().name;
    ui.focusOn(ui.id("profname"));
  }
  Color col = k.profile().color;
  RectF cb(bx + 2, top + 5, bx + 28, top + lineH - 5);
  if (ui.colorBox(ui.id("pcol", i), cb, col)) {
    k.profile().color = col;
    changed();
  }
  ui.tooltip(cb, L"Profile colour");
  float maxX = bx - 6;

  float x = r.l, y = top;
  auto place = [&](float w) {
    if (x + w > maxX && x > r.l) {
      x = r.l;
      y += step;
    }
    RectF c(x, y, x + w, y + lineH);
    x = c.r + 8;
    return c;
  };
  tabRects_.clear();
  for (int j = 0; j < n; j++) {
    Profile& p = k.profiles[(size_t)j];
    if (naming_ == j) {
      bool enter = false;
      RectF t = place(150);
      uint32_t id = ui.id("profname");
      ui.textBox(id, t, nameBuf_, L"Profile name", nullptr, &enter);
      if (enter || !ui.focused(id)) {
        std::wstring nm = trim(nameBuf_);
        if (!nm.empty() && nm != p.name) {
          p.name = nm;
          changed();
        }
        naming_ = -1;
        ui.clearFocus();
      }
      continue;
    }
    float w = std::min(206.f, ui.textWidth(p.name, 13.5f, 600) + 44 + (p.locked ? 16 : 0));
    RectF c = place(w);
    tabRects_.push_back({c, j});
    uint32_t id = ui.id("prof", j);
    bool on = j == k.activeProfile;
    if (ui.hot(c) && ui.pressed && ui.dbl) {
      naming_ = j;
      nameBuf_ = p.name;
      ui.focusOn(ui.id("profname"));
    } else if (ui.press(id, c) && !on) {
      k.activeProfile = j;
      selected_.clear();
      changed(true);
    }
    bool h = ui.hot(c);
    if (h) ui.cursor = LoadCursorW(nullptr, IDC_HAND);
    if (h && ui.rightPressed) after([this, j] { profileMenu(j); });
    float a = ui.anim(id, on ? 1.f : (h ? 0.5f : 0.f));
    ui.p->rrect(c, 17, mix(ui.pal.card, ui.pal.cardHover, a));
    ui.p->rrectStroke(c.inset(0.5f), 16.5f, on ? p.color : ui.pal.stroke, on ? 1.8f : 1.f);
    ui.p->circle({c.l + 18, c.cy()}, 5, p.locked ? p.color.withA(0.45f) : p.color);
    float tr = c.r - 8 - (p.locked ? 16 : 0);
    ui.text(RectF(c.l + 31, c.t - 0.5f, tr, c.b), p.name, 13.5f, on ? ui.pal.text : ui.pal.dim, on ? 600 : 400);
    if (p.locked) {
      ui.glyph(RectF(tr - 1, c.t, tr + 15, c.b), L"\xE72E", 11.f, ui.pal.dim);
      ui.tooltip(c, L"Locked: the wheel skips this profile");
    }
  }
  RectF add = place(32);
  if (ui.iconButton(ui.id("profadd"), RectF(add.l, add.t + 1, add.r, add.b - 1), L"\xE710", L"New profile")) {
    Profile p;
    p.id = newId();
    p.name = L"Profile " + std::to_wstring(k.profiles.size() + 1);
    p.color = Color::hex(kProfileColors[k.profiles.size() % 8]);
    k.profiles.push_back(p);
    k.activeProfile = (int)k.profiles.size() - 1;
    naming_ = k.activeProfile;
    nameBuf_ = p.name;
    ui.focusOn(ui.id("profname"));
    selected_.clear();
    changed(true);
  }
  return y + lineH;
}

void SettingsWindow::setLocked(int index, bool on) {
  Config& k = app_.cfg;
  if (index < 0 || index >= (int)k.profiles.size()) return;
  Profile& p = k.profiles[(size_t)index];
  if (p.locked == on) return;
  if (on && k.unlockedCount() < 2) {
    say(L"The wheel needs one profile that is not locked");
    return;
  }
  p.locked = on;
  say(on ? L"Locked " + p.name + L": the wheel skips it" : p.name + L" is back on the wheel");
  changed(true);
}

void SettingsWindow::profileMenu(int index) {
  Config& k = app_.cfg;
  if (index < 0 || index >= (int)k.profiles.size()) return;
  std::string id = k.profiles[(size_t)index].id;
  bool locked = k.profiles[(size_t)index].locked, onlyOpen = !locked && k.unlockedCount() < 2;
  HMENU m = CreatePopupMenu();
  AppendMenuW(m, MF_STRING, 1, L"Rename");
  AppendMenuW(m, MF_STRING | (onlyOpen ? MF_GRAYED : 0), 3, locked ? L"Unlock: show it on the wheel" : L"Lock: keep it off the wheel");
  AppendMenuW(m, MF_STRING | (k.profiles.size() > 1 && !onlyOpen ? 0 : MF_GRAYED), 2, L"Delete");
  POINT p;
  GetCursorPos(&p);
  UINT cmd = (UINT)TrackPopupMenuEx(m, TPM_RETURNCMD, p.x, p.y, hwnd_, nullptr);
  DestroyMenu(m);
  // The list may have changed while the menu was up.
  for (int i = 0; i < (int)k.profiles.size(); i++) {
    if (k.profiles[(size_t)i].id != id) continue;
    if (cmd == 1) {
      naming_ = i;
      nameBuf_ = k.profiles[(size_t)i].name;
      ui.focusOn(ui.id("profname"));
    } else if (cmd == 2) {
      removeProfile(i);
    } else if (cmd == 3) {
      setLocked(i, !k.profiles[(size_t)i].locked);
    }
    return;
  }
}

void SettingsWindow::removeProfile(int index) {
  Config& k = app_.cfg;
  if (k.profiles.size() < 2 || index < 0 || index >= (int)k.profiles.size()) return;
  if (!k.profiles[(size_t)index].locked && k.unlockedCount() < 2) {
    say(L"The wheel needs one profile that is not locked");
    return;
  }
  std::string id = k.profiles[(size_t)index].id;
  size_t n = k.profiles[(size_t)index].pins.size();
  std::wstring q = L"Delete \"" + k.profiles[(size_t)index].name + L"\" and its " + std::to_wstring(n) + (n == 1 ? L" pin?" : L" pins?");
  if (MessageBoxW(hwnd_, q.c_str(), L"Delete profile", MB_OKCANCEL | MB_ICONQUESTION | MB_DEFBUTTON2) != IDOK) return;
  for (int i = 0; i < (int)k.profiles.size(); i++) {
    if (k.profiles[(size_t)i].id != id || k.profiles.size() < 2) continue;
    k.profiles.erase(k.profiles.begin() + i);
    if (i < k.activeProfile) k.activeProfile--;
    k.activeProfile = clampi(k.activeProfile, 0, (int)k.profiles.size() - 1);
    naming_ = -1;
    selected_.clear();
    changed(true);
    return;
  }
}

Pin* SettingsWindow::pinById(const std::string& id) {
  if (isDraft(id)) return addingUrl_ && draft_.id == id ? &draft_ : nullptr;
  for (auto& p : app_.cfg.profiles)
    if (Pin* q = findPin(p.pins, id)) return q;
  return nullptr;
}

// To another profile, at the end. A copy gets ids of its own; pictures are shared, they are kept while anything uses them.
void SettingsWindow::movePin(const std::string& id, int to, bool copy) {
  Config& k = app_.cfg;
  if (to < 0 || to >= (int)k.profiles.size() || to == k.activeProfile) return;
  auto& pins = k.profile().pins;
  Pin* p = findPin(pins, id);
  if (!p) return;
  Profile& dest = k.profiles[(size_t)to];
  std::wstring name = p->name;
  bool there = p->kind != Pin::Kind::Group && alreadyPinned(dest.pins, *p);
  if (copy) {
    if (there) {
      say(dest.name + L" has " + name + L" already");
      return;
    }
    Pin c = *p;
    c.id = newId();
    for (auto& ch : c.children) ch.id = newId();
    dest.pins.push_back(std::move(c));
    say(L"Copied " + name + L" to " + dest.name);
  } else {
    Pin moved;
    if (!removePin(pins, id, &moved)) return;
    if (!there) dest.pins.push_back(std::move(moved));
    if (selected_ == id) selected_.clear();
    say(there ? dest.name + L" has " + name + L" already: it is gone from here" : L"Moved " + name + L" to " + dest.name);
  }
  changed(true);
}

void SettingsWindow::moveIntoGroup(const std::string& id, const std::string& group) {
  auto& pins = app_.cfg.profile().pins;
  Pin moved;
  if (id == group || !findPin(pins, group) || !removePin(pins, id, &moved)) return;
  Pin* g = findPin(pins, group);
  if (!g) {
    pins.push_back(std::move(moved));
    return;
  }
  std::wstring name = moved.name;
  g->children.push_back(std::move(moved));
  expanded_[group] = true;
  say(L"Moved " + name + L" into " + g->name);
  changed(true);
}

void SettingsWindow::pinMenu(const std::string& id) {
  Config& k = app_.cfg;
  auto& pins = k.profile().pins;
  Pin* p = findPin(pins, id);
  if (!p) return;
  bool grp = p->kind == Pin::Kind::Group;
  std::string parent;
  for (auto& q : pins)
    for (auto& c : q.children)
      if (c.id == id) parent = q.id;
  enum : UINT { kEdit = 1, kOut, kRemove, kMove0 = 100, kCopy0 = 400, kGroup0 = 700 };
  HMENU m = CreatePopupMenu();
  AppendMenuW(m, MF_STRING, kEdit, grp ? L"Edit group" : L"Edit");
  SetMenuDefaultItem(m, kEdit, FALSE);
  std::vector<std::string> groups;
  if (!grp) {
    HMENU g = CreatePopupMenu();
    for (auto& q : pins)
      if (q.kind == Pin::Kind::Group && q.id != parent && groups.size() < 250) {
        AppendMenuW(g, MF_STRING, kGroup0 + (UINT)groups.size(), q.name.c_str());
        groups.push_back(q.id);
      }
    if (groups.empty()) DestroyMenu(g);
    else AppendMenuW(m, MF_POPUP, (UINT_PTR)g, L"Move into group");
    if (!parent.empty()) AppendMenuW(m, MF_STRING, kOut, L"Take out of the group");
  }
  if (k.profiles.size() > 1) {
    HMENU mv = CreatePopupMenu(), cp = CreatePopupMenu();
    for (size_t i = 0; i < k.profiles.size() && i < 250; i++) {
      if ((int)i == k.activeProfile) continue;
      std::wstring n = k.profiles[i].name + (k.profiles[i].locked ? L"  (locked)" : L"");
      AppendMenuW(mv, MF_STRING, kMove0 + (UINT)i, n.c_str());
      AppendMenuW(cp, MF_STRING, kCopy0 + (UINT)i, n.c_str());
    }
    AppendMenuW(m, MF_POPUP, (UINT_PTR)mv, L"Move to profile");
    AppendMenuW(m, MF_POPUP, (UINT_PTR)cp, L"Copy to profile");
  }
  AppendMenuW(m, MF_SEPARATOR, 0, nullptr);
  AppendMenuW(m, MF_STRING, kRemove, grp ? L"Remove group" : L"Unpin");
  POINT pt;
  GetCursorPos(&pt);
  UINT cmd = (UINT)TrackPopupMenuEx(m, TPM_RETURNCMD | TPM_RIGHTBUTTON, pt.x, pt.y, hwnd_, nullptr);
  DestroyMenu(m);
  if (!findPin(app_.cfg.profile().pins, id)) return;  // gone, or another profile, while the menu was up
  if (cmd == kEdit) {
    selected_ = id;
    if (grp) expanded_[id] = true;
  } else if (cmd == kOut) {
    auto& v = app_.cfg.profile().pins;
    Pin moved;
    if (removePin(v, id, &moved)) {
      size_t at = v.size();
      for (size_t i = 0; i < v.size(); i++)
        if (v[i].id == parent) at = i + 1;
      v.insert(v.begin() + (ptrdiff_t)at, std::move(moved));
      changed(true);
    }
  } else if (cmd == kRemove) {
    removeAsking(id);
  } else if (cmd >= kGroup0 && cmd - kGroup0 < groups.size()) {
    moveIntoGroup(id, groups[cmd - kGroup0]);
  } else if (cmd >= kCopy0 && cmd < kGroup0) {
    movePin(id, (int)(cmd - kCopy0), true);
  } else if (cmd >= kMove0 && cmd < kCopy0) {
    movePin(id, (int)(cmd - kMove0), false);
  }
  invalidate();
}

// Removing a group takes its items along, so say so first.
void SettingsWindow::removeAsking(const std::string& id) {
  after([this, id] {
    Pin* p = pinById(id);
    if (!p) return;
    if (p->kind == Pin::Kind::Group && !p->children.empty()) {
      size_t n = p->children.size();
      std::wstring q = L"Remove \"" + p->name + L"\" and the " + std::to_wstring(n) + (n == 1 ? L" item" : L" items") + L" in it?\n\nTo keep the items, cancel and use Ungroup instead.";
      if (MessageBoxW(hwnd_, q.c_str(), L"Remove group", MB_OKCANCEL | MB_ICONQUESTION | MB_DEFBUTTON2) != IDOK) return;
    }
    for (auto& pr : app_.cfg.profiles)
      if (removePin(pr.pins, id)) break;
    if (selected_ == id) selected_.clear();
    changed(true);
  });
}

// ---------------------------------------------------------------- list
void SettingsWindow::pinList(RectF r) {
  auto& pins = app_.cfg.profile().pins;
  ui.card(r, 10);
  RectF in(r.l + 6, r.t + 6, r.r - 4, r.b - 6);

  struct Row { int top, kid; };  // kid -1: the top-level row, -2: placeholder inside an empty group
  std::vector<Row> rows;
  for (int i = 0; i < (int)pins.size(); i++) {
    rows.push_back({i, -1});
    if (pins[(size_t)i].kind == Pin::Kind::Group && expanded_[pins[(size_t)i].id]) {
      for (int c = 0; c < (int)pins[(size_t)i].children.size(); c++) rows.push_back({i, c});
      if (pins[(size_t)i].children.empty()) rows.push_back({i, -2});
    }
  }
  if (rows.empty()) {
    ui.glyph(RectF(r.l, r.cy() - 70, r.r, r.cy() - 20), L"\xE718", 34, ui.pal.faint);
    ui.text(RectF(r.l + 20, r.cy() - 14, r.r - 20, r.cy() + 10), L"This profile is empty", 15, ui.pal.text, 600, Align::Center);
    ui.text(RectF(r.l + 30, r.cy() + 10, r.r - 30, r.cy() + 60), L"Pick apps on the right, or drop files and shortcuts here.", 13, ui.pal.dim, 400, Align::Center, VAlign::Top, true);
    return;
  }

  // where a dragged row would land
  struct Target { bool ok = false, into = false; int top = 0, kid = 0; float lineY = 0; int hiRow = -1; } tg;
  bool dragGroup = false;
  if (dragging_)
    if (Pin* d = findPin(pins, dragId_)) dragGroup = d->kind == Pin::Kind::Group;

  uint32_t sid = ui.id("pinlist");
  if (dragging_) {  // scroll while dragging near the ends
    float edge = 36;
    if (ui.mouse.y < in.t + edge && ui.mouse.y > in.t - 24) ui.store(sid) -= 420.f * ui.dt;  // not while over the profiles
    if (ui.mouse.y > in.b - edge && ui.mouse.y < in.b + 40) ui.store(sid) += 420.f * ui.dt;
    ui.animating = true;
  }
  float off = ui.beginScroll(sid, in, rows.size() * kRowH + 4);
  float y0 = in.t + off;

  if (dragging_) {
    float f = (ui.mouse.y - y0) / kRowH;
    int ri = (int)floorf(f);
    float fr = f - ri;
    tg.ok = ui.mouse.x > r.l - 60 && ui.mouse.x < r.r + 60;
    if (ri < 0) {
      tg.top = 0;
      tg.lineY = y0;
    } else if (ri >= (int)rows.size()) {
      tg.top = (int)pins.size();
      tg.lineY = y0 + rows.size() * kRowH;
    } else {
      Row w = rows[(size_t)ri];
      Pin& p = pins[(size_t)w.top];
      bool grp = p.kind == Pin::Kind::Group;
      if (w.kid == -1 && grp && !dragGroup && fr > 0.26f && fr < 0.80f) {
        tg.into = true;
        tg.top = w.top;
        tg.kid = (int)p.children.size();
        tg.hiRow = ri;
      } else if (w.kid == -1) {
        bool after = fr >= 0.5f;
        if (after && grp && expanded_[p.id] && !dragGroup) {
          tg.into = true;
          tg.top = w.top;
          tg.kid = 0;
        } else {
          tg.top = w.top + (after ? 1 : 0);
        }
        tg.lineY = y0 + (ri + (after ? 1 : 0)) * kRowH;
        if (after && grp && expanded_[p.id] && dragGroup) tg.lineY = y0 + (ri + 1 + std::max<size_t>(1, p.children.size())) * kRowH;
      } else if (dragGroup) {
        tg.top = w.top + 1;
        int last = ri;
        while (last + 1 < (int)rows.size() && rows[(size_t)last + 1].top == w.top) last++;
        tg.lineY = y0 + (last + 1) * kRowH;
      } else {
        tg.into = true;
        tg.top = w.top;
        tg.kid = w.kid == -2 ? 0 : w.kid + (fr >= 0.5f ? 1 : 0);
        tg.lineY = y0 + (ri + (w.kid != -2 && fr >= 0.5f ? 1 : 0)) * kRowH;
        if (w.kid == -2) tg.hiRow = ri;
      }
    }
  }

  // Over another profile: it goes there (with Ctrl a copy does).
  int overTab = -1;
  RectF overRect;
  if (dragging_)
    for (auto& t : tabRects_)
      if (t.index != app_.cfg.activeProfile && t.r.inset(-4.f).contains(ui.mouse)) {
        overTab = t.index;
        overRect = t.r;
      }
  if (overTab >= 0) tg.ok = false;

  std::string remove, toggle, select;
  for (size_t i = 0; i < rows.size(); i++) {
    RectF q = RectF::xywh(in.l, y0 + i * kRowH, in.w() - 12, kRowH - 3);
    if (q.b < in.t - 4 || q.t > in.b + 4) continue;
    Row w = rows[i];
    float ind = w.kid != -1 ? 30.f : 0.f;
    q.l += ind;
    if (ind > 0) ui.p->rrect(RectF::xywh(q.l - 14, q.t - 3, 2, kRowH), 1, ui.pal.stroke);
    if (w.kid == -2) {
      ui.text(RectF(q.l + 14, q.t, q.r, q.b), L"Drag items here", 12.5f, ui.pal.faint);
      if (tg.hiRow == (int)i && dragging_) ui.p->rrectStroke(q.inset(0.5f), 7, ui.pal.accent, 1.5f);
      continue;
    }
    Pin& pin = w.kid == -1 ? pins[(size_t)w.top] : pins[(size_t)w.top].children[(size_t)w.kid];
    uint32_t id = ui.id(pin.id);
    bool isDrag = dragging_ && dragId_ == pin.id;
    bool sel = selected_ == pin.id;
    bool h = ui.hot(q) && !dragging_;
    float a = ui.anim(id, h ? 1.f : 0.f), s = ui.anim(id ^ 3u, sel ? 1.f : 0.f);
    if (h && ui.rightPressed) after([this, pid = pin.id] { pinMenu(pid); });
    ui.p->rrect(q, 7, (ui.pal.dark ? Color(1, 1, 1, 0.06f) : Color(0, 0, 0, 0.035f)).alpha(std::max(a, s)));
    if (s > 0.01f) ui.p->rrectStroke(q.inset(0.5f), 7, ui.pal.accent.alpha(s * 0.8f), 1.3f);
    if (tg.hiRow == (int)i && dragging_) {
      ui.p->rrect(q, 7, ui.pal.accent.withA(0.14f));
      ui.p->rrectStroke(q.inset(0.5f), 7, ui.pal.accent, 1.5f);
    }
    float op = isDrag ? 0.30f : 1.f;
    ui.glyph(RectF(q.l + 2, q.t, q.l + 22, q.b), L"\xE784", 12.f, ui.pal.faint.alpha((0.35f + 0.65f * a) * op));
    if (app_.logoBusy(pin.id)) spinner({q.l + 42, q.cy()}, 10);
    else drawPinIcon(pin, {q.l + 42, q.cy()}, 28, op);
    float tx = q.l + 66, rightEdge = q.r - 8;
    bool grp = pin.kind == Pin::Kind::Group;
    RectF chev(q.r - 34, q.t + 6, q.r - 6, q.b - 6), del(q.r - (grp ? 64 : 34), q.t + 6, q.r - (grp ? 36 : 6), q.b - 6);
    rightEdge = (h || grp) ? del.l - 4 : q.r - 8;
    std::wstring sub = grp ? std::to_wstring(pin.children.size()) + (pin.children.size() == 1 ? L" item" : L" items")
                     : pin.kind == Pin::Kind::Url ? pin.target : pin.admin ? L"Runs as administrator" : L"";
    if (sub.empty()) {
      ui.text(RectF(tx, q.t - 0.5f, rightEdge, q.b), pin.name, 13.5f, ui.pal.text.alpha(op));
    } else {
      ui.text(RectF(tx, q.t + 4, rightEdge, q.t + 24), pin.name, 13.5f, ui.pal.text.alpha(op));
      ui.text(RectF(tx, q.t + 22, rightEdge, q.b - 4), sub, 11.5f, ui.pal.dim.alpha(op));
    }
    bool onBtn = false;
    if (grp) {
      onBtn |= ui.hot(chev);
      if (ui.iconButton(id ^ 21u, chev, expanded_[pin.id] ? L"\xE70E" : L"\xE70D", nullptr, true, 11.f)) toggle = pin.id;
    }
    if (h) {
      onBtn |= ui.hot(del);
      if (ui.iconButton(id ^ 22u, del, L"\xE74D", L"Unpin", true, 13.f)) remove = pin.id;
    }
    if (h && !onBtn) {
      ui.cursor = LoadCursorW(nullptr, IDC_HAND);
      if (ui.pressed) {
        pressId_ = pin.id;
        pressAt_ = ui.mouse;
        dragGrab_ = {ui.mouse.x - q.l, ui.mouse.y - q.t};
      }
    }
    if (!dragging_ && ui.released && pressId_ == pin.id && h && !onBtn) select = pin.id;
  }
  if (dragging_ && tg.ok && tg.hiRow < 0) {
    float lx = in.l + (tg.into ? 34.f : 6.f);
    ui.p->line({lx, tg.lineY - 1.5f}, {in.r - 16, tg.lineY - 1.5f}, ui.pal.accent, 2.4f);
    ui.p->circle({lx, tg.lineY - 1.5f}, 4, ui.pal.accent);
  }
  ui.endScroll();

  if (!pressId_.empty() && ui.down && !dragging_ && (ui.mouse - pressAt_).len() > 6) {
    dragging_ = true;
    dragId_ = pressId_;
  }
  if (dragging_) {
    if (Pin* d = findPin(pins, dragId_)) {
      RectF g = RectF::xywh(ui.mouse.x - std::min(dragGrab_.x, 120.f), ui.mouse.y - dragGrab_.y, std::min(300.f, r.w() - 30), kRowH - 4);
      ui.p->rrect(g.offset(0, 5).inset(-2), 9, Color(0, 0, 0, 0.22f));
      ui.p->rrect(g, 8, ui.pal.popup);
      ui.p->rrectStroke(g.inset(0.5f), 8, ui.pal.accent, 1.4f);
      drawPinIcon(*d, {g.l + 30, g.cy()}, 28);
      ui.text(RectF(g.l + 54, g.t, g.r - 8, g.b), d->name, 13.5f, ui.pal.text, 600);
      if (overTab >= 0) {
        ui.p->rrect(overRect, 17, ui.pal.accent.withA(0.16f));
        ui.p->rrectStroke(overRect.inset(0.5f), 16.5f, ui.pal.accent, 2.2f);
        bool copy = GetKeyState(VK_CONTROL) < 0;
        std::wstring t = (copy ? L"Copy to " : L"Move to ") + app_.cfg.profiles[(size_t)overTab].name + (copy ? L"" : L"   \x00B7   Ctrl: copy");
        float tw = std::min(ui.textWidth(t, 12.5f, 600) + 24, 360.f);
        RectF lab = RectF::xywh(g.l + 10, g.b + 6, tw, 26);
        ui.p->rrect(lab, 13, ui.pal.accent);
        ui.text(lab, t, 12.5f, ui.pal.onAccent, 600, Align::Center);
      }
    }
    ui.cursor = LoadCursorW(nullptr, IDC_SIZEALL);
    ui.animating = true;
  }
  if (ui.released || !ui.down) {
    if (dragging_ && overTab >= 0) {
      after([this, id = dragId_, to = overTab, copy = GetKeyState(VK_CONTROL) < 0] { movePin(id, to, copy); });
    } else if (dragging_ && tg.ok) {
      int st = -1, sk = -1;
      for (int i = 0; i < (int)pins.size(); i++) {
        if (pins[(size_t)i].id == dragId_) st = i;
        for (int c = 0; c < (int)pins[(size_t)i].children.size(); c++)
          if (pins[(size_t)i].children[(size_t)c].id == dragId_) { st = i; sk = c; }
      }
      bool same = tg.into && sk < 0 && tg.top == st;  // a group cannot go inside itself
      Pin moved;
      if (st >= 0 && !same && removePin(pins, dragId_, &moved)) {
        int top = tg.top, kid = tg.kid;
        if (sk < 0 && top > st) top--;
        if (sk >= 0 && tg.into && top == st && kid > sk) kid--;
        if (tg.into && top < (int)pins.size()) {
          auto& ch = pins[(size_t)top].children;
          ch.insert(ch.begin() + clampi(kid, 0, (int)ch.size()), std::move(moved));
        } else {
          pins.insert(pins.begin() + clampi(top, 0, (int)pins.size()), std::move(moved));
        }
        changed(true);
      }
    }
    dragging_ = false;
    dragId_.clear();
    pressId_.clear();
  }
  if (!select.empty()) selected_ = selected_ == select ? std::string() : select;
  if (!toggle.empty()) expanded_[toggle] = !expanded_[toggle];
  if (!remove.empty()) removeAsking(remove);
}

// ---------------------------------------------------------------- adding
void SettingsWindow::addPanel(RectF r) {
  ui.card(r, 10);
  RectF in = r.inset(14, 12);
  ui.text(RectF(in.l, in.t, in.r, in.t + 22), L"Add to " + app_.cfg.profile().name, 14.5f, ui.pal.text, 600);
  addArea(RectF(in.l, in.t + 30, in.r, r.b - 8), r, nullptr);
}

bool SettingsWindow::inGroup(const AppEntry& a, const Pin& g) {
  std::wstring id = toLower(a.aumid), exe = toLower(a.exe);
  for (auto& c : g.children) {
    if (c.kind == Pin::Kind::App && toLower(c.target) == id) return true;
    if (c.kind != Pin::Kind::File) continue;
    MatchInfo m = resolveMatch(c);
    if ((!m.aumid.empty() && m.aumid == id) || (!m.exe.empty() && m.exe == exe)) return true;
  }
  return false;
}

// Every way to add something: to the profile, or with `group` straight into that group. What is added waits for the
// end of the frame, because the group being drawn may move in the list.
void SettingsWindow::addArea(RectF in, RectF zone, const Pin* group) {
  ensureApps();
  float y = in.t;
  struct B { const wchar_t* g; const wchar_t* n; int what; };
  static const B all[] = {{L"\xE8E5", L"File", 0}, {L"\xE8B7", L"Folder", 1}, {L"\xE774", L"Website", 2}, {L"\xF168", L"Group", 3}, {L"\xE90E", L"Taskbar", 4}};
  std::vector<B> bs;
  for (auto& b : all)
    if (!group || b.what != 3) bs.push_back(b);  // no groups inside groups
  int nb = (int)bs.size();
  float bw = (in.w() - (nb - 1) * 6.f) / nb;
  for (int i = 0; i < nb; i++) {
    RectF b = RectF::xywh(in.l + i * (bw + 6), y, bw, 58);
    int what = bs[(size_t)i].what;
    uint32_t id = ui.id("addb", what);
    bool c = ui.press(id, b), h = ui.hot(b);
    if (h) ui.cursor = LoadCursorW(nullptr, IDC_HAND);
    float a = ui.anim(id, h ? 1.f : 0.f);
    ui.p->rrect(b, 8, mix(ui.pal.control, ui.pal.controlHover, a));
    ui.p->rrectStroke(b.inset(0.5f), 8, ui.pal.strokeStrong.alpha(0.6f), 1);
    ui.glyph(RectF(b.l, b.t + 7, b.r, b.t + 33), bs[(size_t)i].g, 17, ui.pal.accent);
    ui.text(RectF(b.l, b.t + 33, b.r, b.b - 4), bs[(size_t)i].n, 12.f, ui.pal.text, 400, Align::Center);
    if (what == 4) ui.tooltip(b, group ? L"Copy everything pinned to the Windows taskbar into this group" : L"Copy everything pinned to the Windows taskbar");
    if (!c) continue;
    switch (what) {
      case 0:
      case 1:
        after([this, what] {
          std::wstring f = pickFile(hwnd_, what ? L"Choose a folder" : L"Choose a program or file", what == 1);
          if (!f.empty()) addPins({pinFromPath(f)});
        });
        break;
      case 2:
        addingUrl_ = !addingUrl_;
        newDraft();
        if (addingUrl_) ui.focusOn(ui.id("url"));
        break;
      case 3: {
        Pin g;
        g.id = newId();
        g.kind = Pin::Kind::Group;
        g.name = L"New group";
        expanded_[g.id] = true;
        selected_ = g.id;
        app_.cfg.profile().pins.push_back(g);
        changed(true);
        ui.focusOn(ui.id("ename"));
        return;
      }
      case 4: after([this] { addPins(importTaskbarPins()); }); break;
    }
  }
  y += 66;
  if (addingUrl_) {
    bool enter = false;
    y += 6;
    ui.text(RectF(in.l, y, in.r, y + 18), L"Address", 12.f, ui.pal.dim, 600);
    ui.textBox(ui.id("url"), RectF(in.l, y + 20, in.r, y + 54), urlBuf_, L"For example youtube.com", L"\xE774", &enter);
    y += 64;
    ui.text(RectF(in.l, y, in.r, y + 18), L"Name", 12.f, ui.pal.dim, 600);
    ui.textBox(ui.id("urlname"), RectF(in.l, y + 20, in.r, y + 54), urlName_, L"Optional, the site's own name otherwise", nullptr, &enter);
    y += 64;
    draft_.name = trim(urlName_).empty() ? (trim(urlBuf_).empty() ? L"?" : siteHost(pinFromUrl(urlBuf_).target)) : trim(urlName_);
    pictureFor_ = draft_.id;
    pictureZone_ = zone;
    y += picturePanel(in.l, y, in.w(), draft_) + 12;
    bool ok = ui.button(ui.id("urlok"), RectF(in.r - 110, y, in.r, y + 36), L"Add", Btn::Accent, nullptr, !trim(urlBuf_).empty());
    if (ui.button(ui.id("urlno"), RectF(in.r - 216, y, in.r - 118, y + 36), L"Cancel")) addingUrl_ = false;
    if ((ok || enter) && !trim(urlBuf_).empty()) {
      Pin p = pinFromUrl(urlBuf_, trim(urlName_));
      p.icon = draft_.icon;
      p.iconShape = draft_.iconShape;
      after([this, p] { addPins({p}); });
      addingUrl_ = false;
    }
    if (!addingUrl_) {
      dropDraft();
      ui.clearFocus();
    }
    return;
  }
  ui.textBox(ui.id("search"), RectF(in.l, y, in.r, y + 34), search_, L"Search installed apps", L"\xE721");
  y += 42;

  if (search_ != foundFor_ || (appsLoaded_ && found_.empty() && search_.empty())) {
    found_.clear();
    std::wstring q = toLower(trim(search_));
    std::vector<int> starts, words, inside;
    for (int i = 0; i < (int)apps_.size(); i++) {
      std::wstring n = toLower(apps_[(size_t)i].name);
      size_t at = n.find(q);
      if (q.empty() || at == 0) starts.push_back(i);
      else if (at != std::wstring::npos) (n[at - 1] == L' ' ? words : inside).push_back(i);
    }
    for (auto* v : {&starts, &words, &inside}) found_.insert(found_.end(), v->begin(), v->end());
    foundFor_ = search_;
    ui.scrollTo(ui.id("apps"), 0);
  }
  RectF list(in.l - 4, y, in.r + 8, in.b);
  if (!appsLoaded_) {
    ui.text(RectF(in.l, y, in.r, y + 60), L"Looking for installed apps...", 13.f, ui.pal.dim, 400, Align::Center);
    return;
  }
  if (found_.empty()) {
    ui.text(RectF(in.l, y, in.r, y + 60), L"No app matches. Use File to pick a program yourself.", 13.f, ui.pal.dim, 400, Align::Center, VAlign::Middle, true);
    return;
  }
  const float rh = 42;
  float off = ui.beginScroll(ui.id("apps"), list, found_.size() * rh);
  for (size_t i = 0; i < found_.size(); i++) {
    RectF q = RectF::xywh(list.l, list.t + off + i * rh, list.w() - 14, rh - 2);
    if (q.b < list.t || q.t > list.b) continue;
    AppEntry& e = apps_[(size_t)found_[i]];
    uint32_t id = ui.id("app", found_[i]);
    bool pinned = group ? inGroup(e, *group) : appPinned(e);
    bool elsewhere = group && !pinned && appPinned(e);  // in this profile, outside the group
    bool h = ui.hot(q);
    float a = ui.anim(id, h ? 1.f : 0.f);
    ui.p->rrect(q, 7, (ui.pal.dark ? Color(1, 1, 1, 0.06f) : Color(0, 0, 0, 0.035f)).alpha(a));
    Pin tmp;
    tmp.kind = Pin::Kind::App;
    tmp.target = e.aumid;
    tmp.name = e.name;
    drawPinIcon(tmp, {q.l + 24, q.cy()}, 26);
    ui.text(RectF(q.l + 46, q.t - 0.5f, q.r - 42, q.b), e.name, 13.5f, pinned ? ui.pal.dim : ui.pal.text);
    if (pinned) {
      ui.glyph(RectF(q.r - 36, q.t, q.r - 8, q.b), L"\xE73E", 13, ui.pal.accent);
    } else {
      if (h) ui.cursor = LoadCursorW(nullptr, IDC_HAND);
      ui.glyph(RectF(q.r - 36, q.t, q.r - 8, q.b), elsewhere ? L"\xE8DE" : L"\xE710", 13, ui.pal.text.withA(lerp(0.35f, 1.f, a)));
      if (elsewhere) ui.tooltip(q, L"Pinned outside this group. Click to move it in");
      if (ui.press(id, q)) after([this, p = pinFromApp(e)] { addPins({p}); });
    }
  }
  ui.endScroll();
}

// ---------------------------------------------------------------- editing
void SettingsWindow::editPanel(RectF r, Pin& pin) {
  ui.card(r, 10);
  RectF in = r.inset(16, 14);
  bool grp = pin.kind == Pin::Kind::Group;
  drawPinIcon(pin, {in.l + 24, in.t + 24}, 44);
  ui.text(RectF(in.l + 60, in.t + 2, in.r - 34, in.t + 26), grp ? L"Edit group" : L"Edit pin", 15.5f, ui.pal.text, 600);
  ui.text(RectF(in.l + 60, in.t + 25, in.r - 34, in.t + 46), pinSubtitle(pin), 12.f, ui.pal.dim);
  if (ui.iconButton(ui.id("eclose"), RectF(in.r - 30, in.t, in.r, in.t + 30), L"\xE711", L"Close", true, 12.f)) {
    selected_.clear();
    return;
  }
  if (editFor_ != pin.id) {
    editFor_ = pin.id;
    ui.scrollTo(ui.id("edit"), 0);
  }
  pictureFor_ = pin.id;
  pictureZone_ = r;
  if (grp) {
    groupPanel(r, in, pin);
    return;
  }
  RectF body(in.l - 6, in.t + 56, in.r + 12, r.b - 58);
  float y = body.t + 6 + ui.beginScroll(ui.id("edit"), body, editH_), top = y;
  auto field = [&](const char* key, const wchar_t* label, std::wstring& v, const wchar_t* hint, float reserve = 0) {
    ui.text(RectF(in.l, y, in.r, y + 18), label, 12.f, ui.pal.dim, 600);
    bool ch = ui.textBox(ui.id(key), RectF(in.l, y + 20, in.r - reserve, y + 54), v, hint);
    y += 62;
    return ch;
  };
  bool ch = field("ename", L"Name", pin.name, L"Shown in the centre of the wheel");
  if (pin.kind == Pin::Kind::File) {
    float fy = y;
    if (field("etarget", L"Opens", pin.target, L"Program, file or folder", 44)) {
      pin.folder = false;
      ch = true;
    }
    if (ui.iconButton(ui.id("ebrowse"), RectF(in.r - 36, fy + 20, in.r, fy + 54), L"\xE838", L"Browse")) {
      after([this, id = pin.id] {
        std::wstring f = pickFile(hwnd_, L"Choose a program or file", false);
        Pin* t = f.empty() ? nullptr : pinById(id);
        if (!t) return;
        Pin q = pinFromPath(f);
        adoptPin(q);
        t->target = q.target;
        t->folder = q.folder;
        forgetMatches();
        changed(true);
      });
    }
    ch |= field("eargs", L"Arguments", pin.args, L"Optional");
    ch |= field("edir", L"Start in", pin.workDir, L"Optional");
  } else if (pin.kind == Pin::Kind::Url) {
    ch |= field("eurl", L"Address", pin.target, L"https://");
  }
  y += picturePanel(in.l, y, in.w(), pin);
  if (pin.kind == Pin::Kind::File || pin.kind == Pin::Kind::App) {
    RectF t(in.l, y, in.r, y + 34);
    ui.text(RectF(t.l, t.t, t.r - 60, t.b), L"Run as administrator", 13.5f, ui.pal.text);
    ch |= ui.toggle(ui.id("eadmin"), t, pin.admin);
    y += 44;
  }
  if (fabsf(y - top + 12 - editH_) > 0.5f) ui.animating = true;
  editH_ = y - top + 12;
  ui.endScroll();
  if (ch) {
    forgetMatches();
    changed(true);
  }
  RectF foot(in.l, r.b - 50, in.r, r.b - 16);
  float bw = std::min(110.f, (foot.w() - 16) / 3);
  bool rem = ui.button(ui.id("erem"), RectF(foot.l, foot.t, foot.l + bw, foot.b), L"Unpin", Btn::Danger, bw > 100 ? L"\xE74D" : nullptr);
  bool done = ui.button(ui.id("edone"), RectF(foot.r - bw, foot.t, foot.r, foot.b), L"Done", Btn::Accent);
  if (ui.button(ui.id("etest"), RectF(foot.r - bw * 2 - 8, foot.t, foot.r - bw - 8, foot.b), L"Try it")) launchPin(pin);
  if (rem) {
    removeAsking(selected_);
  } else if (done) {
    selected_.clear();
  }
}

// A group: its name and picture at the top, and below them everything there is to add straight into it.
void SettingsWindow::groupPanel(RectF r, RectF in, Pin& pin) {
  const std::string gid = pin.id;
  float y = in.t + 56;
  RectF well = RectF::xywh(in.l, y, 72, 72);
  pictureWell(well, pin);
  float bx = well.r + 12, mid = (bx + in.r) * 0.5f;
  if (ui.textBox(ui.id("ename"), RectF(bx, y, in.r, y + 34), pin.name, L"Group name")) changed(true);
  RectF pick(bx, y + 38, mid - 3, y + 72), paste(mid + 3, y + 38, in.r, y + 72);
  ui.tooltip(pick, L"A picture, an icon or a program. You can also drop one here");
  if (ui.button(ui.id("gpick"), pick, L"Picture", Btn::Standard, pick.w() > 100 ? L"\xEB9F" : nullptr)) after([this, gid] { choosePicture(gid); });
  ui.tooltip(paste, L"A picture you copied (Ctrl+V)");
  if (ui.button(ui.id("gpaste"), paste, L"Paste", Btn::Standard, paste.w() > 100 ? L"\xE77F" : nullptr)) after([this, gid] { pastePicture(gid); });
  y += 86;
  ui.text(RectF(in.l, y, in.r, y + 22), L"Add to " + pin.name, 14.f, ui.pal.text, 600);
  y += 28;
  RectF foot(in.l, r.b - 50, in.r, r.b - 16);
  addArea(RectF(in.l, y, in.r, foot.t - 10), r, &pin);
  float bw = std::min(110.f, (foot.w() - 16) / 3);
  bool rem = ui.button(ui.id("erem"), RectF(foot.l, foot.t, foot.l + bw, foot.b), L"Remove", Btn::Danger, bw > 100 ? L"\xE74D" : nullptr);
  bool ungroup = ui.button(ui.id("ungroup"), RectF(foot.l + bw + 8, foot.t, foot.l + bw * 2 + 8, foot.b), L"Ungroup", Btn::Standard, nullptr, !pin.children.empty());
  ui.tooltip(RectF(foot.l + bw + 8, foot.t, foot.l + bw * 2 + 8, foot.b), L"Put its items back on the wheel and remove the group");
  bool done = ui.button(ui.id("edone"), RectF(foot.r - bw, foot.t, foot.r, foot.b), L"Done", Btn::Accent);
  if (rem) {
    removeAsking(gid);
  } else if (ungroup) {
    after([this, gid] {
      for (auto& pr : app_.cfg.profiles)
        if (ungroupPin(pr.pins, gid)) break;
      selected_.clear();
      changed(true);
    });
  } else if (done) {
    selected_.clear();
  }
}

}  // namespace rt
