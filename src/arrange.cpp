// The other arrangements. They share picking, groups, name tags, profile dots and skins; each one only decides where
// things are and how they move.
#include "scene.h"

namespace rt {

namespace {

class FreeLayout : public Layout {
 protected:
  struct It {
    Spring in, hot;
    float delay = 0;
    // worked out by place()
    V2 pos;
    float size = 48, half = 30, alpha = 1, z = 0, turn = 0;
    bool there = true;       // can be picked
  };
  std::vector<It> its_;
  float s_ = 1, icon_ = 48;
  V2 c_, ext_{300, 300};     // centre and half size of the arrangement
  int hot_ = -1;
  bool keyed_ = false;
  Spring presence_;
  Flyout fly_;
  std::wstring tag_, tagSub_;
  float tagT_ = 0;
  float launchT() const { return closing && launched ? smooth01(closeT / 0.17f) : 0.f; }
  int count() const { return (int)its_.size(); }

  // ---- for each arrangement
  virtual void arrange() = 0;                        // sizes for s_; sets ext_
  virtual void place() = 0;                          // positions for this moment
  virtual bool animate(float) { return false; }      // own springs
  virtual void drawBack(Painter&, const Backdrop*, float) {}
  virtual void drawItem(Painter& p, const Backdrop* bd, int i, float a) {
    It& t = its_[(size_t)i];
    Entry e;
    e.index = i;
    e.count = count();
    e.hot = t.hot.x;
    e.alpha = a;
    e.turn = t.turn;
    e.clock = std::max(0.f, time - t.delay);
    drawEntry(p, bd, model.items[(size_t)i], t.pos, t.half, t.size, e);
    if (cfg.labels == Labels::Always && i != hot_ && t.there) {
      float w = t.half * 2.3f;
      RectF r = RectF::xywh(t.pos.x - w * 0.5f, t.pos.y + t.half + 3.f * s_, w, 16.f * s_);
      p.textHalo(model.items[(size_t)i].label, label(11.f * s_, 500, Align::Center, VAlign::Top), r, st.text.withA(0.9f * a), halo(0.8f * a), 4.f * s_);
    }
  }
  virtual V2 tagDir(int i) const { return its_[(size_t)i].pos.y > c_.y + 0.75f * ext_.y ? V2{0, -1} : V2{0, 1}; }
  virtual void focusOn(int i) { setHot(i); }
  virtual float order(int i) const { return (float)i / std::max(1, count()); }
  virtual float introSpread() const { return 0.22f; }
  virtual bool inside(V2 p) const { return fabsf(p.x - c_.x) < ext_.x && fabsf(p.y - c_.y) < ext_.y; }
  virtual bool ownTag() const { return true; }
  virtual V2 margins() const { return {330.f * s_, 96.f * s_}; }

 public:
  void build() override {
    float fit = 1.f;
    for (int pass = 0; pass < 3; pass++) {
      s_ = env.s * fit;
      icon_ = cfg.iconSize * s_;
      if (its_.size() != model.items.size() || !pass) {
        its_.assign(model.items.size(), It{});
        for (auto& t : its_) t.size = icon_;
      }
      arrange();
      float k = std::min((env.work.w() * 0.5f - 12.f) / std::max(1.f, ext_.x), (env.work.h() * 0.5f - 30.f) / std::max(1.f, ext_.y));
      if (k >= 1.f || k < 0.05f) break;
      fit *= k * 0.995f;
    }
    c_ = env.anchor;
    settle();
    for (int i = 0; i < count(); i++) {
      its_[(size_t)i].in.snap(0);
      its_[(size_t)i].delay = cfg.reduceMotion || st.open == OpenAnim::Fade || st.open == OpenAnim::Zoom ? 0.f : order(i) * introSpread() / std::max(0.4f, motion());
    }
    hot_ = -1;
    fly_ = Flyout{};
    presence_.snap(0);
    seenPick_ = -1;
    place();
  }
  virtual void settle() {  // keeps the whole arrangement on screen
    if (env.work.w() > ext_.x * 2) c_.x = clampf(c_.x, env.work.l + ext_.x, env.work.r - ext_.x);
    else c_.x = env.work.cx();
    if (env.work.h() > ext_.y * 2) c_.y = clampf(c_.y, env.work.t + ext_.y, env.work.b - ext_.y);
    else c_.y = env.work.cy();
  }
  RectF bounds() const override {
    V2 m = margins();
    RectF r(c_.x - ext_.x - m.x, c_.y - ext_.y - m.y, c_.x + ext_.x + m.x, c_.y + ext_.y + m.y);
    return RectF(std::max(0.f, r.l), std::max(0.f, r.t), std::min(env.vw, r.r), std::min(env.vh, r.b));
  }
  V2 tiltCenter() const override { return c_; }
  V2 home() const override { return c_; }
  Pick pick() const override {
    if (hot_ < 0 || hot_ >= count()) return {};
    Pick k;
    k.item = hot_;
    if (fly_.item == hot_ && fly_.open.target > 0.5f && fly_.hotKid >= 0) k.kid = fly_.hotKid;
    return k;
  }
  V2 spot(Pick k) const override {
    if (k.item < 0 || k.item >= count()) return c_;
    if (k.kid >= 0 && k.item == fly_.item && k.kid < (int)fly_.cells.size()) return fly_.cells[(size_t)k.kid];
    return its_[(size_t)k.item].pos;
  }
  bool outside(V2 p) const override {
    if (fly_.item >= 0 && fly_.open.target > 0.5f && fly_.rect.inset(-20.f * s_).contains(p)) return false;
    if (dotAt(p, s_) >= 0) return false;
    return !(fabsf(p.x - c_.x) < ext_.x + 40.f * s_ && fabsf(p.y - c_.y) < ext_.y + 40.f * s_);
  }
  float drawScale() const override { return s_; }
  void skinVars(float* v) const override {
    if (hot_ >= 0) {
      V2 d = its_[(size_t)hot_].pos - c_;
      float to = angleOf(d) * 180.f / kPi;
      v[vSel] += wrapAngle((to - v[vSel]) * kPi / 180.f) * 180.f / kPi * 0.35f;
      v[vSelIndex] = (float)hot_;
    }
    v[vOn] = tagT_;
    v[vIdle] = 1.f - tagT_;
  }
  SkinPlace skinPlace() const override {
    SkinPlace q;
    q.center = c_;
    q.wheel = std::min(ext_.x, ext_.y);
    q.hub = q.wheel * 0.3f;
    q.ringIn = q.hub;
    q.ringOut = q.wheel;
    q.stage = RectF(c_.x - ext_.x, c_.y - ext_.y, c_.x + ext_.x, c_.y + ext_.y);
    q.cell = icon_ * 0.66f;
    q.spot = pick().valid() ? spot(pick()) : c_;
    return q;
  }

  // ------------------------------------------------------------ profiles
  V2 dotPos(int i) const override { return {c_.x + (i - (dotCount() - 1) * 0.5f) * 19.f * s_, dotY()}; }
  virtual float dotY() const {
    float below = c_.y + ext_.y + 26.f * s_;
    return below < env.work.b - 12.f * s_ ? below : c_.y - ext_.y - 26.f * s_ > env.work.t + 12.f * s_ ? c_.y - ext_.y - 26.f * s_ : env.work.b - 14.f * s_;
  }
  int profileAt(V2 p) const override { return dotAt(p, s_); }
  int hotProfile() const override { return hotDot_; }

  // ------------------------------------------------------------ input
  virtual int hitAt(V2 p) const {
    int best = -1;
    float bz = -1e9f, bd = 1e9f;
    for (int i = 0; i < count(); i++) {
      const It& t = its_[(size_t)i];
      if (!t.there || t.alpha < 0.2f) continue;
      float d = (t.pos - p).len();
      if (d > t.half * 1.22f) continue;
      // In front first, then whichever is nearer.
      if (t.z > bz + 0.08f || (t.z > bz - 0.08f && d < bd)) {
        best = i;
        bz = t.z;
        bd = d;
      }
    }
    return best;
  }
  void setHot(int i) {
    if (i >= 0) hotDot_ = -1;
    if (i == hot_) return;
    hot_ = i;
    fly_.dwell = 0;
    if (fly_.item >= 0 && fly_.item != i) {
      fly_.open.target = 0;
      fly_.hotKid = -1;
    }
  }
  void pointer(V2 p) override {
    ptr = p;
    pointerKnown = true;
    keyed_ = false;
    hotDot_ = dotAt(p, s_);
    if (hotDot_ >= 0) {
      setHot(-1);
      return;
    }
    if (fly_.item >= 0 && fly_.open.target > 0.5f) {
      int k = fly_.hit(p);
      if (k >= 0 || fly_.rect.inset(-8.f * s_).contains(p)) {
        fly_.hotKid = k;
        return;
      }
      fly_.hotKid = -1;
    }
    presence_.target = inside(p) ? 1.f : 0.f;
    int i = hitAt(p);
    // On the way from a group to its panel there is nothing to pick.
    if (i < 0 && fly_.item >= 0 && fly_.open.target > 0.5f && (p - its_[(size_t)fly_.item].pos).len() < icon_ * 1.6f) return;
    setHot(i);
  }
  void clearHover() override {
    setHot(-1);
    hotDot_ = -1;
    presence_.target = 0;
    pointerKnown = false;
  }
  void select(int item) override {
    if (item < 0 || item >= count()) return;
    keyed_ = true;
    focusOn(item);
  }
  // The nearest entry in a direction, as seen on screen.
  int toward(V2 dir) const {
    if (hot_ < 0) return count() ? 0 : -1;
    V2 from = its_[(size_t)hot_].pos;
    int best = -1;
    float bs = 1e9f;
    for (int i = 0; i < count(); i++) {
      if (i == hot_ || !its_[(size_t)i].there || its_[(size_t)i].alpha < 0.2f) continue;
      V2 d = its_[(size_t)i].pos - from;
      float along = d.x * dir.x + d.y * dir.y, side = fabsf(d.x * dir.y - d.y * dir.x);
      if (along < 4.f) continue;
      float score = along + side * 2.2f;
      if (side > along * 2.4f) continue;
      if (score < bs) {
        bs = score;
        best = i;
      }
    }
    return best;
  }
  bool inKids() const { return fly_.item >= 0 && fly_.item == hot_ && fly_.open.target > 0.5f && fly_.hotKid >= 0; }
  bool kidKey(NavKey k) {
    if (!inKids()) return false;
    int m = (int)fly_.cells.size();
    V2 d = k == NavKey::Left ? V2{-1, 0} : k == NavKey::Right ? V2{1, 0} : k == NavKey::Up ? V2{0, -1} : V2{0, 1};
    if (k == NavKey::Next) { fly_.hotKid = (fly_.hotKid + 1) % m; return true; }
    if (k == NavKey::Prev) { fly_.hotKid = (fly_.hotKid + m - 1) % m; return true; }
    int best = -1;
    float bs = 1e9f;
    V2 from = fly_.cells[(size_t)fly_.hotKid];
    for (int i = 0; i < m; i++) {
      V2 q = fly_.cells[(size_t)i] - from;
      float along = q.x * d.x + q.y * d.y, side = fabsf(q.x * d.y - q.y * d.x);
      if (along < 2.f || side > along * 1.2f) continue;
      if (along + side * 2 < bs) { bs = along + side * 2; best = i; }
    }
    if (best >= 0) {
      fly_.hotKid = best;
    } else {  // out of the panel, back to the group
      fly_.open.target = 0;
      fly_.hotKid = -1;
      fly_.dwell = -10;
    }
    return true;
  }
  void key(NavKey k) override {
    int n = count();
    if (!n) return;
    keyed_ = true;
    presence_.target = 1;
    if (kidKey(k)) return;
    if (hot_ < 0) {
      focusOn(k == NavKey::Prev ? n - 1 : first());
      return;
    }
    switch (k) {
      case NavKey::Next: focusOn((hot_ + 1) % n); return;
      case NavKey::Prev: focusOn((hot_ + n - 1) % n); return;
      default: break;
    }
    V2 d = k == NavKey::Left ? V2{-1, 0} : k == NavKey::Right ? V2{1, 0} : k == NavKey::Up ? V2{0, -1} : V2{0, 1};
    int to = toward(d);
    if (to >= 0) focusOn(to);
    else if (k == NavKey::Up) openKids();
  }
  virtual int first() const { return 0; }
  bool wheel(float) override { return false; }

