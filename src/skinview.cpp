#include "skinview.h"

#include "live.h"
#include "scene.h"

namespace rt {

namespace {
D2D1_MATRIX_3X2_F now(ID2D1DeviceContext* dc) {
  D2D1_MATRIX_3X2_F m;
  dc->GetTransform(&m);
  return m;
}
const D2D1::Matrix3x2F& as(const D2D1_MATRIX_3X2_F& m) { return *D2D1::Matrix3x2F::ReinterpretBaseType(&m); }
bool sane(float v, float most = 60000.f) { return v > -most && v < most; }  // false for what is not a number, too
}  // namespace

// ---------------------------------------------------------------- arrival
float SkinView::arrived(const SkinIntro& in, float time, float order, float speed) {
  float t = (time * speed - in.delay - in.stagger * order) / std::max(0.01f, in.time);
  return t <= 0 ? 0.f : t >= 1 ? 1.f : easeAt(in.ease, t);
}
float SkinView::orderOf(SkinIntro::Order o, int i, int n, float angle, uint32_t seed) {
  switch (o) {
    case SkinIntro::Order::Ring: return (float)i;
    case SkinIntro::Order::Reverse: return (float)(n - 1 - i);
    case SkinIntro::Order::Random: return (float)((seed * 2654435761u >> 8) % (uint32_t)std::max(1, n));
    case SkinIntro::Order::Pairs: return (float)(i % std::max(1, (n + 1) / 2));
    default: return fabsf(wrapAngle(angle)) / kPi * std::max(1, n) * 0.5f;
  }
}

// ---------------------------------------------------------------- colours and text
Color SkinView::color(const SkinColor& c, const SceneItem* it) const {
  Color o;
  switch (c.from) {
    case SkinColor::From::Accent: o = L.st.accent; break;
    case SkinColor::From::Accent2: o = L.st.accent2; break;
    case SkinColor::From::Text: o = L.st.text; break;
    case SkinColor::From::Base: o = L.st.base; break;
    case SkinColor::From::Border: o = L.st.border; break;
    case SkinColor::From::Profile: o = L.model.profileColor; break;
    case SkinColor::From::Item: o = it ? icons().tint(it->iconKey, L.st.accent) : L.st.accent; break;
    default: o = skinArt().tuned(c.c); break;
  }
  return o.withA(c.a);
}

std::wstring SkinView::expand(const std::wstring& t, const SceneItem* it, bool old) const {
  size_t at = t.find(L'{');
  if (at == std::wstring::npos) return t;
  std::wstring o;
  SYSTEMTIME n;
  GetLocalTime(&n);
  if (live().staged) {
    n.wYear = 2026; n.wMonth = 11; n.wDay = 25; n.wDayOfWeek = 3; n.wHour = 10; n.wMinute = 9; n.wSecond = 36; n.wMilliseconds = 0;
  }
  auto two = [](int v) { wchar_t b[8]; swprintf(b, 8, L"%02d", v); return std::wstring(b); };
  auto date = [&](const wchar_t* f) {
    wchar_t b[80] = {};
    GetDateFormatEx(LOCALE_NAME_USER_DEFAULT, 0, &n, f, b, 80, nullptr);
    return std::wstring(b);
  };
  auto percent = [](float v) { return std::to_wstring((int)lroundf(saturate(v) * 100.f)); };
  size_t from = 0;
  while (at != std::wstring::npos) {
    o.append(t, from, at - from);
    size_t e = t.find(L'}', at);
    if (e == std::wstring::npos) {
      from = at;
      break;
    }
    std::wstring k = t.substr(at + 1, e - at - 1);
    if (k == L"title") o += old ? titleOld_ : title_;
    else if (k == L"sub") o += old ? subOld_ : sub_;
    else if (k == L"label") o += it ? it->label : L"";
    else if (k == L"number") o += std::to_wstring((int)vars[vNumber]);
    else if (k == L"windows") o += std::to_wstring(it ? it->windows : 0);
    else if (k == L"profile") o += L.model.profileName;
    else if (k == L"count") o += std::to_wstring(L.model.items.size());
    else if (k == L"time") {
      wchar_t b[32] = {};
      GetTimeFormatEx(LOCALE_NAME_USER_DEFAULT, TIME_NOSECONDS, &n, nullptr, b, 32);
      o += b;
    } else if (k == L"hh") o += two(n.wHour);
    else if (k == L"h12") o += std::to_wstring(n.wHour % 12 ? n.wHour % 12 : 12);
    else if (k == L"mm") o += two(n.wMinute);
    else if (k == L"ss") o += two(n.wSecond);
    else if (k == L"ampm") o += n.wHour < 12 ? L"AM" : L"PM";
    else if (k == L"date") o += date(L"ddd d MMM");
    else if (k == L"weekday") o += date(L"dddd");
    else if (k == L"wd") o += date(L"ddd");
    else if (k == L"month") o += date(L"MMMM");
    else if (k == L"mon") o += date(L"MMM");
    else if (k == L"day") o += std::to_wstring(n.wDay);
    else if (k == L"year") o += std::to_wstring(n.wYear);
    else if (k == L"cpu") o += percent(vars[vCpu]);
    else if (k == L"ram") o += percent(vars[vRam]);
    else if (k == L"battery") o += percent(vars[vBattery]);
    else if (k == L"page") o += std::to_wstring((int)vars[vPage]);
    else if (k == L"pages") o += std::to_wstring((int)vars[vPages]);
    else o += t.substr(at, e - at + 1);
    from = e + 1;
    at = t.find(L'{', from);
  }
  o.append(t, from, std::wstring::npos);
  return o;
}

void SkinView::caption(const std::wstring& title, const std::wstring& sub) {
  if (title == title_ && sub == sub_) return;
  titleOld_ = title_;
  subOld_ = sub_;
  title_ = title;
  sub_ = sub;
  swap_ = 0;
}

// ---------------------------------------------------------------- one frame
bool SkinView::tick(float dt, const SkinPlace& at) {
  at_ = at;
  dt_ = dt;
  frameNo_++;
  budget_ = 9000;
  skinArt().tick(dt);
  bool calm = L.cfg.reduceMotion;
  const LiveValues& v = live().sample(dt, skin->system, skin->sound);
  float* q = vars;
  q[vTime] = calm ? 0.f : L.time;
  q[vMotion] = calm ? 0.f : 1.f;
  q[vOpen] = L.open.x;
  q[vFade] = L.fade();
  q[vClosing] = L.closing ? saturate(L.closeT / 0.18f) : 0.f;
  q[vLaunch] = L.closing && L.launched ? saturate(L.closeT / 0.18f) : 0.f;
  V2 d = L.pointerKnown ? L.ptr - at.center : V2{};
  float w = std::max(1.f, at.wheel);
  // Eased, so artwork that follows the pointer never jerks.
  float k = 1.f - expf(-dt * 12.f);
  q[vPx] += (clampf(d.x / w, -2.f, 2.f) - q[vPx]) * k;
  q[vPy] += (clampf(d.y / w, -2.f, 2.f) - q[vPy]) * k;
  q[vPDist] = sqrtf(q[vPx] * q[vPx] + q[vPy] * q[vPy]);
  q[vPAngle] = q[vPDist] > 0.001f ? atan2f(q[vPx], -q[vPy]) * 180.f / kPi : 0.f;
  q[vProfile] = (float)L.model.profileIndex;
  q[vProfiles] = (float)L.model.profileCount;
  q[vItems] = (float)L.model.items.size();
  q[vSticky] = L.sticky ? 1.f : 0.f;
  q[vNumbers] = L.cfg.showNumbers ? 1.f : 0.f;
  q[vRadius] = at.wheel / units.px;
  q[vHub] = at.hub / units.px;
  q[vRingIn] = at.ringIn / units.px;
  q[vRingOut] = at.ringOut / units.px;
  q[vHour] = v.hour;
  q[vMinute] = v.minute;
  q[vSecond] = v.second;
  q[vTick] = v.tick;
  q[vDay] = v.day;
  q[vMonth] = v.month;
  q[vCpu] = v.cpu;
  q[vRam] = v.ram;
  q[vBattery] = v.battery;
  q[vCharging] = v.charging;
  q[vSound] = v.sound;
  q[vSoundL] = v.soundL;
  q[vSoundR] = v.soundR;
  q[vBeat] = v.beat;

  bool busy = skinArt().pending();
  if (swap_ < 1) {
    swap_ = std::min(1.f, swap_ + dt * 8.f * L.motion());
    busy = true;
  }
  // artwork that follows the pointer is still moving
  busy |= fabsf(clampf(d.x / w, -2.f, 2.f) - q[vPx]) > 0.002f || fabsf(clampf(d.y / w, -2.f, 2.f) - q[vPy]) > 0.002f;

  // particles
  if (emit_.empty() && !skin->particles.empty())
    for (auto& p : skin->particles) emit_.push_back({&p, {}, 0});
  float s = units.px;
  for (auto& e : emit_) {
    const SkinParticles& p = *e.p;
    if (calm) continue;
    if (!L.closing && p.when.get(q) > 0) {
      e.owed += std::max(0.f, p.rate.get(q)) * dt;
      e.owed = std::min(e.owed, 12.f);
      while (e.owed >= 1.f) {
        e.owed -= 1.f;
        if ((int)e.bits.size() >= p.max) continue;
        float a = rnd() * kTau, R0 = 0, R1 = at.wheel;
        V2 where = at.center;
        switch (p.area) {
          case SkinParticles::Area::Ring: R0 = at.ringIn; R1 = at.ringOut; break;
          case SkinParticles::Area::Hub: R0 = 0; R1 = at.hub; break;
          case SkinParticles::Area::Rim: R0 = at.wheel * 0.97f; R1 = at.wheel * 1.02f; break;
          case SkinParticles::Area::Slot:
            if (q[vOn] < 0.3f) continue;
            where = at.spot;
            R1 = at.cell;
            break;
          case SkinParticles::Area::Pointer:
            if (!L.pointerKnown) continue;
            where = L.ptr;
            R1 = 4 * s;
            break;
          case SkinParticles::Area::Stage: {
            V2 pos{lerp(at.stage.l, at.stage.r, rnd()), lerp(at.stage.t, at.stage.b, rnd())};
            e.bits.push_back(born(p, pos, angleOf(pos - at.center)));
            continue;
          }
          default: break;
        }
        V2 pos = polar(where, a, sqrtf(lerp(R0 * R0, R1 * R1, rnd())));
        e.bits.push_back(born(p, pos, a));
      }
    }
  }
  auto move = [&](Emitter& e) {
    const SkinParticles& p = *e.p;
    for (size_t i = 0; i < e.bits.size();) {
      Bit& b = e.bits[i];
      b.age += dt;
      if (b.age >= b.life) {
        b = e.bits.back();
        e.bits.pop_back();
        continue;
      }
      b.vel.y += p.gravity * s * dt;
      b.vel = b.vel * expf(-p.drag * dt);
      if (p.swirl != 0) {
        V2 o = b.pos - at.center;
        b.vel += V2{-o.y, o.x} * (p.swirl * dt);
      }
      b.pos += b.vel * dt;
      if (p.sway > 0) b.pos.x += cosf((b.age * p.swayHz + b.seed) * kTau) * p.sway * s * dt;
      b.rot += b.spin * dt;
      i++;
    }
    busy |= !e.bits.empty();
  };
  for (auto& e : emit_) move(e);
  for (auto& e : bursts_) move(e);
  for (size_t i = 0; i < bursts_.size();) {
    if (bursts_[i].bits.empty()) bursts_.erase(bursts_.begin() + (ptrdiff_t)i);
    else i++;
  }
  return busy || (skin->alive && !calm);
}

SkinView::Bit SkinView::born(const SkinParticles& q, V2 where, float outAngle) const {
  Bit b{};
  float s = units.px;
  float a = rnd(q.dir) * kPi / 180.f + (q.outward ? outAngle : 0.f);
  b.pos = where;
  b.vel = V2{sinf(a), -cosf(a)} * (rnd(q.speed) * s);
  b.life = std::max(0.02f, rnd(q.life));
  b.size = rnd(q.size) * s;
  b.spin = rnd(q.spin);
  b.rot = q.spin[0] != 0 || q.spin[1] != 0 ? rnd() * 360.f : 0.f;
  b.seed = rnd();
  b.frame = (int)(rnd() * 64);
  return b;
}

void SkinView::burst(const std::vector<SkinParticles>& list, V2 at, float spread, float outAngle) {
  if (L.cfg.reduceMotion) return;
  for (auto& p : list) {
    if (bursts_.size() > 8) return;
    Emitter e{&p, {}, 0};
    for (int i = 0; i < p.count; i++) {
      float a = rnd() * kTau;
      V2 where = p.area == SkinParticles::Area::Slot || p.area == SkinParticles::Area::Ring ? polar(at, a, spread * sqrtf(rnd())) : at;
      if (p.area == SkinParticles::Area::Hub) where = polar(at_.center, a, at_.hub * sqrtf(rnd()));
      if (p.area == SkinParticles::Area::Rim) where = polar(at_.center, a, at_.wheel);
      float out = p.area == SkinParticles::Area::Hub || p.area == SkinParticles::Area::Rim ? a : p.area == SkinParticles::Area::Slot ? a : outAngle;
      e.bits.push_back(born(p, where, out));
    }
    bursts_.push_back(std::move(e));
  }
}
void SkinView::hoverChanged(V2 at, float cell) { burst(skin->burstHover, at, cell, angleOf(at - at_.center)); }
void SkinView::launched(V2 at, float cell, V2 dir) { burst(skin->burstLaunch, at, cell, angleOf(dir)); }
void SkinView::openedNow() { burst(skin->burstOpen, at_.center, at_.wheel, 0); }

void SkinView::particles(Painter& p, float alpha, bool behind) const {
  if (warm) {
    for (auto* list : {&skin->particles, &skin->burstLaunch, &skin->burstHover, &skin->burstOpen})
      for (auto& q : *list) {
        SkinArt::Pic pic;
        if (q.image >= 0) skinArt().get(q.image, std::max(q.size[0], q.size[1]) * units.px * std::max(1.f, q.grow), pic);
      }
    return;
  }
  auto draw = [&](const Emitter& e) {
    const SkinParticles& q = *e.p;
    SkinArt::Pic pic;
    float biggest = 0;
    for (auto& b : e.bits) biggest = std::max(biggest, b.size);
    if (!spend((int)e.bits.size() * 2)) return;
    bool img = q.image >= 0 && !e.bits.empty() && skinArt().get(q.image, std::max(q.size[0], q.size[1]) * units.px * std::max(1.f, q.grow), pic);
    if (q.image >= 0 && !img) return;
    Color c = color(q.color);
    D2D1_MATRIX_3X2_F base = now(p.dc);
    for (auto& b : e.bits) {
      float t = b.age / b.life;
      float a = alpha * q.opacity * (q.fadeIn > 0 ? smooth01(t / q.fadeIn) : 1.f) * (q.fadeOut > 0 ? 1.f - smooth01((t - 1.f + q.fadeOut) / q.fadeOut) : 1.f);
      if (a < 0.004f) continue;
      float size = b.size * lerp(1.f, q.grow, t);
      if (!img) {
        if (q.stretch > 0) {
          V2 tail = b.pos - b.vel * (0.03f * q.stretch);
          p.line(b.pos, tail, c.withA(c.a * a), size, true);
          if (q.light) p.line(b.pos, tail, c.withA(0.16f * c.a * a), size * 3.2f, true);
          continue;
        }
        if (q.light) p.circle(b.pos, size * 1.6f, c.withA(0.14f * c.a * a));
        p.circle(b.pos, size * 0.5f, c.withA(c.a * a));
        continue;
      }
      float h = size * pic.ch / std::max(1.f, pic.cw);
      float rot = b.rot;
      if (q.stretch > 0 && (fabsf(b.vel.x) > 1 || fabsf(b.vel.y) > 1)) rot = angleOf(b.vel) * 180.f / kPi;
      int f = pic.frames > 1 ? b.frame % pic.frames : 0;
      D2D1_RECT_F src = D2D1::RectF((f % pic.cols) * pic.cw, (f / pic.cols) * pic.ch, (f % pic.cols + 1) * pic.cw, (f / pic.cols + 1) * pic.ch);
      D2D1_RECT_F dst = D2D1::RectF(-size * 0.5f, -h * 0.5f, size * 0.5f, h * 0.5f);
      p.dc->SetTransform(D2D1::Matrix3x2F::Rotation(rot) * D2D1::Matrix3x2F::Translation(b.pos.x, b.pos.y) * as(base));
      if (q.tinted) {
        p.tinted(pic.bmp, dst, src, c.withA(c.a * a), pic.light);
      } else {
        p.dc->DrawBitmap(pic.bmp, &dst, a * pic.fade, pic.sharp ? D2D1_INTERPOLATION_MODE_NEAREST_NEIGHBOR : D2D1_INTERPOLATION_MODE_LINEAR, &src, nullptr);
      }
    }
    p.dc->SetTransform(base);
  };
  if (behind) {
    for (auto& e : emit_) draw(e);
  } else {
    for (auto& e : bursts_) draw(e);
  }
}

// ---------------------------------------------------------------- layers
bool SkinView::usesOnly(const std::vector<SkinLayer>& list) const {
  uint32_t bit = 1u << (int)L.cfg.layout;
  for (auto& y : list)
    if (y.only & bit) return true;
  return false;
}

void SkinView::layers(Painter& p, const std::vector<SkinLayer>& list, const Stage& s, const SkinUnits& u) const {
  if (s.alpha <= 0.003f && !warm) return;
  uint32_t bit = 1u << (int)L.cfg.layout;
  bool wheelLike = L.cfg.layout == LayoutType::Radial || s.item;
  float speed = L.st.speed;
  for (auto& y : list) {
    if (y.only ? !(y.only & bit) : !wheelLike) continue;
    if (warm) {
      if (y.kind == SkinLayer::Kind::Image) {
        float w = y.w.get(vars) * u.of(y.unit) * (y.unit == SkinUnit::Px ? 1.f : 2.f);
        SkinArt::Pic pic;
        if (w > 0.5f) skinArt().get(y.image, w * y.sharpness, pic);
      } else if (y.kind == SkinLayer::Kind::Shape) {
        for (auto* f : {&y.fill, &y.stroke}) {
          SkinArt::Pic pic;
          if (f->kind == SkinPaint::Kind::Image) skinArt().get(f->image, 2.f * (f->wheel ? u.wheel : u.of(y.unit)) * std::max(0.01f, f->zoom.get(vars)), pic);
        }
      }
      continue;
    }
    int m = clampi((int)lroundf(y.copies.get(vars)), 0, 120);
    vars[vM] = (float)m;
    for (int j = 0; j < m; j++) {
      vars[vJ] = (float)j;
      if (!spend(1)) return;  // working out that nothing is drawn costs time as well
      if (y.when.get(vars) <= 0) continue;
      float op = std::min(3.f, y.opacity.get(vars)) * s.alpha;
      if (op <= 0.003f) continue;
      if (y.kind == SkinLayer::Kind::Text && !spend(5 + (int)y.text.size() / 8)) return;
      if (y.kind == SkinLayer::Kind::Shape && !spend(1 + (int)y.points.size() / 3 + (y.shape == SkinShape::Star ? y.count : 0))) return;
      Put q;
      q.unit = u.of(y.unit);
      q.moving = u.moving;
      q.alpha = op;
      q.rot = y.rotate.get(vars);
      q.sx = y.scaleX.get(vars);
      q.sy = y.scaleY.get(vars);
      float a = y.angle.get(vars), r = y.radius.get(vars);
      float ix = 0, iy = 0;
      if (y.intro.on && !s.still && !L.cfg.reduceMotion) {
        float e = arrived(y.intro, s.clock >= 0 ? s.clock : L.time, orderOf(y.intro.order, j, m, a * kPi / 180.f, (uint32_t)j * 7919u + 13u), speed);
        float f = 1.f - e;
        q.alpha *= lerp(y.intro.opacity, 1.f, saturate(e));
        q.rot += y.intro.rotate * f;
        float k = lerp(y.intro.scale, 1.f, e);
        q.sx *= k;
        q.sy *= k;
        a += y.intro.angle * f;
        r += y.intro.radius * f;
        ix = y.intro.x * f;
        iy = y.intro.y * f;
        if (q.alpha <= 0.003f) continue;
      }
      V2 off{(y.x.get(vars) + ix) * q.unit, (y.y.get(vars) + iy) * q.unit};
      if (r != 0) off += V2{sinf(a * kPi / 180.f), -cosf(a * kPi / 180.f)} * (r * q.unit);
      if (y.turns) q.rot += a + s.turn;
      if (s.turn != 0 && y.turns) {  // the offset turns along with its entry
        float c = cosf(s.turn * kPi / 180.f), n = sinf(s.turn * kPi / 180.f);
        off = {off.x * c - off.y * n, off.x * n + off.y * c};
      }
      float depth = y.depth.get(vars);
      if (depth != 0 && !L.cfg.reduceMotion) off += V2{vars[vPx], vars[vPy]} * (depth * units.px * -10.f);
      q.pos = s.at + off;
      // Formulas can come to anything, and one number Direct2D cannot take makes the whole frame fail.
      if (!sane(q.pos.x) || !sane(q.pos.y) || !sane(q.sx, 400.f) || !sane(q.sy, 400.f) || !sane(q.alpha, 100.f)) continue;
      if (!sane(q.rot, 1e6f)) q.rot = 0;
      if (q.sx == 0 || q.sy == 0) continue;
      switch (y.kind) {
        case SkinLayer::Kind::Image: drawImage(p, y, q, s); break;
        case SkinLayer::Kind::Shape: drawShape(p, y, q, s, u); break;
        case SkinLayer::Kind::Text: drawText(p, y, q, s); break;
      }
    }
  }
}

void SkinView::drawImage(Painter& p, const SkinLayer& y, const Put& q, const Stage& s) const {
  float two = y.unit == SkinUnit::Px ? 1.f : 2.f;
  float w = y.w.get(vars) * q.unit * two;
  if (!(w >= 0.5f) || !sane(w, 16000.f)) return;
  SkinArt::Pic pic;
  if (!skinArt().get(y.image, w * y.sharpness, pic, q.moving || !y.w.fixed(), !q.moving) || pic.cw < 1) return;
  float h = y.hasH ? y.h.get(vars) * q.unit * two : w * pic.ch / pic.cw;
  if (!(h >= 0.05f) || !sane(h, 16000.f)) return;  // a picture without any height is an error to Direct2D
  int f = 0;
  if (pic.frames > 1) {
    float fr = y.frame.get(vars) + (L.cfg.reduceMotion ? 0.f : L.time * y.fps);
    f = (int)floorf(fr) % pic.frames;
    if (f < 0) f += pic.frames;
  }
  D2D1_RECT_F src = D2D1::RectF((f % pic.cols) * pic.cw, (f / pic.cols) * pic.ch, (f % pic.cols + 1) * pic.cw, (f / pic.cols + 1) * pic.ch);
  V2 pos = q.pos;
  if (pic.sharp) {  // pixel art: whole multiples on whole pixels
    float k = std::max(1.f, roundf(w / pic.cw));
    w = pic.cw * k;
    h = pic.ch * k;
  }
  D2D1_RECT_F dst = D2D1::RectF(-w * y.pivot.x, -h * y.pivot.y, w * (1 - y.pivot.x), h * (1 - y.pivot.y));
  D2D1_MATRIX_3X2_F base = now(p.dc);
  bool plain = fabsf(q.rot) < 0.01f && fabsf(q.sx - 1) < 0.002f && fabsf(q.sy - 1) < 0.002f;
  if ((plain || pic.sharp) && fabsf(w - pic.cw * std::max(1.f, roundf(w / pic.cw))) < 1.5f) {  // keep it crisp
    pos.x = roundf(pos.x + dst.left) - dst.left;
    pos.y = roundf(pos.y + dst.top) - dst.top;
  }
  p.dc->SetTransform(D2D1::Matrix3x2F::Scale(q.sx, q.sy) * D2D1::Matrix3x2F::Rotation(q.rot) * D2D1::Matrix3x2F::Translation(pos.x, pos.y) * as(base));
  float a = q.alpha * pic.fade;
  if (y.tinted) {
    Color c = color(y.tint, s.item);
    p.tinted(pic.bmp, dst, src, c.withA(c.a * a), pic.light);
  } else if (y.round) {
    ComPtr<ID2D1BitmapBrush1> br;
    auto m = D2D1::Matrix3x2F::Translation(-src.left, -src.top) * D2D1::Matrix3x2F::Scale(w / pic.cw, h / pic.ch) * D2D1::Matrix3x2F::Translation(dst.left, dst.top);
    p.dc->CreateBitmapBrush(pic.bmp, D2D1::BitmapBrushProperties1(D2D1_EXTEND_MODE_CLAMP, D2D1_EXTEND_MODE_CLAMP, D2D1_INTERPOLATION_MODE_LINEAR), D2D1::BrushProperties(std::min(1.f, a), m), &br);
    if (br) p.dc->FillEllipse(D2D1::Ellipse(D2D1::Point2F((dst.left + dst.right) * 0.5f, (dst.top + dst.bottom) * 0.5f), w * 0.5f, h * 0.5f), br.Get());
  } else {
    auto mode = pic.sharp ? D2D1_INTERPOLATION_MODE_NEAREST_NEIGHBOR
                : plain && fabsf(w - pic.cw) < 1.f ? D2D1_INTERPOLATION_MODE_LINEAR
                : w * fabsf(q.sx) < pic.cw * 0.7f ? D2D1_INTERPOLATION_MODE_HIGH_QUALITY_CUBIC
                : w < 420 ? D2D1_INTERPOLATION_MODE_CUBIC : D2D1_INTERPOLATION_MODE_LINEAR;
    p.dc->DrawBitmap(pic.bmp, &dst, std::min(1.f, a), mode, &src, nullptr);
    for (float more = a - 1.f; more > 0.01f; more -= 1.f)  // light can be turned up past full
      p.dc->DrawBitmap(pic.bmp, &dst, std::min(1.f, more), mode, &src, nullptr);
  }
  p.dc->SetTransform(base);
}

ComPtr<ID2D1Brush> SkinView::brush(Painter& p, const SkinPaint& f, V2 half, float unit, float alpha, const Stage& s, V2 origin) const {
  ComPtr<ID2D1Brush> o;
  switch (f.kind) {
    case SkinPaint::Kind::Linear:
    case SkinPaint::Kind::Radial: {
      bool varies = false;  // colours that depend on the entry cannot be shared
      for (auto& e : f.stops) varies |= e.second.from == SkinColor::From::Item || e.second.from == SkinColor::From::Profile;
      if (gradGen_ != gfx().generation) {
        grads_.clear();
        gradGen_ = gfx().generation;
      }
      Grad one;
      Grad& g = varies ? one : grads_[&f];
      if (!g.lin && !g.rad) {
        D2D1_GRADIENT_STOP gs[12];
        UINT n = 0;
        for (auto& e : f.stops)
          if (n < 12) gs[n++] = {e.first, color(e.second, s.item).f()};
        ComPtr<ID2D1GradientStopCollection> col;
        p.dc->CreateGradientStopCollection(gs, n, &col);
        if (!col) return o;
        if (f.kind == SkinPaint::Kind::Linear) p.dc->CreateLinearGradientBrush(D2D1::LinearGradientBrushProperties({0, 0}, {1, 0}), col.Get(), &g.lin);
        else p.dc->CreateRadialGradientBrush(D2D1::RadialGradientBrushProperties({0, 0}, {0, 0}, 1, 1), col.Get(), &g.rad);
      }
      if (g.lin) {
        g.lin->SetStartPoint(D2D1::Point2F(f.from.x * half.x, f.from.y * half.y));
        g.lin->SetEndPoint(D2D1::Point2F(f.to.x * half.x, f.to.y * half.y));
        g.lin->SetOpacity(saturate(alpha));
        g.lin->SetTransform(D2D1::Matrix3x2F::Identity());
        g.lin.As(&o);
      } else if (g.rad) {
        g.rad->SetCenter(D2D1::Point2F(f.from.x * half.x, f.from.y * half.y));
        g.rad->SetRadiusX(std::max(0.1f, f.to.x * half.x));
        g.rad->SetRadiusY(std::max(0.1f, f.to.x * half.y));
        g.rad->SetOpacity(saturate(alpha));
        g.rad->SetTransform(D2D1::Matrix3x2F::Identity());
        g.rad.As(&o);
      }
      return o;
    }
    case SkinPaint::Kind::Image: {
      float span = 2.f * unit * std::max(0.01f, f.zoom.get(vars));
      SkinArt::Pic pic;
      if (!skinArt().get(f.image, span, pic) || pic.cw < 1) return o;
      float k = span / pic.cw;
      V2 c = f.wheel ? at_.center - origin : V2{};
      auto m = D2D1::Matrix3x2F::Translation((f.u.get(vars) - 0.5f) * pic.cw, (f.v.get(vars) - 0.5f) * pic.ch) * D2D1::Matrix3x2F::Scale(k, k) *
               D2D1::Matrix3x2F::Rotation(f.turn.get(vars)) * D2D1::Matrix3x2F::Translation(c.x, c.y);
      auto ext = f.tile ? D2D1_EXTEND_MODE_WRAP : D2D1_EXTEND_MODE_CLAMP;
      ComPtr<ID2D1BitmapBrush1> br;
      p.dc->CreateBitmapBrush(pic.bmp, D2D1::BitmapBrushProperties1(ext, ext, pic.sharp ? D2D1_INTERPOLATION_MODE_NEAREST_NEIGHBOR : D2D1_INTERPOLATION_MODE_LINEAR),
                              D2D1::BrushProperties(std::min(1.f, alpha * pic.fade), m), &br);
      if (br) br.As(&o);
      return o;
    }
    case SkinPaint::Kind::Solid: {
      Color c = color(f.c, s.item);
      ComPtr<ID2D1SolidColorBrush> br;
      p.dc->CreateSolidColorBrush(c.withA(c.a * alpha).f(), &br);
      if (br) br.As(&o);
      return o;
    }
    default: return o;
  }
}

void SkinView::drawShape(Painter& p, const SkinLayer& y, const Put& q, const Stage& s, const SkinUnits& u) const {
  float k = q.unit, px = u.px;
  float two = y.unit == SkinUnit::Px ? 0.5f : 1.f;
  Geo g;
  V2 half{k * y.w.get(vars) * two, 0};
  half.y = y.hasH ? k * y.h.get(vars) * two : half.x;
  if (!sane(half.x) || !sane(half.y)) return;
  bool absolute = false, filled = true;
  switch (y.shape) {
    case SkinShape::Circle: {
      gfx().ensureFactories();
      ComPtr<ID2D1EllipseGeometry> e;
      gfx().d2d->CreateEllipseGeometry(D2D1::Ellipse(D2D1::Point2F(0, 0), std::max(0.1f, half.x), std::max(0.1f, half.y)), &e);
      if (e) e.As(&g);
      break;
    }
    case SkinShape::Ring: {
      float a0 = y.from.get(vars) * kPi / 180.f, a1 = y.to.get(vars) * kPi / 180.f;
      float ri = std::max(0.f, y.inner.get(vars) * k), ro = y.outer.get(vars) * k;
      if (!(a1 - a0 >= 0.002f) || !(ro - ri >= 0.2f) || !sane(a0) || !sane(a1) || !sane(ro)) return;
      half = {ro, ro};
      if (a1 - a0 >= kTau - 0.002f) g = ri < 0.3f ? circleGeo({0, 0}, ro) : ringGeo({0, 0}, ri, ro);
      else if (float in = y.inset.get(vars) * px, co = y.corner.get(vars) * px; sane(in) && sane(co)) g = wedgeGeo({0, 0}, std::max(0.5f, ri), ro, a0, a1, 2.f * in, co);
      break;
    }
    case SkinShape::Arc: {
      float a0 = y.from.get(vars) * kPi / 180.f, a1 = y.to.get(vars) * kPi / 180.f, r = y.r.get(vars) * k;
      if (a1 < a0) std::swap(a0, a1);
      if (!(a1 - a0 >= 0.002f) || !(r >= 0.3f) || !sane(a0) || !sane(a1) || !sane(r)) return;
      half = {r, r};
      g = arcGeo({0, 0}, r, a0, std::min(a1, a0 + kTau));
      filled = false;
      break;
    }
    case SkinShape::Rect:
      if (float co = y.corner.get(vars) * px; sane(co)) g = rrectGeo(RectF(-half.x, -half.y, half.x, half.y), co);
      break;
    case SkinShape::Line:
    case SkinShape::Poly: {
      std::vector<V2> pts;
      for (auto& e : y.points) {
        pts.push_back({e.first.get(vars) * k, e.second.get(vars) * k});
        if (!sane(pts.back().x) || !sane(pts.back().y)) return;
      }
      if (pts.size() < 2) return;
      half = {k, k};
      g = polyGeo(pts, y.shape == SkinShape::Poly && (y.closed || y.fill.any()), y.curve);
      filled = y.shape == SkinShape::Poly;
      break;
    }
    case SkinShape::Star: {
      std::vector<V2> pts;
      for (int i = 0; i < y.count * 2 && i < 400; i++) pts.push_back(polar({0, 0}, i * kPi / y.count, (i % 2 ? y.inner.get(vars) : y.outer.get(vars)) * k));
      if (pts.size() < 4) return;
      for (auto& e : pts)
        if (!sane(e.x) || !sane(e.y)) return;
      half = {k, k};
      g = polyGeo(pts, true, y.curve);
      break;
    }
    case SkinShape::Ticks: {
      float a0 = y.from.get(vars) * kPi / 180.f, a1 = y.to.get(vars) * kPi / 180.f, ri = y.inner.get(vars) * k, ro = y.outer.get(vars) * k;
      float w = y.width.get(vars) * px;
      if (!sane(a0) || !sane(a1) || !sane(ri) || !sane(ro) || !sane(w, 2000.f)) return;
      bool full = a1 - a0 > kTau - 0.01f;
      Color c = color(y.stroke.any() ? y.stroke.c : y.fill.c, s.item);
      if (!spend(y.count)) return;
      D2D1_MATRIX_3X2_F base = now(p.dc);
      p.dc->SetTransform(D2D1::Matrix3x2F::Scale(q.sx, q.sy) * D2D1::Matrix3x2F::Rotation(q.rot) * D2D1::Matrix3x2F::Translation(q.pos.x, q.pos.y) * as(base));
      for (int i = 0; i < y.count; i++) {
        float a = lerp(a0, a1, full ? (float)i / y.count : y.count > 1 ? (float)i / (y.count - 1) : 0.f);
        bool big = y.major > 0 && i % y.major == 0;
        p.line(polar({0, 0}, a, big ? ri - (ro - ri) * 0.6f : ri), polar({0, 0}, a, ro), c.withA(c.a * q.alpha * (big || !y.major ? 1.f : 0.7f)), big ? w * 1.7f : w, y.caps);
      }
      p.dc->SetTransform(base);
      return;
    }
    case SkinShape::Slot:
      if (!s.shape || !*s.shape) return;
      if (float in = y.inset.get(vars) * px; sane(in, 4000.f)) g = (*s.shape)(in);
      half = {u.cell, u.cell};
      absolute = true;
      break;
  }
  if (!g) return;
  D2D1_MATRIX_3X2_F base = now(p.dc);
  V2 origin = absolute ? V2{} : q.pos;
  if (!absolute) p.dc->SetTransform(D2D1::Matrix3x2F::Scale(q.sx, q.sy) * D2D1::Matrix3x2F::Rotation(q.rot) * D2D1::Matrix3x2F::Translation(q.pos.x, q.pos.y) * as(base));
  bool many = s.item || !y.copies.fixed() || y.copies.k > 1.5f;
  if (float gl = std::min(60.f, y.glow.get(vars)); gl > 0.05f && q.alpha > 0.01f && spend(many ? 4 : 25)) {
    Color c = color(y.glowColor, s.item);
    float w = y.stroke.any() || !filled ? std::max(1.f, y.width.get(vars) * px) : 0.f;
    if (many) p.halo(g.Get(), c.withA(c.a * q.alpha), gl * px, w);
    else p.glow(g.Get(), c.withA(c.a * q.alpha), gl * px, w, filled && y.fill.any());
  }
  auto put = [&](const SkinPaint& f, bool stroke) {
    if (!f.any()) return;
    ComPtr<ID2D1Brush> br;
    if (f.kind == SkinPaint::Kind::Glass) {
      if (stroke) return;
      if (s.glass && s.glass->bmp) {
        V2 o = s.glass->origin - origin;
        br = p.image(s.glass->bmp.Get(), o, s.glass->scale, q.alpha * saturate(s.glass->fade));
        p.fill(g.Get(), br.Get());
      }
      return;
    }
    if (absolute) {
      // Gradients and pictures are laid out around the entry's own centre.
      Stage t = s;
      br = brush(p, f, half, f.wheel ? u.wheel : u.of(y.unit), q.alpha, t, s.at);
      if (br) {
        D2D1_MATRIX_3X2_F m;
        br->GetTransform(&m);
        br->SetTransform(as(m) * D2D1::Matrix3x2F::Translation(s.at.x, s.at.y));
      }
    } else {
      br = brush(p, f, half, f.wheel ? u.wheel : u.of(y.unit), q.alpha, s, q.pos);
    }
    if (!br) return;
    if (stroke) {
      float w = y.width.get(vars) * px;
      if (!(w > 0.01f)) return;
      w = std::min(w, 2000.f);
      if (y.dashes) {
        ComPtr<ID2D1StrokeStyle> ss;
        auto cap = y.caps ? D2D1_CAP_STYLE_ROUND : D2D1_CAP_STYLE_FLAT;
        gfx().d2d->CreateStrokeStyle(D2D1::StrokeStyleProperties(cap, cap, cap, D2D1_LINE_JOIN_ROUND, 10.f, D2D1_DASH_STYLE_CUSTOM, 0.f), y.dash, (UINT32)y.dashes, ss.GetAddressOf());
        if (w > 0.01f) p.dc->DrawGeometry(g.Get(), br.Get(), w, ss.Get());
      } else {
        p.stroke(g.Get(), br.Get(), w, y.caps);
      }
    } else {
      p.fill(g.Get(), br.Get());
    }
  };
  if (filled) put(y.fill, false);
  put(y.stroke, true);
  p.dc->SetTransform(base);
}

// ---------------------------------------------------------------- lettering
void SkinView::drawText(Painter& p, const SkinLayer& y, const Put& q, const Stage& s) const {
  D2D1_MATRIX_3X2_F base = now(p.dc);
  bool turned = fabsf(q.rot) > 0.01f || fabsf(q.sx - 1) > 0.002f || fabsf(q.sy - 1) > 0.002f;
  if (turned) p.dc->SetTransform(D2D1::Matrix3x2F::Scale(q.sx, q.sy) * D2D1::Matrix3x2F::Rotation(q.rot) * D2D1::Matrix3x2F::Translation(q.pos.x, q.pos.y) * as(base));
  V2 at = turned ? V2{} : q.pos;
  if (y.caption) {
    float t = easeOutCubic(swap_), px = units.px;
    if (swap_ < 1) {
      std::wstring old = expand(y.text, s.item, true);
      textLine(p, y, old, {at.x, at.y - 5.f * px * t}, q.unit, q.alpha * (1 - t) * 0.9f, s.item);
    }
    textLine(p, y, expand(y.text, s.item), {at.x, at.y + 6.f * px * (1 - t)}, q.unit, q.alpha * t, s.item);
  } else {
    textLine(p, y, expand(y.text, s.item), at, q.unit, q.alpha, s.item);
  }
  p.dc->SetTransform(base);
}

void SkinView::textLine(Painter& p, const SkinLayer& y, const std::wstring& raw, V2 at, float unit, float alpha, const SceneItem* it) const {
  if (raw.empty() || alpha <= 0.004f) return;
  std::wstring text = raw;
  if (y.upper) CharUpperBuffW(text.data(), (DWORD)text.size());
  float s = units.px;
  TextStyle ts;
  ts.family = widen(L.st.font);
  int w = 0;
  if (y.font >= 0) {
    std::wstring fam = skinArt().fontFamily(y.font, &w);
    if (!fam.empty()) ts.family = fam;
  }
  ts.weight = y.weight ? y.weight : w ? w : 500;
  ts.italic = y.italic;
  ts.size = std::min(600.f, y.em > 0 ? y.em * unit : y.px.get(vars) * s);
  ts.tracking = y.tracking * s;
  ts.align = y.align;
  ts.valign = y.valign;
  ts.wrap = y.wrap;
  ts.ellipsis = !y.marquee;
  if (!(ts.size >= 3) || !sane(ts.tracking, 600.f)) return;
  float bw = y.boxW * unit, bh = y.boxH * unit;
  if (!sane(bw) || !sane(bh)) return;
  Color c = color(y.color, it);
  c = c.withA(c.a * alpha);

  if (y.ring) {  // along a circle, centred on its angle
    float r = y.r.get(vars) * unit;
    auto lay = gfx().layout(text, ts, 8000.f, 200.f);
    UINT32 n = 0;
    if (!lay || !(r >= 4) || !sane(r)) return;
    lay->GetClusterMetrics(nullptr, 0, &n);
    std::vector<DWRITE_CLUSTER_METRICS> m(n);
    if (!n || FAILED(lay->GetClusterMetrics(m.data(), n, &n))) return;
    float total = 0;
    for (auto& e : m) total += e.width;
    float most = bw > 0 ? bw : kTau * r * 0.96f;
    if (total > most && y.fit) {
      float f = std::max(0.5f, most / total);
      ts.size *= f;
      for (auto& e : m) e.width *= f;
      total *= f;
    }
    D2D1_MATRIX_3X2_F base = now(p.dc);
    TextStyle one = ts;
    one.align = Align::Center;
    one.valign = VAlign::Middle;
    one.ellipsis = one.wrap = false;
    one.tracking = 0;
    float x = -total * 0.5f;
    size_t ch = 0;
    bool inside = r < 0;
    (void)inside;
    for (auto& e : m) {
      float a = (x + e.width * 0.5f) / r;
      if (x + e.width > total * 0.5f + 0.5f + (most - total) * 0.5f && total > most) break;
      V2 at2 = polar(at, a, r);
      p.dc->SetTransform(D2D1::Matrix3x2F::Rotation(a * 180.f / kPi, at2.p()) * as(base));
      p.text(std::wstring_view(text).substr(ch, e.length), one, RectF::xywh(at2.x - ts.size * 2, at2.y - ts.size, ts.size * 4, ts.size * 2), c);
      x += e.width;
      ch += e.length;
    }
    p.dc->SetTransform(base);
    return;
  }

  if (y.pixel > 1) {
    float k = std::max(1.f, roundf(y.pixel * std::max(1.f, roundf(s * 1.0f)) / std::max(1.f, roundf(s))));
    k = std::max(1.f, roundf((float)y.pixel * s));
    TextStyle small = ts;
    small.size = std::max(6.f, roundf(ts.size / k));
    small.tracking = ts.tracking / k;
    small.align = Align::Left;
    small.valign = VAlign::Top;
    small.ellipsis = !y.marquee;
    float maxW = bw > 0 ? floorf(bw / k) : 4000.f;
    wchar_t key[96];
    swprintf(key, 96, L"|%.1f|%d|%.0f|%d|%.3f %.3f %.3f|", small.size, small.weight, maxW, (int)y.wrap, c.r, c.g, c.b);
    std::wstring id = small.family + key + text;
    PixelText* hit = nullptr;
    for (auto& e : pixel_)
      if (e.key == id && e.gen == gfx().generation) hit = &e;
    if (!hit) {
      V2 m = gfx().measure(text, small, y.wrap ? maxW : 8000.f);
      float tw = ceilf(y.marquee ? m.x : std::min(m.x, maxW)) + 2, th = ceilf(m.y) + 1;
      tw = std::min(tw, 2000.f);
      th = std::min(th, 400.f);
      auto bmp = gfx().target((int)tw, (int)th);
      auto lay = gfx().layout(text, small, y.marquee ? 4000.f : std::max(1.f, tw), th);
      if (!bmp || !lay) return;
      ID2D1DeviceContext* aux = gfx().aux.Get();
      aux->SetTarget(bmp.Get());
      aux->SetTransform(D2D1::Matrix3x2F::Identity());
      aux->BeginDraw();
      aux->Clear(D2D1::ColorF(0, 0, 0, 0));
      aux->SetTextAntialiasMode(D2D1_TEXT_ANTIALIAS_MODE_ALIASED);
      ComPtr<ID2D1SolidColorBrush> br;
      aux->CreateSolidColorBrush(c.withA(1).f(), &br);
      if (br) aux->DrawTextLayout(D2D1::Point2F(0, 0), lay.Get(), br.Get());
      aux->SetTextAntialiasMode(D2D1_TEXT_ANTIALIAS_MODE_GRAYSCALE);
      aux->EndDraw();
      aux->SetTarget(nullptr);
      if (pixel_.size() > 24) pixel_.erase(std::min_element(pixel_.begin(), pixel_.end(), [](const PixelText& a, const PixelText& b) { return a.used < b.used; }));
      pixel_.push_back({id, bmp, tw, th, frameNo_, gfx().generation});
      hit = &pixel_.back();
    }
    hit->used = frameNo_;
    float W = hit->w * k, H = hit->h * k;
    float x = y.align == Align::Left ? at.x : y.align == Align::Right ? at.x - W : at.x - W * 0.5f;
    if (bw > 0) x = y.align == Align::Left ? at.x - bw * 0.5f : y.align == Align::Right ? at.x + bw * 0.5f - W : at.x - W * 0.5f;
    float yy = y.valign == VAlign::Top ? at.y : y.valign == VAlign::Bottom ? at.y - H : at.y - H * 0.5f;
    bool scroll = y.marquee && bw > 0 && W > bw;
    x = roundf(x);
    yy = roundf(yy);
    auto blit = [&](float bx, float a, Color* tint) {
      D2D1_RECT_F d = D2D1::RectF(bx, yy, bx + W, yy + H);
      p.dc->DrawBitmap(hit->bmp.Get(), &d, std::min(1.f, a), D2D1_INTERPOLATION_MODE_NEAREST_NEIGHBOR, nullptr, nullptr);
      (void)tint;
    };
    auto clean = [&](float bx) {
      if (y.shadow) {
        Color sc = color(y.shadowColor, it);
        D2D1_RECT_F d = D2D1::RectF(bx + y.shadowX * k, yy + y.shadowY * k, bx + y.shadowX * k + W, yy + y.shadowY * k + H);
        p.dc->SetAntialiasMode(D2D1_ANTIALIAS_MODE_ALIASED);
        // The mask brush samples smoothly; at whole multiples that only softens the shadow's edge.
        p.dc->FillOpacityMask(hit->bmp.Get(), p.solid(sc.withA(sc.a * alpha)), &d, nullptr);
        p.dc->SetAntialiasMode(D2D1_ANTIALIAS_MODE_PER_PRIMITIVE);
      }
      blit(bx, c.a, nullptr);
    };
    if (scroll) {
      float left = at.x - bw * 0.5f, gap = 24.f * s, run = W + gap;
      float off = L.cfg.reduceMotion ? 0.f : fmodf(std::max(0.f, L.time - 0.8f) * 46.f * s, run);
      off = floorf(off / k) * k;
      p.dc->PushAxisAlignedClip(D2D1::RectF(left, yy - 4, left + bw, yy + H + 4), D2D1_ANTIALIAS_MODE_ALIASED);
      clean(roundf(left - off));
      clean(roundf(left - off + run));
      p.dc->PopAxisAlignedClip();
    } else {
      clean(x);
    }
    return;
  }

  float maxW = bw > 0 ? bw : 4000.f;
  V2 m = gfx().measure(text, ts, y.wrap ? maxW : 8000.f);
  if (y.fit && !y.marquee && bw > 0) {
    for (int i = 0; i < 8 && (m.x > bw + 0.5f || (bh > 0 && m.y > bh + 0.5f)) && ts.size > 7.f * s; i++) {
      ts.size *= 0.92f;
      m = gfx().measure(text, ts, y.wrap ? maxW : 8000.f);
    }
  }
  float h = bh > 0 ? bh : m.y + 2;
  RectF r;
  if (bw > 0) r = RectF::xywh(at.x - bw * 0.5f, 0, bw, h);
  else r = y.align == Align::Left ? RectF::xywh(at.x, 0, m.x + 4, h) : y.align == Align::Right ? RectF::xywh(at.x - m.x - 4, 0, m.x + 4, h) : RectF::xywh(at.x - m.x * 0.5f - 2, 0, m.x + 4, h);
  float top = bh > 0 || y.valign == VAlign::Middle ? at.y - h * 0.5f : y.valign == VAlign::Top ? at.y : at.y - h;
  r.t = top;
  r.b = top + h;
  bool scroll = y.marquee && bw > 0 && m.x > bw;
  if (scroll) ts.align = Align::Left;
  auto put = [&](RectF q) {
    if (y.shadow) {
      Color sc = color(y.shadowColor, it);
      RectF o = q.offset(y.shadowX * s, y.shadowY * s);
      if (y.shadowBlur > 0.4f) p.textBlur(text, ts, o, sc.withA(sc.a * alpha), y.shadowBlur * s);
      else p.text(text, ts, o, sc.withA(sc.a * alpha));
    }
    if (y.outline && spend(40)) {
      Color oc = color(y.outlineColor, it);
      float w2 = y.outlineW * s;
      int n = w2 > 1.6f ? 16 : 8;
      for (int i = 0; i < n; i++) p.text(text, ts, q.offset(cosf(i * kTau / n) * w2, sinf(i * kTau / n) * w2), oc.withA(oc.a * std::min(1.f, alpha * 1.0f)));
    }
    p.text(text, ts, q, c);
  };
  if (scroll) {
    float gap = 30.f * s, run = m.x + gap;
    float off = L.cfg.reduceMotion ? 0.f : fmodf(std::max(0.f, L.time - 0.8f) * 46.f * s, run);
    p.dc->PushAxisAlignedClip(D2D1::RectF(r.l, r.t - 6, r.r, r.b + 6), D2D1_ANTIALIAS_MODE_PER_PRIMITIVE);
    RectF q = r;
    q.l = r.l - off;
    q.r = q.l + m.x + 8;
    put(q);
    put(q.offset(run, 0));
    p.dc->PopAxisAlignedClip();
  } else {
    put(r);
  }
}

// ---------------------------------------------------------------- entries
void SkinView::slot(Painter& p, const SkinSlot& S, const SceneItem& it, const Stage& s0, float cell, float iconPx, float iconScale, float hot) const {
  SkinUnits u = units;
  u.cell = cell;
  Stage s = s0;
  s.item = &it;
  layers(p, S.under, s, u);
  if (warm) {
    layers(p, S.over, s, u);
    return;
  }
  const SkinIcon& I = S.icon;
  float k = units.px, h = saturate(hot);
  float zoom = I.zoom > 0 ? I.zoom : L.st.iconZoom;
  float size = std::min(iconPx * 1.25f, I.size.get(vars) * cell) * lerp(1.f, zoom, h) * iconScale;
  float op = I.opacity.get(vars) * s.alpha;
  if (size > 2 && op > 0.004f) {
    V2 c = s.at + V2{I.x.get(vars) * cell, I.y.get(vars) * cell};
    float rot = I.rotate.get(vars) + (I.turns ? s.turn : 0.f);
    D2D1_MATRIX_3X2_F base = now(p.dc);
    if (fabsf(rot) > 0.01f) p.dc->SetTransform(D2D1::Matrix3x2F::Rotation(rot, c.p()) * as(base));
    if (float gl = I.glow.get(vars); gl > 0.02f) {
      Color gc = color(I.glowColor, &it);
      float R = size * 0.95f;
      auto br = p.radial(c, R, R, {{0, gc.withA(0.55f * gl * gc.a * op)}, {0.5f, gc.withA(0.22f * gl * gc.a * op)}, {1, gc.withA(0)}});
      p.dc->FillEllipse(D2D1::Ellipse(c.p(), R, R), br.Get());
    }
    IconLook look{I.tone, I.toneHot, color(I.ink, &it), color(I.paper, &it), I.round};
    if (I.shadow) {
      Color sc = color(I.shadowColor, &it);
      L.iconShadow(p, it, {c.x + I.shadowX * k, c.y + I.shadowY * k}, size, sc.withA(sc.a * op), I.shadowBlur * k);
    }
    L.drawIconAs(p, it, c, size, op, h, look);
    p.dc->SetTransform(base);
  }
  layers(p, S.over, s, u);
}

// ---------------------------------------------------------------- panels
ComPtr<ID2D1Brush> SkinView::panelBrush(Painter& p, const SkinPaint& f, V2 c, V2 half, float alpha) const {
  Stage st;
  st.at = c;
  auto br = brush(p, f, half, units.px * 100.f, alpha, st, c);
  if (br) {
    D2D1_MATRIX_3X2_F m;
    br->GetTransform(&m);
    br->SetTransform(as(m) * D2D1::Matrix3x2F::Translation(c.x, c.y));
  }
  return br;
}

bool SkinView::panel(Painter& p, const SkinPanel& P, RectF r, float s, float alpha, const Backdrop* glass, const SceneItem* it) const {
  if (!P.on) return false;
  r = RectF(r.l - P.pad[0] * s, r.t - P.pad[1] * s, r.r + P.pad[2] * s, r.b + P.pad[3] * s);
  if (P.image >= 0) {
    float k = P.scale * s;
    SkinArt::Pic pic;
    // drawn from the full picture: the corners keep their size and the middle stretches
    if (!skinArt().get(P.image, 4096, pic) || pic.cw < 2) return true;
    float cx[4] = {0, P.cut[0], pic.cw - P.cut[2], pic.cw}, cy[4] = {0, P.cut[1], pic.ch - P.cut[3], pic.ch};
    float w = r.w(), h = r.h();
    float kx = std::min(k, w / std::max(1.f, P.cut[0] + P.cut[2])), ky = std::min(k, h / std::max(1.f, P.cut[1] + P.cut[3]));
    float q = std::min(kx, ky);
    float dx[4] = {r.l, r.l + P.cut[0] * q, r.r - P.cut[2] * q, r.r}, dy[4] = {r.t, r.t + P.cut[1] * q, r.b - P.cut[3] * q, r.b};
    for (auto& v : dx) v = roundf(v);
    for (auto& v : dy) v = roundf(v);
    p.dc->SetAntialiasMode(D2D1_ANTIALIAS_MODE_ALIASED);
    for (int j = 0; j < 3; j++)
      for (int i = 0; i < 3; i++) {
        if (dx[i + 1] - dx[i] < 0.5f || dy[j + 1] - dy[j] < 0.5f || cx[i + 1] - cx[i] < 0.5f || cy[j + 1] - cy[j] < 0.5f) continue;
        D2D1_RECT_F src = D2D1::RectF(cx[i], cy[j], cx[i + 1], cy[j + 1]), dst = D2D1::RectF(dx[i], dy[j], dx[i + 1], dy[j + 1]);
        p.dc->DrawBitmap(pic.bmp, &dst, std::min(1.f, alpha * pic.fade), pic.sharp ? D2D1_INTERPOLATION_MODE_NEAREST_NEIGHBOR : D2D1_INTERPOLATION_MODE_LINEAR, &src, nullptr);
      }
    p.dc->SetAntialiasMode(D2D1_ANTIALIAS_MODE_PER_PRIMITIVE);
    return true;
  }
  Geo g = P.cutCorner ? cutRectGeo(r, P.corner * s) : rrectGeo(r, P.corner * s);
  Stage st;
  st.at = r.center();
  st.glass = glass;
  st.item = it;
  V2 half{r.w() * 0.5f, r.h() * 0.5f};
  D2D1_MATRIX_3X2_F base = now(p.dc);
  auto fill = [&](const SkinPaint& f, bool stroke) {
    if (!f.any()) return;
    if (f.kind == SkinPaint::Kind::Glass) {
      if (glass && glass->bmp && !stroke) {
        auto br = p.image(glass->bmp.Get(), glass->origin, glass->scale, alpha * saturate(glass->fade));
        p.fill(g.Get(), br.Get());
      }
      return;
    }
    auto br = brush(p, f, half, units.px * 100.f, alpha, st, st.at);
    if (!br) return;
    D2D1_MATRIX_3X2_F m;
    br->GetTransform(&m);
    br->SetTransform(as(m) * D2D1::Matrix3x2F::Translation(st.at.x, st.at.y));
    if (stroke) p.stroke(g.Get(), br.Get(), P.width * s);
    else p.fill(g.Get(), br.Get());
  };
  fill(P.fill, false);
  fill(P.stroke, true);
  p.dc->SetTransform(base);
  return true;
}

}  // namespace rt
