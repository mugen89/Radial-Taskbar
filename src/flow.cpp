// Side flow: icons run down a screen edge inside a liquid-looking membrane that swells under the pointer.
#include "scene.h"

namespace rt {

namespace {

class FlowLayout final : public Layout {
  struct It {
    Spring in, hot;
    float delay = 0;
    V2 pos;
    float size = 0, wave = 0, alpha = 1;
  };
  std::vector<It> its_;
  float s_ = 1, sp_ = 66, icon_ = 46, panelW_ = 90, bulge_ = 60, lift_ = 30, half_ = 300, cy_ = 0, edge_ = 0;
  float dir_ = -1;  // from the edge toward the screen's middle
  bool scrolls_ = false;
  Spring focus_, presence_, scroll_;
  int hot_ = -1;
  bool keyed_ = false;
  Flyout fly_;
  std::wstring tag_, tagSub_;
  float tagT_ = 0;

 public:
  void build() override {
    s_ = env.s;
    icon_ = cfg.iconSize * s_;
    sp_ = icon_ + cfg.flowSpacing * s_;
    bool right = cfg.flowSide == FlowSide::Right;
    if (env.anchorIsMouse) right = env.anchor.x >= env.vw * 0.5f;  // nearest edge
    dir_ = right ? -1.f : 1.f;
    edge_ = right ? env.work.r : env.work.l;
    panelW_ = icon_ + 34.f * s_;
    int n = (int)model.items.size();
    // Leave space for the neighbours the wave pushes outward.
    float room = env.work.h() * 0.5f - sp_ * 0.5f - 30.f * s_ - 1.25f * (cfg.flowMagnify - 1.f) * sp_;
    float need = std::max(0, n - 1) * sp_ * 0.5f;
    scrolls_ = need > room;
    half_ = std::max(sp_ * 0.5f, std::min(need, room));
    bulge_ = cfg.flowCurve * std::min(130.f * s_, half_ * 0.32f);
    lift_ = 26.f * s_ * std::min(1.f, (cfg.flowMagnify - 1.f) / 0.5f);
    cy_ = env.anchor.y;
    float lim = half_ + sp_ * 0.5f + 34.f * s_;
    cy_ = env.work.h() > lim * 2 ? clampf(cy_, env.work.t + lim, env.work.b - lim) : env.work.cy();
    its_.assign((size_t)n, It{});
    for (int i = 0; i < n; i++) {
      its_[(size_t)i].delay = (st.open == OpenAnim::Fade || st.open == OpenAnim::Zoom || cfg.reduceMotion) ? 0.f : std::min(0.26f, i * 0.016f) / std::max(0.4f, motion());
      its_[(size_t)i].size = icon_;
    }
    scroll_.snap(scrolls_ ? half_ : std::max(0, n - 1) * sp_ * 0.5f);
    focus_.snap(0);
    presence_.snap(0);
    hot_ = -1;
    fly_ = Flyout{};
    place();
  }

  float tagRoom() const { return 440.f * s_; }
  RectF bounds() const override {
    float w = panelW_ + bulge_ + lift_ + tagRoom();
    float l = dir_ < 0 ? edge_ - w : edge_, r = dir_ < 0 ? edge_ : edge_ + w;
    float h = half_ + sp_ + 110.f * s_;
    return RectF(std::max(0.f, l), std::max(0.f, cy_ - h), std::min(env.vw, r), std::min(env.vh, cy_ + h));
  }

  float baseU(int i) const { return i * sp_ - scroll_.x; }
  float arch(float dy) const {
    float k = clampf(dy / (half_ + sp_), -1.f, 1.f);
    return bulge_ * (1.f - k * k);
  }