  virtual V2 flyDir(int i) const {
    V2 d = its_[(size_t)i].pos - c_;
    if (fabsf(d.x) < 8.f * s_ && fabsf(d.y) < 8.f * s_) return {0, -1};
    return fabsf(d.x) > fabsf(d.y) ? V2{d.x > 0 ? 1.f : -1.f, 0} : V2{0, d.y > 0 ? 1.f : -1.f};
  }
  void openFly() {
    if (hot_ < 0) return;
    auto& kids = model.items[(size_t)hot_].kids;
    if (kids.empty()) return;
    const It& t = its_[(size_t)hot_];
    if (fly_.item != hot_) {
      fly_ = Flyout{};
      fly_.item = hot_;
    }
    V2 d = flyDir(hot_);
    float cell = cfg.iconSize * s_ * 1.55f, ic = cfg.iconSize * s_ * 0.92f;
    RectF area = bounds().inset(6.f * s_);
    fly_.layoutCells((int)kids.size(), t.pos + d * (t.half * 0.9f), d, cell, ic, area);
    fly_.caption = 24.f * s_;
    fly_.rect.b += fly_.caption;
    if (fly_.rect.b > area.b) {
      float up = fly_.rect.b - area.b;
      fly_.rect = fly_.rect.offset(0, -up);
      for (auto& q : fly_.cells) q.y -= up;
    }
    fly_.from = t.pos;
    fly_.open.target = 1;
  }
  bool openKids() override {
    if (hot_ < 0 || model.items[(size_t)hot_].kids.empty()) return false;
    openFly();
    fly_.hotKid = (int)fly_.cells.size() / 2;
    return true;
  }
  bool slideIn(int dir) override {
    for (auto& t : its_) {
      t.in.snap(cfg.reduceMotion ? 0.3f : 0.4f);
      t.delay = 0;
    }
    time = std::max(time, 1.f);
    return true;
  }

  // ------------------------------------------------------------ animation
  bool tick(float dt) override {
    tickBase(dt);
    float m = motion();
    bool busy = !open.settled() || closing;
    busy |= tickDots(dt);
    presence_.step(dt, 4.f * m, 0.9f);
    busy |= !presence_.settled();
    for (int i = 0; i < count(); i++) {
      It& t = its_[(size_t)i];
      t.in.target = time >= t.delay ? 1.f : 0.f;
      if (cfg.reduceMotion || st.open == OpenAnim::Fade) t.in.step(dt, 8.f, 1.f);
      else t.in.step(dt, 3.6f * st.speed, 0.68f);
      t.hot.target = i == hot_ && !closing ? (inKids() ? 0.6f : 1.f) : 0.f;
      if (closing && launched && launchPick.item == i) t.hot.target = 1.f;
      t.hot.step(dt, 6.5f * m, 0.68f);
      busy |= !t.in.settled() || !t.hot.settled();
    }
    if (hot_ >= 0 && !closing && !model.items[(size_t)hot_].kids.empty() && !(fly_.item == hot_ && fly_.open.target > 0.5f)) {
      fly_.dwell += dt;
      busy = true;
      if (fly_.dwell > (model.items[(size_t)hot_].isGroup() ? 0.16f : 0.45f)) openFly();
    }
    fly_.open.step(dt, (fly_.open.target > 0.5f ? 4.2f : 6.5f) * m, 0.8f);
    busy |= !fly_.open.settled();
    if (fly_.item >= 0 && fly_.open.target < 0.5f && fly_.open.x < 0.02f) fly_.item = -1;
    for (size_t i = 0; i < fly_.hot.size(); i++) {
      fly_.hot[i].target = (int)i == fly_.hotKid ? 1.f : 0.f;
      fly_.hot[i].step(dt, 7.f * m, 0.75f);
      busy |= !fly_.hot[i].settled();
    }
    std::wstring t, sb;
    if (hot_ >= 0) {
      t = model.items[(size_t)hot_].label;
      sb = model.items[(size_t)hot_].sub;
    }
    if (!t.empty() && (t != tag_ || sb != tagSub_)) {
      tag_ = t;
      tagSub_ = sb;
    }
    float want = t.empty() ? 0.f : 1.f;
    if (tagT_ != want) {
      tagT_ = want > tagT_ ? std::min(1.f, tagT_ + dt * 7.f * m) : std::max(0.f, tagT_ - dt * 9.f * m);
      busy = true;
    }
    busy |= animate(dt);
    place();
    busy |= tickSkin(dt, t, sb);
    tickParticles(dt, c_, std::min(ext_.x, ext_.y) * 0.2f, std::min(ext_.x, ext_.y));
    if (!bits_.empty() || !sparks_.empty()) busy = true;
    return busy;
  }
  // Something slid under a pointer that rests: that is what it points at now.
  void repick() {
    if (pointerKnown && !keyed_ && !closing && hotDot_ < 0 && !(fly_.item >= 0 && fly_.open.target > 0.5f)) setHot(hitAt(ptr));
  }

  // ------------------------------------------------------------ drawing
  void draw(Painter& p, const Backdrop* bd) override {
    float alpha = fade();
    plates_ = true;
    drawBack(p, bd, alpha);
    drawSkinStage(p, bd, alpha, false);
    if (st.particles != Particles::Off && !(view && skin->radial)) drawParticles(p, alpha * 0.8f);
    std::vector<int> ord(its_.size());
    for (size_t i = 0; i < ord.size(); i++) ord[i] = (int)i;
    std::sort(ord.begin(), ord.end(), [&](int a, int b) {
      const It &x = its_[(size_t)a], &y = its_[(size_t)b];
      float kx = x.z + std::max(0.f, x.hot.x) * lift(), ky = y.z + std::max(0.f, y.hot.x) * lift();
      return kx != ky ? kx < ky : a < b;
    });
    drawItems(p, bd, ord, alpha);
    bool flyOpen = fly_.item >= 0 && fly_.open.x > 0.02f;
    if (flyOpen) drawFlyout(p, bd, fly_, model.items[(size_t)fly_.item], alpha);
    if (ownTag() && hot_ >= 0 && tagT_ > 0.01f) {
      const It& t = its_[(size_t)hot_];
      float a = tagT_ * alpha * (fly_.item == hot_ ? 1.f - saturate(fly_.open.x * 1.6f) : 1.f);
      V2 d = tagDir(hot_);
      float out = t.half + (10.f + (1.f - easeOutCubic(tagT_)) * 10.f) * s_;
      drawTag(p, bd, t.pos + d * out, d, tag_, tagSub_, a, bounds().inset(4.f * s_));
    }
    if (model.items.empty()) drawTag(p, bd, c_, {0, 0.001f}, L"No pins yet", L"Right-click for settings", alpha, bounds());
    drawDots(p, bd, s_, alpha);
    drawSkinStage(p, bd, alpha, true);
    if (dotTag_ > 0.01f && dotCount()) {
      V2 d{0, dotY() > c_.y ? -1.f : 1.f};
      drawTag(p, bd, dotTagAt() + d * ((18.f + (1.f - easeOutCubic(dotTag_)) * 8.f) * s_), d, dotName_, dotSub_, dotTag_ * alpha, bounds().inset(4.f * s_));
    }
    if (!sparks_.empty()) {
      auto keep = std::move(bits_);
      bits_.clear();
      drawParticles(p, 1.f);
      bits_ = std::move(keep);
    }
    plates_ = false;
  }
  virtual float lift() const { return 10.f; }
  virtual void drawItems(Painter& p, const Backdrop* bd, const std::vector<int>& ord, float alpha) {
    for (int i : ord) {
      It& t = its_[(size_t)i];
      float a = alpha * t.alpha * saturate(t.in.x * 1.4f);
      if (a <= 0.01f) continue;
      if (closing && launched && launchPick.item == i) {
        float k = lerp(1.f, 1.25f, launchT());
        It keep = t;
        t.size *= k;
        t.half *= k;
        drawItem(p, bd, i, a);
        t = keep;
      } else {
        drawItem(p, bd, i, a);
      }
    }
  }
};

// ---------------------------------------------------------------- orbit: a small solar system, seen at an angle
class OrbitLayout final : public FreeLayout {
  struct Ring {
    float r = 0, phase = 0, speed = 1;
    int first = 0, n = 0;
    Spring stop;
  };
  std::vector<Ring> rings_;
  float sun_ = 54;
  static constexpr float kTilt = 0.64f;

