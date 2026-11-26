#include "scene.h"

#include <process.h>

#include "live.h"

namespace rt {

// ---------------------------------------------------------------- model
static SceneItem makeItem(const Config& cfg, const Pin& pin, const WindowList* running, bool top) {
  SceneItem it;
  it.pin = pin;
  it.label = pin.name;
  it.iconKey = IconCache::keyFor(pin);
  if (pin.kind == Pin::Kind::Group) {
    for (auto& c : pin.children) it.kids.push_back(makeItem(cfg, c, running, false));
    it.sub = std::to_wstring(it.kids.size()) + (it.kids.size() == 1 ? L" item" : L" items");
    return it;
  }
  if (running) {
    auto hits = running->matching(pin);
    it.windows = (int)hits.size();
    for (int h : hits)
      if (running->wins[(size_t)h].hwnd == running->foreground) it.active = true;
    if (it.windows > 0) it.sub = it.windows == 1 ? L"Open" : std::to_wstring(it.windows) + L" windows";
    if (top && cfg.windowsFan && it.windows >= 2) {
      for (int h : hits) {
        auto& w = running->wins[(size_t)h];
        SceneItem k;
        k.pin = pin;
        k.pin.kind = Pin::Kind::File;
        k.label = w.title;
        k.sub = pin.name;
        k.iconKey = it.iconKey;
        k.hwnd = w.hwnd;
        k.windows = 1;
        k.active = w.hwnd == running->foreground;
        it.kids.push_back(std::move(k));
        if (it.kids.size() >= 12) break;
      }
    }
  }
  if (it.sub.empty()) {
    if (pin.kind == Pin::Kind::Url) it.sub = L"Website";
    else if (pin.folder) it.sub = L"Folder";
  }
  return it;
}

SceneModel buildModel(const Config& cfg, const WindowList* running) {
  SceneModel m;
  const Profile& p = cfg.profile();
  m.profileName = p.name;
  m.profileColor = p.color;
  LayoutType shows = cfg.layoutFor(p);
  for (int i = 0; i < (int)cfg.profiles.size(); i++) {
    auto& q = cfg.profiles[(size_t)i];
    if (q.locked && i != cfg.activeProfile) continue;  // locked ones stay out
    if (i == cfg.activeProfile) m.profileIndex = (int)m.tabs.size();
    m.tabs.push_back({q.name, q.color, (int)q.pins.size()});
    m.tabProfile.push_back(i);
    // the centre stays one size between profiles that look alike; another arrangement redraws everything anyway
    if (cfg.layoutFor(q) == shows) m.ringFor = std::max(m.ringFor, (int)q.pins.size());
  }
  m.profileCount = (int)m.tabs.size();
  for (auto& pin : p.pins) m.items.push_back(makeItem(cfg, pin, running, true));
  return m;
}

Style effectiveStyle(const Config& cfg) {
  if (auto t = skins().get(cfg.skinNow())) {
    Style s = t->style;
    Config::Tune u = cfg.tune();
    for (Color* c : {&s.base, &s.accent, &s.accent2, &s.text, &s.border}) *c = SkinArt::tuneColor(*c, u);
    if (skinArt().skin() == t.get())
      if (std::wstring f = skinArt().fontByName(s.font); !f.empty()) s.font = narrow(f);
    return s;
  }
  Style s = cfg.style;
  if (s.systemAccent) {
    Color a = systemAccent();
    Hsv h = toHsv(a);
    // Keep the accent bright enough to read as light on dark panels.
    if (s.base.luma() < 0.5f) h.v = std::max(h.v, 0.85f);
    s.accent = fromHsv(h);
    h.h += 0.08f;
    s.accent2 = fromHsv(h);
  }
  return s;
}

std::unique_ptr<Layout> makeLayout(LayoutType t) {
  switch (t) {
    case LayoutType::Radial: return makeRadial();
    case LayoutType::Flow: return makeFlow();
    case LayoutType::Strip: return makeStrip();
    default: return makeFree(t);
  }
}

void dressLayout(Layout& l, const Config& cfg, bool persistArt) {
  l.cfg = cfg;
  l.cfg.layout = cfg.layoutNow();  // what this profile shows: skin layers and caches ask the layout's own copy
  l.skin = skins().get(cfg.skinNow());
  skinArt().use(l.skin, cfg.tune(), persistArt);
  l.st = effectiveStyle(cfg);
  l.view.reset();
  if (!l.skin) return;
  l.view = std::make_unique<SkinView>(l, l.skin);
  // A skin proposes sizes; the sliders stay in charge of making things bigger or smaller.
  const SkinWheel& w = l.skin->wheel;
  if (w.hub > 0) l.cfg.hubRadius = w.hub * (cfg.hubRadius / 80.f);
  if (w.thickness > 0) l.cfg.ringThickness = w.thickness * (cfg.ringThickness / 84.f);
  if (w.icon > 0) l.cfg.iconSize = w.icon * (cfg.iconSize / 48.f);
  if (w.shadow >= 0) l.st.shadow = w.shadow;
}

SkinPlace Layout::skinPlace() const {
  SkinPlace p;
  p.center = tiltCenter();
  p.stage = bounds();
  p.spot = p.center;
  p.cell = cfg.iconSize * env.s * 0.75f;
  p.wheel = std::min(p.stage.w(), p.stage.h()) * 0.5f;
  p.hub = p.wheel * 0.4f;
  p.ringIn = p.hub;
  p.ringOut = p.wheel;
  if (Pick k = pick(); k.valid()) p.spot = spot(k);
  return p;
}

bool Layout::tickSkin(float dt, const std::wstring& title, const std::wstring& sub) {
  if (!view) return false;
  view->caption(title, sub);
  Pick k = pick();
  if (k.item != seenPick_) {
    seenPick_ = k.item;
    if (k.valid() && time > 0.12f && !closing) view->hoverChanged(spot(k), cfg.iconSize * env.s * 0.6f);
  }
  return tickView(dt);
}

void Layout::drawSkinStage(Painter& p, const Backdrop* bd, float alpha, bool front) const {
  if (!view) return;
  SkinView::Stage s;
  s.at = skinPlace().center;
  s.alpha = alpha;
  s.glass = bd;
  if (front) {
    for (auto* g : {&skin->over, &skin->hub, &skin->front}) view->layers(p, *g, s, view->units);
    view->particles(p, alpha, false);
  } else {
    view->layers(p, skin->back, s, view->units);
    view->particles(p, alpha, true);
  }
}

bool Layout::tickView(float dt) {
  if (!view) return false;
  SkinPlace at = skinPlace();
  auto& had = view->units;
  had.moving = had.wheel > 1 && (fabsf(had.wheel - at.wheel) > 0.02f || fabsf(had.hub - at.hub) > 0.02f || fabsf(had.ring - at.ringOut) > 0.02f);
  view->units.wheel = at.wheel;
  view->units.hub = at.hub;
  view->units.ring = at.ringOut;
  view->units.cell = at.cell;
  view->units.px = drawScale();
  bool busy = view->tick(dt, at);
  view->vars[vOn] = pick().valid() ? 1.f : 0.f;
  view->vars[vIdle] = 1.f - view->vars[vOn];
  skinVars(view->vars);
  view->vars[vPress] = press;
  return busy;
}

// ---------------------------------------------------------------- lifecycle
void Layout::beginOpen() {
  closing = launched = false;
  closeT = 0;
  time = 0;
  open.snap(0);
  open.target = 1;
}

void Layout::beginClose(bool didLaunch, Pick p) {
  if (closing) return;
  closing = true;
  launched = didLaunch;
  launchPick = p;
  closeT = 0;
  if (didLaunch && p.valid()) {
    V2 at = spot(p), d = at - env.anchor;
    float l = std::max(1.f, d.len());
    if (view && !view->skin->burstLaunch.empty()) view->launched(at, skinPlace().cell, d);
    else if (st.burst) burst(at, d * (1.f / l));
  }
}

float Layout::fade() const {
  float a = saturate(open.x * 1.25f);
  if (closing) a *= 1.f - smooth01(closeT / (launched ? 0.19f : 0.14f));
  return a;
}

const SceneItem* Layout::itemAt(Pick k) const {
  if (k.item < 0 || k.item >= (int)model.items.size()) return nullptr;
  auto& it = model.items[(size_t)k.item];
  if (k.kid < 0) return &it;
  return k.kid < (int)it.kids.size() ? &it.kids[(size_t)k.kid] : nullptr;
}

void Layout::tickBase(float dt) {
  time += dt;
  if (cfg.reduceMotion) open.step(dt, 9.f, 1.f);
  else open.step(dt, 3.1f * st.speed, 0.74f);
  if (closing) closeT += dt * std::max(0.8f, st.speed);
}

// ---------------------------------------------------------------- profile dots
int Layout::dotAt(V2 p, float s) const {
  if (closing) return -1;
  for (int i = 0; i < dotCount(); i++) {
    V2 d = p - dotPos(i);
    if (fabsf(d.x) < 9.f * s && fabsf(d.y) < 11.f * s) return i;
  }
  return -1;
}

bool Layout::tickDots(float dt) {
  int n = dotCount();
  bool busy = false;
  if ((int)dotHot_.size() != n) dotHot_.assign((size_t)n, Spring{});
  for (int i = 0; i < n; i++) {
    dotHot_[(size_t)i].target = i == hotDot_ ? 1.f : 0.f;
    dotHot_[(size_t)i].step(dt, 7.f * motion(), 0.7f);
    busy |= !dotHot_[(size_t)i].settled();
  }
  if (tabsHold > 0) {
    tabsHold -= dt;
    busy = true;
  }
  int show = hotDot_ >= 0 ? hotDot_ : tabsHold > 0 && n ? model.profileIndex : -1;
  if (show >= 0 && show < n) {
    dotName_ = model.tabs[(size_t)show].name;
    dotSub_ = show == model.profileIndex ? L"In use now" : countText(model.tabs[(size_t)show].items);
  }
  float want = show >= 0 && !closing ? 1.f : 0.f;
  if (dotTag_ != want) {
    dotTag_ = want > dotTag_ ? std::min(1.f, dotTag_ + dt * 7.f * motion()) : std::max(0.f, dotTag_ - dt * 9.f * motion());
    busy = true;
  }
  return busy;
}

void Layout::drawDots(Painter& p, const Backdrop* bd, float s, float alpha) const {
  int n = dotCount();
  if (!n) return;
  V2 a = dotPos(0), b = dotPos(n - 1);
  RectF r(std::min(a.x, b.x) - 11.f * s, std::min(a.y, b.y) - 9.f * s, std::max(a.x, b.x) + 11.f * s, std::max(a.y, b.y) + 9.f * s);
  auto g = rrectGeo(r, 9.f * s);
  fillPanel(p, g.Get(), bd, alpha, 0.12f);
  p.stroke(g.Get(), st.border.withA(std::max(0.14f, st.borderOpacity * 0.6f) * alpha), 1.f * s);
  for (int i = 0; i < n; i++) {
    auto& t = model.tabs[(size_t)i];
    bool on = i == model.profileIndex;
    float h = i < (int)dotHot_.size() ? clampf(dotHot_[(size_t)i].x, 0.f, 1.3f) : 0.f;
    V2 q = dotPos(i);
    if (st.glow > 0.02f && (on || h > 0.02f)) p.circle(q, (7.f + 2.f * h) * s, t.color.withA(0.25f * st.glow * std::max(on ? 0.8f : 0.f, h) * alpha));
    p.circle(q, lerp(on ? 4.f : 2.8f, 5.2f, saturate(h)) * s, (on ? t.color : mix(st.text, t.color, 0.35f + 0.65f * saturate(h)).withA(lerp(0.55f, 1.f, saturate(h)))).alpha(alpha));
    if (on) p.circleStroke(q, (5.6f + h) * s, mix(t.color, Color(1, 1, 1), 0.3f).withA(0.55f * alpha), 1.f * s);
  }
}

// ---------------------------------------------------------------- particles
void Layout::tickParticles(float dt, V2 c, float rMin, float rMax) {
  float s = env.s;
  if (st.particles != Particles::Off && !closing && !cfg.reduceMotion) {
    size_t want = st.particles == Particles::Embers ? 34 : 46;
    int spawn = 0;
    while (bits_.size() < want && spawn++ < 2) {
      Bit b{};
      float a = rnd() * kTau, r = lerp(rMin, rMax, sqrtf(rnd()));
      b.pos = polar(c, a, r);
      b.seed = rnd() * 100.f;
      if (st.particles == Particles::Embers) {
        b.vel = {(rnd() - 0.5f) * 26.f * s, -(26.f + rnd() * 60.f) * s};
        b.life = 0.9f + rnd() * 1.5f;
        b.size = (0.8f + rnd() * 1.9f) * s;
      } else {
        b.vel = {(rnd() - 0.5f) * 5.f * s, (rnd() - 0.5f) * 5.f * s};
        b.life = 1.4f + rnd() * 2.2f;
        b.size = (0.6f + rnd() * 1.4f) * s;
      }
      bits_.push_back(b);
    }
  }
  auto advance = [&](std::vector<Bit>& v, float drag) {
    for (size_t i = 0; i < v.size();) {
      v[i].age += dt;
      if (v[i].age >= v[i].life) {
        v[i] = v.back();
        v.pop_back();
        continue;
      }
      v[i].pos += v[i].vel * dt;
      v[i].vel = v[i].vel * expf(-drag * dt);
      i++;
    }
  };
  advance(bits_, 0.4f);
  advance(sparks_, 4.2f);
}

void Layout::burst(V2 at, V2 dir) {
  float s = env.s;
  for (int i = 0; i < 30; i++) {
    Bit b{};
    float spread = (rnd() - 0.5f) * 2.6f;
    float ca = cosf(spread), sa = sinf(spread);
    V2 d{dir.x * ca - dir.y * sa, dir.x * sa + dir.y * ca};
    b.pos = at + d * (10.f * s);
    b.vel = d * ((220.f + rnd() * 620.f) * s);
    b.life = 0.16f + rnd() * 0.22f;
    b.size = (1.f + rnd() * 2.2f) * s;
    b.seed = rnd();
    sparks_.push_back(b);
  }
}

void Layout::drawParticles(Painter& p, float alpha) const {
  for (auto& b : bits_) {
    float t = b.age / b.life;
    float a = smooth01(t * 5.f) * (1.f - smooth01((t - 0.55f) / 0.45f));
    if (st.particles == Particles::Stars) a *= 0.55f + 0.45f * sinf(b.seed + time * 5.f);
    Color c = mix(st.accent2, st.accent, st.particles == Particles::Embers ? t : 0.5f + 0.5f * sinf(b.seed));
    p.circle(b.pos, b.size * 3.2f, c.withA(0.10f * a * alpha));
    p.circle(b.pos, b.size, c.withA(0.9f * a * alpha));
  }
  for (auto& b : sparks_) {
    float t = b.age / b.life;
    Color c = mix(Color(1, 1, 1, 1), mix(st.accent, st.accent2, b.seed), smooth01(t * 1.6f));
    float a = 1.f - t * t;
    p.circle(b.pos, b.size * 3.f, c.withA(0.14f * a));
    p.line(b.pos, b.pos - b.vel * 0.016f, c.withA(a), b.size, true);
  }
}

// ---------------------------------------------------------------- shared drawing
TextStyle Layout::label(float size, int weight, Align al, VAlign va) const {
  TextStyle t;
  t.family = widen(st.font);
  t.size = size;
  t.weight = weight;
  t.align = al;
  t.valign = va;
  return t;
}

static Color tileColor(const std::wstring& name) {
  uint32_t h = 2166136261u;
  for (wchar_t c : name) h = (h ^ (uint32_t)c) * 16777619u;
  return fromHsv({(h % 360) / 360.f, 0.55f, 0.82f});
}

void Layout::drawTileIcon(Painter& p, const SceneItem& it, V2 c, float size, float alpha, float hot, int depth, const IconLook& look) const {
  float h = size * 0.5f;
  RectF r(c.x - h, c.y - h, c.x + h, c.y + h);
  if (it.isGroup() && it.iconKey.empty()) {
    // A folder tile with up to four of its members inside.
    Color tile = st.text.withA(0.10f + 0.06f * hot);
    p.rrect(r, size * 0.26f, tile.alpha(alpha));
    p.rrectStroke(r, size * 0.26f, st.text.withA(0.22f * alpha), std::max(1.f, size * 0.02f));
    if (depth == 0) {
      size_t n = std::min<size_t>(4, it.kids.size());
      float q = size * 0.335f, off = size * 0.205f;
      for (size_t i = 0; i < n; i++) {
        V2 cc{c.x + ((i % 2) ? off : -off), c.y + ((i / 2) ? off : -off)};
        drawTileIcon(p, it.kids[i], cc, q, alpha, hot, 1, look);
      }
      if (!n) {
        TextStyle ts;
        ts.family = L"Segoe Fluent Icons";
        ts.size = size * 0.46f;
        ts.align = Align::Center;
        p.text(L"\xE8B7", ts, r, st.text.withA(0.7f * alpha));
      }
    }
    return;
  }
  auto put = [&](IconTone tone, float o) {
    D2D1_RECT_F crop{};
    auto* b = icons().get(it.iconKey, tone, look.ink, &crop, look.paper);
    if (!b || o <= 0.003f) return b != nullptr;
    if (tone == IconTone::Pixel) {  // whole multiples on whole pixels
      float n = crop.right - crop.left, k = std::max(1.f, roundf(size / n)), s2 = n * k;
      RectF q = RectF::xywh(roundf(c.x - s2 * 0.5f), roundf(c.y - s2 * 0.5f), s2, s2);
      D2D1_RECT_F d = q.f();
      p.dc->DrawBitmap(b, &d, o, D2D1_INTERPOLATION_MODE_NEAREST_NEIGHBOR, &crop, nullptr);
    } else if (look.round && tone == IconTone::Original) {
      ComPtr<ID2D1BitmapBrush1> br;
      float k = size / std::max(1.f, crop.right - crop.left);
      p.dc->CreateBitmapBrush(b, D2D1::BitmapBrushProperties1(D2D1_EXTEND_MODE_CLAMP, D2D1_EXTEND_MODE_CLAMP, D2D1_INTERPOLATION_MODE_HIGH_QUALITY_CUBIC),
                              D2D1::BrushProperties(o, D2D1::Matrix3x2F::Translation(-crop.left, -crop.top) * D2D1::Matrix3x2F::Scale(k, k) * D2D1::Matrix3x2F::Translation(r.l, r.t)), &br);
      if (br) p.dc->FillEllipse(D2D1::Ellipse(c.p(), h, h), br.Get());
    } else {
      p.bitmap(b, r, o, &crop);
    }
    return true;
  };
  if (look.tone == look.hot) {
    if (put(look.tone, alpha)) return;
  } else {
    bool any = false;
    if (hot < 0.999f) any |= put(look.tone, alpha * (1.f - hot) * (look.tone == IconTone::Muted || look.tone == IconTone::Mono ? 0.92f : 1.f));
    if (hot > 0.001f) any |= put(look.hot, alpha * hot);
    if (any) return;
  }
  if (!it.iconKey.empty() && !icons().failed(it.iconKey)) return;  // still loading
  Color tc = tileColor(it.label), letter(1, 1, 1);
  switch (look.tone) {
    case IconTone::Muted: tc = mix(Color(tc.luma(), tc.luma(), tc.luma()), tc, hot); break;
    case IconTone::Mono: tc = mix(mix(look.ink, Color(0, 0, 0), 0.25f), tc, hot); break;
    case IconTone::Duo: case IconTone::Ink: case IconTone::Engrave: {
      float q = look.hot == IconTone::Original ? hot : 0.f;
      letter = mix(look.paper, letter, q);
      tc = mix(look.ink, tc, q);
      break;
    }
    case IconTone::Neon: {
      p.rrectStroke(r.inset(size * 0.06f), size * 0.22f, look.ink.withA(alpha), std::max(1.5f, size * 0.035f));
      TextStyle ts = label(size * 0.5f, 600);
      std::wstring ch = it.label.empty() ? L"?" : it.label.substr(0, 1);
      CharUpperBuffW(ch.data(), 1);
      p.text(ch, ts, r, mix(look.ink, Color(1, 1, 1), 0.4f).withA(alpha));
      return;
    }
    default: break;
  }
  if (look.tone == IconTone::Pixel) {
    float u = std::max(2.f, roundf(size / 24.f)), q = floorf(size / u) * u * 0.5f;
    RectF b = RectF(roundf(c.x - q), roundf(c.y - q), roundf(c.x + q), roundf(c.y + q));
    p.dc->SetAntialiasMode(D2D1_ANTIALIAS_MODE_ALIASED);
    p.dc->FillRectangle(b.f(), p.solid(mix(tc, Color(0, 0, 0), 0.5f).withA(alpha)));
    p.dc->FillRectangle(b.inset(u).f(), p.solid(tc.withA(alpha)));
    p.dc->SetAntialiasMode(D2D1_ANTIALIAS_MODE_PER_PRIMITIVE);
  } else if (look.round) {
    p.circle(c, h, tc.withA(alpha));
  } else {
    auto br = p.linear({r.l, r.t}, {r.r, r.b}, {{0, mix(tc, Color(1, 1, 1), 0.15f).withA(alpha)}, {1, mix(tc, Color(0, 0, 0), 0.35f).withA(alpha)}});
    p.rrect(r, size * 0.26f, br.Get());
  }
  TextStyle ts = label(size * 0.5f, 600);
  ts.family = L"Segoe UI";
  std::wstring ch = it.label.empty() ? L"?" : it.label.substr(0, 1);
  CharUpperBuffW(ch.data(), 1);
  p.text(ch, ts, r, letter.withA(alpha));
}

void Layout::drawIconAs(Painter& p, const SceneItem& it, V2 c, float size, float alpha, float hot, const IconLook& look) const {
  if (alpha <= 0.003f || size < 1.f) return;
  drawTileIcon(p, it, c, size, alpha, hot, 0, look);
}

void Layout::drawIcon(Painter& p, const SceneItem& it, V2 c, float size, float alpha, float hot) const {
  drawIconAs(p, it, c, size, alpha, hot, {st.tone, IconTone::Original, st.accent, st.base, false});
}

void Layout::iconShadow(Painter& p, const SceneItem& it, V2 c, float size, Color col, float) const {
  if (it.isGroup() && it.iconKey.empty()) return;
  D2D1_RECT_F crop{};
  auto* b = icons().get(it.iconKey, IconTone::Shadow, Color(1, 1, 1), &crop);
  if (!b || col.a <= 0.003f) return;
  float h = size * 0.5f / (1.f - 2.f * kShadowInset);
  D2D1_RECT_F d = D2D1::RectF(c.x - h, c.y - h, c.x + h, c.y + h);
  p.dc->SetAntialiasMode(D2D1_ANTIALIAS_MODE_ALIASED);
  p.dc->FillOpacityMask(b, p.solid(col), &d, &crop);
  p.dc->SetAntialiasMode(D2D1_ANTIALIAS_MODE_PER_PRIMITIVE);
}

void Layout::entryVars(const SceneItem& it, const Entry& e) const {
  if (!view) return;
  float* v = view->vars;
  v[vHot] = e.hot;
  v[vIn] = 1;
  v[vI] = (float)e.index;
  v[vN] = (float)e.count;
  v[vA] = e.turn;
  v[vSpan] = 360.f / std::max(1, e.count);
  v[vRing] = 0;
  v[vRunning] = cfg.showRunning && it.windows > 0 && !it.hwnd ? 1.f : 0.f;
  v[vWindows] = (float)it.windows;
  v[vActive] = cfg.showRunning && it.active ? 1.f : 0.f;
  v[vGroup] = it.isGroup() ? 1.f : 0.f;
  v[vKid] = e.kid ? 1.f : 0.f;
  v[vNumber] = (float)(e.index + 1);
  v[vSeed] = fmodf((float)(e.index + 1) * 0.6180340f, 1.f);
  v[vNear] = saturate(e.hot);
}

void Layout::drawEntry(Painter& p, const Backdrop* bd, const SceneItem& it, V2 c, float half, float iconPx, const Entry& e) const {
  if (e.alpha <= 0.004f || half < 1) return;
  float s = env.s;
  bool marks = e.marks;
  if (view && skin->hasSlot) {
    const SkinSlot& S = e.kid ? skin->kid : skin->slot;
    entryVars(it, e);
    SkinView::Stage q;
    q.at = c;
    q.alpha = e.alpha;
    q.turn = e.turn;
    q.glass = bd;
    q.clock = e.clock;
    q.still = e.clock < 0;
    std::function<Geo(float)> shape = [&](float inset) { return tileGeo(c, std::max(1.f, half - inset)); };
    q.shape = &shape;
    view->slot(p, S, it, q, half, iconPx, e.scale, e.hot);
    marks = marks && S.marks;
  } else {
    drawTile(p, bd, c, half, e.hot, e.alpha);
    drawIcon(p, it, c, iconPx * e.scale * lerp(1.f, st.iconZoom, saturate(e.hot)), e.alpha * lerp(0.94f, 1.f, saturate(e.hot)), saturate(e.hot));
  }
  if (marks && cfg.showRunning && it.windows > 0 && !it.hwnd) {
    int dots = std::min(3, it.windows);
    float y = c.y + half + 5.f * s;
    if (it.active) p.rrect(RectF::xywh(c.x - 8.f * s, y - 1.5f * s, 16.f * s, 3.f * s), 1.5f * s, st.accent.withA(e.alpha));
    else
      for (int i = 0; i < dots; i++) p.circle({c.x + (i - (dots - 1) * 0.5f) * 7.f * s, y}, 1.9f * s, st.text.withA(0.75f * e.alpha));
  }
  if (it.isGroup() && !e.kid && (!view || skin->slot.chevron)) {
    V2 t{c.x + half * 0.80f, c.y + half * 0.80f};
    Color cc = st.text.withA(lerp(0.5f, 0.95f, saturate(e.hot)) * e.alpha);
    p.line({t.x - 3.5f * s, t.y - 1.5f * s}, {t.x, t.y + 2.f * s}, cc, 1.6f * s);
    p.line({t.x + 3.5f * s, t.y - 1.5f * s}, {t.x, t.y + 2.f * s}, cc, 1.6f * s);
  }
  if (cfg.showNumbers && e.index < 9 && !e.kid && (!view || skin->slot.badge))
    p.text(std::to_wstring(e.index + 1), label(10.5f * s, 600), RectF::xywh(c.x + half * 0.62f - 10 * s, c.y - half * 0.80f - 8 * s, 20 * s, 16 * s), st.text.withA(0.6f * e.alpha));
}

void Layout::fillPanel(Painter& p, ID2D1Geometry* g, const Backdrop* bd, float alpha, float boost) const {
  if (view && skin->panel.on && skin->panel.fill.any() && skin->panel.fill.kind != SkinPaint::Kind::Glass) {
    D2D1_RECT_F r{};
    g->GetBounds(nullptr, &r);
    V2 c{(r.left + r.right) * 0.5f, (r.top + r.bottom) * 0.5f}, half{(r.right - r.left) * 0.5f, (r.bottom - r.top) * 0.5f};
    if (auto br = view->panelBrush(p, skin->panel.fill, c, half, alpha)) p.fill(g, br.Get());
    return;
  }
  bool glassy = st.material == Material::Frosted || st.material == Material::Liquid;
  float have = bd && bd->bmp ? saturate(bd->fade) : 0.f;
  if (glassy && have > 0.003f) {
    auto br = p.image(bd->bmp.Get(), bd->origin, bd->scale, alpha * have);
    p.fill(g, br.Get());
  }
  float op = st.opacity;
  if (st.material == Material::Outline) op *= 0.86f;
  // With no picture behind, frosted panels need a little more body to stay readable.
  if (glassy) op = lerp(op, 1.f, 0.35f * (1.f - have));
  p.fill(g, st.base.withA(saturate(op + boost) * alpha));
}

void Layout::strokePanel(Painter& p, ID2D1Geometry* g, V2 a, V2 b, float alpha) const {
  if (view && skin->panel.on && skin->panel.stroke.any()) {
    D2D1_RECT_F r{};
    g->GetBounds(nullptr, &r);
    V2 c{(r.left + r.right) * 0.5f, (r.top + r.bottom) * 0.5f}, half{(r.right - r.left) * 0.5f, (r.bottom - r.top) * 0.5f};
    if (auto br = view->panelBrush(p, skin->panel.stroke, c, half, alpha)) p.stroke(g, br.Get(), skin->panel.width * env.s);
    return;
  }
  if (st.borderWidth <= 0.01f || st.borderOpacity <= 0.003f) return;
  float o = st.borderOpacity * alpha;
  float w = st.borderWidth * env.s;
  if (st.material == Material::Outline) {
    auto br = p.linear(a, b, {{0, st.border.withA(o)}, {1, mix(st.border, st.accent2, 0.6f).withA(o * 0.8f)}});
    p.stroke(g, br.Get(), w);
    return;
  }
  if (st.material == Material::Liquid) {
    auto br = p.linear(a, b, {{0, st.border.withA(o * 1.35f)}, {0.32f, st.border.withA(o * 0.25f)}, {0.68f, st.border.withA(o * 0.18f)}, {1, st.border.withA(o * 0.95f)}});
    p.stroke(g, br.Get(), w);
    p.stroke(g, st.border.withA(o * 0.10f), w * 4.5f);
    return;
  }
  auto br = p.linear(a, b, {{0, st.border.withA(o)}, {0.55f, st.border.withA(o * 0.35f)}, {1, st.border.withA(o * 0.22f)}});
  p.stroke(g, br.Get(), w);
}

// ---------------------------------------------------------------- backdrop
bool wantsBackdrop(const Style& st) {
  if (st.shape == SlotShape::None) return false;
  return st.material == Material::Frosted || st.material == Material::Liquid;
}

Backdrop makeBackdrop(ID2D1Bitmap1* src, RectF area, const Layout& layout) {
  Backdrop out;
  auto& g = gfx();
  if (!src || !g.ready()) return out;
  const Style& st = layout.st;
  D2D1_SIZE_U sz = src->GetPixelSize();
  if (!sz.width || !sz.height) return out;
  float pxPer = (float)sz.width / std::max(1.f, area.w());  // source px per viewport px
  bool liquid = st.material == Material::Liquid;
  int down = liquid ? 1 : 2;                               // heavy blur does not need full resolution
  int w = std::max(1, (int)sz.width / down), h = std::max(1, (int)sz.height / down);
  auto tgt = g.target(w, h);
  if (!tgt) return out;

  ComPtr<ID2D1Effect> scale, blur, sat, disp, soft;
  g.aux->CreateEffect(CLSID_D2D1Scale, &scale);
  g.aux->CreateEffect(CLSID_D2D1GaussianBlur, &blur);
  g.aux->CreateEffect(CLSID_D2D1Saturation, &sat);
  if (!scale || !blur || !sat) return out;
  scale->SetInput(0, src);
  scale->SetValue(fx::kScale, D2D1::Vector2F((float)w / sz.width, (float)h / sz.height));
  scale->SetValue(fx::kScaleInterpolation, fx::kScaleLinear);
  scale->SetValue(fx::kScaleBorder, D2D1_BORDER_MODE_HARD);
  blur->SetInputEffect(0, scale.Get());
  blur->SetValue(D2D1_GAUSSIANBLUR_PROP_STANDARD_DEVIATION, std::max(0.1f, st.blur * layout.env.s * pxPer / down));
  blur->SetValue(D2D1_GAUSSIANBLUR_PROP_BORDER_MODE, D2D1_BORDER_MODE_HARD);
  blur->SetValue(D2D1_GAUSSIANBLUR_PROP_OPTIMIZATION, fx::kBlurBalanced);
  sat->SetInputEffect(0, blur.Get());
  sat->SetValue(fx::kSaturation, liquid ? 1.15f : 1.35f);
  ID2D1Effect* last = sat.Get();

  ComPtr<ID2D1Bitmap1> map;
  if (liquid && st.refraction > 0.01f) {
    // Edge lens: near a panel's rim, sample the desktop from further inside.
    // It only depends on geometry, so it is kept between openings.
    const int cell = 2;
    int mw = std::max(1, (w + cell - 1) / cell), mh = std::max(1, (h + cell - 1) / cell);
    const Config& c = layout.cfg;
    V2 ctr = layout.tiltCenter();
    char key[256];
    snprintf(key, sizeof key, "%d %d %d %.1f %.1f %.1f %.1f %d %d %d %d %.1f %.1f %.1f %.1f %.2f %.3f %d", (int)c.layout, w, h, area.l - ctr.x, area.t - ctr.y, area.w(), area.h(),
             (int)st.shape, (int)layout.model.items.size(), c.perRing, (int)c.overflow, c.hubRadius, c.ringThickness, c.iconSize, st.gap, layout.env.s, pxPer, (int)c.stripEdge);
    static std::string madeFor;
    static std::vector<uint8_t> px;
    if (madeFor != key || px.size() != (size_t)mw * mh * 4) {
      px.assign((size_t)mw * mh * 4, 0);
      struct Band {
        const Layout* l;
        RectF area;
        float step, lens;
        int mw, y0, y1;
        uint8_t* out;
        static unsigned __stdcall run(void* p) {
          auto& t = *(Band*)p;
          for (int y = t.y0; y < t.y1; y++) {
            for (int x = 0; x < t.mw; x++) {
              V2 vp{t.area.l + (x + 0.5f) * t.step, t.area.t + (y + 0.5f) * t.step}, n;
              float d = t.l->glass(vp, n), dx = 0, dy = 0;
              if (d >= 0 && d < t.lens) {
                float q = 1.f - d / t.lens;
                float k = q * q * (0.35f + 0.65f * q);
                dx = -n.x * k;
                dy = -n.y * k;
              }
              uint8_t* o = t.out + ((size_t)y * t.mw + x) * 4;
              o[0] = 128;
              o[1] = (uint8_t)lroundf(clampf(127.5f + dy * 127.f, 0.f, 255.f));
              o[2] = (uint8_t)lroundf(clampf(127.5f + dx * 127.f, 0.f, 255.f));
              o[3] = 255;
            }
          }
          return 0;
        }
      };
      const int bands = 4;
      Band job[bands];
      HANDLE th[bands] = {};
      int started = 0;
      for (int i = 0; i < bands; i++) {
        job[i] = {&layout, area, cell * down / pxPer, 26.f * layout.env.s, mw, mh * i / bands, mh * (i + 1) / bands, px.data()};
        if (i + 1 == bands) {
          Band::run(&job[i]);
        } else if (HANDLE t = (HANDLE)_beginthreadex(nullptr, 0, Band::run, &job[i], 0, nullptr)) {
          th[started++] = t;
        } else {
          Band::run(&job[i]);
        }
      }
      if (started) WaitForMultipleObjects((DWORD)started, th, TRUE, INFINITE);
      for (int i = 0; i < started; i++) CloseHandle(th[i]);
      madeFor = key;
    }
    map = g.bitmap(px.data(), mw, mh, mw * 4);
    g.aux->CreateEffect(CLSID_D2D1DisplacementMap, &disp);
    ComPtr<ID2D1Effect> up;
    g.aux->CreateEffect(CLSID_D2D1Scale, &up);
    if (map && disp && up) {
      up->SetInput(0, map.Get());
      up->SetValue(fx::kScale, D2D1::Vector2F((float)cell, (float)cell));
      up->SetValue(fx::kScaleInterpolation, fx::kScaleLinear);
      up->SetValue(fx::kScaleBorder, D2D1_BORDER_MODE_HARD);
      disp->SetInputEffect(0, last);
      disp->SetInputEffect(1, up.Get());
      disp->SetValue(D2D1_DISPLACEMENTMAP_PROP_SCALE, st.refraction * 96.f * layout.env.s * pxPer / down);
      disp->SetValue(D2D1_DISPLACEMENTMAP_PROP_X_CHANNEL_SELECT, D2D1_CHANNEL_SELECTOR_R);
      disp->SetValue(D2D1_DISPLACEMENTMAP_PROP_Y_CHANNEL_SELECT, D2D1_CHANNEL_SELECTOR_G);
      last = disp.Get();
      // A whisper of blur hides the steps of an 8-bit displacement map.
      g.aux->CreateEffect(CLSID_D2D1GaussianBlur, &soft);
      if (soft) {
        soft->SetInputEffect(0, last);
        soft->SetValue(D2D1_GAUSSIANBLUR_PROP_STANDARD_DEVIATION, 1.35f * layout.env.s * pxPer / down);
        soft->SetValue(D2D1_GAUSSIANBLUR_PROP_BORDER_MODE, D2D1_BORDER_MODE_HARD);
        last = soft.Get();
      }
    }
  }

  g.aux->SetTarget(tgt.Get());
  g.aux->SetTransform(D2D1::Matrix3x2F::Identity());
  g.aux->BeginDraw();
  g.aux->Clear(D2D1::ColorF(0, 0, 0, 1));
  g.aux->DrawImage(last);
  HRESULT hr = g.aux->EndDraw();
  g.aux->SetTarget(nullptr);
  if (FAILED(hr)) return out;
  out.bmp = tgt;
  out.origin = {area.l, area.t};
  out.scale = area.w() / (float)w;
  return out;
}

// ---------------------------------------------------------------- tags, tiles and flyouts (flow + strip)
void Layout::drawTag(Painter& p, const Backdrop* bd, V2 at, V2 dir, const std::wstring& title, const std::wstring& sub, float alpha, RectF keepIn) const {
  if (title.empty() || alpha <= 0.01f) return;
  float s = env.s;
  TextStyle t1 = label(16.f * s, 600, Align::Left, VAlign::Top), t2 = label(11.5f * s, 500, Align::Left, VAlign::Top);
  float maxW = 300.f * s;
  V2 m1 = gfx().measure(title, t1, 10000.f), m2 = sub.empty() ? V2{} : gfx().measure(sub, t2, 10000.f);
  float tw = std::min(maxW, std::max(m1.x, m2.x)) + 1.f;
  float w = tw + 28.f * s, h = m1.y + (sub.empty() ? 0 : m2.y + 1.f * s) + 16.f * s;
  V2 c = at + V2{dir.x * w * 0.5f, dir.y * h * 0.5f};
  RectF r = RectF::xywh(c.x - w * 0.5f, c.y - h * 0.5f, w, h);
  float dx = 0, dy = 0;
  if (r.l < keepIn.l) dx = keepIn.l - r.l;
  if (r.r > keepIn.r) dx = keepIn.r - r.r;
  if (r.t < keepIn.t) dy = keepIn.t - r.t;
  if (r.b > keepIn.b) dy = keepIn.b - r.b;
  r = r.offset(dx, dy);
  bool bare = st.shape == SlotShape::None;
  Align al = dir.x < -0.5f ? Align::Right : (dir.x > 0.5f ? Align::Left : Align::Center);
  t1.align = t2.align = al;
  RectF tr = r.inset(14.f * s, 8.f * s);
  RectF sr = tr;
  sr.t += m1.y + 1.f * s;
  if (bare) {
    p.textHalo(title, t1, tr, st.text.withA(alpha), halo(alpha), 5.f * s);
    p.textHalo(sub, t2, sr, st.text.withA(0.75f * alpha), halo(alpha), 4.f * s);
    return;
  }
  if (view && skin->tag.on) {
    view->panel(p, skin->tag, r, s, alpha, bd);
    Color tc = skin->tag.hasText ? view->color(skin->tag.text) : st.text;
    t1.align = t2.align = al;
    p.text(title, t1, tr, tc.withA(alpha));
    p.text(sub, t2, sr, tc.withA(0.75f * alpha));
    return;
  }
  Geo g = st.shape == SlotShape::Blade ? cutRectGeo(r, 9.f * s) : rrectGeo(r, std::min(h * 0.5f, std::max(6.f, st.corner) * s));
  if (st.shadow > 0.01f) p.glow(g.Get(), Color(0, 0, 0, 0.45f * st.shadow * alpha), 9.f * s, 0, true, false);
  fillPanel(p, g.Get(), bd, alpha, 0.14f);
  strokePanel(p, g.Get(), {r.l, r.t}, {r.r, r.b}, alpha);
  // accent bar on the side facing the icon
  if (al == Align::Right) p.rrect(RectF::xywh(r.r - 5.f * s, r.t + h * 0.26f, 2.6f * s, h * 0.48f), 1.3f * s, st.accent.withA(alpha));
  else if (al == Align::Left) p.rrect(RectF::xywh(r.l + 2.4f * s, r.t + h * 0.26f, 2.6f * s, h * 0.48f), 1.3f * s, st.accent.withA(alpha));
  p.text(title, t1, tr, st.text.withA(alpha));
  p.text(sub, t2, sr, mix(st.text, st.accent, 0.45f).withA(0.85f * alpha));
}

Geo Layout::tileGeo(V2 c, float h) const {
  float s = env.s;
  RectF r(c.x - h, c.y - h, c.x + h, c.y + h);
  if (hexPlates_ && st.shape != SlotShape::Orb && st.shape != SlotShape::Petal) return hexGeo(c, h * 1.13f, 0, std::min(st.corner, 12.f) * s);
  switch (st.shape) {
    case SlotShape::Blade: return cutRectGeo(r, std::min(st.corner * s, h * 0.5f));
    case SlotShape::Orb: return circleGeo(c, h);
    case SlotShape::Hex: return hexGeo(c, h * 1.1f, 0, st.corner * s);
    case SlotShape::Petal: return rrectGeo(r, h * 0.72f);
    default: return rrectGeo(r, std::min(st.corner * s, h * 0.6f));
  }
}

void Layout::drawTile(Painter& p, const Backdrop* bd, V2 c, float h, float hot, float alpha) const {
  if (st.shape == SlotShape::None) {
    if (hot > 0.01f) {
      float R = h * 1.7f;
      auto br = p.radial(c, R, R, {{0, st.accent.withA(0.5f * hot * alpha * (0.4f + 0.6f * st.glow))}, {1, st.accent.withA(0)}});
      p.dc->FillEllipse(D2D1::Ellipse(c.p(), R, R), br.Get());
    }
    return;
  }
  bool plate = st.shape != SlotShape::Wedge || plates_;  // wedge styles use one shared panel in the flow and the strip
  if (!plate && hot < 0.01f) return;
  auto g = tileGeo(c, h);
  if (plate) {
    fillPanel(p, g.Get(), bd, alpha, 0.f);
    strokePanel(p, g.Get(), {c.x - h, c.y - h}, {c.x + h, c.y + h}, alpha * (1.f - 0.6f * saturate(hot)));
  }
  if (hot > 0.01f) {
    float q = saturate(hot);
    auto br = p.linear({c.x - h, c.y - h}, {c.x + h, c.y + h}, {{0, st.accent.withA(0.42f * q * alpha)}, {1, st.accent2.withA(0.28f * q * alpha)}});
    p.fill(g.Get(), br.Get());
    if (st.glow > 0.01f) p.glow(g.Get(), st.accent.withA(0.75f * st.glow * q * alpha), (4.f + 8.f * st.glow) * env.s, 2.2f * env.s);
    p.stroke(g.Get(), st.accent.withA(0.9f * q * alpha), std::max(1.f, st.borderWidth) * env.s);
  }
}

void Layout::drawFlyout(Painter& p, const Backdrop* bd, const Flyout& f, const SceneItem& owner, float alpha) const {
  float o = clampf(f.open.x, 0.f, 1.1f);
  if (o <= 0.01f || f.cells.empty()) return;
  float a = alpha * saturate(o * 1.3f);
  V2 c = f.rect.center();
  // grows out of the icon it belongs to
  V2 pc = lerp(f.from, c, lerp(0.35f, 1.f, saturate(o)));
  float hw = f.rect.w() * 0.5f * lerp(0.4f, 1.f, o), hh = f.rect.h() * 0.5f * lerp(0.4f, 1.f, o);
  RectF r(pc.x - hw, pc.y - hh, pc.x + hw, pc.y + hh);
  bool bare = st.shape == SlotShape::None;
  if (view && skin->panel.on) {
    view->panel(p, skin->panel, r, env.s, a, bd);
  } else if (!bare) {
    Geo g = st.shape == SlotShape::Blade ? cutRectGeo(r, 14.f * env.s) : rrectGeo(r, (st.corner + 8.f) * env.s);
    if (st.shadow > 0.01f) p.glow(g.Get(), Color(0, 0, 0, 0.5f * st.shadow * a), 14.f * env.s, 0, true, false);
    fillPanel(p, g.Get(), bd, a, 0.10f);
    strokePanel(p, g.Get(), {r.l, r.t}, {r.r, r.b}, a);
  }
  for (size_t i = 0; i < f.cells.size() && i < owner.kids.size(); i++) {
    V2 q = lerp(f.from, f.cells[i], saturate(o));
    float hot = i < f.hot.size() ? f.hot[i].x : 0.f;
    float k = lerp(0.3f, 1.f, o);
    if (view && skin->hasSlot) {
      Entry e;
      e.index = (int)i;
      e.count = (int)owner.kids.size();
      e.hot = hot;
      e.alpha = a;
      e.kid = true;
      drawEntry(p, bd, owner.kids[i], q, f.icon * 0.72f * k, f.icon * k, e);
      continue;
    }
    if (hot > 0.01f) drawTile(p, nullptr, q, f.icon * 0.72f * k, hot, a);
    drawIcon(p, owner.kids[i], q, f.icon * k * lerp(1.f, 1.f + (st.iconZoom - 1.f) * 0.6f, saturate(hot)), a, saturate(hot));
    if (cfg.showRunning && owner.kids[i].windows > 0)
      p.circle({q.x, q.y + f.icon * 0.66f}, 1.9f * env.s, (owner.kids[i].active ? st.accent : st.text.withA(0.75f)).alpha(a));
  }
  if (f.caption > 0) {
    std::wstring t = f.hotKid >= 0 && f.hotKid < (int)owner.kids.size() ? owner.kids[(size_t)f.hotKid].label : owner.label;
    RectF tr(f.rect.l + 14.f * env.s, f.rect.b - f.caption - 2.f * env.s, f.rect.r - 14.f * env.s, f.rect.b - 6.f * env.s);
    float ta = a * smooth01((o - 0.6f) / 0.4f);
    if (bare) p.textHalo(t, label(12.5f * env.s, 600), tr, st.text.withA(ta), halo(ta), 4.f * env.s);
    else p.text(t, label(12.5f * env.s, 600), tr, (f.hotKid >= 0 ? st.text : mix(st.text, st.accent, 0.4f)).withA(ta));
  }
}

// ---------------------------------------------------------------- flyout
void Flyout::layoutCells(int n, V2 origin, V2 dir, float cellPx, float iconPx, RectF clampTo) {
  cell = cellPx;
  icon = iconPx;
  from = origin;
  int cols = n <= 4 ? std::max(1, n) : std::min(5, (int)ceilf(sqrtf((float)n * 1.6f)));
  int rows = std::max(1, (n + cols - 1) / cols);
  float pad = cellPx * 0.16f;
  float w = cols * cellPx + pad * 2, h = rows * cellPx + pad * 2;
  float gapOut = cellPx * 0.18f;
  V2 c = origin + V2{dir.x * (w * 0.5f + gapOut), dir.y * (h * 0.5f + gapOut)};
  rect = RectF::xywh(c.x - w * 0.5f, c.y - h * 0.5f, w, h);
  float dx = 0, dy = 0;
  if (rect.l < clampTo.l) dx = clampTo.l - rect.l;
  if (rect.r > clampTo.r) dx = clampTo.r - rect.r;
  if (rect.t < clampTo.t) dy = clampTo.t - rect.t;
  if (rect.b > clampTo.b) dy = clampTo.b - rect.b;
  rect = rect.offset(dx, dy);
  cells.clear();
  for (int i = 0; i < n; i++) {
    int r = i / cols, inRow = std::min(cols, n - r * cols), cidx = i % cols;
    float x0 = rect.cx() - inRow * cellPx * 0.5f;
    cells.push_back({x0 + (cidx + 0.5f) * cellPx, rect.t + pad + (r + 0.5f) * cellPx});
  }
  hot.assign((size_t)n, Spring(0.f));
}

int Flyout::hit(V2 p) const {
  if (!rect.inset(-cell * 0.2f).contains(p)) return -1;
  int best = -1;
  float bd = cell * 0.75f;
  for (size_t i = 0; i < cells.size(); i++) {
    float d = (cells[i] - p).len();
    if (d < bd) { bd = d; best = (int)i; }
  }
  return best;
}

}  // namespace rt
