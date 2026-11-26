#include "skin.h"

#include "backfx.h"

#include <set>

#include "install.h"
#include "zip.h"

namespace rt {

float easeAt(Ease e, float t) {
  t = saturate(t);
  switch (e) {
    case Ease::Linear: return t;
    case Ease::InOut: return smooth01(t);
    case Ease::Back: { float q = t - 1; return 1 + 2.70158f * q * q * q + 1.70158f * q * q; }
    case Ease::Elastic: return t <= 0 ? 0.f : t >= 1 ? 1.f : powf(2.f, -9 * t) * sinf((t * 9 - 0.75f) * kTau / 3) + 1;
    case Ease::Bounce: {
      const float n = 7.5625f, d = 2.75f;
      if (t < 1 / d) return n * t * t;
      if (t < 2 / d) { t -= 1.5f / d; return n * t * t + 0.75f; }
      if (t < 2.5f / d) { t -= 2.25f / d; return n * t * t + 0.9375f; }
      t -= 2.625f / d;
      return n * t * t + 0.984375f;
    }
    case Ease::Quint: return easeOutQuint(t);
    default: return easeOutCubic(t);
  }
}

int Skin::imageIndex(std::string_view n) const {
  for (size_t i = 0; i < images.size(); i++)
    if (images[i].name == n) return (int)i;
  return -1;
}

// ---------------------------------------------------------------- reading skin.json
namespace {

struct Reader {
  Skin& t;
  std::map<std::string, SkinColor> colors;
  std::string where;
  int layers = 0;

  void problem(const std::string& m) {
    if (t.problems.size() < 40) t.problems.push_back(where.empty() ? m : where + ": " + m);
  }
  struct Scope {
    Reader& r;
    std::string old;
    Scope(Reader& rd, const std::string& name) : r(rd), old(rd.where) { r.where = old.empty() ? name : old + " > " + name; }
    ~Scope() { r.where = old; }
  };

  void known(const Json& o, std::initializer_list<const char*> keys) {
    for (auto& kv : o.o) {
      if (kv.first.empty() || kv.first[0] == '_' || kv.first == "note") continue;  // remarks
      bool ok = false;
      for (auto k : keys) ok = ok || kv.first == k;
      if (!ok) problem("\"" + kv.first + "\" is not something a skin can set here");
    }
  }

  void num(const Json& o, const char* key, Num& out) {
    if (auto j = o.find(key)) value(*j, key, out);
  }
  void value(const Json& j, const char* key, Num& out) {
    if (j.t == Json::T::Num) {
      out = Num((float)clampf((float)j.n, -1e6f, 1e6f));
    } else if (j.t == Json::T::Bool) {
      out = Num(j.b ? 1.f : 0.f);
    } else if (j.t == Json::T::Str) {
      auto e = std::make_shared<Expr>();
      std::string err;
      if (!e->parse(j.s, &err)) {
        problem(std::string(key) + ": " + err);
        return;
      }
      if (e->constant()) {
        out = Num(e->eval(nullptr));
      } else {
        out = Num();
        out.e = e;
        watch(*e);
      }
    } else {
      problem(std::string(key) + " should be a number or a formula");
    }
  }
  // Remembers what a formula depends on, so that only what is needed is measured.
  bool liveNow = false;
  void watch(const Expr& e) {
    static const Var clock[] = {vHour, vMinute, vSecond, vTick}, sys[] = {vCpu, vRam, vBattery, vCharging}, snd[] = {vSound, vSoundL, vSoundR, vBeat};
    for (auto v : clock) if (e.uses(v)) { t.clock = true; liveNow = liveNow || v == vSecond || v == vTick; }
    for (auto v : sys) if (e.uses(v)) t.system = liveNow = true;
    for (auto v : snd) if (e.uses(v)) t.sound = liveNow = true;
    if (e.uses(vTime)) liveNow = true;
  }
  void real(const Json& o, const char* key, float& out, float lo, float hi) {
    auto j = o.find(key);
    if (!j) return;
    if (j->t != Json::T::Num) {
      problem(std::string(key) + " should be a plain number");
      return;
    }
    out = clampf((float)j->n, lo, hi);
  }
  void integer(const Json& o, const char* key, int& out, int lo, int hi) {
    float v = (float)out;
    real(o, key, v, (float)lo, (float)hi);
    out = (int)lroundf(v);
  }
  void flag(const Json& o, const char* key, bool& out) {
    auto j = o.find(key);
    if (!j) return;
    if (j->t != Json::T::Bool) {
      problem(std::string(key) + " should be true or false");
      return;
    }
    out = j->b;
  }
  bool text(const Json& o, const char* key, std::string& out) {
    auto j = o.find(key);
    if (!j) return false;
    if (j->t != Json::T::Str) {
      problem(std::string(key) + " should be text in quotes");
      return false;
    }
    out = j->s;
    return true;
  }
  void text(const Json& o, const char* key, std::wstring& out, size_t most) {
    std::string s;
    if (text(o, key, s)) out = widen(s).substr(0, most);
  }
  void pair(const Json& o, const char* key, float& a, float& b, float lo, float hi) {
    auto j = o.find(key);
    if (!j) return;
    if (j->t == Json::T::Num) {
      a = b = clampf((float)j->n, lo, hi);
    } else if (j->isArr() && j->a.size() == 2 && j->a[0].t == Json::T::Num && j->a[1].t == Json::T::Num) {
      a = clampf((float)j->a[0].n, lo, hi);
      b = clampf((float)j->a[1].n, lo, hi);
    } else {
      problem(std::string(key) + " should be a number or two numbers in brackets");
    }
  }
  template <class E>
  void choice(const Json& o, const char* key, E& out, std::initializer_list<std::pair<const char*, E>> opts) {
    std::string s;
    if (!text(o, key, s)) return;
    std::string all;
    for (auto& k : opts) {
      if (s == k.first) {
        out = k.second;
        return;
      }
      all += all.empty() ? k.first : std::string(", ") + k.first;
    }
    problem(std::string(key) + " can be " + all + ", not \"" + s + "\"");
  }

  bool parseColor(const std::string& raw, SkinColor& out) {
    std::string s = raw;
    float a = 1.f;
    size_t slash = s.find('/');
    if (slash != std::string::npos) {
      double v = atof(s.c_str() + slash + 1);
      a = std::isfinite(v) ? clampf((float)(v / 100.0), 0.f, 1.f) : 1.f;
      s.resize(slash);
    }
    while (!s.empty() && s.back() == ' ') s.pop_back();
    if (auto it = colors.find(s); it != colors.end()) {
      out = it->second;
      out.a *= a;
      return true;
    }
    static const std::pair<const char*, SkinColor::From> named[] = {
        {"accent", SkinColor::From::Accent}, {"accent2", SkinColor::From::Accent2}, {"text", SkinColor::From::Text}, {"base", SkinColor::From::Base},
        {"border", SkinColor::From::Border}, {"profile", SkinColor::From::Profile}, {"item", SkinColor::From::Item}};
    for (auto& n : named)
      if (s == n.first) {
        out.from = n.second;
        out.a = a;
        return true;
      }
    if (s == "white" || s == "black" || s == "none") {
      out.from = SkinColor::From::Fixed;
      out.c = s == "white" ? Color(1, 1, 1) : Color(0, 0, 0);
      out.a = s == "none" ? 0.f : a;
      return true;
    }
    Color c;
    if (!Color::parse(s, c)) return false;
    out.from = SkinColor::From::Fixed;
    out.c = c.withA(1);
    out.a = a * c.a;
    return true;
  }
  bool color(const Json& o, const char* key, SkinColor& out) {
    std::string s;
    if (!text(o, key, s)) return false;
    if (parseColor(s, out)) return true;
    problem(std::string(key) + ": \"" + s + "\" is not a colour");
    return false;
  }