  void arrange() override {
    rings_.clear();
    int n = count(), done = 0;
    sun_ = 50.f * s_;
    float r = sun_ + icon_ * 1.55f * cfg.spread;
    while (done < n) {
      Ring g;
      g.r = r;
      int cap = std::max(3, (int)(kTau * r * 0.78f / (icon_ * 1.75f * cfg.spread)));
      if (rings_.empty()) cap = std::min(cap, cfg.perRing);
      g.first = done;
      g.n = std::min(n - done, cap);
      if (n - done - g.n == 1 && g.n > 3) g.n++;  // nobody likes to travel alone
      done += g.n;
      size_t k = rings_.size();
      g.speed = (k % 2 ? -1.f : 1.f) * 0.30f / (1.f + 0.45f * k);
      g.phase = kPi + 0.5f * k;
      rings_.push_back(g);
      r += icon_ * 1.95f * cfg.spread;
    }
    float R = rings_.empty() ? sun_ : rings_.back().r;
    ext_ = {R + icon_ * 0.95f, R * kTilt + icon_ * 1.05f};
  }
  int ringOf(int i) const {
    for (size_t k = 0; k < rings_.size(); k++)
      if (i < rings_[k].first + rings_[k].n) return (int)k;
    return 0;
  }
  bool animate(float dt) override {
    bool moving = false;
    int hr = hot_ >= 0 ? ringOf(hot_) : -1;
    bool still = cfg.reduceMotion || cfg.drift < 0.01f;
    for (size_t k = 0; k < rings_.size(); k++) {
      Ring& g = rings_[k];
      g.stop.target = hr >= 0 ? ((int)k == hr ? 1.f : 0.85f) : presence_.target > 0.5f && pointerKnown && (ptr - c_).len() > sun_ * 1.3f ? 0.75f : 0.f;
      g.stop.step(dt, 3.f, 1.f);
      if (!still) {
        g.phase += g.speed * cfg.drift * dt * (1.f - saturate(g.stop.x));
        moving = true;
      }
    }
    if (moving) repick();
    return moving;
  }
  void place() override {
    for (auto& g : rings_)
      for (int j = 0; j < g.n; j++) {
        It& t = its_[(size_t)(g.first + j)];
        float in = clampf(t.in.x, 0.f, 1.2f), a = g.phase + j * kTau / g.n - (1.f - in) * 1.6f;
        float r = g.r * lerp(0.15f, 1.f, in);
        t.pos = {c_.x + sinf(a) * r, c_.y - cosf(a) * r * kTilt};
        float depth = 0.5f - 0.5f * cosf(a), k = lerp(0.72f, 1.10f, depth) * lerp(1.f, 1.f + (cfg.lens - 1.f) * 0.5f, saturate(t.hot.x)) * lerp(0.4f, 1.f, in);
        t.size = icon_ * k * 0.92f;
        t.half = icon_ * 0.64f * k;
        t.z = depth * 2.f - 1.f;
        t.alpha = lerp(0.72f, 1.f, depth);
      }
  }
  float order(int i) const override { return (ringOf(i) + (float)(i - rings_[(size_t)ringOf(i)].first) / std::max(1, rings_[(size_t)ringOf(i)].n)) / std::max<size_t>(1, rings_.size()); }
  float lift() const override { return 0.6f; }
  void drawBack(Painter& p, const Backdrop*, float alpha) override {
    float o = saturate(open.x);
    auto glow = p.radial(c_, ext_.x * 0.9f, ext_.x * 0.9f * kTilt, {{0, st.accent.withA(0.16f * alpha)}, {0.5f, st.accent2.withA(0.05f * alpha)}, {1, st.accent2.withA(0)}});
    p.dc->FillEllipse(D2D1::Ellipse(c_.p(), ext_.x * 0.9f, ext_.x * 0.9f * kTilt), glow.Get());
    int hr = hot_ >= 0 ? ringOf(hot_) : -1;
    for (size_t k = 0; k < rings_.size(); k++) {
      float r = rings_[k].r * o;
      Color c = (int)k == hr ? st.accent.withA(0.55f * alpha) : st.border.withA(0.24f * alpha);
      p.dc->DrawEllipse(D2D1::Ellipse(c_.p(), r, r * kTilt), p.solid(c), ((int)k == hr ? 1.8f : 1.1f) * s_);
    }
  }
  void drawItems(Painter& p, const Backdrop* bd, const std::vector<int>& ord, float alpha) override {
    bool sun = false;
    std::vector<int> one(1);
    for (int i : ord) {
      const It& t = its_[(size_t)i];
      if (!sun && t.z + std::max(0.f, t.hot.x) * lift() > 0.f) {
        drawSun(p, bd, alpha);
        sun = true;
      }
      one[0] = i;
      FreeLayout::drawItems(p, bd, one, alpha);
    }
    if (!sun) drawSun(p, bd, alpha);
  }
  void drawSun(Painter& p, const Backdrop* bd, float alpha) const {
    float R = sun_ * lerp(0.3f, 1.f, clampf(open.x, 0.f, 1.1f)), beat = cfg.reduceMotion ? 0.f : 0.5f + 0.5f * sinf(time * 1.7f);
    float H = R * (2.0f + 0.10f * beat);
    auto corona = p.radial(c_, H, H, {{0, st.accent.withA(0.55f * alpha)}, {0.48f, st.accent.withA(0.32f * alpha)}, {0.7f, st.accent2.withA(0.10f * alpha)}, {1, st.accent2.withA(0)}});
    p.dc->FillEllipse(D2D1::Ellipse(c_.p(), H, H), corona.Get());
    auto g = circleGeo(c_, R);
    fillPanel(p, g.Get(), bd, alpha, 0.35f);
    auto body = p.radial({c_.x - R * 0.2f, c_.y - R * 0.3f}, R * 1.4f, R * 1.4f, {{0, mix(st.accent, Color(1, 1, 1), 0.35f).withA(0.50f * alpha)}, {0.6f, st.accent.withA(0.28f * alpha)}, {1, st.accent2.withA(0.34f * alpha)}});
    p.fill(g.Get(), body.Get());
    p.stroke(g.Get(), mix(st.accent, Color(1, 1, 1), 0.4f).withA(0.8f * alpha), 1.4f * s_);
    SYSTEMTIME lt;
    GetLocalTime(&lt);
    wchar_t tm[32] = {};
    GetTimeFormatEx(LOCALE_NAME_USER_DEFAULT, TIME_NOSECONDS, &lt, nullptr, tm, 32);
    if (cfg.hub == HubShow::Profile) wcsncpy(tm, model.profileName.substr(0, 14).c_str(), 31);
    if (cfg.hub != HubShow::Empty) {
      TextStyle ts = label(21.f * s_, 600);
      float w = gfx().measure(tm, ts).x;
      if (w > R * 1.7f) ts.size *= R * 1.7f / w;
      p.textHalo(tm, ts, RectF(c_.x - R, c_.y - R, c_.x + R, c_.y + R), st.text.withA(alpha), Color(0, 0, 0, st.text.luma() > 0.5f ? 0.55f * alpha : 0.f), 5.f * s_);
    }
  }
  V2 tagDir(int i) const override { return its_[(size_t)i].pos.y > c_.y ? V2{0, 1} : V2{0, -1}; }
};

// ---------------------------------------------------------------- honeycomb with a lens that follows the pointer
class CombLayout final : public FreeLayout {
  std::vector<V2> base_;
  float sp_ = 80;
  Spring fx_, fy_;

  void arrange() override {
    hexPlates_ = true;
    int n = count();
    sp_ = icon_ * 1.60f * cfg.spread;
    base_.clear();
    // rings of a hexagonal grid, from the middle outward, starting at the top
    for (int ring = 0; (int)base_.size() < n; ring++) {
      if (!ring) {
        base_.push_back({0, 0});
        continue;
      }
      for (int side = 0; side < 6; side++) {
        V2 a = polar({0, 0}, side * kTau / 6.f - kTau / 12.f, sp_ * ring), b = polar({0, 0}, (side + 1) * kTau / 6.f - kTau / 12.f, sp_ * ring);
        for (int k = 0; k < ring && (int)base_.size() < n; k++) base_.push_back(lerp(a, b, (float)k / ring));
      }
    }
    // an unfinished outer ring would hang to one side: centre what is there
    V2 lo, hi;
    for (auto& q : base_) {
      lo = {std::min(lo.x, q.x), std::min(lo.y, q.y)};
      hi = {std::max(hi.x, q.x), std::max(hi.y, q.y)};
    }
    V2 mid = (lo + hi) * 0.5f;
    for (auto& q : base_) q = q - mid;
    ext_ = {(hi.x - lo.x) * 0.5f + icon_ * 1.1f, (hi.y - lo.y) * 0.5f + icon_ * 1.1f};
  }
  bool animate(float dt) override {
    V2 want = keyed_ && hot_ >= 0 ? base_[(size_t)hot_] : pointerKnown ? ptr - c_ : V2{};
    if (presence_.target > 0.5f) {
      fx_.target = want.x;
      fy_.target = want.y;
    }
    fx_.step(dt, 7.f * motion(), 1.f);
    fy_.step(dt, 7.f * motion(), 1.f);
    if (keyed_ && hot_ >= 0) presence_.target = 1;
    return !fx_.settled(0.05f) || !fy_.settled(0.05f);
  }
  void place() override {
    V2 f{fx_.x, fy_.x};
    float pr = saturate(presence_.x), m = cfg.lens - 1.f;
    for (int i = 0; i < count(); i++) {
      It& t = its_[(size_t)i];
      V2 q = base_[(size_t)i], d = q - f;
      float r = d.len() / sp_, g = expf(-r * r / 2.6f) * pr;
      q = f + d * (1.f + m * 0.55f * expf(-r * r / 5.5f) * pr);
      float in = clampf(t.in.x, 0.f, 1.2f);
      q = q * lerp(0.35f, 1.f, in);
      float away = saturate(base_[(size_t)i].len() / std::max(1.f, ext_.x * 1.6f));
      float k = lerp(1.f, 0.84f, away) * (1.f + m * 0.72f * g) * lerp(0.3f, 1.f, in);
      t.pos = c_ + q;
      t.size = icon_ * k;
      t.half = icon_ * 0.70f * k;
      t.z = g;
      t.alpha = 1;
    }
  }
  float order(int i) const override { return saturate(base_[(size_t)i].len() / std::max(1.f, std::max(ext_.x, ext_.y))); }
  void focusOn(int i) override {
    presence_.target = 1;
    setHot(i);
  }
};

// ---------------------------------------------------------------- carousel: a ring that turns in depth
class CarouselLayout final : public FreeLayout {
  Spring f_;
  float rx_ = 400, ry_ = 70, step_ = 0.4f;
  int vis_ = 8;

