#include "config.h"

namespace rt {

// ---------------------------------------------------------------- enum names
namespace {
const char* const kLayout[] = {"radial", "flow", "strip", "orbit", "comb", "carousel", "globe", "cards", "corner", "galaxy", "board", "drum"};
const char* const kAnchor[] = {"center", "mouse"};
const char* const kOverflow[] = {"rings", "unfold", "pages"};
const char* const kShape[] = {"wedge", "blade", "orb", "hex", "petal", "none"};
const char* const kMaterial[] = {"frosted", "liquid", "solid", "outline"};
const char* const kTone[] = {"original", "muted", "mono", "duo", "ink", "engrave", "neon", "pixel", "sticker", "shadow"};
const char* const kOpen[] = {"bloom", "spin", "unfold", "zoom", "fade"};
const char* const kRim[] = {"off", "solid", "spin"};
const char* const kParticles[] = {"off", "embers", "stars"};
const char* const kHub[] = {"clock", "profile", "empty"};
const char* const kActivation[] = {"smart", "hold", "toggle"};
const char* const kSide[] = {"right", "left"};
const char* const kEdge[] = {"bottom", "top", "left", "right", "center"};
const char* const kLabels[] = {"focused", "always"};
const char* const kMonitor[] = {"mouse", "primary"};
const char* const kKind[] = {"app", "file", "url", "group"};
const char* const kPic[] = {"auto", "plain", "tile", "circle"};

template <class E, size_t N>
void readEnum(const Json& j, const char* key, const char* const (&names)[N], E& v) {
  std::string s = j.str(key);
  for (size_t i = 0; i < N; i++)
    if (s == names[i]) { v = (E)i; return; }
}
template <class E, size_t N>
Json enumJson(const char* const (&names)[N], E v) { return Json(names[clampi((int)v, 0, (int)N - 1)]); }

void readF(const Json& j, const char* k, float& v) { v = (float)j.num(k, v); }
void readB(const Json& j, const char* k, bool& v) { v = j.flag(k, v); }
void readC(const Json& j, const char* k, Color& v) {
  std::string s = j.str(k);
  if (!s.empty()) Color::parse(s, v);
}
void readW(const Json& j, const char* k, std::wstring& v) {
  auto p = j.find(k);
  if (p && p->t == Json::T::Str) v = widen(p->s);
}

Json styleToJson(const Style& s) {
  Json j = Json::object();
  j.set("skin", s.look);
  j.set("shape", enumJson(kShape, s.shape));
  j.set("material", enumJson(kMaterial, s.material));
  j.set("base", s.base.str());
  j.set("accent", s.accent.str());
  j.set("accent2", s.accent2.str());
  j.set("text", s.text.str());
  j.set("border", s.border.str());
  j.set("systemAccent", s.systemAccent);
  j.set("opacity", s.opacity);
  j.set("blur", s.blur);
  j.set("refraction", s.refraction);
  j.set("corner", s.corner);
  j.set("borderWidth", s.borderWidth);
  j.set("borderOpacity", s.borderOpacity);
  j.set("gap", s.gap);
  j.set("shadow", s.shadow);
  j.set("iconTone", enumJson(kTone, s.tone));
  j.set("font", s.font);
  j.set("open", enumJson(kOpen, s.open));
  j.set("speed", s.speed);
  j.set("hoverGrow", s.hoverGrow);
  j.set("iconZoom", s.iconZoom);
  j.set("glow", s.glow);
  j.set("tilt", s.tilt);
  j.set("pointer", s.pointer);
  j.set("rim", enumJson(kRim, s.rim));
  j.set("ticks", s.ticks);
  j.set("scan", s.scan);
  j.set("pulse", s.pulse);
  j.set("particles", enumJson(kParticles, s.particles));
  j.set("burst", s.burst);
  j.set("dim", s.dim);
  return j;
}

void styleFromJson(const Json& j, Style& s) {
  s.look = j.str("skin", s.look);
  readEnum(j, "shape", kShape, s.shape);
  readEnum(j, "material", kMaterial, s.material);
  readC(j, "base", s.base);
  readC(j, "accent", s.accent);
  readC(j, "accent2", s.accent2);
  readC(j, "text", s.text);
  readC(j, "border", s.border);
  readB(j, "systemAccent", s.systemAccent);
  readF(j, "opacity", s.opacity);
  readF(j, "blur", s.blur);
  readF(j, "refraction", s.refraction);
  readF(j, "corner", s.corner);
  readF(j, "borderWidth", s.borderWidth);
  readF(j, "borderOpacity", s.borderOpacity);
  readF(j, "gap", s.gap);
  readF(j, "shadow", s.shadow);
  readEnum(j, "iconTone", kTone, s.tone);
  s.font = j.str("font", s.font);
  readEnum(j, "open", kOpen, s.open);
  readF(j, "speed", s.speed);
  readF(j, "hoverGrow", s.hoverGrow);
  readF(j, "iconZoom", s.iconZoom);
  readF(j, "glow", s.glow);
  readF(j, "tilt", s.tilt);
  readB(j, "pointer", s.pointer);
  readEnum(j, "rim", kRim, s.rim);
  readB(j, "ticks", s.ticks);
  readB(j, "scan", s.scan);
  readB(j, "pulse", s.pulse);
  readEnum(j, "particles", kParticles, s.particles);
  readB(j, "burst", s.burst);
  readF(j, "dim", s.dim);
}

void sanitizeStyle(Style& s) {
  s.opacity = clampf(s.opacity, 0.f, 1.f);
  s.blur = clampf(s.blur, 0.f, 80.f);
  s.refraction = clampf(s.refraction, 0.f, 1.f);
  s.corner = clampf(s.corner, 0.f, 40.f);
  s.borderWidth = clampf(s.borderWidth, 0.f, 6.f);
  s.borderOpacity = clampf(s.borderOpacity, 0.f, 1.f);
  s.gap = clampf(s.gap, 0.f, 30.f);
  s.shadow = clampf(s.shadow, 0.f, 1.f);
  s.speed = clampf(s.speed, 0.4f, 2.5f);
  s.hoverGrow = clampf(s.hoverGrow, 0.f, 40.f);
  s.iconZoom = clampf(s.iconZoom, 1.f, 1.8f);
  s.glow = clampf(s.glow, 0.f, 1.f);
  s.tilt = clampf(s.tilt, 0.f, 1.f);
  s.dim = clampf(s.dim, 0.f, 0.85f);
  if (s.font.empty() || s.font.size() > 80) s.font = "Segoe UI Variable Display";
}

Json pinToJson(const Pin& p) {
  Json j = Json::object();
  j.set("id", p.id);
  j.set("kind", enumJson(kKind, p.kind));
  j.set("name", narrow(p.name));
  if (!p.target.empty()) j.set("target", narrow(p.target));
  if (!p.args.empty()) j.set("args", narrow(p.args));
  if (!p.workDir.empty()) j.set("workDir", narrow(p.workDir));
  if (!p.icon.empty()) j.set("icon", narrow(p.icon));
  if (p.iconShape != PicShape::Auto) j.set("iconShape", enumJson(kPic, p.iconShape));
  if (p.admin) j.set("admin", true);
  if (p.folder) j.set("folder", true);
  if (p.kind == Pin::Kind::Group) {
    Json a = Json::array();
    for (auto& c : p.children) a.push(pinToJson(c));
    j.set("children", std::move(a));
  }
  return j;
}

Pin pinFromJson(const Json& j, int depth = 0) {
  Pin p;
  p.id = j.str("id");
  if (p.id.empty()) p.id = newId();
  readEnum(j, "kind", kKind, p.kind);
  readW(j, "name", p.name);
  readW(j, "target", p.target);
  readW(j, "args", p.args);
  readW(j, "workDir", p.workDir);
  readW(j, "icon", p.icon);
  readEnum(j, "iconShape", kPic, p.iconShape);
  readB(j, "admin", p.admin);
  readB(j, "folder", p.folder);
  if (auto c = j.find("children"); c && c->isArr() && depth == 0) {
    for (auto& e : c->a)
      if (e.isObj()) {
        Pin ch = pinFromJson(e, depth + 1);
        if (ch.kind != Pin::Kind::Group) p.children.push_back(std::move(ch));
      }
  }
  return p;
}
}  // namespace

static_assert(sizeof kLayout / sizeof *kLayout == kLayoutCount && sizeof kTone / sizeof *kTone == kToneCount);

const char* layoutId(LayoutType t) { return kLayout[clampi((int)t, 0, kLayoutCount - 1)]; }
bool toneFromText(const std::string& s, IconTone& out) {
  for (int i = 0; i < kToneCount - 1; i++)
    if (s == kTone[i]) {
      out = (IconTone)i;
      return true;
    }
  return false;
}
void readStyle(const Json& j, Style& s) {
  styleFromJson(j, s);
  sanitizeStyle(s);
}

std::string styleText(const Style& s) { return styleToJson(s).dump(); }

bool sameLook(const Style& a, const Style& b) {
  Json x = styleToJson(a), y = styleToJson(b);
  return x.dump() == y.dump();
}

// ---------------------------------------------------------------- hotkey text
std::wstring keyName(UINT vk) {
  switch (vk) {
    case VK_OEM_3: return L"`";
    case VK_OEM_102: return L"<";
    case VK_ESCAPE: return L"Esc";
    case VK_TAB: return L"Tab";
    case VK_CAPITAL: return L"Caps Lock";
    case VK_SPACE: return L"Space";
    case VK_RETURN: return L"Enter";
    case VK_BACK: return L"Backspace";
    case VK_INSERT: return L"Insert";
    case VK_DELETE: return L"Delete";
    case VK_HOME: return L"Home";
    case VK_END: return L"End";
    case VK_PRIOR: return L"Page Up";
    case VK_NEXT: return L"Page Down";
    case VK_LEFT: return L"Left";
    case VK_RIGHT: return L"Right";
    case VK_UP: return L"Up";
    case VK_DOWN: return L"Down";
    case VK_PAUSE: return L"Pause";
    case VK_SCROLL: return L"Scroll Lock";
    case VK_OEM_MINUS: return L"-";
    case VK_OEM_PLUS: return L"=";
    case VK_OEM_COMMA: return L",";
    case VK_OEM_PERIOD: return L".";
    case VK_OEM_1: return L";";
    case VK_OEM_2: return L"/";
    case VK_OEM_4: return L"[";
    case VK_OEM_5: return L"\\";
    case VK_OEM_6: return L"]";
    case VK_OEM_7: return L"'";
  }
  if (vk >= VK_F1 && vk <= VK_F24) return L"F" + std::to_wstring(vk - VK_F1 + 1);
  if (vk >= VK_NUMPAD0 && vk <= VK_NUMPAD9) return L"Num " + std::to_wstring(vk - VK_NUMPAD0);
  if ((vk >= '0' && vk <= '9') || (vk >= 'A' && vk <= 'Z')) return std::wstring(1, (wchar_t)vk);
  wchar_t b[64] = {};
  UINT sc = MapVirtualKeyW(vk, MAPVK_VK_TO_VSC);
  if (sc && GetKeyNameTextW((LONG)(sc << 16), b, 64)) return b;
  return L"Key " + std::to_wstring(vk);
}

std::wstring hotkeyText(const Hotkey& h) {
  std::wstring s;
  if (h.mods & MOD_WIN) s += L"Win + ";
  if (h.mods & MOD_CONTROL) s += L"Ctrl + ";
  if (h.mods & MOD_ALT) s += L"Alt + ";
  if (h.mods & MOD_SHIFT) s += L"Shift + ";
  return s + keyName(h.vk);
}

// ---------------------------------------------------------------- config
Profile& Config::profile() {
  if (profiles.empty()) {
    Profile p;
    p.id = newId();
    profiles.push_back(p);
  }
  activeProfile = clampi(activeProfile, 0, (int)profiles.size() - 1);
  return profiles[(size_t)activeProfile];
}

const std::string& Config::skinFor(const Profile& p) const {
  static const std::string none;
  if (p.skin.empty()) return skin;
  return p.skin == kNoSkin ? none : p.skin;
}

void Config::chooseSkin(const std::string& id) {
  Profile& p = profile();
  if (p.skin.empty()) skin = id;
  else p.skin = id.empty() ? std::string(kNoSkin) : id;
}

void Config::chooseLayout(LayoutType t) {
  Profile& p = profile();
  if (p.layout < 0) layout = t;
  else p.layout = (int)t;
}

bool Config::anyLayout(LayoutType t) const {
  if (profiles.empty()) return layout == t;
  for (auto& p : profiles)
    if (layoutFor(p) == t) return true;
  return false;
}

bool Config::onlyLayout(LayoutType t) const {
  for (auto& p : profiles)
    if (layoutFor(p) != t) return false;
  return layout == t || !profiles.empty();
}

int Config::wheelStep(int from, int dir) const {
  int n = (int)profiles.size();
  for (int k = 1; k < n; k++) {
    int i = ((from + dir * k) % n + n) % n;
    if (!profiles[(size_t)i].locked) return i;
  }
  return from;
}

int Config::wheelIndex() const {
  int i = clampi(activeProfile, 0, std::max(0, (int)profiles.size() - 1));
  return profiles.empty() || !profiles[(size_t)i].locked ? i : wheelStep(i, 1);
}

int Config::unlockedCount() const {
  int n = 0;
  for (auto& p : profiles) n += !p.locked;
  return n;
}

Profile& Config::profileById(const std::string& id) {
  if (!id.empty())
    for (auto& p : profiles)
      if (p.id == id) return p;
  return profile();
}

std::wstring Config::path() { return joinPath(dataDir(), L"config.json"); }

Json Config::toJson() const {
  Json j = Json::object();
  j.set("version", version);
  j.set("firstRun", firstRun);

  Json h = Json::object();
  h.set("mods", (int)hotkey.mods);
  h.set("vk", (int)hotkey.vk);
  h.set("takeOver", hotkey.takeOver);
  h.set("activation", enumJson(kActivation, activation));
  j.set("hotkey", std::move(h));

  Json l = Json::object();
  l.set("type", enumJson(kLayout, layout));
  l.set("anchor", enumJson(kAnchor, anchor));
  l.set("monitor", enumJson(kMonitor, monitor));
  l.set("scale", scale);
  l.set("iconSize", iconSize);
  l.set("labels", enumJson(kLabels, labels));
  l.set("perRing", perRing);
  l.set("overflow", enumJson(kOverflow, overflow));
  l.set("hubRadius", hubRadius);
  l.set("ringThickness", ringThickness);
  l.set("hub", enumJson(kHub, hub));
  l.set("hubProfiles", hubProfiles);
  l.set("showNumbers", showNumbers);
  l.set("arc", arc);
  l.set("arcAt", arcAt);
  l.set("flowSide", enumJson(kSide, flowSide));
  l.set("flowCurve", flowCurve);
  l.set("flowSpacing", flowSpacing);
  l.set("flowMagnify", flowMagnify);
  l.set("stripEdge", enumJson(kEdge, stripEdge));
  l.set("stripMagnify", stripMagnify);
  l.set("stripSpacing", stripSpacing);
  l.set("spread", spread);
  l.set("drift", drift);
  l.set("lens", lens);
  l.set("columns", columns);
  l.set("cornerAt", cornerAt);
  j.set("layout", std::move(l));

  if (!skin.empty()) j.set("skin", skin);
  j.set("profileSkins", true);  // a profile's skin means: empty the main one, "-" none
  if (!hiddenSkins.empty()) {
    Json hs = Json::array();
    for (auto& h : hiddenSkins) hs.push(h);
    j.set("hiddenSkins", std::move(hs));
  }
  Json tn = Json::object();
  for (auto& t : tunes) {
    if (t.second.plain()) continue;
    Json o = Json::object();
    o.set("hue", t.second.hue);
    o.set("sat", t.second.sat);
    o.set("light", t.second.light);
    tn.set(t.first, std::move(o));
  }
  if (!tn.o.empty()) j.set("skinTunes", std::move(tn));

  j.set("style", styleToJson(style));
  Json cs = Json::array();
  for (auto& k : customLooks) {
    Json o = Json::object();
    o.set("id", k.id);
    o.set("name", narrow(k.name));
    o.set("style", styleToJson(k.style));
    cs.push(std::move(o));
  }
  j.set("customSkins", std::move(cs));

  Json b = Json::object();
  b.set("warpCursor", warpCursor);
  b.set("restoreCursor", restoreCursor);
  b.set("switchToRunning", switchToRunning);
  b.set("showRunning", showRunning);
  b.set("windowsFan", windowsFan);
  b.set("blockFullscreen", blockFullscreen);
  b.set("sounds", sounds);
  b.set("volume", volume);
  b.set("lowMemory", lowMemory);
  b.set("reduceMotion", reduceMotion);
  b.set("trayIcon", trayIcon);
  b.set("taskbarMenu", taskbarMenu);
  b.set("siteLogos", siteLogos);
  b.set("skinCursor", skinCursor);
  b.set("reverseScroll", reverseScroll);
  if (!startProfile.empty()) b.set("startProfile", startProfile);
  b.set("backFx", backFx);
  b.set("backFxKind", backFxKind);
  if (!helpLang.empty()) b.set("helpLang", helpLang);
  j.set("behavior", std::move(b));

  j.set("activeProfile", activeProfile);
  Json ps = Json::array();
  for (auto& p : profiles) {
    Json o = Json::object();
    o.set("id", p.id);
    o.set("name", narrow(p.name));
    o.set("color", p.color.str());
    if (!p.skin.empty()) o.set("skin", p.skin);
    if (p.layout >= 0 && p.layout < kLayoutCount) o.set("layout", layoutId((LayoutType)p.layout));
    if (p.locked) o.set("locked", true);
    Json a = Json::array();
    for (auto& pin : p.pins) a.push(pinToJson(pin));
    o.set("pins", std::move(a));
    ps.push(std::move(o));
  }
  j.set("profiles", std::move(ps));
  return j;
}

void Config::fromJson(const Json& j) {
  version = (int)j.num("version", 1);
  readB(j, "firstRun", firstRun);
  if (auto h = j.find("hotkey")) {
    hotkey.mods = (UINT)h->num("mods", hotkey.mods);
    hotkey.vk = (UINT)h->num("vk", hotkey.vk);
    readB(*h, "takeOver", hotkey.takeOver);
    readEnum(*h, "activation", kActivation, activation);
  }
  if (auto l = j.find("layout")) {
    readEnum(*l, "type", kLayout, layout);
    readEnum(*l, "anchor", kAnchor, anchor);
    readEnum(*l, "monitor", kMonitor, monitor);
    readF(*l, "scale", scale);
    readF(*l, "iconSize", iconSize);
    readEnum(*l, "labels", kLabels, labels);
    perRing = (int)l->num("perRing", perRing);
    readEnum(*l, "overflow", kOverflow, overflow);
    readF(*l, "hubRadius", hubRadius);
    readF(*l, "ringThickness", ringThickness);
    readEnum(*l, "hub", kHub, hub);
    readB(*l, "hubProfiles", hubProfiles);
    readB(*l, "showNumbers", showNumbers);
    readF(*l, "arc", arc);
    arcAt = (int)l->num("arcAt", arcAt);
    readEnum(*l, "flowSide", kSide, flowSide);
    readF(*l, "flowCurve", flowCurve);
    readF(*l, "flowSpacing", flowSpacing);
    readF(*l, "flowMagnify", flowMagnify);
    readEnum(*l, "stripEdge", kEdge, stripEdge);
    readF(*l, "stripMagnify", stripMagnify);
    readF(*l, "stripSpacing", stripSpacing);
    readF(*l, "spread", spread);
    readF(*l, "drift", drift);
    readF(*l, "lens", lens);
    columns = (int)l->num("columns", columns);
    cornerAt = (int)l->num("cornerAt", cornerAt);
  }
  skin = j.str("skin");
  bool perProfile = j.flag("skinPerProfile", false), mainModel = j.flag("profileSkins", false);
  hiddenSkins.clear();
  if (auto h = j.find("hiddenSkins"); h && h->isArr())
    for (auto& e : h->a)
      if (e.t == Json::T::Str && !e.s.empty() && e.s.size() <= 60 && hiddenSkins.size() < 300) hiddenSkins.push_back(e.s);
  tunes.clear();
  if (auto t = j.find("skinTunes"); t && t->isObj())
    for (auto& kv : t->o) {
      if (!kv.second.isObj() || tunes.size() >= 200) continue;
      Tune u;
      readF(kv.second, "hue", u.hue);
      readF(kv.second, "sat", u.sat);
      readF(kv.second, "light", u.light);
      u.hue = clampf(u.hue, -180.f, 180.f);
      u.sat = clampf(u.sat, 0.f, 2.f);
      u.light = clampf(u.light, 0.4f, 1.8f);
      if (!u.plain()) tunes[kv.first] = u;
    }
  if (auto s = j.find("style")) styleFromJson(*s, style);
  customLooks.clear();
  if (auto c = j.find("customSkins"); c && c->isArr()) {
    for (auto& e : c->a) {
      Look k;
      k.id = e.str("id", newId());
      readW(e, "name", k.name);
      k.group = L"Yours";
      if (auto s = e.find("style")) styleFromJson(*s, k.style);
      sanitizeStyle(k.style);
      k.style.look = k.id;
      customLooks.push_back(std::move(k));
    }
  }
  if (auto b = j.find("behavior")) {
    readB(*b, "warpCursor", warpCursor);
    readB(*b, "restoreCursor", restoreCursor);
    readB(*b, "switchToRunning", switchToRunning);
    readB(*b, "showRunning", showRunning);
    readB(*b, "windowsFan", windowsFan);
    readB(*b, "blockFullscreen", blockFullscreen);
    readB(*b, "sounds", sounds);
    readF(*b, "volume", volume);
    readB(*b, "lowMemory", lowMemory);
    readB(*b, "reduceMotion", reduceMotion);
    readB(*b, "trayIcon", trayIcon);
    readB(*b, "taskbarMenu", taskbarMenu);
    readB(*b, "siteLogos", siteLogos);
    readB(*b, "skinCursor", skinCursor);
    readB(*b, "reverseScroll", reverseScroll);
    startProfile = b->str("startProfile").substr(0, 40);
    readB(*b, "backFx", backFx);
    backFxKind = b->str("backFxKind", backFxKind).substr(0, 20);
    helpLang = b->str("helpLang").substr(0, 4);
  }
  activeProfile = (int)j.num("activeProfile", 0);
  profiles.clear();
  if (auto p = j.find("profiles"); p && p->isArr()) {
    for (auto& e : p->a) {
      if (!e.isObj()) continue;
      Profile pr;
      pr.id = e.str("id");
      if (pr.id.empty()) pr.id = newId();
      readW(e, "name", pr.name);
      readC(e, "color", pr.color);
      pr.skin = e.str("skin").substr(0, 60);
      std::string lay = e.str("layout");
      for (int t = 0; t < kLayoutCount; t++)
        if (lay == kLayout[t]) pr.layout = t;  // anything else: the main arrangement
      readB(e, "locked", pr.locked);
      if (auto a = e.find("pins"); a && a->isArr())
        for (auto& q : a->a)
          if (q.isObj()) pr.pins.push_back(pinFromJson(q));
      profiles.push_back(std::move(pr));
    }
  }
  if (!mainModel) {
    // Before, a profile's skin counted only with "every profile has its own skin" on, and then the first one led.
    if (perProfile && !profiles.empty()) {
      skin = profiles[0].skin;
      for (auto& p : profiles) p.skin = p.skin == skin ? std::string() : p.skin.empty() ? std::string(kNoSkin) : p.skin;
    } else {
      for (auto& p : profiles) p.skin.clear();
    }
  }
  sanitize();
}

void Config::sanitize() {
  hotkey.mods &= (MOD_ALT | MOD_CONTROL | MOD_SHIFT | MOD_WIN);
  if (hotkey.vk == 0 || hotkey.vk > 0xFE) { hotkey.vk = VK_OEM_3; hotkey.mods = MOD_WIN; }
  scale = clampf(scale, 0.6f, 2.2f);
  iconSize = clampf(iconSize, 24.f, 96.f);
  perRing = clampi(perRing, 3, 20);
  hubRadius = clampf(hubRadius, 50.f, 180.f);
  ringThickness = clampf(ringThickness, 48.f, 140.f);
  arc = clampf(arc, 90.f, 360.f);
  arcAt = clampi(arcAt, 0, 3);
  flowCurve = clampf(flowCurve, 0.f, 1.f);
  flowSpacing = clampf(flowSpacing, 4.f, 60.f);
  flowMagnify = clampf(flowMagnify, 1.f, 2.4f);
  stripMagnify = clampf(stripMagnify, 1.f, 2.4f);
  stripSpacing = clampf(stripSpacing, 2.f, 60.f);
  spread = clampf(spread, 0.7f, 1.6f);
  drift = clampf(drift, 0.f, 1.f);
  lens = clampf(lens, 1.f, 2.2f);
  columns = clampi(columns, 0, 14);
  cornerAt = clampi(cornerAt, 0, 3);
  if (skin.size() > 60) skin.clear();
  volume = clampf(volume, 0.f, 1.f);
  sanitizeStyle(style);
  profile();  // guarantees at least one and a valid index
  if (!unlockedCount()) profiles[0].locked = false;
  for (auto& p : profiles)
    if (p.layout < -1 || p.layout >= kLayoutCount) p.layout = -1;
}

Config::Load Config::load(int tries) {
  std::wstring file = path(), bak = file + L".bak";
  std::string text;
  DWORD err = 0;
  bool got = false;
  // A scanner, a sync client or our other process may hold it for a moment.
  for (int i = 0; i < tries && !got; i++) {
    got = readFile(file, text, &err);
    if (got || err == ERROR_FILE_NOT_FOUND || err == ERROR_PATH_NOT_FOUND) break;
    Sleep(90);
  }
  bool absent = !got && (err == ERROR_FILE_NOT_FOUND || err == ERROR_PATH_NOT_FOUND);
  if (!got && !absent) {
    logf("config: cannot read it now (error %lu)", err);
    return Load::Unreadable;
  }
  Json j;
  intact = false;
  if (got && Json::parse(text, j) && j.isObj()) {
    fromJson(j);
    intact = true;
    return Load::Ok;
  }
  if (got) {
    // Never silently replace a file we could not understand: keep a copy beside it.
    CopyFileW(file.c_str(), (file + L".broken").c_str(), FALSE);
    logf("config: damaged, kept a copy as config.json.broken");
  }
  Json k;
  if (readFile(bak, text) && Json::parse(text, k) && k.isObj()) {
    logf("config: using the backup");
    fromJson(k);
    return Load::Ok;
  }
  return Load::Missing;
}

bool Config::save() const { return !locked && writeFileAtomic(path(), toJson().dump(), true); }

// ---------------------------------------------------------------- backup files
std::wstring linksDir() { return joinPath(dataDir(), L"links"); }
std::wstring imagesDir() { return joinPath(dataDir(), L"images"); }

static bool ourPicture(const std::wstring& path) { return toLower(dirName(path)) == toLower(imagesDir()); }

static void collectImages(const std::vector<Pin>& pins, Json& out) {
  for (auto& p : pins) {
    collectImages(p.children, out);
    std::string bytes;
    if (ourPicture(p.icon) && readFile(p.icon, bytes) && bytes.size() < 2 * 1024 * 1024) out.set(p.id, base64(bytes));
  }
}

static void collectLinks(const std::vector<Pin>& pins, Json& out) {
  for (auto& p : pins) {
    collectLinks(p.children, out);
    if (p.kind != Pin::Kind::File || fileExt(p.target) != L".lnk") continue;
    std::string bytes;
    if (readFile(expandEnv(p.target), bytes) && bytes.size() < 1024 * 1024) out.set(p.id, base64(bytes));
  }
}

std::string Config::exportText() const {
  Json j = toJson(), links = Json::object();
  for (auto& p : profiles) collectLinks(p.pins, links);
  j.set("links", std::move(links));
  Json images = Json::object();
  for (auto& p : profiles) collectImages(p.pins, images);
  j.set("images", std::move(images));
  return j.dump();
}

bool Config::checkBackup(const std::string& text, int& nProfiles, int& nPins) {
  Json j;
  nProfiles = nPins = 0;
  if (!Json::parse(text, j) || !j.isObj()) return false;
  auto ps = j.find("profiles");
  if (!ps || !ps->isArr() || ps->a.empty()) return false;
  for (auto& p : ps->a) {
    auto pins = p.isObj() ? p.find("pins") : nullptr;
    if (!pins || !pins->isArr()) return false;
    nProfiles++;
    for (auto& q : pins->a) {
      auto ch = q.find("children");
      nPins += ch && ch->isArr() ? (int)ch->a.size() : 1;
    }
  }
  return j.find("layout") && j.find("style");
}

static void restoreLinks(std::vector<Pin>& pins, const Json& links) {
  for (auto& p : pins) {
    restoreLinks(p.children, links);
    if (p.kind != Pin::Kind::File || fileExt(p.target) != L".lnk") continue;
    std::string b64 = links.str(p.id), bytes;
    if (b64.empty() || !unbase64(b64, bytes) || bytes.size() < 76) continue;
    std::wstring name = fileName(p.target), dst = joinPath(linksDir(), name);
    std::string have;
    if (readFile(dst, have) && have != bytes) dst = joinPath(linksDir(), fileStem(name) + L"-" + widen(newId()).substr(0, 8) + L".lnk");
    if (have != bytes && !writeFileAtomic(dst, bytes)) continue;
    p.target = dst;
  }
}

static void restoreImages(std::vector<Pin>& pins, const Json& images) {
  for (auto& p : pins) {
    restoreImages(p.children, images);
    std::string b64 = images.str(p.id), bytes;
    if (p.icon.empty() || b64.empty() || !unbase64(b64, bytes) || bytes.size() < 60 || bytes.compare(1, 3, "PNG")) continue;
    std::wstring dst = joinPath(imagesDir(), fileName(p.icon));
    std::string have;
    if (readFile(dst, have) && have != bytes) dst = joinPath(imagesDir(), fileStem(dst) + L"-" + widen(newId()).substr(0, 8) + L".png");
    if (have != bytes && !writeFileAtomic(dst, bytes)) continue;
    p.icon = dst;
  }
}

bool Config::importText(const std::string& text) {
  Json j;
  int a, b;
  if (!checkBackup(text, a, b) || !Json::parse(text, j)) return false;
  SHCreateDirectoryExW(nullptr, linksDir().c_str(), nullptr);
  CopyFileW(path().c_str(), (path() + L".before-import").c_str(), FALSE);
  fromJson(j);
  firstRun = false;
  if (auto l = j.find("links"); l && l->isObj())
    for (auto& p : profiles) restoreLinks(p.pins, *l);
  if (auto m = j.find("images"); m && m->isObj()) {
    SHCreateDirectoryExW(nullptr, imagesDir().c_str(), nullptr);
    for (auto& p : profiles) restoreImages(p.pins, *m);
  }
  return true;
}

// ---------------------------------------------------------------- pins
std::string pinText(const Pin& p, const std::string& profileId) {
  Json j = pinToJson(p);
  if (!profileId.empty()) j.set("profile", profileId);
  return j.dump();
}
bool pinParse(const std::string& text, Pin& p, std::string* profileId) {
  Json j;
  if (!Json::parse(text, j) || !j.isObj()) return false;
  p = pinFromJson(j);
  if (profileId) *profileId = j.str("profile");
  return !p.target.empty();
}

Pin* findPin(std::vector<Pin>& pins, const std::string& id) {
  for (auto& p : pins) {
    if (p.id == id) return &p;
    for (auto& c : p.children)
      if (c.id == id) return &c;
  }
  return nullptr;
}

bool ungroupPin(std::vector<Pin>& pins, const std::string& id) {
  for (size_t i = 0; i < pins.size(); i++) {
    if (pins[i].id != id || pins[i].kind != Pin::Kind::Group) continue;
    std::vector<Pin> kids = std::move(pins[i].children);
    pins.erase(pins.begin() + (ptrdiff_t)i);
    pins.insert(pins.begin() + (ptrdiff_t)i, std::make_move_iterator(kids.begin()), std::make_move_iterator(kids.end()));
    return true;
  }
  return false;
}

bool removePin(std::vector<Pin>& pins, const std::string& id, Pin* out) {
  for (size_t i = 0; i < pins.size(); i++) {
    if (pins[i].id == id) {
      if (out) *out = std::move(pins[i]);
      pins.erase(pins.begin() + (ptrdiff_t)i);
      return true;
    }
    auto& ch = pins[i].children;
    for (size_t k = 0; k < ch.size(); k++) {
      if (ch[k].id == id) {
        if (out) *out = std::move(ch[k]);
        ch.erase(ch.begin() + (ptrdiff_t)k);
        return true;
      }
    }
  }
  return false;
}

}  // namespace rt