  int image(const std::string& name) {
    int i = t.imageIndex(name);
    if (i < 0 && name.find('.') != std::string::npos) {  // a file used directly
      SkinImage im;
      im.name = im.file = name;
      if (!safeInnerPath(name)) {
        problem("\"" + name + "\" is not a usable file name");
        return -1;
      }
      t.images.push_back(im);
      i = (int)t.images.size() - 1;
    }
    if (i < 0) problem("there is no image called \"" + name + "\"");
    return i;
  }
  bool image(const Json& o, const char* key, int& out) {
    std::string s;
    if (!text(o, key, s)) return false;
    out = image(s);
    return out >= 0;
  }

  void paint(const Json& o, const char* key, SkinPaint& out) {
    auto j = o.find(key);
    if (!j) return;
    Scope sc(*this, key);
    if (j->t == Json::T::Str) {
      if (j->s == "glass") {
        out.kind = SkinPaint::Kind::Glass;
      } else if (parseColor(j->s, out.c)) {
        out.kind = SkinPaint::Kind::Solid;
      } else {
        problem("\"" + j->s + "\" is not a colour");
      }
      return;
    }
    if (!j->isObj()) {
      problem("should be a colour or a description in braces");
      return;
    }
    known(*j, {"type", "stops", "from", "to", "image", "tile", "wheel", "zoom", "u", "v", "turn", "radius"});
    auto stops = [&] {
      auto s = j->find("stops");
      if (!s || !s->isArr() || s->a.size() < 2) {
        problem("needs at least two stops");
        return false;
      }
      for (auto& e : s->a) {
        SkinColor c;
        if (!e.isArr() || e.a.size() != 2 || e.a[0].t != Json::T::Num || e.a[1].t != Json::T::Str || !parseColor(e.a[1].s, c)) {
          problem("each stop is [position, colour]");
          return false;
        }
        if (out.stops.size() < 12) out.stops.push_back({saturate((float)e.a[0].n), c});
      }
      return true;
    };
    std::string type;
    text(*j, "type", type);
    if (j->find("image")) {
      if (!image(*j, "image", out.image)) return;
      out.kind = SkinPaint::Kind::Image;
      flag(*j, "tile", out.tile);
      flag(*j, "wheel", out.wheel);
      num(*j, "zoom", out.zoom);
      num(*j, "u", out.u);
      num(*j, "v", out.v);
      num(*j, "turn", out.turn);
    } else if (type == "radial") {
      out.from = {0, 0};
      out.to = {1, 0};
      pair(*j, "from", out.from.x, out.from.y, -10, 10);
      real(*j, "radius", out.to.x, 0.001f, 20);
      if (stops()) out.kind = SkinPaint::Kind::Radial;
    } else if (type == "linear" || type.empty()) {
      pair(*j, "from", out.from.x, out.from.y, -10, 10);
      pair(*j, "to", out.to.x, out.to.y, -10, 10);
      if (stops()) out.kind = SkinPaint::Kind::Linear;
    } else {
      problem("type can be linear or radial");
    }
  }

  void intro(const Json& o, const char* key, SkinIntro& out) {
    auto j = o.find(key);
    if (!j) return;
    Scope sc(*this, key);
    if (!j->isObj()) {
      problem("should be a description in braces");
      return;
    }
    known(*j, {"delay", "time", "stagger", "ease", "order", "x", "y", "radius", "angle", "scale", "rotate", "opacity"});
    out.on = true;
    out.opacity = 0;
    real(*j, "delay", out.delay, 0, 3);
    real(*j, "time", out.time, 0.02f, 4);
    real(*j, "stagger", out.stagger, 0, 0.4f);
    choice<Ease>(*j, "ease", out.ease, {{"linear", Ease::Linear}, {"out", Ease::Out}, {"inout", Ease::InOut}, {"back", Ease::Back}, {"elastic", Ease::Elastic}, {"bounce", Ease::Bounce}, {"quint", Ease::Quint}});
    using O = SkinIntro::Order;
    choice<O>(*j, "order", out.order, {{"both", O::Both}, {"ring", O::Ring}, {"reverse", O::Reverse}, {"random", O::Random}, {"pairs", O::Pairs}});
    real(*j, "x", out.x, -20, 20);
    real(*j, "y", out.y, -20, 20);
    real(*j, "radius", out.radius, -10, 10);
    real(*j, "angle", out.angle, -1080, 1080);
    real(*j, "scale", out.scale, 0, 10);
    real(*j, "rotate", out.rotate, -2160, 2160);
    real(*j, "opacity", out.opacity, 0, 1);
  }

  void unit(const Json& o, SkinUnit& out) {
    choice<SkinUnit>(o, "in", out, {{"wheel", SkinUnit::Wheel}, {"hub", SkinUnit::Hub}, {"ring", SkinUnit::Ring}, {"cell", SkinUnit::Cell}, {"px", SkinUnit::Px}});
  }

  void layouts(const Json& o, uint32_t& out) {
    auto j = o.find("only");
    if (!j) return;
    auto one = [&](const Json& e) {
      if (e.t == Json::T::Str && e.s == "all") {
        out = 0xFFFFFFFFu;
        return;
      }
      for (int i = 0; i < kLayoutCount; i++)
        if (e.t == Json::T::Str && e.s == layoutId((LayoutType)i)) {
          out |= 1u << i;
          return;
        }
      problem("only: unknown layout \"" + e.s + "\"");
    };
    if (j->isArr()) for (auto& e : j->a) one(e);
    else one(*j);
  }