  void arrange() override {
    int n = std::max(1, count());
    step_ = kTau / std::max(9, std::min(n, 17));
    rx_ = icon_ * clampf(n * 0.66f, 4.2f, 7.4f) * cfg.spread;
    ry_ = icon_ * 1.35f;
    ext_ = {rx_ + icon_ * 1.1f, ry_ + icon_ * 2.1f};
  }
  float rel(int i) const {  // how many places from the front, the short way round when the ring is full
    float d = i - f_.x;
    int n = count();
    if (n >= 9) {
      d = fmodf(d, (float)n);
      if (d > n * 0.5f) d -= n;
      if (d < -n * 0.5f) d += n;
    }
    return d;
  }
  void place() override {
    for (int i = 0; i < count(); i++) {
      It& t = its_[(size_t)i];
      float in = clampf(t.in.x, 0.f, 1.2f), d = rel(i), a = d * step_;
      float lim = kPi * 0.94f;
      float depth = 0.5f + 0.5f * cosf(clampf(a, -kPi, kPi));
      t.pos = {c_.x + sinf(clampf(a, -kPi, kPi)) * rx_ * lerp(0.2f, 1.f, in), c_.y + ry_ * (depth * 2.f - 1.f) * 0.85f - (1.f - in) * 40.f * s_};
      float near_ = expf(-d * d * 1.2f);
      float k = lerp(0.50f, 1.18f, depth) * (1.f + (cfg.lens - 1.f) * 1.0f * near_) * lerp(1.f, 1.08f, saturate(t.hot.x)) * lerp(0.4f, 1.f, in);
      t.size = icon_ * k;
      t.half = icon_ * 0.70f * k;
      t.z = depth;
      t.alpha = fabsf(a) > lim ? saturate(1.f - (fabsf(a) - lim) * 6.f) : lerp(0.55f, 1.f, depth);
      t.there = t.alpha > 0.2f;
    }
  }
  bool animate(float dt) override {
    int n = count();
    bool busy = false;
    if (n && pointerKnown && !keyed_ && !closing && presence_.target > 0.5f && !(fly_.item >= 0 && fly_.open.target > 0.5f)) {
      // Resting near either end turns the ring.
      float x = (ptr.x - c_.x) / std::max(1.f, rx_), over = fabsf(x) - 0.72f;
      if (over > 0) {
        f_.target += (x > 0 ? 1.f : -1.f) * std::min(1.f, over * 2.6f) * 5.f * dt;
        busy = true;
      }
    } else if (!cfg.reduceMotion && cfg.drift > 0.01f && n && presence_.target < 0.5f && hot_ < 0 && !closing) {
      f_.target += cfg.drift * 0.5f * dt;
      busy = true;
    }
    if (n && n < 9) f_.target = clampf(f_.target, 0.f, (float)(n - 1));
    f_.step(dt, 3.4f * motion(), 0.9f);
    if (!f_.settled(0.004f)) {
      busy = true;
      repick();
    }
    return busy;
  }
  void turnTo(int i) {
    float d = rel(i) + (f_.x - f_.target);
    int n = count();
    if (n >= 9) {
      if (d > n * 0.5f) d -= n;
      if (d < -n * 0.5f) d += n;
      f_.target += d;
    } else {
      f_.target = (float)i;
    }
  }
  void focusOn(int i) override {
    turnTo(i);
    setHot(i);
  }
  void key(NavKey k) override {
    int n = count();
    if (!n) return;
    keyed_ = true;
    if (kidKey(k)) return;
    if (k == NavKey::Up) { if (hot_ >= 0) openKids(); return; }
    if (k == NavKey::Down) return;
    if (hot_ < 0) { focusOn(front()); return; }
    int d = k == NavKey::Right || k == NavKey::Next ? 1 : -1;
    int to = n >= 9 ? (hot_ + d + n) % n : clampi(hot_ + d, 0, n - 1);
    focusOn(to);
  }
  int front() const {
    int n = count(), i = (int)lroundf(f_.target);
    return n ? ((i % n) + n) % n : 0;
  }
  bool smoothWheel() const override { return true; }
  bool wheel(float notches) override {
    if (count() < 2) return false;
    f_.target -= notches;
    keyed_ = false;
    return true;
  }
  float order(int i) const override { return std::min(1.f, fabsf(rel(i)) / 6.f); }
  void drawBack(Painter& p, const Backdrop*, float alpha) override {
    // the floor it stands on
    float y = c_.y + ry_ + icon_ * 0.55f, w = rx_ * 1.12f, h = icon_ * 1.15f;
    auto fl = p.radial({c_.x, y}, w, h, {{0, st.accent.withA(0.20f * alpha)}, {0.55f, st.base.withA(0.34f * alpha)}, {1, st.base.withA(0)}});
    p.dc->FillEllipse(D2D1::Ellipse(D2D1::Point2F(c_.x, y - icon_ * 0.35f), w, h), fl.Get());
    p.dc->DrawEllipse(D2D1::Ellipse(D2D1::Point2F(c_.x, c_.y + icon_ * 0.62f), rx_ * saturate(open.x), ry_ * 0.85f * saturate(open.x)), p.solid(st.border.withA(0.16f * alpha)), 1.2f * s_);
  }
  void drawItem(Painter& p, const Backdrop* bd, int i, float a) override {
    It& t = its_[(size_t)i];
    if (t.z > 0.35f) {  // a faint reflection
      D2D1_MATRIX_3X2_F base;
      p.dc->GetTransform(&base);
      float fy = t.pos.y + t.half * 1.06f;
      p.dc->SetTransform(D2D1::Matrix3x2F(1, 0, 0, -0.55f, 0, fy * 1.55f) * *D2D1::Matrix3x2F::ReinterpretBaseType(&base));
      drawIcon(p, model.items[(size_t)i], t.pos, t.size, a * 0.13f * smooth01((t.z - 0.35f) / 0.5f), 0.f);
      p.dc->SetTransform(base);
    }
    FreeLayout::drawItem(p, bd, i, a);
  }
  V2 tagDir(int) const override { return {0, -1}; }
  V2 flyDir(int) const override { return {0, -1}; }
  int first() const override { return front(); }
  V2 home() const override { return {c_.x, c_.y + ry_ * 0.6f}; }
  float lift() const override { return 0.12f; }
  float dotY() const override { return std::min(env.work.b - 14.f * s_, c_.y + ext_.y + 20.f * s_); }
};

// ---------------------------------------------------------------- globe: everything on a ball that rolls
class GlobeLayout final : public FreeLayout {
  std::vector<std::pair<float, float>> at_;  // longitude, latitude
  Spring yaw_, pitch_;
  float R_ = 200;

  void arrange() override {
    int n = std::max(1, count());
    R_ = std::max(icon_ * 2.1f, icon_ * 0.74f * sqrtf((float)n) * cfg.spread + icon_ * 0.35f);
    at_.clear();
    for (int i = 0; i < n; i++) {
      float y = n == 1 ? 0.f : 1.f - 2.f * (i + 0.5f) / n;
      at_.push_back({i * 2.39996323f, asinf(clampf(y, -1, 1))});
    }
    ext_ = {R_ + icon_ * 0.85f, R_ + icon_ * 0.85f};
  }
  void turned(int i, float yaw, float pitch, float& x, float& y, float& z) const {
    float lon = at_[(size_t)i].first + yaw, lat = at_[(size_t)i].second;
    float px = cosf(lat) * sinf(lon), py = sinf(lat), pz = cosf(lat) * cosf(lon);
    float c = cosf(pitch), s = sinf(pitch);
    x = px;
    y = py * c - pz * s;
    z = py * s + pz * c;
  }
  void place() override {
    for (int i = 0; i < count(); i++) {
      It& t = its_[(size_t)i];
      float x, y, z, in = clampf(t.in.x, 0.f, 1.2f);
      turned(i, yaw_.x - (1.f - saturate(open.x)) * 1.2f, pitch_.x, x, y, z);
      float depth = 0.5f + 0.5f * z, persp = lerp(0.80f, 1.10f, depth);
      t.pos = {c_.x + x * R_ * persp * lerp(0.2f, 1.f, in), c_.y - y * R_ * persp * lerp(0.2f, 1.f, in)};
      float k = lerp(0.42f, 1.04f, smooth01(depth)) * lerp(1.f, 1.f + (cfg.lens - 1.f) * 0.55f, saturate(t.hot.x)) * lerp(0.4f, 1.f, in);
      t.size = icon_ * k * 0.94f;
      t.half = icon_ * 0.66f * k;
      t.z = z;
      t.alpha = lerp(0.14f, 1.f, smooth01((depth - 0.12f) / 0.6f));
      t.there = z > -0.12f;
    }
  }
  bool animate(float dt) override {
    bool busy = false;
    if (!closing && pointerKnown && !keyed_ && presence_.target > 0.5f && !(fly_.item >= 0 && fly_.open.target > 0.5f)) {
      // Toward the rim the ball rolls that way and brings the far side round.
      V2 d = (ptr - c_) * (1.f / std::max(1.f, R_));
      float r = d.len(), over = r - 0.62f;
      if (over > 0 && r < 1.6f) {
        float v = std::min(1.f, over * 1.9f) * 2.1f * dt / r;
        yaw_.target -= d.x * v;
        pitch_.target = clampf(pitch_.target + d.y * v, -1.25f, 1.25f);
        busy = true;
      }
    } else if (!cfg.reduceMotion && cfg.drift > 0.01f && !closing && hot_ < 0 && presence_.target < 0.5f) {
      yaw_.target += cfg.drift * 0.35f * dt;
      busy = true;
    }
    yaw_.step(dt, 3.f * motion(), 0.95f);
    pitch_.step(dt, 3.f * motion(), 0.95f);
    if (!yaw_.settled(0.002f) || !pitch_.settled(0.002f)) {
      busy = true;
      repick();
    }
    return busy;
  }
  void focusOn(int i) override {
    yaw_.target += wrapAngle(-at_[(size_t)i].first - yaw_.target);
    pitch_.target = clampf(at_[(size_t)i].second, -1.25f, 1.25f);
    setHot(i);
  }
  bool smoothWheel() const override { return true; }
  bool wheel(float notches) override {
    if (count() < 2) return false;
    yaw_.target += notches * 0.55f;
    keyed_ = false;
    return true;
  }
  int first() const override {
    int best = 0;
    for (int i = 1; i < count(); i++)
      if (its_[(size_t)i].z > its_[(size_t)best].z) best = i;
    return best;
  }
  bool inside(V2 p) const override { return (p - c_).len() < R_ * 1.5f; }
  void drawBack(Painter& p, const Backdrop* bd, float alpha) override {
    float R = R_ * 0.93f * lerp(0.4f, 1.f, clampf(open.x, 0.f, 1.05f));
    auto g = circleGeo(c_, R);
    if (st.shape != SlotShape::None) {
      if (st.shadow > 0.01f) {
        auto sh = p.radial({c_.x, c_.y + 10.f * s_}, R * 1.25f, R * 1.25f, {{0, Color(0, 0, 0, 0.5f * st.shadow * alpha)}, {0.75f, Color(0, 0, 0, 0.4f * st.shadow * alpha)}, {1, Color(0, 0, 0, 0)}});
        p.dc->FillEllipse(D2D1::Ellipse(D2D1::Point2F(c_.x, c_.y + 10.f * s_), R * 1.25f, R * 1.25f), sh.Get());
      }
      fillPanel(p, g.Get(), bd, alpha * 0.9f, -0.10f);
    }
    auto body = p.radial({c_.x - R * 0.35f, c_.y - R * 0.45f}, R * 1.5f, R * 1.5f, {{0, st.accent.withA(0.20f * alpha)}, {0.5f, st.accent2.withA(0.07f * alpha)}, {1, Color(0, 0, 0, 0.25f * alpha)}});
    p.fill(g.Get(), body.Get());
    p.circleStroke(c_, R, st.border.withA(0.28f * alpha), 1.2f * s_);
    // meridians and parallels
    Color line = st.border.withA(0.11f * alpha);
    for (int m = 0; m < 6; m++) {
      std::vector<V2> pts;
      for (int k = 0; k <= 48; k++) {
        float lon = m * kPi / 6.f + yaw_.x, lat = -kPi * 0.5f + k * kPi / 24.f;
        float px = cosf(lat) * sinf(lon), py = sinf(lat), pz = cosf(lat) * cosf(lon), cp = cosf(pitch_.x), sp = sinf(pitch_.x);
        pts.push_back({c_.x + px * R, c_.y - (py * cp - pz * sp) * R});
      }
      auto q = polyGeo(pts, false, false);
      p.stroke(q.Get(), line, 1.f * s_);
    }
    for (int m = -2; m <= 2; m++) {
      float lat = m * kPi / 6.f, ry = R * cosf(lat) * fabsf(sinf(pitch_.x));
      p.dc->DrawEllipse(D2D1::Ellipse(D2D1::Point2F(c_.x, c_.y - sinf(lat) * cosf(pitch_.x) * R), R * cosf(lat), std::max(0.5f, ry)), p.solid(line), 1.f * s_);
    }
  }
  float lift() const override { return 3.f; }
};

// ---------------------------------------------------------------- a hand of cards
class CardsLayout final : public FreeLayout {
  Spring f_, spread_;
  float cw_ = 96, ch_ = 136, R_ = 900, gap_ = 0.07f;