  // Dock-style wave: icons grow near the focus and push the others along the line.
  void place() {
    int n = (int)its_.size();
    if (!n) return;
    float f = focus_.x, pr = saturate(presence_.x), mag = cfg.flowMagnify;
    std::vector<float> sc((size_t)n), w((size_t)n, 0.f);
    for (int i = 0; i < n; i++) {
      float q = (baseU(i) - f) / (1.3f * sp_);
      its_[(size_t)i].wave = expf(-q * q) * pr;
      sc[(size_t)i] = 1.f + (mag - 1.f) * its_[(size_t)i].wave;
    }
    for (int i = 1; i < n; i++) w[(size_t)i] = w[(size_t)i - 1] + sp_ * (sc[(size_t)i] + sc[(size_t)i - 1]) * 0.5f;
    // Keep the point under the pointer still.
    float fi = clampf((f + scroll_.x) / sp_, 0.f, (float)(n - 1));
    int i0 = clampi((int)floorf(fi), 0, n - 1), i1 = std::min(n - 1, i0 + 1);
    float wf = lerp(w[(size_t)i0], w[(size_t)i1], fi - i0);
    float fc = fi * sp_ - scroll_.x;
    for (int i = 0; i < n; i++) {
      auto& t = its_[(size_t)i];
      float u = w[(size_t)i] - wf + fc;
      float in = clampf(t.in.x, 0.f, 1.2f);
      float y = cy_ + u + (1.f - in) * 46.f * s_;
      float x = edge_ + dir_ * (panelW_ * 0.5f + arch(u) + lift_ * t.wave) - dir_ * (1.f - in) * (panelW_ + 60.f * s_);
      t.pos = {x, y};
      t.size = icon_ * sc[(size_t)i] * lerp(0.6f, 1.f, saturate(in));
      float over = fabsf(u) - half_ - sp_ * 0.25f;
      t.alpha = scrolls_ ? 1.f - smooth01(over / (sp_ * 0.8f)) : 1.f;
    }
  }

  V2 dotPos(int i) const override { return {edge_ + dir_ * (20.f + 18.f * (float)i) * s_, cy_ - half_ - sp_ * 0.5f - 26.f * s_}; }
  int profileAt(V2 p) const override { return dotAt(p, s_); }
  int hotProfile() const override { return hotDot_; }