  bool layer(const Json& o, SkinLayer& L, SkinUnit unit0) {
    if (!o.isObj()) {
      problem("a layer is a description in braces");
      return false;
    }
    if (++layers > 400) {
      if (layers == 401) problem("a skin can have at most 400 layers");
      return false;
    }
    known(o, {"image", "text", "shape", "in", "only", "x", "y", "angle", "radius", "rotate", "opacity", "scale", "when", "depth", "copies", "turns", "size", "pivot", "intro",
              "frame", "fps", "detail", "tint", "round", "fill", "stroke", "width", "from", "to", "inner", "outer", "r", "corner", "inset", "points", "closed", "curve", "caps", "count",
              "major", "dash", "glow", "glowcolor", "font", "px", "em", "weight", "italic", "wrap", "upper", "marquee", "fit", "align", "valign", "box", "pixel", "tracking", "color",
              "shadow", "outline", "ring"});
    L.unit = unit0;
    unit(o, L.unit);
    layouts(o, L.only);
    bool outer = liveNow;
    liveNow = false;
    num(o, "x", L.x);
    num(o, "y", L.y);
    num(o, "angle", L.angle);
    num(o, "radius", L.radius);
    num(o, "rotate", L.rotate);
    num(o, "opacity", L.opacity);
    num(o, "when", L.when);
    num(o, "depth", L.depth);
    num(o, "copies", L.copies);
    flag(o, "turns", L.turns);
    if (auto s = o.find("scale")) {
      if (s->isArr() && s->a.size() == 2) {
        value(s->a[0], "scale", L.scaleX);
        value(s->a[1], "scale", L.scaleY);
      } else {
        value(*s, "scale", L.scaleX);
        L.scaleY = L.scaleX;
      }
    }
    if (auto s = o.find("size")) {
      if (s->isArr() && s->a.size() == 2) {
        value(s->a[0], "size", L.w);
        value(s->a[1], "size", L.h);
        L.hasH = true;
      } else {
        value(*s, "size", L.w);
      }
    }
    pair(o, "pivot", L.pivot.x, L.pivot.y, -5, 6);
    intro(o, "intro", L.intro);

    std::string s;
    bool ok = false;
    if (o.find("image")) {
      L.kind = SkinLayer::Kind::Image;
      ok = image(o, "image", L.image);
      num(o, "frame", L.frame);
      real(o, "fps", L.fps, 0, 120);
      if (L.fps > 0) liveNow = true;
      real(o, "detail", L.sharpness, 0.25f, 3);
      L.tinted = color(o, "tint", L.tint);
      flag(o, "round", L.round);
    } else if (o.find("shape")) {
      L.kind = SkinLayer::Kind::Shape;
      using S = SkinShape;
      choice<S>(o, "shape", L.shape, {{"circle", S::Circle}, {"ring", S::Ring}, {"arc", S::Arc}, {"rect", S::Rect}, {"line", S::Line}, {"poly", S::Poly}, {"ticks", S::Ticks}, {"slot", S::Slot}, {"star", S::Star}});
      paint(o, "fill", L.fill);
      paint(o, "stroke", L.stroke);
      num(o, "width", L.width);
      num(o, "from", L.from);
      num(o, "to", L.to);
      num(o, "inner", L.inner);
      num(o, "outer", L.outer);
      num(o, "r", L.r);
      num(o, "corner", L.corner);
      num(o, "inset", L.inset);
      flag(o, "closed", L.closed);
      flag(o, "curve", L.curve);
      flag(o, "caps", L.caps);
      integer(o, "count", L.count, 1, 720);
      integer(o, "major", L.major, 0, 720);
      if (auto p = o.find("points")) {
        if (p->isArr())
          for (auto& e : p->a) {
            if (!e.isArr() || e.a.size() != 2) {
              problem("points are pairs [x, y]");
              break;
            }
            std::pair<Num, Num> q;
            value(e.a[0], "points", q.first);
            value(e.a[1], "points", q.second);
            if (L.points.size() < 200) L.points.push_back(q);
          }
      }
      if (auto d = o.find("dash"); d && d->isArr())
        for (auto& e : d->a)
          if (L.dashes < 4 && e.t == Json::T::Num) L.dash[L.dashes++] = clampf((float)e.n, 0.3f, 1000);
      num(o, "glow", L.glow);
      if (!color(o, "glowcolor", L.glowColor)) L.glowColor.from = SkinColor::From::Accent;
      ok = L.fill.any() || L.stroke.any() || !L.glow.fixed() || L.glow.k > 0;
      if (!ok) problem("a shape needs a fill, a stroke or a glow");
    } else if (text(o, "text", s)) {
      L.kind = SkinLayer::Kind::Text;
      L.text = widen(s).substr(0, 400);
      L.caption = s.find("{title}") != std::string::npos || s.find("{sub}") != std::string::npos;
      if (s.find("{ss}") != std::string::npos) liveNow = true;
      for (auto k : {"{cpu}", "{ram}", "{battery}"})
        if (s.find(k) != std::string::npos) t.system = true;
      std::string f;
      if (text(o, "font", f)) {
        for (size_t i = 0; i < t.fonts.size(); i++)
          if (t.fonts[i].name == f) L.font = (int)i;
        if (L.font < 0) {
          SkinFont nf;
          nf.name = f;
          nf.families.push_back(widen(f));
          t.fonts.push_back(nf);
          L.font = (int)t.fonts.size() - 1;
        }
      }
      num(o, "px", L.px);
      real(o, "em", L.em, 0, 10);
      if (L.px.fixed() && L.px.k <= 0 && L.em <= 0) L.px = Num(14);
      integer(o, "weight", L.weight, 0, 950);
      flag(o, "italic", L.italic);
      flag(o, "wrap", L.wrap);
      flag(o, "upper", L.upper);
      flag(o, "marquee", L.marquee);
      flag(o, "fit", L.fit);
      flag(o, "ring", L.ring);
      num(o, "r", L.r);
      choice<Align>(o, "align", L.align, {{"left", Align::Left}, {"center", Align::Center}, {"right", Align::Right}});
      choice<VAlign>(o, "valign", L.valign, {{"top", VAlign::Top}, {"middle", VAlign::Middle}, {"bottom", VAlign::Bottom}});
      pair(o, "box", L.boxW, L.boxH, 0, 4000);
      integer(o, "pixel", L.pixel, 0, 12);
      real(o, "tracking", L.tracking, -10, 40);
      if (!color(o, "color", L.color)) L.color.from = SkinColor::From::Text;
      if (auto sh = o.find("shadow"); sh && sh->isObj()) {
        Scope sc(*this, "shadow");
        known(*sh, {"x", "y", "blur", "color"});
        L.shadow = true;
        real(*sh, "x", L.shadowX, -50, 50);
        real(*sh, "y", L.shadowY, -50, 50);
        real(*sh, "blur", L.shadowBlur, 0, 40);
        if (!color(*sh, "color", L.shadowColor)) L.shadowColor = {SkinColor::From::Fixed, Color(0, 0, 0), 0.6f};
      }
      if (auto ol = o.find("outline"); ol && ol->isObj()) {
        Scope sc(*this, "outline");
        known(*ol, {"width", "color"});
        L.outline = true;
        real(*ol, "width", L.outlineW, 0.2f, 12);
        if (!color(*ol, "color", L.outlineColor)) L.outlineColor = {SkinColor::From::Fixed, Color(0, 0, 0), 1.f};
      }
      ok = true;
    } else {
      problem("a layer needs an image, a shape or a text");
    }
    L.live = liveNow || L.marquee;
    if (L.live) t.alive = true;
    liveNow = outer;
    return ok;
  }

  void layerList(const Json& o, const char* key, std::vector<SkinLayer>& out, SkinUnit u) {
    auto j = o.find(key);
    if (!j) return;
    if (!j->isArr()) {
      problem(std::string(key) + " should be a list in brackets");
      return;
    }
    for (size_t i = 0; i < j->a.size(); i++) {
      Scope sc(*this, std::string(key) + " " + std::to_string(i + 1));
      SkinLayer L;
      if (layer(j->a[i], L, u)) out.push_back(std::move(L));
    }
  }

  void tone(const Json& o, const char* key, IconTone& out) {
    std::string s;
    if (!text(o, key, s)) return;
    if (!toneFromText(s, out)) problem(std::string(key) + ": \"" + s + "\" is not an icon style");
  }

  void slot(const Json& o, const char* key, SkinSlot& S) {
    auto j = o.find(key);
    if (!j) return;
    Scope sc(*this, key);
    if (!j->isObj()) {
      problem("should be a description in braces");
      return;
    }
    known(*j, {"under", "over", "icon", "marks", "chevron", "badge", "intro", "names"});
    S.on = true;
    layerList(*j, "under", S.under, SkinUnit::Cell);
    layerList(*j, "over", S.over, SkinUnit::Cell);
    flag(*j, "marks", S.marks);
    flag(*j, "chevron", S.chevron);
    flag(*j, "badge", S.badge);
    real(*j, "names", S.nameDy, -3, 3);
    intro(*j, "intro", S.intro);
    if (auto k = j->find("icon"); k && k->isObj()) {
      Scope s2(*this, "icon");
      known(*k, {"size", "x", "y", "rotate", "opacity", "tone", "hot", "ink", "paper", "zoom", "round", "turns", "shadow", "glow", "glowcolor"});
      SkinIcon& I = S.icon;
      num(*k, "size", I.size);
      num(*k, "x", I.x);
      num(*k, "y", I.y);
      num(*k, "rotate", I.rotate);
      num(*k, "opacity", I.opacity);
      tone(*k, "tone", I.tone);
      I.toneHot = IconTone::Original;
      tone(*k, "hot", I.toneHot);
      if (!color(*k, "ink", I.ink)) I.ink.from = SkinColor::From::Accent;
      if (!color(*k, "paper", I.paper)) I.paper.from = SkinColor::From::Base;
      real(*k, "zoom", I.zoom, 0, 3);
      flag(*k, "round", I.round);
      flag(*k, "turns", I.turns);
      num(*k, "glow", I.glow);
      if (!color(*k, "glowcolor", I.glowColor)) I.glowColor.from = SkinColor::From::Item;
      if (auto sh = k->find("shadow"); sh && sh->isObj()) {
        Scope s3(*this, "shadow");
        known(*sh, {"x", "y", "blur", "color"});
        I.shadow = true;
        real(*sh, "x", I.shadowX, -50, 50);
        real(*sh, "y", I.shadowY, -50, 50);
        real(*sh, "blur", I.shadowBlur, 0, 30);
        if (!color(*sh, "color", I.shadowColor)) I.shadowColor = {SkinColor::From::Fixed, Color(0, 0, 0), 0.5f};
      }
    }
  }