  void arrange() override {
    int n = std::max(1, count());
    cw_ = icon_ * 1.85f;
    ch_ = icon_ * 2.65f;
    R_ = icon_ * 15.f;
    float span = std::min(1.05f, 0.105f * (n - 1) * cfg.spread);
    gap_ = n > 1 ? span / (n - 1) : 0.f;
    float w = R_ * sinf(std::min(span, 1.05f) * 0.5f) + cw_ * 0.9f;
    ext_ = {w, ch_ * 0.5f + R_ * (1.f - cosf(std::min(span, 1.05f) * 0.5f)) * 0.5f + icon_ * 0.9f};
  }
  void settle() override {
    FreeLayout::settle();
    if (!env.anchorIsMouse && !env.preview) c_.y = env.work.b - ext_.y - 24.f * s_;  // held from below
  }
  V2 foot() const { return {c_.x, c_.y - ext_.y + icon_ * 1.15f + ch_ * 0.5f + R_}; }
  void place() override {
    int n = count();
    V2 o = foot();
    for (int i = 0; i < n; i++) {
      It& t = its_[(size_t)i];
      float in = clampf(t.in.x, 0.f, 1.2f), mid = (n - 1) * 0.5f;
      float a = (i - mid) * gap_;
      // Cards beside the focused one make room.
      float need = std::max(0.f, cw_ * 0.80f - gap_ * R_) / R_;
      float d = i - f_.x;
      a += saturate(spread_.x) * need * (d > 0 ? 1.f : -1.f) * smooth01(fabsf(d)) * expf(-std::max(0.f, fabsf(d) - 1.f) * 0.45f);
      a = lerp(-0.9f, a, in);
      float h = saturate(t.hot.x), k = lerp(1.f, 1.f + (cfg.lens - 1.f) * 0.36f, h);
      float r = R_ + h * icon_ * 0.62f;
      V2 q = polar(o, a, r);
      q.y += (1.f - in) * ch_ * 1.1f;
      t.pos = q;
      t.turn = lerp(a * 180.f / kPi, 0.f, h * 0.65f);
      t.size = icon_ * k;
      t.half = cw_ * 0.5f * k;
      t.z = i * 0.01f;
      t.alpha = 1;
    }
  }
  bool animate(float dt) override {
    if (hot_ >= 0) f_.target = (float)hot_;
    spread_.target = hot_ >= 0 && !closing ? 1.f : 0.f;
    f_.step(dt, 6.f * motion(), 0.9f);
    spread_.step(dt, 5.f * motion(), 0.9f);
    return !f_.settled() || !spread_.settled();
  }
  int hitAt(V2 p) const override {
    // The card under the pointer, topmost first; below the fan the angle decides.
    V2 o = foot(), d = p - o;
    float r = d.len(), a = angleOf(d);
    if (r < R_ - ch_ * 0.95f || r > R_ + ch_ * 0.5f + icon_ * 1.1f || !count()) return -1;
    int best = -1;
    float bd = 1e9f;
    for (int i = 0; i < count(); i++) {
      V2 q = its_[(size_t)i].pos - o;
      float off = fabsf(angleOf(q) - a);
      // the visible part of an overlapped card is its left side
      if (off < bd) {
        bd = off;
        best = i;
      }
    }
    return bd * R_ < cw_ * 0.62f ? best : -1;
  }
  void key(NavKey k) override {
    int n = count();
    if (!n) return;
    keyed_ = true;
    if (kidKey(k)) return;
    if (k == NavKey::Up) { if (hot_ >= 0) openKids(); return; }
    if (k == NavKey::Down) return;
    if (hot_ < 0) { focusOn(n / 2); return; }
    focusOn(clampi(hot_ + (k == NavKey::Right || k == NavKey::Next ? 1 : -1), 0, n - 1));
  }
  bool ownTag() const override { return false; }
  V2 flyDir(int) const override { return {0, -1}; }
  float order(int i) const override { return (float)i / std::max(1, count() - 1); }
  V2 margins() const override { return {60.f * s_, 190.f * s_}; }
  V2 home() const override { return {c_.x, c_.y}; }
  float lift() const override { return 0.f; }  // the fan keeps its order; the focused card is drawn last below
  float dotY() const override { return c_.y - ext_.y - 8.f * s_; }
  void drawItems(Painter& p, const Backdrop* bd, const std::vector<int>& ord, float alpha) override {
    std::vector<int> o2 = ord;
    std::stable_sort(o2.begin(), o2.end(), [&](int a, int b) { return (its_[(size_t)a].hot.x > 0.35f) < (its_[(size_t)b].hot.x > 0.35f); });
    FreeLayout::drawItems(p, bd, o2, alpha);
  }
  void drawItem(Painter& p, const Backdrop* bd, int i, float a) override {
    It& t = its_[(size_t)i];
    const SceneItem& it = model.items[(size_t)i];
    float k = t.half / (cw_ * 0.5f), w = cw_ * k, h = ch_ * k, hv = saturate(t.hot.x);
    D2D1_MATRIX_3X2_F base;
    p.dc->GetTransform(&base);
    p.dc->SetTransform(D2D1::Matrix3x2F::Rotation(t.turn, t.pos.p()) * *D2D1::Matrix3x2F::ReinterpretBaseType(&base));
    RectF r = RectF::xywh(t.pos.x - w * 0.5f, t.pos.y - h * 0.5f, w, h);
    bool skinned = view && skin->tile.on;
    if (skinned || (view && skin->panel.on)) {
      view->panel(p, skinned ? skin->tile : skin->panel, r, s_, a, bd, &it);
    } else {
      float corner = std::max(8.f, st.corner) * s_;
      Geo g = st.shape == SlotShape::Blade ? cutRectGeo(r, 12.f * s_) : rrectGeo(r, corner);
      auto sh = p.linear({r.l - 10 * s_, 0}, {r.l + 4 * s_, 0}, {{0, Color(0, 0, 0, 0)}, {1, Color(0, 0, 0, 0.35f * a)}});
      p.rrect(RectF(r.l - 10 * s_, r.t + corner, r.l + 4 * s_, r.b - corner), 0, sh.Get());
      fillPanel(p, g.Get(), nullptr, a, 0.40f);
      auto tint = p.linear({r.l, r.t}, {r.l, r.b}, {{0, mix(st.accent, st.accent2, (float)i / std::max(1, count())).withA(lerp(0.16f, 0.42f, hv) * a)}, {0.65f, st.accent.withA(0.04f * a)}, {1, Color(0, 0, 0, 0.16f * a)}});
      p.fill(g.Get(), tint.Get());
      if (hv > 0.02f && st.glow > 0.02f) p.glow(g.Get(), st.accent.withA(0.6f * st.glow * hv * a), 9.f * s_, 2.f * s_);
      p.stroke(g.Get(), mix(st.border.withA(std::max(0.22f, st.borderOpacity)), st.accent, hv).alpha(a), std::max(1.f, st.borderWidth) * s_);
    }
    V2 c{t.pos.x, t.pos.y - h * 0.10f};
    Entry e;
    e.index = i;
    e.count = count();
    e.hot = t.hot.x;
    e.alpha = a;
    e.marks = false;
    if (view && skin->hasSlot) drawEntry(p, bd, it, c, t.size * 0.66f, t.size, e);
    else drawIcon(p, it, c, t.size * lerp(1.f, st.iconZoom, hv * 0.6f), a, hv);
    Color tc = view && skin->tile.on && skin->tile.hasText ? view->color(skin->tile.text) : view && skin->panel.on && skin->panel.hasText ? view->color(skin->panel.text) : st.text;
    TextStyle ts = label(11.5f * s_ * k, 600);
    ts.wrap = true;
    p.text(it.label, ts, RectF(r.l + 6 * s_, r.b - h * 0.27f, r.r - 6 * s_, r.b - 5 * s_), tc.withA(0.95f * a));
    if (cfg.showRunning && it.windows > 0) {
      int dots = std::min(3, it.windows);
      for (int j = 0; j < dots; j++) p.circle({t.pos.x + (j - (dots - 1) * 0.5f) * 8.f * s_, r.t + 10.f * s_}, (it.active ? 3.f : 2.2f) * s_, (it.active ? st.accent : tc.withA(0.7f)).alpha(a));
    }
    if (cfg.showNumbers && i < 9) p.text(std::to_wstring(i + 1), label(11.f * s_, 600), RectF::xywh(r.l + 6 * s_, r.t + 4 * s_, 18 * s_, 16 * s_), tc.withA(0.6f * a));
    if (it.isGroup()) {
      V2 q{r.r - 14 * s_, r.t + 13 * s_};
      p.line({q.x - 4 * s_, q.y + 2 * s_}, {q.x, q.y - 2.5f * s_}, tc.withA(0.7f * a), 1.6f * s_);
      p.line({q.x + 4 * s_, q.y + 2 * s_}, {q.x, q.y - 2.5f * s_}, tc.withA(0.7f * a), 1.6f * s_);
    }
    p.dc->SetTransform(base);
  }
};

// ---------------------------------------------------------------- a quarter wheel in a corner of the screen
class CornerLayout final : public FreeLayout {
  struct Ring {
    float r = 0;
    int first = 0, n = 0;
  };
  std::vector<Ring> rings_;
  float R_ = 300, band_ = 80;
  V2 o_;
  int at_ = 0;  // 0 bottom left, 1 bottom right, 2 top left, 3 top right
  float a0() const { return at_ == 0 ? 0.f : at_ == 1 ? -kPi * 0.5f : at_ == 2 ? kPi * 0.5f : kPi; }