  // ------------------------------------------------------------ input
  float reachX() const { return panelW_ + bulge_ + lift_ + 70.f * s_; }
  void pointer(V2 p) override {
    ptr = p;
    pointerKnown = true;
    keyed_ = false;
    hotDot_ = dotAt(p, s_);
    if (hotDot_ >= 0) {
      setHot(-1);
      presence_.target = 0;
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
    float into = (p.x - edge_) * dir_;
    float lim = half_ + sp_ * 1.3f;
    bool within = into < reachX() && fabsf(p.y - cy_) < lim;
    if (!within) {
      // Keep the group open while crossing from its icon to its panel.
      if (fly_.item >= 0 && fly_.open.target > 0.5f && into < reachX() + fly_.rect.w() + 60.f * s_ && fabsf(p.y - its_[(size_t)fly_.item].pos.y) < sp_) return;
      setHot(-1);
      presence_.target = 0;
      return;
    }
    presence_.target = 1;
    focus_.target = clampf(p.y - cy_, -half_ - sp_ * 0.5f, half_ + sp_ * 0.5f);
    int best = -1;
    float bd = 1e9f;
    for (size_t i = 0; i < its_.size(); i++) {
      float d = fabsf(its_[i].pos.y - p.y);
      if (its_[i].alpha > 0.3f && d < bd) { bd = d; best = (int)i; }
    }
    setHot(bd < sp_ * 1.2f ? best : -1);
  }
  void setHot(int i) {
    if (i >= 0) hotDot_ = -1;  // an item is meant now, however it was chosen
    if (i == hot_) return;
    hot_ = i;
    fly_.dwell = 0;
    if (fly_.item >= 0 && fly_.item != i) {
      fly_.open.target = 0;
      fly_.hotKid = -1;
    }
  }
  void clearHover() override {
    setHot(-1);
    hotDot_ = -1;
    presence_.target = 0;
    pointerKnown = false;
  }
  void focusOn(int i) {
    int n = (int)its_.size();
    if (!n) return;
    i = clampi(i, 0, n - 1);
    keyed_ = true;
    if (scrolls_) scroll_.target = clampf(i * sp_, half_, (n - 1) * sp_ - half_);
    presence_.target = 1;
    focus_.target = i * sp_ - (scrolls_ ? scroll_.target : scroll_.x);
    setHot(i);
  }
  void select(int item) override { focusOn(item); }
  void key(NavKey k) override {
    int n = (int)its_.size();
    if (!n) return;
    bool inKids = fly_.item >= 0 && fly_.open.target > 0.5f && fly_.hotKid >= 0;
    bool toMid = (k == NavKey::Left && dir_ < 0) || (k == NavKey::Right && dir_ > 0);
    bool toEdge = (k == NavKey::Right && dir_ < 0) || (k == NavKey::Left && dir_ > 0);
    if (inKids) {
      int m = (int)fly_.cells.size();
      if (k == NavKey::Next) { fly_.hotKid = (fly_.hotKid + 1) % m; return; }
      if (k == NavKey::Prev) { fly_.hotKid = (fly_.hotKid + m - 1) % m; return; }
      if (k == NavKey::Left) { if (dir_ > 0 && fly_.hotKid == 0) { fly_.open.target = 0; fly_.hotKid = -1; } else fly_.hotKid = std::max(0, fly_.hotKid - 1); return; }
      if (k == NavKey::Right) { if (dir_ < 0 && fly_.hotKid == m - 1) { fly_.open.target = 0; fly_.hotKid = -1; } else fly_.hotKid = std::min(m - 1, fly_.hotKid + 1); return; }
      fly_.open.target = 0;
      fly_.hotKid = -1;
    }
    if (hot_ < 0) { focusOn(k == NavKey::Prev || k == NavKey::Up ? n - 1 : 0); return; }
    if (toMid) { openKids(); return; }
    if (toEdge) return;
    if (k == NavKey::Down || k == NavKey::Next) focusOn((hot_ + 1) % n);
    else focusOn((hot_ + n - 1) % n);
  }
  bool openKids() override {
    if (hot_ < 0 || model.items[(size_t)hot_].kids.empty()) return false;
    openFly();
    fly_.hotKid = dir_ < 0 ? (int)fly_.cells.size() - 1 : 0;
    return true;
  }
  void openFly() {
    auto& it = model.items[(size_t)hot_];
    if (fly_.item != hot_) {
      fly_ = Flyout{};
      fly_.item = hot_;
      fly_.caption = 24.f * s_;
    }
    V2 o = its_[(size_t)hot_].pos;
    float out = icon_ * cfg.flowMagnify * 0.5f + lift_ * 0.4f + 8.f * s_;
    RectF keep = bounds().inset(8.f * s_);
    keep.b -= fly_.caption;
    fly_.layoutCells((int)it.kids.size(), {o.x + dir_ * out, o.y}, {dir_, 0}, icon_ * 1.42f, icon_ * 0.92f, keep);
    fly_.rect.b += fly_.caption;
    fly_.open.target = 1;
  }
  bool smoothWheel() const override { return scrolls_; }
  bool wheel(float notches) override {
    int n = (int)its_.size();
    if (!scrolls_) return false;
    scroll_.target = clampf(scroll_.target - notches * sp_ * 1.5f, half_, (n - 1) * sp_ - half_);
    return true;
  }

  // ------------------------------------------------------------ animation
  bool tick(float dt) override {
    tickBase(dt);
    float m = motion();
    bool busy = !open.settled() || closing;
    busy |= tickDots(dt);
    if (scrolls_ && !closing && presence_.target > 0.5f && !keyed_ && pointerKnown) {
      // Drift when the pointer rests near either end.
      float over = fabsf(ptr.y - cy_) - (half_ - sp_ * 0.4f);
      if (over > 0) {
        float v = std::min(1.f, over / sp_) * 9.f * sp_ * dt;
        float lo = half_, hi = ((int)its_.size() - 1) * sp_ - half_;
        float t = clampf(scroll_.target + (ptr.y > cy_ ? v : -v), lo, hi);
        if (t != scroll_.target) { scroll_.target = t; busy = true; }
      }
    }
    scroll_.step(dt, 4.5f * m, 1.f);
    // Icons that slide under a resting pointer become the choice.
    if (!scroll_.settled(0.05f) && pointerKnown && !keyed_ && !closing) pointer(ptr);
    focus_.step(dt, 8.5f * m, 1.f);
    presence_.step(dt, 4.f * m, 0.85f);
    busy |= !scroll_.settled(0.05f) || !focus_.settled(0.05f) || !presence_.settled();
    for (size_t i = 0; i < its_.size(); i++) {
      auto& t = its_[i];
      t.in.target = time >= t.delay ? 1.f : 0.f;
      if (cfg.reduceMotion || st.open == OpenAnim::Fade) t.in.step(dt, 8.f, 1.f);
      else t.in.step(dt, 3.4f * st.speed, 0.70f);
      t.hot.target = ((int)i == hot_ && !closing) ? 1.f : 0.f;
      if (closing && launched && launchPick.item == (int)i) t.hot.target = 1.f;
      t.hot.step(dt, 6.5f * m, 0.7f);
      busy |= !t.in.settled() || !t.hot.settled();
    }
    if (hot_ >= 0 && !closing && !model.items[(size_t)hot_].kids.empty() && !(fly_.item == hot_ && fly_.open.target > 0.5f)) {
      fly_.dwell += dt;
      busy = true;
      if (fly_.dwell > (model.items[(size_t)hot_].isGroup() ? 0.13f : 0.40f)) openFly();
    }
    fly_.open.step(dt, (fly_.open.target > 0.5f ? 4.2f : 6.5f) * m, 0.8f);
    busy |= !fly_.open.settled();
    for (size_t i = 0; i < fly_.hot.size(); i++) {
      fly_.hot[i].target = (int)i == fly_.hotKid ? 1.f : 0.f;
      fly_.hot[i].step(dt, 7.f * m, 0.75f);
      busy |= !fly_.hot[i].settled();
    }
    std::wstring t, sb;
    if (hot_ >= 0) { t = model.items[(size_t)hot_].label; sb = model.items[(size_t)hot_].sub; }
    if (!t.empty() && (t != tag_ || sb != tagSub_)) {
      tag_ = t;
      tagSub_ = sb;
    }
    float want = t.empty() ? 0.f : 1.f;
    if (tagT_ != want) {
      tagT_ = want > tagT_ ? std::min(1.f, tagT_ + dt * 7.f * m) : std::max(0.f, tagT_ - dt * 9.f * m);
      busy = true;
    }
    place();
    busy |= tickSkin(dt, t, sb);
    tickParticles(dt, {edge_, cy_}, panelW_ * 0.3f, half_ + sp_);
    if (!bits_.empty() || !sparks_.empty()) busy = true;
    if (!cfg.reduceMotion && !closing && st.rim == RimStyle::Spin) busy = true;
    return busy;
  }

  // ------------------------------------------------------------ queries
  Pick pick() const override {
    Pick k;
    k.item = hot_;
    if (hot_ >= 0 && fly_.item == hot_ && fly_.open.target > 0.5f) k.kid = fly_.hotKid;
    return k;
  }
  V2 spot(Pick k) const override {
    if (k.kid >= 0 && k.kid < (int)fly_.cells.size()) return fly_.cells[(size_t)k.kid];
    if (k.item >= 0 && k.item < (int)its_.size()) return its_[(size_t)k.item].pos;
    return {edge_, cy_};
  }
  bool outside(V2 p) const override {
    if (fly_.contains(p, 20.f * s_)) return false;
    float into = (p.x - edge_) * dir_;
    return into > reachX() || fabsf(p.y - cy_) > half_ + sp_ * 1.6f;
  }
  V2 tiltCenter() const override { return {edge_, cy_}; }
  V2 home() const override { return {edge_ + dir_ * (panelW_ * 0.5f + bulge_), clampf(env.anchor.y, cy_ - half_, cy_ + half_)}; }

  // ------------------------------------------------------------ drawing
  void draw(Painter& p, const Backdrop* bd) override {
    float alpha = fade();
    float o = cfg.reduceMotion ? 1.f : clampf(open.x, 0.f, 1.15f);
    if (closing) o *= lerp(1.f, 0.75f, smooth01(closeT / 0.17f));
    if (st.shape != SlotShape::None) membrane(p, bd, alpha, o);
    drawSkinStage(p, bd, alpha, false);
    bool own = view && skin->hasSlot;
    if (st.particles != Particles::Off) drawParticles(p, alpha * 0.8f);

    std::vector<size_t> order(its_.size());
    for (size_t i = 0; i < order.size(); i++) order[i] = i;
    std::sort(order.begin(), order.end(), [&](size_t a, size_t b) { return its_[a].wave < its_[b].wave; });
    for (size_t i : order) {
      auto& t = its_[i];
      float a = alpha * t.alpha * saturate(t.in.x * 1.4f);
      if (a <= 0.01f) continue;
      auto& it = model.items[i];
      V2 c = t.pos;
      float size = t.size;
      if (closing && launched && launchPick.item == (int)i) size *= lerp(1.f, 1.25f, smooth01(closeT / 0.17f));
      if (own) {
        Entry e;
        e.index = (int)i;
        e.count = (int)its_.size();
        e.hot = t.hot.x;
        e.alpha = a;
        e.marks = false;
        drawEntry(p, bd, it, c, size * 0.5f + 8.f * s_, size, e);
      } else {
        drawTile(p, bd, c, size * 0.5f + 8.f * s_, t.hot.x, a);
        drawIcon(p, it, c, size, a, saturate(t.hot.x));
      }
      if (cfg.showRunning && it.windows > 0 && (!own || skin->slot.marks)) {
        float x = edge_ + dir_ * 6.f * s_, len = (it.active ? 9.f : 4.f) * s_;
        p.rrect(RectF::xywh(x - 1.6f * s_, c.y - len, 3.2f * s_, len * 2), 1.6f * s_, (it.active ? st.accent : st.text.withA(0.6f)).alpha(a));
      }
      if (it.isGroup() && !own) {
        float x = c.x + dir_ * (size * 0.5f + 7.f * s_);
        Color cc = st.text.withA(0.6f * a);
        p.line({x, c.y - 4.f * s_}, {x + dir_ * 4.f * s_, c.y}, cc, 1.5f * s_);
        p.line({x, c.y + 4.f * s_}, {x + dir_ * 4.f * s_, c.y}, cc, 1.5f * s_);
      }
      if (cfg.showNumbers && i < 9 && !own)
        p.text(std::to_wstring(i + 1), label(10.f * s_, 600), RectF::xywh(c.x - size * 0.5f - 9.f * s_, c.y - size * 0.5f - 6.f * s_, 16.f * s_, 14.f * s_), st.text.withA(0.6f * a));
      if (cfg.labels == Labels::Always && (int)i != hot_) {
        Align al = dir_ < 0 ? Align::Right : Align::Left;
        float x = c.x + dir_ * (size * 0.5f + 16.f * s_);
        RectF r = dir_ < 0 ? RectF(x - 260.f * s_, c.y - 12.f * s_, x, c.y + 12.f * s_) : RectF(x, c.y - 12.f * s_, x + 260.f * s_, c.y + 12.f * s_);
        p.textHalo(it.label, label(12.5f * s_, 500, al), r, st.text.withA(0.85f * a), halo(a), 4.f * s_);
      }
    }
    bool flyOpen = fly_.item >= 0 && fly_.open.x > 0.02f;
    if (flyOpen) drawFlyout(p, bd, fly_, model.items[(size_t)fly_.item], alpha);
    if (hot_ >= 0 && tagT_ > 0.01f) {
      auto& t = its_[(size_t)hot_];
      float a = tagT_ * alpha * (fly_.item == hot_ ? 1.f - saturate(fly_.open.x * 1.6f) : 1.f);
      float out = t.size * 0.5f + (st.shape == SlotShape::None ? 14.f : 24.f) * s_ + (1.f - easeOutCubic(tagT_)) * 14.f * s_;
      drawTag(p, bd, {t.pos.x + dir_ * out, t.pos.y}, {dir_, 0}, tag_, tagSub_, a, bounds().inset(4.f * s_));
    } else if (model.items.empty()) {
      drawTag(p, bd, {edge_ + dir_ * 30.f * s_, cy_}, {dir_, 0}, L"No pins yet", L"Right-click for settings", alpha, bounds());
    }
    drawDots(p, bd, s_, alpha);
    drawSkinStage(p, bd, alpha, true);
    if (dotTag_ > 0.01f && dotCount()) {
      V2 end = dotPos(dotCount() - 1);
      drawTag(p, bd, {end.x + dir_ * (20.f + (1.f - easeOutCubic(dotTag_)) * 10.f) * s_, end.y}, {dir_, 0}, dotName_, dotSub_, dotTag_ * alpha, bounds().inset(4.f * s_));
    }
    if (!sparks_.empty()) {
      auto keep = std::move(bits_);
      bits_.clear();
      drawParticles(p, 1.f);
      bits_ = std::move(keep);
    }
  }

 private:
  void membrane(Painter& p, const Backdrop* bd, float alpha, float o) const {
    float ext = half_ + sp_ * 0.5f, taper = 78.f * s_;
    float full = ext + taper;
    const int n = 56;
    std::vector<V2> rim;
    for (int i = 0; i <= n; i++) {
      float dy = lerp(-full, full, (float)i / n);
      float edgeK = 1.f - smooth01((fabsf(dy) - ext) / taper);
      float q = (dy - focus_.x) / (1.55f * sp_);
      float swell = (lift_ + icon_ * (cfg.flowMagnify - 1.f) * 0.44f) * expf(-q * q) * saturate(presence_.x);
      float w = (panelW_ + arch(dy) + swell) * edgeK * o;
      rim.push_back({edge_ + dir_ * w, cy_ + dy});
    }
    std::vector<V2> body = rim;
    body.push_back({edge_ - dir_ * 2.f, cy_ + full});
    body.push_back({edge_ - dir_ * 2.f, cy_ - full});
    // Smooth rim, straight back along the screen edge.
    auto rimGeo = polyGeo(rim, false, true);
    ComPtr<ID2D1PathGeometry> g;
    gfx().d2d->CreatePathGeometry(g.GetAddressOf());
    ComPtr<ID2D1GeometrySink> sk;
    if (!g || FAILED(g->Open(&sk))) return;
    sk->BeginFigure(rim[0].p(), D2D1_FIGURE_BEGIN_FILLED);
    size_t m = rim.size();
    for (size_t i = 0; i + 1 < m; i++) {
      V2 p0 = rim[i ? i - 1 : 0], p1 = rim[i], p2 = rim[i + 1], p3 = rim[std::min(i + 2, m - 1)];
      V2 c1 = p1 + (p2 - p0) * (1.f / 6.f), c2 = p2 - (p3 - p1) * (1.f / 6.f);
      sk->AddBezier(D2D1::BezierSegment(c1.p(), c2.p(), p2.p()));
    }
    sk->AddLine(D2D1::Point2F(edge_ - dir_ * 2.f, cy_ + full));
    sk->AddLine(D2D1::Point2F(edge_ - dir_ * 2.f, cy_ - full));
    sk->EndFigure(D2D1_FIGURE_END_CLOSED);
    sk->Close();

    if (st.shadow > 0.01f) p.glow(g.Get(), Color(0, 0, 0, 0.55f * st.shadow * alpha), 16.f * s_, 0, true, false);
    fillPanel(p, g.Get(), bd, alpha, 0.f);
    float W = panelW_ + bulge_ + lift_ + 20.f * s_;
    auto sheen = p.linear({edge_, cy_}, {edge_ + dir_ * W, cy_}, {{0, Color(1, 1, 1, 0.f)}, {0.55f, Color(1, 1, 1, 0.02f * alpha)}, {1, Color(1, 1, 1, 0.09f * alpha)}});
    p.fill(g.Get(), sheen.Get());
    float fy = cy_ + focus_.x, pr = saturate(presence_.x) * alpha;
    if (pr > 0.01f) {
      auto hot = p.radial({edge_ + dir_ * panelW_ * 0.6f, fy}, panelW_ + lift_ + 30.f * s_, sp_ * 2.f, {{0, st.accent.withA(0.30f * pr)}, {1, st.accent.withA(0)}});
      p.fill(g.Get(), hot.Get());
    }
    auto fadeEnds = [&](Color c, float k) {
      return p.linear({0, cy_ - full}, {0, cy_ + full}, {{0, c.withA(0)}, {0.16f, c.withA(c.a * k)}, {0.84f, c.withA(c.a * k)}, {1, c.withA(0)}});
    };
    auto line = fadeEnds(st.border.withA(std::max(0.12f, st.borderOpacity) * alpha), 1.f);
    p.stroke(rimGeo.Get(), line.Get(), std::max(1.f, st.borderWidth) * s_);
    // light travelling along the rim, brightest at the pointer
    float at = pr > 0.02f ? fy : cy_ + sinf(time * 0.9f) * half_;
    float k = std::max(pr, (st.rim == RimStyle::Spin && !cfg.reduceMotion) ? 0.7f * alpha : (st.rim == RimStyle::Solid ? 0.4f * alpha : 0.f));
    if (k > 0.01f) {
      float span = sp_ * 2.6f;
      auto glowBr = p.linear({0, at - span}, {0, at + span}, {{0, st.accent.withA(0)}, {0.5f, mix(st.accent, Color(1, 1, 1), 0.25f).withA(k)}, {1, st.accent2.withA(0)}});
      if (st.glow > 0.02f) {
        auto softBr = p.linear({0, at - span}, {0, at + span}, {{0, st.accent.withA(0)}, {0.5f, st.accent.withA(0.22f * st.glow * k)}, {1, st.accent2.withA(0)}});
        p.stroke(rimGeo.Get(), softBr.Get(), 13.f * s_, true);
        p.stroke(rimGeo.Get(), softBr.Get(), 7.f * s_, true);
      }
      p.stroke(rimGeo.Get(), glowBr.Get(), 2.4f * s_, true);
    }
  }
};

}  // namespace

std::unique_ptr<Layout> makeFlow() { return std::make_unique<FlowLayout>(); }

}  // namespace rt