  void particle(const Json& o, SkinParticles& P) {
    known(o, {"image", "color", "light", "outward", "rate", "when", "max", "count", "area", "life", "size", "speed", "dir", "spin", "gravity", "drag", "sway", "swayhz", "fadein", "fadeout", "grow",
              "swirl", "stretch", "opacity"});
    if (o.find("image")) {
      image(o, "image", P.image);
      P.dot = false;
      P.light = false;
    }
    P.tinted = color(o, "color", P.color);
    if (!P.tinted && P.image < 0) P.color.from = SkinColor::From::Accent;
    flag(o, "light", P.light);
    flag(o, "outward", P.outward);
    num(o, "rate", P.rate);
    num(o, "when", P.when);
    integer(o, "max", P.max, 1, 240);
    integer(o, "count", P.count, 1, 120);
    using A = SkinParticles::Area;
    choice<A>(o, "area", P.area, {{"wheel", A::Wheel}, {"ring", A::Ring}, {"hub", A::Hub}, {"rim", A::Rim}, {"slot", A::Slot}, {"stage", A::Stage}, {"pointer", A::Pointer}});
    pair(o, "life", P.life[0], P.life[1], 0.02f, 30);
    pair(o, "size", P.size[0], P.size[1], 0.1f, 400);
    pair(o, "speed", P.speed[0], P.speed[1], -3000, 3000);
    pair(o, "dir", P.dir[0], P.dir[1], -720, 720);
    pair(o, "spin", P.spin[0], P.spin[1], -2000, 2000);
    real(o, "gravity", P.gravity, -4000, 4000);
    real(o, "drag", P.drag, 0, 20);
    real(o, "sway", P.sway, 0, 400);
    real(o, "swayhz", P.swayHz, 0, 10);
    real(o, "fadein", P.fadeIn, 0, 1);
    real(o, "fadeout", P.fadeOut, 0, 1);
    real(o, "grow", P.grow, 0, 20);
    real(o, "swirl", P.swirl, -20, 20);
    real(o, "stretch", P.stretch, 0, 1);
    real(o, "opacity", P.opacity, 0, 1);
  }
  void particleList(const Json& o, const char* key, std::vector<SkinParticles>& out) {
    auto j = o.find(key);
    if (!j) return;
    auto one = [&](const Json& e, size_t i) {
      Scope sc(*this, std::string(key) + " " + std::to_string(i + 1));
      if (!e.isObj()) {
        problem("should be a description in braces");
        return;
      }
      if (out.size() >= 12) return;
      SkinParticles P;
      particle(e, P);
      out.push_back(std::move(P));
    };
    if (j->isArr()) for (size_t i = 0; i < j->a.size(); i++) one(j->a[i], i);
    else one(*j, 0);
  }

  void panel(const Json& o, const char* key, SkinPanel& P) {
    auto j = o.find(key);
    if (!j) return;
    Scope sc(*this, key);
    if (!j->isObj()) {
      problem("should be a description in braces");
      return;
    }
    known(*j, {"image", "cut", "scale", "pad", "fill", "stroke", "corner", "width", "text", "cutcorner"});
    P.on = true;
    if (j->find("image")) image(*j, "image", P.image);
    auto four = [&](const char* k, float* v, float lo, float hi) {
      auto a = j->find(k);
      if (!a) return;
      if (a->t == Json::T::Num) for (int i = 0; i < 4; i++) v[i] = clampf((float)a->n, lo, hi);
      else if (a->isArr() && a->a.size() == 4) for (size_t i = 0; i < 4; i++) v[i] = clampf((float)a->a[i].n, lo, hi);
      else problem(std::string(k) + " should be one number or four: left, top, right, bottom");
    };
    four("cut", P.cut, 0, 2000);
    four("pad", P.pad, -100, 200);
    real(*j, "scale", P.scale, 0.05f, 8);
    paint(*j, "fill", P.fill);
    paint(*j, "stroke", P.stroke);
    real(*j, "corner", P.corner, 0, 100);
    real(*j, "width", P.width, 0, 20);
    flag(*j, "cutcorner", P.cutCorner);
    P.hasText = color(*j, "text", P.text);
  }

  void button(const Json& o, const char* key, SkinButton& B) {
    auto j = o.find(key);
    if (!j) return;
    Scope sc(*this, key);
    if (!j->isObj()) {
      problem("should be a description in braces");
      return;
    }
    known(*j, {"in", "x", "y", "size", "layers", "hidden"});
    B.on = true;
    flag(*j, "hidden", B.hidden);
    unit(*j, B.unit);
    real(*j, "x", B.at.x, -4000, 4000);
    real(*j, "y", B.at.y, -4000, 4000);
    real(*j, "size", B.size, 4, 200);
    layerList(*j, "layers", B.layers, SkinUnit::Cell);
  }