  void arrange() override {
    at_ = cfg.cornerAt;
    if (env.anchorIsMouse) at_ = (env.anchor.y < env.vh * 0.5f ? 2 : 0) + (env.anchor.x > env.vw * 0.5f ? 1 : 0);
    rings_.clear();
    int n = count(), done = 0;
    band_ = icon_ * 1.56f;
    float r = icon_ * 2.35f * cfg.spread;
    while (done < n) {
      Ring g;
      g.r = r;
      int cap = std::max(2, (int)((kPi * 0.5f * r - icon_ * 0.35f) / (icon_ * 1.42f * cfg.spread)));
      g.first = done;
      g.n = std::min(cap, n - done);
      done += g.n;
      rings_.push_back(g);
      r += band_;
    }
    R_ = (rings_.empty() ? r : rings_.back().r) + band_ * 0.56f;
    ext_ = {R_ * 0.5f, R_ * 0.5f};
  }
  void settle() override {
    o_ = {at_ % 2 ? env.work.r : env.work.l, at_ >= 2 ? env.work.t : env.work.b};
    if (env.preview) o_ = {at_ % 2 ? env.vw : 0.f, at_ >= 2 ? 0.f : env.vh};
    c_ = {o_.x + (at_ % 2 ? -1.f : 1.f) * R_ * 0.5f, o_.y + (at_ >= 2 ? 1.f : -1.f) * R_ * 0.5f};
  }
  void place() override {
    for (auto& g : rings_)
      for (int j = 0; j < g.n; j++) {
        It& t = its_[(size_t)(g.first + j)];
        float in = clampf(t.in.x, 0.f, 1.2f);
        float pad = icon_ * 0.80f / g.r, span = kPi * 0.5f - pad * 2;
        float u = g.n > 1 ? (float)j / (g.n - 1) : 0.5f;
        // read like text: from the upper end of the arc for the left corners
        float a = a0() + pad + span * (at_ == 0 || at_ == 3 ? u : 1.f - u);
        a += (at_ == 0 || at_ == 3 ? -1.f : 1.f) * (1.f - in) * 0.8f;
        float k = lerp(1.f, 1.f + (cfg.lens - 1.f) * 0.5f, saturate(t.hot.x)) * lerp(0.4f, 1.f, in);
        t.pos = polar(o_, a, g.r * lerp(0.55f, 1.f, in) + saturate(t.hot.x) * 8.f * s_);
        t.size = icon_ * k;
        t.half = icon_ * 0.66f * k;
        t.z = 0;
        t.alpha = 1;
      }
  }
  bool inside(V2 p) const override { return (p - o_).len() < R_ + 30.f * s_; }
  bool outside(V2 p) const override {
    if (fly_.item >= 0 && fly_.open.target > 0.5f && fly_.rect.inset(-20.f * s_).contains(p)) return false;
    return (p - o_).len() > R_ + 60.f * s_ && dotAt(p, s_) < 0;
  }
  V2 tagDir(int i) const override {
    V2 d = its_[(size_t)i].pos - o_;
    return fabsf(d.x) > fabsf(d.y) * 1.6f ? V2{0, at_ >= 2 ? 1.f : -1.f} : V2{at_ % 2 ? -1.f : 1.f, 0};
  }
  V2 flyDir(int) const override { return {at_ % 2 ? -1.f : 1.f, 0}; }
  V2 home() const override { return polar(o_, a0() + kPi * 0.25f, rings_.empty() ? R_ * 0.5f : std::max(20.f, rings_[0].r - band_ * 0.55f)); }
  V2 tiltCenter() const override { return c_; }
  RectF bounds() const override {
    float m = R_ + 340.f * s_, v = R_ + 150.f * s_;
    RectF r(o_.x - m, o_.y - v, o_.x + m, o_.y + v);
    return RectF(std::max(0.f, r.l), std::max(0.f, r.t), std::min(env.vw, r.r), std::min(env.vh, r.b));
  }
  V2 dotPos(int i) const override {
    V2 q = polar(o_, a0() + kPi * 0.25f, R_ + 40.f * s_);
    int n = dotCount();
    return {q.x + (at_ % 2 ? -(float)(n - 1 - i) : (float)i) * 19.f * s_, q.y};
  }
  float dotY() const override { return dotPos(0).y; }
  void drawBack(Painter& p, const Backdrop* bd, float alpha) override {
    if (st.shape == SlotShape::None) return;
    float R = R_ * lerp(0.55f, 1.f, clampf(open.x, 0.f, 1.08f));
    auto g = wedgeGeo(o_, 1.f, R, a0(), a0() + kPi * 0.5f, 0, 0);
    if (st.shadow > 0.01f) p.glow(g.Get(), Color(0, 0, 0, 0.5f * st.shadow * alpha), 18.f * s_, 0, true, false);
    fillPanel(p, g.Get(), bd, alpha, 0.f);
    auto sheen = p.radial(o_, R, R, {{0, Color(1, 1, 1, 0)}, {0.72f, Color(1, 1, 1, 0.01f * alpha)}, {1, Color(1, 1, 1, 0.10f * alpha)}});
    p.fill(g.Get(), sheen.Get());
    for (size_t k = 0; k + 1 < rings_.size(); k++) {
      auto arc = arcGeo(o_, rings_[k].r + band_ * 0.5f, a0(), a0() + kPi * 0.5f);
      p.stroke(arc.Get(), st.border.withA(0.14f * alpha), 1.f * s_);
    }
    auto rim = arcGeo(o_, R - 1.f * s_, a0(), a0() + kPi * 0.5f);
    p.stroke(rim.Get(), mix(st.border, st.accent, 0.35f).withA(0.55f * alpha), std::max(1.2f, st.borderWidth) * s_);
    if (hot_ >= 0) {
      V2 d = its_[(size_t)hot_].pos - o_;
      float a = angleOf(d), q = saturate(its_[(size_t)hot_].hot.x);
      auto lit = arcGeo(o_, R + 4.f * s_, std::max(a - 0.12f, a0()), std::min(a + 0.12f, a0() + kPi * 0.5f));
      p.stroke(lit.Get(), st.accent.withA(0.9f * q * alpha), 3.f * s_, true);
    }
    SYSTEMTIME lt;
    GetLocalTime(&lt);
    wchar_t tm[32] = {};
    GetTimeFormatEx(LOCALE_NAME_USER_DEFAULT, TIME_NOSECONDS, &lt, nullptr, tm, 32);
    if (cfg.hub == HubShow::Clock && !rings_.empty()) {
      V2 q = polar(o_, a0() + kPi * 0.25f, (rings_[0].r - band_ * 0.5f) * 0.56f);
      TextStyle ts = label(20.f * s_, 600);
      p.text(tm, ts, RectF::xywh(q.x - 60.f * s_, q.y - 16.f * s_, 120.f * s_, 32.f * s_), st.text.withA(0.9f * alpha));
    }
  }
  void drawItem(Painter& p, const Backdrop* bd, int i, float a) override {
    plates_ = false;  // they share one panel
    FreeLayout::drawItem(p, bd, i, a);
    plates_ = true;
  }
};

// ---------------------------------------------------------------- galaxy: a sunflower spiral, the first pins in its core
class GalaxyLayout final : public FreeLayout {
  float phase_ = 0, unit_ = 60;
  Spring stop_;
  struct Dust {
    float a, r, s, q;
  };
  std::vector<Dust> dust_;

  void arrange() override {
    int n = std::max(1, count());
    unit_ = icon_ * 1.06f * cfg.spread;
    float R = radius(n - 1) + icon_ * 0.9f;
    ext_ = {R, R};
    dust_.clear();
    uint32_t h = 12345;
    auto r01 = [&] {
      h = h * 1664525u + 1013904223u;
      return (h >> 8 & 0xFFFF) / 65536.f;
    };
    for (int i = 0; i < 150; i++) {
      float t = r01(), arm = (float)(i % 3) * kTau / 3.f;
      dust_.push_back({arm + t * 4.6f + (r01() - 0.5f) * 0.7f, lerp(0.12f, 1.12f, t) + (r01() - 0.5f) * 0.10f, 0.6f + r01() * 1.6f, r01()});
    }
  }
  float radius(int i) const { return unit_ * 0.92f * sqrtf(i + 0.55f) - unit_ * 0.40f * (i == 0 ? 1.f : 0.f); }
  bool animate(float dt) override {
    stop_.target = hot_ >= 0 ? 1.f : presence_.target > 0.5f && pointerKnown && (ptr - c_).len() > icon_ ? 0.8f : 0.f;
    stop_.step(dt, 3.f, 1.f);
    if (cfg.reduceMotion || cfg.drift < 0.01f) return !stop_.settled();
    phase_ += 0.16f * cfg.drift * dt * (1.f - saturate(stop_.x));
    repick();
    return true;
  }
  void place() override {
    for (int i = 0; i < count(); i++) {
      It& t = its_[(size_t)i];
      float in = clampf(t.in.x, 0.f, 1.15f);
      float a = i * 2.39996323f + phase_ - (1.f - in) * 2.4f, r = radius(i) * lerp(0.1f, 1.f, in);
      float away = saturate(radius(i) / std::max(1.f, ext_.x));
      float k = lerp(1.08f, 0.82f, away) * lerp(1.f, 1.f + (cfg.lens - 1.f) * 0.62f, saturate(t.hot.x)) * lerp(0.2f, 1.f, in);
      t.pos = polar(c_, a, r);
      t.size = icon_ * k * 0.94f;
      t.half = icon_ * 0.64f * k;
      t.z = -away;
      t.alpha = 1;
    }
  }
  float order(int i) const override { return sqrtf((float)i / std::max(1, count())); }
  float introSpread() const override { return 0.30f; }
  bool inside(V2 p) const override { return (p - c_).len() < ext_.x * 1.1f; }
  void drawBack(Painter& p, const Backdrop*, float alpha) override {
    float R = ext_.x * 1.12f * saturate(open.x);
    auto core = p.radial(c_, R, R, {{0, st.base.withA(std::min(1.f, st.opacity * 0.9f + 0.1f) * 0.75f * alpha)}, {0.55f, st.base.withA(st.opacity * 0.45f * alpha)}, {1, st.base.withA(0)}});
    if (st.shape != SlotShape::None) p.dc->FillEllipse(D2D1::Ellipse(c_.p(), R, R), core.Get());
    auto glow = p.radial(c_, R * 0.7f, R * 0.7f, {{0, st.accent.withA(0.28f * alpha)}, {0.45f, st.accent2.withA(0.09f * alpha)}, {1, st.accent2.withA(0)}});
    p.dc->FillEllipse(D2D1::Ellipse(c_.p(), R * 0.7f, R * 0.7f), glow.Get());
    for (auto& d : dust_) {
      float a = d.a + phase_ * 0.8f - (1.f - saturate(open.x)) * 1.5f;
      float tw = cfg.reduceMotion ? 0.7f : 0.55f + 0.45f * sinf(time * 1.8f + d.q * 40.f);
      p.circle(polar(c_, a, d.r * ext_.x), d.s * s_, mix(st.accent, st.accent2, d.q).withA(0.5f * tw * alpha));
    }
  }
};

// ---------------------------------------------------------------- board: a tidy grid with names
class BoardLayout final : public FreeLayout {
  int cols_ = 5, rows_ = 3, page_ = 0, pages_ = 1;
  float cw_ = 100, ch_ = 100, head_ = 44;
  Spring slide_;
  RectF panel_;