  void all(const Json& j) {
    known(j, {"format", "id", "name", "author", "version", "about", "license", "tags", "style", "wheel", "colors", "images", "fonts", "back", "ring", "fan", "over", "hub", "front", "slot", "kid",
              "pinbutton", "settingsbutton", "panel", "tag", "tile", "particles", "onlaunch", "onhover", "onopen", "sounds", "cursor", "draw", "tabs", "preview", "screen"});
    if ((int)j.num("format", 1) > 1) problem("this skin was made for a newer version of the program");
    std::string s;
    text(j, "name", t.name, 60);
    text(j, "author", t.author, 60);
    text(j, "version", t.version, 24);
    text(j, "about", t.about, 160);
    text(j, "license", t.license, 80);
    if (auto g = j.find("tags"); g && g->isArr())
      for (auto& e : g->a)
        if (e.t == Json::T::Str && t.tags.size() < 8) t.tags.push_back(widen(e.s).substr(0, 24));

    if (auto st = j.find("style"); st && st->isObj()) readStyle(*st, t.style);
    if (auto cs = j.find("colors"); cs && cs->isObj()) {
      Scope sc(*this, "colors");
      for (auto& kv : cs->o) {
        SkinColor c;
        if (kv.second.t == Json::T::Str && parseColor(kv.second.s, c)) colors[kv.first] = c;
        else problem("\"" + kv.first + "\" is not a colour");
      }
    }
    if (auto im = j.find("images"); im && im->isObj()) {
      Scope sc(*this, "images");
      for (auto& kv : im->o) {
        if (t.images.size() >= 120) {
          problem("a skin can have at most 120 images");
          break;
        }
        SkinImage m;
        m.name = kv.first;
        if (kv.second.t == Json::T::Str) {
          m.file = kv.second.s;
        } else if (kv.second.isObj()) {
          Scope s2(*this, kv.first);
          known(kv.second, {"file", "mask", "cols", "rows", "frames", "light", "keep", "sharp"});
          text(kv.second, "file", m.file);
          text(kv.second, "mask", m.mask);
          integer(kv.second, "cols", m.cols, 1, 64);
          integer(kv.second, "rows", m.rows, 1, 64);
          m.frames = m.cols * m.rows;
          integer(kv.second, "frames", m.frames, 1, m.cols * m.rows);
          flag(kv.second, "light", m.light);
          flag(kv.second, "keep", m.keep);
          flag(kv.second, "sharp", m.sharp);
        }
        if (!safeInnerPath(m.file) || (!m.mask.empty() && !safeInnerPath(m.mask))) {
          problem("\"" + kv.first + "\" does not name a usable file");
          continue;
        }
        t.images.push_back(m);
      }
    }
    if (auto f = j.find("fonts"); f && f->isObj()) {
      Scope sc(*this, "fonts");
      for (auto& kv : f->o) {
        if (t.fonts.size() >= 16) break;
        SkinFont q;
        q.name = kv.first;
        auto family = [&](const std::string& list) {
          size_t at = 0;
          while (at < list.size()) {
            size_t e = list.find(',', at);
            if (e == std::string::npos) e = list.size();
            std::wstring one = trim(widen(list.substr(at, e - at)));
            if (!one.empty() && q.families.size() < 8) q.families.push_back(one.substr(0, 80));
            at = e + 1;
          }
        };
        if (kv.second.t == Json::T::Str) {
          family(kv.second.s);
        } else if (kv.second.isObj()) {
          Scope s2(*this, kv.first);
          known(kv.second, {"family", "file", "weight"});
          std::string fam;
          if (text(kv.second, "family", fam)) family(fam);
          text(kv.second, "file", q.file);
          integer(kv.second, "weight", q.weight, 100, 950);
          if (!q.file.empty() && !safeInnerPath(q.file)) {
            problem("\"" + q.file + "\" is not a usable file name");
            q.file.clear();
          }
        }
        t.fonts.push_back(q);
      }
    }
    if (auto w = j.find("wheel"); w && w->isObj()) {
      Scope sc(*this, "wheel");
      known(*w, {"hub", "thickness", "gap", "ringgap", "icon", "crowd", "rim", "shadow", "area", "hubkeep"});
      real(*w, "hub", t.wheel.hub, 40, 260);
      real(*w, "thickness", t.wheel.thickness, 40, 200);
      real(*w, "gap", t.wheel.gap, 0, 60);
      real(*w, "ringgap", t.wheel.ringGap, 0, 120);
      real(*w, "icon", t.wheel.icon, 16, 128);
      real(*w, "crowd", t.wheel.crowd, 1, 3);
      real(*w, "rim", t.wheel.rim, 0, 200);
      real(*w, "shadow", t.wheel.shadow, 0, 1);
      real(*w, "hubkeep", t.wheel.hubKeep, 0.2f, 1.5f);
      if (auto a = w->find("area")) {
        if (a->t == Json::T::Num) for (float& v : t.wheel.area) v = clampf((float)a->n, 0.5f, 4);
        else if (a->isArr() && a->a.size() == 4) for (size_t i = 0; i < 4; i++) t.wheel.area[i] = clampf((float)a->a[i].n, 0.5f, 4);
        else problem("area should be one number or four: left, top, right, bottom");
      }
    }
    layerList(j, "back", t.back, SkinUnit::Wheel);
    layerList(j, "ring", t.ring, SkinUnit::Ring);
    layerList(j, "fan", t.fan, SkinUnit::Px);
    layerList(j, "over", t.over, SkinUnit::Wheel);
    layerList(j, "hub", t.hub, SkinUnit::Hub);
    layerList(j, "front", t.front, SkinUnit::Wheel);
    slot(j, "slot", t.slot);
    t.hasSlot = t.slot.on;
    t.kid = t.slot;
    if (j.find("kid")) {
      t.kid = SkinSlot{};
      slot(j, "kid", t.kid);
    }
    button(j, "pinbutton", t.pinButton);
    button(j, "settingsbutton", t.settingsButton);
    panel(j, "panel", t.panel);
    panel(j, "tag", t.tag);
    panel(j, "tile", t.tile);
    if (!t.tag.on) t.tag = t.panel;
    particleList(j, "particles", t.particles);
    particleList(j, "onlaunch", t.burstLaunch);
    particleList(j, "onhover", t.burstHover);
    particleList(j, "onopen", t.burstOpen);
    if (!t.particles.empty()) t.alive = true;
    if (auto so = j.find("sounds"); so && so->isObj()) {
      Scope sc(*this, "sounds");
      known(*so, {"open", "move", "launch", "close", "profile"});
      for (auto& kv : so->o) {
        if (kv.second.t != Json::T::Str || !safeInnerPath(kv.second.s)) {
          problem("\"" + kv.first + "\" does not name a usable file");
          continue;
        }
        t.sounds[kv.first] = kv.second.s;
      }
    }
    if (auto c = j.find("cursor"); c && c->isObj()) {
      Scope sc(*this, "cursor");
      known(*c, {"image", "size", "hot"});
      image(*c, "image", t.cursor.image);
      real(*c, "size", t.cursor.size, 8, 96);
      pair(*c, "hot", t.cursor.hot.x, t.cursor.hot.y, 0, 1);
    }
    if (auto d = j.find("screen"); d && d->isObj()) {
      Scope sc(*this, "screen");
      known(*d, {"effect", "color", "color2", "density", "speed", "size"});
      std::string k = d->str("effect");
      if (!backFxKnown(k)) {
        std::string all;
        for (auto& e : backFxKinds()) all += (all.empty() ? "" : ", ") + e.first;
        problem("effect can be " + all);
      } else {
        t.screen.kind = k;
        backFxDefaults(t.screen);
        auto take = [&](const char* key, Color& out) {
          SkinColor c;
          if (!color(*d, key, c)) return;
          const Style& st = t.style;
          Color base = c.from == SkinColor::From::Accent || c.from == SkinColor::From::Profile || c.from == SkinColor::From::Item ? st.accent
                       : c.from == SkinColor::From::Accent2                                                                   ? st.accent2
                       : c.from == SkinColor::From::Text                                                                      ? st.text
                       : c.from == SkinColor::From::Base                                                                      ? st.base
                       : c.from == SkinColor::From::Border                                                                    ? st.border
                                                                                                                              : c.c;
          out = base.withA(c.a);
        };
        take("color", t.screen.color);
        take("color2", t.screen.color2);
        real(*d, "density", t.screen.density, 0.1f, 4);
        real(*d, "speed", t.screen.speed, 0.1f, 4);
        real(*d, "size", t.screen.size, 0.3f, 3);
      }
    }
    if (auto d = j.find("draw"); d && d->isObj()) {
      Scope sc(*this, "draw");
      known(*d, {"title", "clock", "buttons", "tabs", "shadow", "fan", "text"});
      t.hasHubText = color(*d, "text", t.hubText);
      flag(*d, "title", t.ownTitle);
      flag(*d, "clock", t.ownClock);
      flag(*d, "buttons", t.ownButtons);
      flag(*d, "tabs", t.ownTabs);
      flag(*d, "shadow", t.ownShadow);
      flag(*d, "fan", t.ownFan);
    }
    if (auto d = j.find("tabs"); d && d->isObj()) {
      Scope sc(*this, "tabs");
      known(*d, {"inset", "text", "fill", "on"});
      real(*d, "inset", t.tabInset, 0, 60);
      t.hasTabText = color(*d, "text", t.tabText);
      t.hasTabFill = color(*d, "fill", t.tabFill);
      t.hasTabOn = color(*d, "on", t.tabOn);
    }
    t.radial = !t.back.empty() || !t.ring.empty() || !t.over.empty() || !t.hub.empty() || !t.front.empty();
    // A wheel without any clock layer keeps the built-in one unless told otherwise.
    for (auto* g : {&t.back, &t.over, &t.hub, &t.front})
      for (auto& L : *g)
        if (L.caption && !(j.find("draw") && j.find("draw")->find("title"))) t.ownTitle = false;
  }
};

// Changes one of the first entries of skin.json and leaves remarks and spacing as they are.
bool setText(std::string& json, const char* key, const std::string& value) {
  std::string k = std::string("\"") + key + "\"";
  size_t at = json.find(k);
  if (at == std::string::npos) return false;
  at += k.size();
  while (at < json.size() && strchr(" \t\r\n:", json[at])) at++;
  if (at >= json.size() || json[at] != '"') return false;
  size_t e = at + 1;
  while (e < json.size() && json[e] != '"') e += json[e] == '\\' ? 2 : 1;
  if (e >= json.size()) return false;
  std::string v = Json(value).dump();
  while (!v.empty() && v.back() == '\n') v.pop_back();
  json.replace(at, e + 1 - at, v);
  return true;
}

std::string idFrom(const std::string& s) {
  std::string o;
  for (char c : s) {
    if (isalnum((unsigned char)c)) o.push_back((char)tolower((unsigned char)c));
    else if (!o.empty() && o.back() != '-') o.push_back('-');
  }
  while (!o.empty() && o.back() == '-') o.pop_back();
  return o.substr(0, 40);
}

}  // namespace

bool parseSkin(const std::string& json, Skin& out, std::string* err) {
  Json j;
  int line = 0;
  if (json.size() > 2 * 1024 * 1024) {
    if (err) *err = "skin.json is too big.";
    return false;
  }
  if (!Json::parseLoose(json, j, &line) || !j.isObj()) {
    if (err) *err = line > 0 ? "skin.json cannot be read: look at line " + std::to_string(line) + "." : "skin.json cannot be read.";
    return false;
  }
  Reader r{out};
  r.all(j);
  if (auto id = j.str("id"); !idFrom(id).empty()) out.id = idFrom(id);
  return true;
}

// ---------------------------------------------------------------- files
struct SkinFiles::Held {
  CRITICAL_SECTION cs;
  Archive zip;
  bool open = false;
  Held() { InitializeCriticalSection(&cs); }
  ~Held() { DeleteCriticalSection(&cs); }
};
SkinFiles::SkinFiles() : held_(std::make_unique<Held>()) {}
SkinFiles::~SkinFiles() = default;

std::shared_ptr<SkinFiles> SkinFiles::open(const std::wstring& path, std::string* err) {
  std::shared_ptr<SkinFiles> f(new SkinFiles);
  f->path_ = path;
  if (dirExists(path)) {
    f->folder_ = true;
    return f;
  }
  std::string bytes;
  if (!readFile(path, bytes)) {
    if (err) *err = "The skin file cannot be opened.";
    return {};
  }
  if (!f->held_->zip.open(std::move(bytes), err)) return {};
  f->held_->open = true;
  return f;
}

bool SkinFiles::read(const std::string& name, std::string& out, size_t most) const {
  if (!safeInnerPath(name)) return false;
  if (folder_) {
    std::wstring rel = widen(name);
    std::replace(rel.begin(), rel.end(), L'/', L'\\');
    std::wstring p = joinPath(path_, rel);
    WIN32_FILE_ATTRIBUTE_DATA d{};
    if (!GetFileAttributesExW(p.c_str(), GetFileExInfoStandard, &d) || d.nFileSizeHigh || d.nFileSizeLow > most) return false;
    return readFile(p, out);
  }
  EnterCriticalSection(&held_->cs);
  bool ok = held_->open;
  if (!ok) {
    std::string bytes;
    ok = readFile(path_, bytes) && held_->zip.open(std::move(bytes), nullptr);
    held_->open = ok;
  }
  if (ok) {
    auto* e = held_->zip.find(name);
    ok = e && e->size <= most && held_->zip.read(*e, out);
  }
  LeaveCriticalSection(&held_->cs);
  return ok;
}

void SkinFiles::letGo() const {
  EnterCriticalSection(&held_->cs);
  held_->zip = Archive{};
  held_->open = false;
  LeaveCriticalSection(&held_->cs);
}

static void walk(const std::wstring& dir, const std::wstring& rel, int depth, const std::function<void(const std::wstring&, const WIN32_FIND_DATAW&)>& f, int& left) {
  WIN32_FIND_DATAW d;
  HANDLE h = FindFirstFileW(joinPath(dir, L"*").c_str(), &d);
  if (h == INVALID_HANDLE_VALUE) return;
  do {
    if (!wcscmp(d.cFileName, L".") || !wcscmp(d.cFileName, L"..") || --left < 0) continue;
    std::wstring r = rel.empty() ? d.cFileName : rel + L"/" + d.cFileName;
    if (d.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
      if (depth < 4 && !(d.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT)) walk(joinPath(dir, d.cFileName), r, depth + 1, f, left);
    } else {
      f(r, d);
    }
  } while (FindNextFileW(h, &d));
  FindClose(h);
}

std::vector<std::string> SkinFiles::list() const {
  std::vector<std::string> out;
  if (folder_) {
    int left = 2000;
    walk(path_, L"", 0, [&](const std::wstring& rel, const WIN32_FIND_DATAW&) {
      std::string n = narrow(rel);
      if (safeInnerPath(n) && out.size() < 600) out.push_back(n);
    }, left);
    return out;
  }
  EnterCriticalSection(&held_->cs);
  if (held_->open)
    for (auto& e : held_->zip.entries()) out.push_back(e.name);
  LeaveCriticalSection(&held_->cs);
  return out;
}

uint64_t skinStamp(const std::wstring& path) {
  WIN32_FILE_ATTRIBUTE_DATA d{};
  if (!GetFileAttributesExW(path.c_str(), GetFileExInfoStandard, &d)) return 0;
  auto mixIn = [](uint64_t h, uint64_t v) { return (h ^ v) * 0x100000001b3ull; };
  uint64_t h = 0xcbf29ce484222325ull;
  if (d.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
    int left = 2000;
    walk(path, L"", 0, [&](const std::wstring& rel, const WIN32_FIND_DATAW& f) {
      uint64_t one = 0xcbf29ce484222325ull;
      for (wchar_t c : rel) one = mixIn(one, c);
      one = mixIn(one, (uint64_t)f.ftLastWriteTime.dwHighDateTime << 32 | f.ftLastWriteTime.dwLowDateTime);
      h += mixIn(one, f.nFileSizeLow);  // the order of the files does not matter
    }, left);
  } else {
    h = mixIn(h, (uint64_t)d.ftLastWriteTime.dwHighDateTime << 32 | d.ftLastWriteTime.dwLowDateTime);
    h = mixIn(h, d.nFileSizeLow);
  }
  return h ? h : 1;
}

// ---------------------------------------------------------------- store
SkinStore& skins() {
  static SkinStore s;
  return s;
}

std::wstring SkinStore::userDir() { return joinPath(dataDir(), L"skins"); }
std::wstring SkinStore::builtinDir() {
  wchar_t env[1024];
  DWORD n = GetEnvironmentVariableW(RT_ID L"_SKINS", env, 1024);  // for the checks
  if (n > 0 && n < 1024) return env;
  return joinPath(dirName(modulePath()), L"skins");
}

static SkinInfo readInfo(const std::wstring& path, bool folder, bool builtin) {
  SkinInfo i;
  i.path = path;
  i.folder = folder;
  i.builtin = builtin;
  i.name = fileStem(path);
  i.id = idFrom(narrow(fileStem(path)));
  auto f = SkinFiles::open(path, &i.error);
  std::string text;
  if (!f) return i;
  if (!f->read("skin.json", text, SkinFiles::kJsonMost)) {
    i.error = "There is no skin.json in it.";
    return i;
  }
  Json j;
  int line = 0;
  if (!Json::parseLoose(text, j, &line) || !j.isObj()) {
    i.error = "skin.json cannot be read: look at line " + std::to_string(std::max(1, line)) + ".";
    return i;
  }
  if (auto id = idFrom(j.str("id")); !id.empty()) i.id = id;
  if (auto n = widen(j.str("name")); !n.empty()) i.name = n.substr(0, 60);
  i.author = widen(j.str("author")).substr(0, 60);
  i.about = widen(j.str("about")).substr(0, 160);
  if (auto g = j.find("tags"); g && g->isArr())
    for (auto& e : g->a)
      if (e.t == Json::T::Str && i.tags.size() < 8) i.tags.push_back(widen(e.s).substr(0, 24));
  std::string pv = j.str("preview");
  if (!pv.empty() && safeInnerPath(pv)) i.preview = pv;
  else
    for (auto& n : f->list())
      if (n == "preview.jpg" || n == "preview.png") i.preview = n;
  return i;
}

// Only names, sizes and times: cheap enough to ask every second or two.
uint64_t SkinStore::dirsStamp() {
  uint64_t sum = 0;
  for (auto& dir : {builtinDir(), userDir()}) {
    WIN32_FIND_DATAW d;
    HANDLE h = FindFirstFileW(joinPath(dir, L"*").c_str(), &d);
    if (h == INVALID_HANDLE_VALUE) continue;
    int left = 400;
    do {
      if (d.cFileName[0] == L'.' || --left < 0) continue;
      FILETIME t = d.ftLastWriteTime;
      DWORD size = d.nFileSizeLow;
      if (d.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
        WIN32_FILE_ATTRIBUTE_DATA a{};
        if (!GetFileAttributesExW(joinPath(joinPath(dir, d.cFileName), L"skin.json").c_str(), GetFileExInfoStandard, &a)) continue;
        t = a.ftLastWriteTime;
        size = a.nFileSizeLow;
      }
      uint64_t one = 0xcbf29ce484222325ull;
      for (wchar_t* c = d.cFileName; *c; c++) one = (one ^ *c) * 0x100000001b3ull;
      one = (one ^ t.dwLowDateTime) * 0x100000001b3ull;
      one = (one ^ t.dwHighDateTime ^ (uint64_t)size << 20) * 0x100000001b3ull;
      sum += one;
    } while (FindNextFileW(h, &d));
    FindClose(h);
  }
  return sum;
}

bool SkinStore::refreshIfChanged() {
  if (listed_ && dirsStamp() == dirStamp_) return false;
  listed_ = false;
  return true;
}

const std::vector<SkinInfo>& SkinStore::list() {
  if (listed_) return list_;
  double began = nowSec();
  listed_ = true;
  dirStamp_ = dirsStamp();
  list_.clear();
  std::map<std::string, size_t> at;
  for (int pass = 0; pass < 2; pass++) {
    std::wstring dir = pass ? userDir() : builtinDir();
    WIN32_FIND_DATAW d;
    HANDLE h = FindFirstFileW(joinPath(dir, L"*").c_str(), &d);
    if (h == INVALID_HANDLE_VALUE) continue;
    int seen = 0;
    std::vector<SkinInfo> found;
    do {
      if (d.cFileName[0] == L'.' || seen > 300) continue;
      std::wstring p = joinPath(dir, d.cFileName);
      bool folder = (d.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0;
      if (folder ? !fileExists(joinPath(p, L"skin.json")) : fileExt(d.cFileName) != L".rskin") continue;
      seen++;
      // reading one means opening an archive: only what is new or changed
      uint64_t stamp = skinStamp(p);
      auto& known = infos_[p];
      if (known.first != stamp || known.second.id.empty()) known = {stamp, readInfo(p, folder, pass == 0)};
      if (!known.second.id.empty()) found.push_back(known.second);
    } while (FindNextFileW(h, &d));
    FindClose(h);
    // Files put there by hand can share an id. The one that is called like it keeps it, the others get a number.
    std::stable_partition(found.begin(), found.end(), [](const SkinInfo& q) { return idFrom(narrow(fileStem(q.path))) == q.id; });
    std::map<std::string, int> here;
    for (auto& i : found) {
      if (here.count(i.id)) {
        std::string base = i.id;
        for (int k = 2; here.count(i.id) || at.count(i.id); k++) i.id = base + "-" + std::to_string(k);
      }
      here[i.id] = 1;
      // One's own skin of the same id stands in for the one that came with the program.
      auto it = at.find(i.id);
      if (it != at.end()) {
        list_[it->second] = i;
      } else {
        at[i.id] = list_.size();
        list_.push_back(i);
      }
    }
  }
  std::stable_sort(list_.begin(), list_.end(), [](const SkinInfo& a, const SkinInfo& b) {
    if (a.builtin != b.builtin) return b.builtin;  // one's own first
    return CompareStringOrdinal(a.name.c_str(), -1, b.name.c_str(), -1, TRUE) == CSTR_LESS_THAN;
  });
  if (logging()) logf("skins: %zu found in %.1f ms", list_.size(), (nowSec() - began) * 1000);
  return list_;
}

const SkinInfo* SkinStore::info(const std::string& id) {
  for (auto& i : list())
    if (i.id == id) return &i;
  return nullptr;
}

void SkinStore::distrust(const std::string& id) {
  const SkinInfo* i = info(id);
  if (!i) return;
  bad_[id] = skinStamp(i->path);
  loaded_.erase(id);
  logf("skin %s: could not be drawn, left out", id.c_str());
}

std::shared_ptr<const Skin> SkinStore::get(const std::string& id) {
  if (id.empty()) return {};
  if (auto b = bad_.find(id); b != bad_.end()) {
    if (nowSec() - badAt_ < 0.7) return {};
    badAt_ = nowSec();
    const SkinInfo* i = info(id);
    if (!i || skinStamp(i->path) == b->second) return {};
    bad_.erase(b);
  }
  auto it = loaded_.find(id);
  double now = nowSec();
  if (it != loaded_.end()) {
    if (checkedId_ == id && now - checkedAt_ < 0.5) return it->second;
    checkedId_ = id;
    checkedAt_ = now;
    if (it->second && skinStamp(it->second->path) == it->second->stamp) return it->second;
    loaded_.erase(it);
    listed_ = false;
  }
  if (missing_ == id && now - missingAt_ < 1.5) return {};
  const SkinInfo* i = info(id);
  if (!i && refreshIfChanged()) i = info(id);  // perhaps it was put there a moment ago
  if (!i) {
    missing_ = id;
    missingAt_ = now;
    return {};
  }
  missing_.clear();
  auto t = std::make_shared<Skin>();
  t->path = i->path;
  t->folder = i->folder;
  t->builtin = i->builtin;
  t->stamp = skinStamp(i->path);
  t->name = i->name;
  std::string err, text;
  auto f = SkinFiles::open(i->path, &err);
  if (!f || !f->read("skin.json", text, SkinFiles::kJsonMost) || !parseSkin(text, *t, &err)) {
    logf("skin %s: %s", id.c_str(), err.c_str());
    missing_ = id;
    missingAt_ = now;
    return {};
  }
  t->id = i->id;
  // files that are missing are worth knowing about while a skin is being made
  auto have = f->list();
  auto there = [&](const std::string& n) {
    for (auto& h : have)
      if (CompareStringOrdinal(widen(h).c_str(), -1, widen(n).c_str(), -1, TRUE) == CSTR_EQUAL) return true;
    return false;
  };
  for (auto& im : t->images) {
    if (!there(im.file)) t->problems.push_back("the file \"" + im.file + "\" is missing");
    if (!im.mask.empty() && !there(im.mask)) t->problems.push_back("the file \"" + im.mask + "\" is missing");
  }
  for (auto& q : t->fonts)
    if (!q.file.empty() && !there(q.file)) t->problems.push_back("the file \"" + q.file + "\" is missing");
  for (auto& s : t->sounds)
    if (!there(s.second)) t->problems.push_back("the file \"" + s.second + "\" is missing");
  for (auto& p : t->problems) logf("skin %s: %s", id.c_str(), p.c_str());
  if (loaded_.size() > 3) loaded_.clear();
  loaded_[id] = t;
  checkedId_ = id;
  checkedAt_ = now;
  return t;
}

// What a skin consists of. Nothing else is written to a folder that Explorer will show, or passed on.
static bool skinPart(const std::string& name) {
  static const char* const kinds[] = {".json", ".txt", ".md", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".wav", ".ttf", ".otf"};
  std::string low = name;
  for (auto& c : low) c = (char)tolower((unsigned char)c);
  for (auto k : kinds)
    if (low.size() > strlen(k) && low.compare(low.size() - strlen(k), std::string::npos, k) == 0) return true;
  return false;
}

// Every part of a skin, up to what may be imported again.
static bool gather(const SkinFiles& f, std::vector<std::pair<std::string, std::string>>& all, std::string* err) {
  auto names = f.list();
  std::sort(names.begin(), names.end());
  size_t total = 0;
  for (auto& n : names) {
    if (!skinPart(n)) continue;
    std::string b;
    if (!f.read(n, b)) {
      if (err) *err = "\"" + n + "\" cannot be read, or is bigger than 24 MB.";
      return false;
    }
    total += b.size() + n.size() * 2 + 120;
    if (total > 47u << 20) {
      if (err) *err = "The skin is bigger than 48 MB.";
      return false;
    }
    all.push_back({n, std::move(b)});
  }
  return true;
}

static bool recycle(const std::wstring& path) {
  std::wstring from = path;
  from.push_back(L'\0');
  SHFILEOPSTRUCTW op{};
  op.wFunc = FO_DELETE;
  op.pFrom = from.c_str();
  op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI;
  return SHFileOperationW(&op) == 0 && !op.fAnyOperationsAborted;
}

bool SkinStore::install(const std::wstring& file, std::string& id, std::string* err) {
  std::string e2, text;
  if (!err) err = &e2;
  auto f = SkinFiles::open(file, err);
  if (!f) return false;
  if (!f->read("skin.json", text, SkinFiles::kJsonMost)) {
    *err = "This is not a skin: there is no skin.json in it.";
    return false;
  }
  Skin t;
  if (!parseSkin(text, t, err)) return false;
  SkinInfo i = readInfo(file, f->folder(), false);
  id = i.id.empty() ? "skin" : i.id;
  refresh();
  std::wstring dst = joinPath(userDir(), widen(id) + L".rskin");
  std::string rename;
  if (auto* old = info(id); old && toLower(old->path) != toLower(file)) {
    // The same skin again replaces the older copy, whatever its file is called. Another one that happens to share the id
    // (every "My ..." copy does) gets an id of its own.
    bool same = old->name == i.name && old->author == i.author && !old->folder;
    if (same && i.author.empty()) {  // nobody knows whose it is: only the very same file counts as the same
      std::string x, y;
      same = readFile(old->path, x) && readFile(file, y) && x == y;
    }
    if (same) {
      if (!old->builtin) dst = old->path;
    } else {
      std::string base = id.substr(0, 40);
      for (int k = 2; info(id) || fileExists(joinPath(userDir(), widen(id) + L".rskin")); k++) id = base + "-" + std::to_string(k);
      rename = id;
      dst = joinPath(userDir(), widen(id) + L".rskin");
    }
  }
  std::string bytes;
  if (f->folder() || !rename.empty()) {  // somebody's working folder, or one that gets another id
    std::vector<std::pair<std::string, std::string>> all;
    if (!gather(*f, all, err)) return false;
    if (!rename.empty())
      for (auto& q : all)
        if (q.first == "skin.json") setText(q.second, "id", rename);
    bytes = makeZip(all);
  } else if (!readFile(file, bytes)) {
    *err = "The skin file cannot be opened.";
    return false;
  }
  Archive whole;  // everything in it has to be readable, and within the limits
  if (!whole.open(bytes, err)) return false;
  SHCreateDirectoryExW(nullptr, userDir().c_str(), nullptr);
  if (toLower(dst) != toLower(file)) {
    std::string have;
    if (fileExists(dst) && !(readFile(dst, have) && have == bytes)) recycle(dst);  // somebody may miss it
    if (!writeFileAtomic(dst, bytes)) {
      *err = "The skin could not be copied to the skins folder.";
      return false;
    }
  }
  refresh();
  missing_.clear();
  loaded_.erase(id);
  bad_.erase(id);
  return true;
}

bool SkinStore::remove(const std::string& id, std::string* err) {
  const SkinInfo* i = info(id);
  if (!i || i->builtin) {
    if (err) *err = "That skin came with the program.";
    return false;
  }
  bool ok = recycle(i->path);  // somebody may have made it themselves
  if (!ok && err) *err = "The skin could not be removed.";
  loaded_.erase(id);
  refresh();
  return ok;
}

bool SkinStore::copyToFolder(const std::string& id, const std::wstring& name, std::wstring& folder, std::string* err) {
  const SkinInfo* i = info(id);
  auto f = i ? SkinFiles::open(i->path, err) : nullptr;
  if (!f) return false;
  std::string nid = idFrom(narrow(name));
  if (nid.empty()) nid = "my-skin";
  std::string base = nid;
  for (int k = 2; info(nid) || dirExists(joinPath(userDir(), widen(nid))); k++) nid = base + "-" + std::to_string(k);
  folder = joinPath(userDir(), widen(nid));
  for (auto& n : f->list()) {
    std::string bytes;
    if (!skinPart(n) || !f->read(n, bytes)) continue;
    if (n == "skin.json") {
      setText(bytes, "id", nid);
      setText(bytes, "name", narrow(name));
      setText(bytes, "author", "");
    }
    std::wstring rel = widen(n);
    std::replace(rel.begin(), rel.end(), L'/', L'\\');
    std::wstring dst = joinPath(folder, rel);
    SHCreateDirectoryExW(nullptr, dirName(dst).c_str(), nullptr);
    if (!writeFileAtomic(dst, bytes)) {
      if (err) *err = "The copy could not be written.";
      return false;
    }
  }
  refresh();
  return true;
}

bool SkinStore::pack(const std::string& id, const std::wstring& file, std::string* err) {
  const SkinInfo* i = info(id);
  auto f = i ? SkinFiles::open(i->path, err) : nullptr;
  if (!f) return false;
  std::vector<std::pair<std::string, std::string>> all;
  if (!gather(*f, all, err)) return false;
  if (!writeFileAtomic(file, makeZip(all))) {
    if (err) *err = "The file could not be written.";
    return false;
  }
  return true;
}

}  // namespace rt