  void arrange() override {
    int n = std::max(1, count());
    cw_ = icon_ * 2.02f * cfg.spread;
    ch_ = icon_ * 1.30f + 34.f * s_ * cfg.spread;
    head_ = 46.f * s_;
    int want = cfg.columns > 0 ? cfg.columns : clampi((int)ceilf(sqrtf(n * 1.55f)), 3, 9);
    cols_ = std::max(1, std::min(want, n));
    int most = std::max(1, (int)((env.work.h() - 150.f * s_) / ch_));
    rows_ = std::min(most, (n + cols_ - 1) / cols_);
    pages_ = std::max(1, (n + cols_ * rows_ - 1) / (cols_ * rows_));
    page_ = clampi(page_, 0, pages_ - 1);
    ext_ = {cols_ * cw_ * 0.5f + 20.f * s_, rows_ * ch_ * 0.5f + head_ * 0.5f + 18.f * s_};
  }
  int per() const { return cols_ * rows_; }
  void place() override {
    panel_ = RectF(c_.x - ext_.x, c_.y - ext_.y, c_.x + ext_.x, c_.y + ext_.y);
    for (int i = 0; i < count(); i++) {
      It& t = its_[(size_t)i];
      int pg = i / per(), k = i % per(), col = k % cols_, row = k / cols_;
      float in = clampf(t.in.x, 0.f, 1.2f), dx = (pg - page_ + slide_.x) * (ext_.x * 2.f);
      t.pos = {c_.x + (col - (cols_ - 1) * 0.5f) * cw_ + dx, panel_.t + head_ + 8.f * s_ + row * ch_ + icon_ * 0.72f + (1.f - in) * 26.f * s_};
      float z = lerp(1.f, 1.f + (cfg.lens - 1.f) * 0.34f, saturate(t.hot.x)) * lerp(0.6f, 1.f, in);
      t.size = icon_ * z;
      t.half = icon_ * 0.66f * z;
      t.alpha = 1.f - smooth01((fabsf(dx) - ext_.x * 0.25f) / (ext_.x * 0.8f));
      t.there = pg == page_;
      t.z = 0;
    }
  }
  bool animate(float dt) override {
    slide_.step(dt, 4.5f * motion(), 0.95f);
    return !slide_.settled();
  }
  void flip(int d) {
    int np = clampi(page_ + d, 0, pages_ - 1);
    if (np == page_) return;
    slide_.x += (float)(np - page_);
    slide_.target = 0;
    page_ = np;
  }
  void focusOn(int i) override {
    if (i / per() != page_) flip(i / per() - page_);
    setHot(i);
  }
  int hitAt(V2 p) const override {
    if (p.y < panel_.t + head_ || p.y > panel_.b || p.x < panel_.l || p.x > panel_.r) return -1;
    int col = (int)floorf((p.x - (c_.x - cols_ * cw_ * 0.5f)) / cw_), row = (int)floorf((p.y - panel_.t - head_) / ch_);
    if (col < 0 || col >= cols_ || row < 0 || row >= rows_) return -1;
    int i = page_ * per() + row * cols_ + col;
    return i < count() ? i : -1;
  }
  void key(NavKey k) override {
    int n = count();
    if (!n) return;
    keyed_ = true;
    if (kidKey(k)) return;
    if (hot_ < 0) { focusOn(page_ * per()); return; }
    int to = hot_;
    switch (k) {
      case NavKey::Next: to = (hot_ + 1) % n; break;
      case NavKey::Prev: to = (hot_ + n - 1) % n; break;
      case NavKey::Left: to = std::max(0, hot_ - 1); break;
      case NavKey::Right: to = std::min(n - 1, hot_ + 1); break;
      case NavKey::Up: to = hot_ - cols_ >= 0 ? hot_ - cols_ : hot_; break;
      case NavKey::Down: to = hot_ + cols_ < n ? hot_ + cols_ : (hot_ / cols_ < (n - 1) / cols_ ? n - 1 : hot_); break;
    }
    focusOn(to);
  }
  bool wheel(float notches) override {
    if (pages_ <= 1) return false;
    flip(notches > 0 ? -1 : 1);
    return true;
  }
  bool ownTag() const override { return false; }
  V2 margins() const override { return {60.f * s_, 60.f * s_}; }
  float order(int i) const override {
    int k = i % per();
    return (k % cols_ + k / cols_) / (float)std::max(1, cols_ + rows_ - 2);
  }
  float dotY() const override { return panel_.t + head_ * 0.5f; }
  V2 dotPos(int i) const override { return {panel_.r - 34.f * s_ - (dotCount() - 1 - i) * 19.f * s_, panel_.t + head_ * 0.5f + 2.f * s_}; }
  V2 flyDir(int i) const override { return its_[(size_t)i].pos.y > c_.y ? V2{0, -1} : V2{0, 1}; }
  void drawBack(Painter& p, const Backdrop* bd, float alpha) override {
    float o = lerp(0.94f, 1.f, clampf(open.x, 0.f, 1.05f));
    RectF r(c_.x - ext_.x * o, c_.y - ext_.y * o, c_.x + ext_.x * o, c_.y + ext_.y * o);
    if (view && skin->panel.on) {
      view->panel(p, skin->panel, r, s_, alpha, bd);
    } else if (st.shape != SlotShape::None) {
      Geo g = st.shape == SlotShape::Blade ? cutRectGeo(r, 18.f * s_) : rrectGeo(r, (st.corner + 8.f) * s_);
      if (st.shadow > 0.01f) p.glow(g.Get(), Color(0, 0, 0, 0.5f * st.shadow * alpha), 18.f * s_, 0, true, false);
      fillPanel(p, g.Get(), bd, alpha, 0.06f);
      auto sheen = p.linear({r.l, r.t}, {r.l, r.b}, {{0, Color(1, 1, 1, 0.08f * alpha)}, {0.35f, Color(1, 1, 1, 0.01f * alpha)}, {1, Color(1, 1, 1, 0)}});
      p.fill(g.Get(), sheen.Get());
      strokePanel(p, g.Get(), {r.l, r.t}, {r.r, r.b}, alpha);
    }
    Color tc = view && skin->panel.on && skin->panel.hasText ? view->color(skin->panel.text) : st.text;
    p.text(model.profileName, label(17.f * s_, 600, Align::Left), RectF(r.l + 24.f * s_, r.t + 4.f * s_, r.cx() + 60.f * s_, r.t + head_ + 4.f * s_), tc.withA(0.95f * alpha));
    for (int i = 0; pages_ > 1 && i < pages_ && pages_ < 20; i++)
      p.circle({c_.x + (i - (pages_ - 1) * 0.5f) * 11.f * s_, r.b - 11.f * s_}, (i == page_ ? 3.2f : 2.2f) * s_, (i == page_ ? st.accent : tc.withA(0.4f)).alpha(alpha));
  }
  void drawItem(Painter& p, const Backdrop* bd, int i, float a) override {
    It& t = its_[(size_t)i];
    if (t.hot.x > 0.01f && !(view && skin->hasSlot)) {
      float q = saturate(t.hot.x);
      RectF r = RectF::xywh(t.pos.x - cw_ * 0.46f, t.pos.y - icon_ * 0.70f, cw_ * 0.92f, ch_ - 4.f * s_);
      p.rrect(r, std::min(14.f, std::max(6.f, st.corner)) * s_, st.accent.withA(0.22f * q * a));
      p.rrectStroke(r, std::min(14.f, std::max(6.f, st.corner)) * s_, st.accent.withA(0.65f * q * a), std::max(1.f, st.borderWidth) * s_);
    }
    if (view && skin->hasSlot) {
      Entry e;
      e.index = i;
      e.count = count();
      e.hot = t.hot.x;
      e.alpha = a;
      drawEntry(p, bd, model.items[(size_t)i], t.pos, t.half, t.size, e);
    } else {
      drawIcon(p, model.items[(size_t)i], t.pos, t.size, a * lerp(0.95f, 1.f, saturate(t.hot.x)), saturate(t.hot.x));
      const SceneItem& it = model.items[(size_t)i];
      if (cfg.showRunning && it.windows > 0) {
        float y = t.pos.y + icon_ * 0.62f;
        if (it.active) p.rrect(RectF::xywh(t.pos.x - 8 * s_, y, 16 * s_, 3 * s_), 1.5f * s_, st.accent.withA(a));
        else p.rrect(RectF::xywh(t.pos.x - 3 * s_, y, 6 * s_, 3 * s_), 1.5f * s_, st.text.withA(0.7f * a));
      }
      if (cfg.showNumbers && i < 9) p.text(std::to_wstring(i + 1), label(10.5f * s_, 600), RectF::xywh(t.pos.x - cw_ * 0.44f, t.pos.y - icon_ * 0.66f, 18 * s_, 16 * s_), st.text.withA(0.55f * a));
    }
    Color tc = view && skin->panel.on && skin->panel.hasText ? view->color(skin->panel.text) : st.text;
    TextStyle ts = label(11.5f * s_, saturate(t.hot.x) > 0.5f ? 600 : 500, Align::Center, VAlign::Top);
    ts.wrap = true;
    float top = t.pos.y + icon_ * 0.74f;
    p.text(model.items[(size_t)i].label, ts, RectF(t.pos.x - cw_ * 0.46f, top, t.pos.x + cw_ * 0.46f, top + 30.f * s_), tc.withA(lerp(0.82f, 1.f, saturate(t.hot.x)) * a));
  }
};

// ---------------------------------------------------------------- drum: a list on a roller, with names
class DrumLayout final : public FreeLayout {
  Spring f_;
  float row_ = 60, R_ = 220, w_ = 360;
  static constexpr float kStep = 0.29f;

  void arrange() override {
    row_ = icon_ * 1.22f * cfg.spread;
    R_ = row_ / kStep;
    w_ = icon_ * 1.5f + 250.f * s_;
    ext_ = {w_ * 0.5f, std::min(R_ * sinf(1.18f), env.work.h() * 0.46f) + 6.f * s_};
    f_.snap(f_.x == 0 ? std::min(2.f, (count() - 1) * 0.5f) : clampf(f_.x, 0.f, (float)std::max(0, count() - 1)));
  }
  void place() override {
    for (int i = 0; i < count(); i++) {
      It& t = its_[(size_t)i];
      float in = clampf(t.in.x, 0.f, 1.2f), a = (i - f_.x) * kStep;
      float cl = clampf(a, -1.5f, 1.5f), k = cosf(cl);
      t.pos = {c_.x - ext_.x + icon_ * 0.95f + (1.f - in) * -60.f * s_ + saturate(t.hot.x) * 8.f * s_, c_.y + sinf(cl) * R_};
      t.size = icon_ * lerp(0.45f, 1.f, k) * lerp(1.f, 1.f + (cfg.lens - 1.f) * 0.25f, saturate(t.hot.x));
      t.half = t.size * 0.62f;
      t.alpha = smooth01((k - 0.20f) / 0.55f);
      t.there = k > 0.30f;
      t.z = k;
    }
  }
  bool animate(float dt) override {
    int n = count();
    bool busy = false;
    if (n && pointerKnown && !keyed_ && !closing && presence_.target > 0.5f && !(fly_.item >= 0 && fly_.open.target > 0.5f)) {
      float y = (ptr.y - c_.y) / std::max(1.f, ext_.y), over = fabsf(y) - 0.66f;
      if (over > 0) {
        f_.target += (y > 0 ? 1.f : -1.f) * std::min(1.f, over * 3.f) * 7.f * dt;
        busy = true;
      }
    }
    f_.target = clampf(f_.target, 0.f, (float)std::max(0, n - 1));
    f_.step(dt, 4.2f * motion(), 0.9f);
    if (!f_.settled(0.004f)) {
      busy = true;
      repick();
    }
    return busy;
  }
  void focusOn(int i) override {
    f_.target = (float)i;
    setHot(i);
  }
  int hitAt(V2 p) const override {
    if (fabsf(p.x - c_.x) > ext_.x || fabsf(p.y - c_.y) > ext_.y) return -1;
    int best = -1;
    float bd = row_ * 0.62f;
    for (int i = 0; i < count(); i++) {
      const It& t = its_[(size_t)i];
      float d = fabsf(t.pos.y - p.y);
      if (t.there && d < bd) {
        bd = d;
        best = i;
      }
    }
    return best;
  }
  void key(NavKey k) override {
    int n = count();
    if (!n) return;
    keyed_ = true;
    if (kidKey(k)) return;
    if (k == NavKey::Right) { if (hot_ >= 0) openKids(); return; }
    if (k == NavKey::Left) return;
    if (hot_ < 0) { focusOn(clampi((int)lroundf(f_.x), 0, n - 1)); return; }
    focusOn(k == NavKey::Down || k == NavKey::Next ? (k == NavKey::Next ? (hot_ + 1) % n : std::min(n - 1, hot_ + 1)) : (k == NavKey::Prev ? (hot_ + n - 1) % n : std::max(0, hot_ - 1)));
  }
  bool smoothWheel() const override { return true; }
  bool wheel(float notches) override {
    if (count() < 2) return false;
    f_.target -= notches * 1.2f;
    keyed_ = false;
    return true;
  }
  bool ownTag() const override { return false; }
  V2 flyDir(int) const override { return {1, 0}; }
  V2 margins() const override { return {300.f * s_, 60.f * s_}; }
  float order(int i) const override { return std::min(1.f, fabsf(i - f_.x) / 6.f); }
  V2 home() const override { return {c_.x - ext_.x * 0.35f, c_.y}; }
  float lift() const override { return 0.f; }
  void drawItems(Painter& p, const Backdrop* bd, const std::vector<int>& ord, float alpha) override {
    p.dc->PushAxisAlignedClip(D2D1::RectF(c_.x - ext_.x - 80.f * s_, c_.y - ext_.y + 3.f * s_, c_.x + ext_.x + 40.f * s_, c_.y + ext_.y - 3.f * s_), D2D1_ANTIALIAS_MODE_PER_PRIMITIVE);
    FreeLayout::drawItems(p, bd, ord, alpha);
    p.dc->PopAxisAlignedClip();
  }
  void drawBack(Painter& p, const Backdrop* bd, float alpha) override {
    float o = lerp(0.85f, 1.f, clampf(open.x, 0.f, 1.05f));
    RectF r(c_.x - ext_.x, c_.y - ext_.y * o, c_.x + ext_.x, c_.y + ext_.y * o);
    if (view && skin->panel.on) {
      view->panel(p, skin->panel, r, s_, alpha, bd);
    } else if (st.shape != SlotShape::None) {
      Geo g = st.shape == SlotShape::Blade ? cutRectGeo(r, 18.f * s_) : rrectGeo(r, (st.corner + 8.f) * s_);
      if (st.shadow > 0.01f) p.glow(g.Get(), Color(0, 0, 0, 0.5f * st.shadow * alpha), 18.f * s_, 0, true, false);
      fillPanel(p, g.Get(), bd, alpha, 0.06f);
      // a cylinder catches the light in the middle and turns away above and below
      auto roll = p.linear({0, r.t}, {0, r.b}, {{0, Color(0, 0, 0, 0.42f * alpha)}, {0.28f, Color(0, 0, 0, 0.06f * alpha)}, {0.45f, Color(1, 1, 1, 0.09f * alpha)}, {0.55f, Color(1, 1, 1, 0.07f * alpha)}, {0.74f, Color(0, 0, 0, 0.08f * alpha)}, {1, Color(0, 0, 0, 0.46f * alpha)}});
      p.fill(g.Get(), roll.Get());
      strokePanel(p, g.Get(), {r.l, r.t}, {r.r, r.b}, alpha);
    }
    RectF bar(r.l + 8.f * s_, c_.y - row_ * 0.52f, r.r - 8.f * s_, c_.y + row_ * 0.52f);
    p.rrect(bar, std::min(14.f, std::max(5.f, st.corner)) * s_, st.accent.withA(0.10f * alpha));
    p.rrectStroke(bar, std::min(14.f, std::max(5.f, st.corner)) * s_, st.accent.withA(0.40f * alpha), 1.2f * s_);
  }
  void drawItem(Painter& p, const Backdrop* bd, int i, float a) override {
    It& t = its_[(size_t)i];
    const SceneItem& it = model.items[(size_t)i];
    float k = t.z, hv = saturate(t.hot.x), h = row_ * lerp(0.3f, 1.f, k);
    if (hv > 0.01f) {
      RectF r(c_.x - ext_.x + 8.f * s_, t.pos.y - h * 0.5f, c_.x + ext_.x - 8.f * s_, t.pos.y + h * 0.5f);
      p.rrect(r, std::min(14.f, std::max(5.f, st.corner)) * s_, st.accent.withA(0.24f * hv * a));
    }
    Entry e;
    e.index = i;
    e.count = count();
    e.hot = t.hot.x;
    e.alpha = a;
    e.marks = false;
    if (view && skin->hasSlot) drawEntry(p, bd, it, t.pos, t.half, t.size, e);
    else drawIcon(p, it, t.pos, t.size, a, hv);
    Color tc = view && skin->panel.on && skin->panel.hasText ? view->color(skin->panel.text) : st.text;
    D2D1_MATRIX_3X2_F base;
    p.dc->GetTransform(&base);
    p.dc->SetTransform(D2D1::Matrix3x2F::Scale(1.f, std::max(0.25f, k), D2D1::Point2F(0, t.pos.y)) * *D2D1::Matrix3x2F::ReinterpretBaseType(&base));
    float x = c_.x - ext_.x + icon_ * 1.78f + hv * 8.f * s_;
    bool two = !it.sub.empty() && k > 0.8f;
    RectF r(x, t.pos.y - 22.f * s_, c_.x + ext_.x - 34.f * s_, t.pos.y + (two ? 2.f : 22.f) * s_);
    p.text(it.label, label(16.f * s_, hv > 0.5f ? 600 : 500, Align::Left, two ? VAlign::Bottom : VAlign::Middle), r, tc.withA(lerp(0.80f, 1.f, hv) * a));
    if (two) p.text(it.sub, label(11.f * s_, 500, Align::Left, VAlign::Top), RectF(x, t.pos.y + 3.f * s_, r.r, t.pos.y + 22.f * s_), mix(tc, st.accent, 0.45f).withA(0.8f * a * saturate((k - 0.8f) * 8.f)));
    if (it.isGroup()) {
      float gx = c_.x + ext_.x - 22.f * s_;
      p.line({gx - 3 * s_, t.pos.y - 5 * s_}, {gx + 2 * s_, t.pos.y}, tc.withA(0.7f * a), 1.6f * s_);
      p.line({gx - 3 * s_, t.pos.y + 5 * s_}, {gx + 2 * s_, t.pos.y}, tc.withA(0.7f * a), 1.6f * s_);
    } else if (cfg.showRunning && it.windows > 0) {
      p.circle({c_.x + ext_.x - 22.f * s_, t.pos.y}, (it.active ? 4.f : 2.6f) * s_, (it.active ? st.accent : tc.withA(0.6f)).alpha(a));
    }
    p.dc->SetTransform(base);
  }
};

}  // namespace

std::unique_ptr<Layout> makeFree(LayoutType t) {
  switch (t) {
    case LayoutType::Orbit: return std::make_unique<OrbitLayout>();
    case LayoutType::Comb: return std::make_unique<CombLayout>();
    case LayoutType::Carousel: return std::make_unique<CarouselLayout>();
    case LayoutType::Globe: return std::make_unique<GlobeLayout>();
    case LayoutType::Cards: return std::make_unique<CardsLayout>();
    case LayoutType::Corner: return std::make_unique<CornerLayout>();
    case LayoutType::Galaxy: return std::make_unique<GalaxyLayout>();
    case LayoutType::Board: return std::make_unique<BoardLayout>();
    case LayoutType::Drum: return std::make_unique<DrumLayout>();
    default: return makeRadial();
  }
}

}  // namespace rt
