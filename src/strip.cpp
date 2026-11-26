// Line strip: a bar of icons on any edge, in the middle, or under the pointer. Wraps to more rows when full.
#include "scene.h"

namespace rt {

namespace {

class StripLayout final : public Layout {
  struct It {
    Spring in, hot;
    float delay = 0, size = 0, wave = 0;
    int row = 0, col = 0;
    V2 pos;
  };
  std::vector<It> its_;
  std::vector<std::pair<int, int>> rows_;  // first, count
  float s_ = 1, sp_ = 60, icon_ = 46, rowH_ = 66, pad_ = 14, lift_ = 12, mag_ = 1.6f;
  bool vertical_ = false;
  V2 up_{0, -1};      // from the strip toward open screen space
  V2 c_;              // panel centre
  float mainHalf_ = 0, crossHalf_ = 0;
  Spring focus_, cross_, presence_, live_;
  int hot_ = -1;
  Flyout fly_;
  std::wstring tag_, tagSub_;
  float tagT_ = 0;

  V2 pt(float m, float k) const { return vertical_ ? V2{c_.x + k, c_.y + m} : V2{c_.x + m, c_.y + k}; }
  float mainOf(V2 p) const { return vertical_ ? p.y - c_.y : p.x - c_.x; }
  float crossOf(V2 p) const { return vertical_ ? p.x - c_.x : p.y - c_.y; }
  float rowCross(int r) const { return (r - ((int)rows_.size() - 1) * 0.5f) * rowH_; }

 public:
  void build() override {
    float fit = 1.f;
    for (int pass = 0; pass < 4; pass++) {
      construct(env.s * fit);
      float maxCross = (vertical_ ? env.work.w() : env.work.h()) * 0.46f;
      if (crossHalf_ <= maxCross || fit < 0.4f) break;
      fit *= 0.84f;
    }
  }

  void construct(float s) {
    s_ = s;
    icon_ = cfg.iconSize * s;
    sp_ = icon_ + cfg.stripSpacing * s;
    rowH_ = icon_ + std::max(14.f, cfg.stripSpacing) * s + (cfg.labels == Labels::Always ? 14.f * s : 0.f);
    pad_ = 16.f * s;
    vertical_ = !env.anchorIsMouse && (cfg.stripEdge == StripEdge::Left || cfg.stripEdge == StripEdge::Right);
    lift_ = 10.f * s * std::min(1.f, (cfg.stripMagnify - 1.f) / 0.5f);
    int n = (int)model.items.size();
    float room = (vertical_ ? env.work.h() : env.work.w()) * 0.90f - pad_ * 2 - icon_ * (cfg.stripMagnify - 1.f) * 2.2f;
    int per = std::max(1, (int)floorf(room / sp_));
    int rowCount = std::max(1, (n + per - 1) / per);
    rows_.clear();
    its_.assign((size_t)n, It{});
    int i = 0;
    for (int r = 0; r < rowCount; r++) {
      int cnt = (n - i + (rowCount - r) - 1) / (rowCount - r);
      rows_.push_back({i, cnt});
      for (int c = 0; c < cnt; c++, i++) {
        its_[(size_t)i].row = r;
        its_[(size_t)i].col = c;
        its_[(size_t)i].size = icon_;
        float order = fabsf(c - (cnt - 1) * 0.5f) / std::max(1.f, cnt * 0.5f);
        its_[(size_t)i].delay = (st.open == OpenAnim::Fade || st.open == OpenAnim::Zoom || cfg.reduceMotion) ? 0.f : (order * 0.14f + r * 0.04f) / std::max(0.4f, motion());
      }
    }
    // Several rows share the space, so they swell less.
    mag_ = rowCount > 1 ? 1.f + (cfg.stripMagnify - 1.f) * 0.45f : cfg.stripMagnify;
    int widest = 1;
    for (auto& r : rows_) widest = std::max(widest, r.second);
    mainHalf_ = widest * sp_ * 0.5f + pad_;
    crossHalf_ = rowCount * rowH_ * 0.5f + pad_ * 0.45f;

    const RectF& w = env.work;
    float edge = 22.f * s, swell = 1.25f * (mag_ - 1.f) * sp_;
    up_ = {0, -1};
    if (env.anchorIsMouse) {
      c_ = env.anchor;
      c_.x = w.w() > (mainHalf_ + swell) * 2 + 16 ? clampf(c_.x, w.l + mainHalf_ + swell + 8, w.r - mainHalf_ - swell - 8) : w.cx();
      c_.y = w.h() > crossHalf_ * 2 + 16 ? clampf(c_.y, w.t + crossHalf_ + 8, w.b - crossHalf_ - 8) : w.cy();
      if (c_.y < w.t + 150.f * s) up_ = {0, 1};
      float dots = dotCount() ? 22.f * s : 0.f;  // the profile dots stay on the screen too
      if (up_.y > 0) c_.y = std::max(c_.y, w.t + crossHalf_ + 8 + dots);
      else c_.y = std::min(c_.y, w.b - crossHalf_ - 8 - dots);
    } else {
      switch (cfg.stripEdge) {
        case StripEdge::Bottom: c_ = {w.cx(), w.b - edge - crossHalf_}; break;
        case StripEdge::Top: c_ = {w.cx(), w.t + edge + crossHalf_}; up_ = {0, 1}; break;
        case StripEdge::Left: c_ = {w.l + edge + crossHalf_, w.cy()}; up_ = {1, 0}; break;
        case StripEdge::Right: c_ = {w.r - edge - crossHalf_, w.cy()}; up_ = {-1, 0}; break;
        case StripEdge::Center: c_ = {w.cx(), w.cy()}; break;
      }
    }
    focus_.snap(0);
    cross_.snap(0);
    presence_.snap(0);
    live_.snap(0);
    hot_ = -1;
    fly_ = Flyout{};
    place();
  }

  RectF bounds() const override {
    float extra = icon_ * (cfg.stripMagnify - 1.f) * 2.4f + 40.f * s_;
    float crossExtra = 330.f * s_;
    RectF r;
    if (vertical_) r = RectF(c_.x - crossHalf_ - crossExtra, c_.y - mainHalf_ - extra, c_.x + crossHalf_ + crossExtra, c_.y + mainHalf_ + extra);
    else r = RectF(c_.x - mainHalf_ - extra - 60.f * s_, c_.y - crossHalf_ - (up_.y < 0 ? crossExtra : 60.f * s_), c_.x + mainHalf_ + extra + 60.f * s_, c_.y + crossHalf_ + (up_.y > 0 ? crossExtra : 60.f * s_));
    return RectF(std::max(0.f, r.l), std::max(0.f, r.t), std::min(env.vw, r.r), std::min(env.vh, r.b));
  }

  void place() {
    float pr = saturate(presence_.x), f = focus_.x;
    live_.target = 0;
    float widest = 0;
    for (size_t r = 0; r < rows_.size(); r++) {
      int first = rows_[r].first, cnt = rows_[r].second;
      if (!cnt) continue;
      float dq = (cross_.x - rowCross((int)r)) / (rowH_ * 0.85f);
      float rowPr = pr * (rows_.size() == 1 ? 1.f : expf(-dq * dq));
      std::vector<float> sc((size_t)cnt), w((size_t)cnt, 0.f);
      float base0 = -(cnt - 1) * sp_ * 0.5f;
      for (int i = 0; i < cnt; i++) {
        float q = (base0 + i * sp_ - f) / (1.3f * sp_);
        float wv = expf(-q * q) * rowPr;
        its_[(size_t)(first + i)].wave = wv;
        sc[(size_t)i] = 1.f + (mag_ - 1.f) * wv;
      }
      for (int i = 1; i < cnt; i++) w[(size_t)i] = w[(size_t)i - 1] + sp_ * (sc[(size_t)i] + sc[(size_t)i - 1]) * 0.5f;
      float fi = clampf((f - base0) / sp_, 0.f, (float)(cnt - 1));
      int i0 = clampi((int)floorf(fi), 0, cnt - 1), i1 = std::min(cnt - 1, i0 + 1);
      float wf = lerp(w[(size_t)i0], w[(size_t)i1], fi - i0), fc = base0 + fi * sp_;
      for (int i = 0; i < cnt; i++) {
        auto& t = its_[(size_t)(first + i)];
        float in = clampf(t.in.x, 0.f, 1.25f);
        V2 q = pt(w[(size_t)i] - wf + fc, rowCross((int)r));
        float rise = (t.size - icon_) * 0.5f * (rows_.size() == 1 ? 1.f : 0.25f) + lift_ * t.wave - (1.f - in) * 60.f * s_;
        t.pos = q + up_ * rise;
        t.size = icon_ * sc[(size_t)i] * lerp(0.5f, 1.f, saturate(in));
      }
      float lo = w[0] - wf + fc - sc[0] * sp_ * 0.5f, hi = w[(size_t)cnt - 1] - wf + fc + sc[(size_t)cnt - 1] * sp_ * 0.5f;
      widest = std::max({widest, -lo, hi});
      rowsLo_ = r == 0 ? lo : std::min(rowsLo_, lo);
      rowsHi_ = r == 0 ? hi : std::max(rowsHi_, hi);
    }
  }
  float rowsLo_ = 0, rowsHi_ = 0;

  V2 dotPos(int i) const override { return pt(((float)i - (dotCount() - 1) * 0.5f) * 18.f * s_, 0) - up_ * (crossHalf_ + 11.f * s_); }
  int profileAt(V2 p) const override { return dotAt(p, s_); }
  int hotProfile() const override { return hotDot_; }

  // ------------------------------------------------------------ input
  void pointer(V2 p) override {
    ptr = p;
    pointerKnown = true;
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
    float m = mainOf(p), k = crossOf(p);
    float outK = k * (vertical_ ? up_.x : up_.y);  // positive on the open side
    bool within = m > rowsLo_ - 30.f * s_ && m < rowsHi_ + 30.f * s_ && outK > -crossHalf_ - 60.f * s_ && outK < crossHalf_ + icon_ * (cfg.stripMagnify - 1.f) + 34.f * s_;
    if (!within) {
      if (fly_.item >= 0 && fly_.open.target > 0.5f && fly_.rect.inset(-34.f * s_).contains(p)) return;
      setHot(-1);
      presence_.target = 0;
      return;
    }
    presence_.target = 1;
    focus_.target = clampf(m, -mainHalf_ + pad_, mainHalf_ - pad_);
    cross_.target = k;
    int best = -1;
    float bd = 1e9f;
    for (size_t i = 0; i < its_.size(); i++) {
      float dm = fabsf(mainOf(its_[i].pos) - m), dk = rows_.size() > 1 ? fabsf(rowCross(its_[i].row) - k) : 0.f;
      float d = dm + dk * 1.2f;
      if (d < bd) { bd = d; best = (int)i; }
    }
    setHot(bd < sp_ * 1.3f ? best : -1);
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
    auto& t = its_[(size_t)i];
    presence_.target = 1;
    focus_.target = (t.col - (rows_[(size_t)t.row].second - 1) * 0.5f) * sp_;
    cross_.target = rowCross(t.row);
    setHot(i);
  }
  void select(int item) override { focusOn(item); }
  void key(NavKey k) override {
    int n = (int)its_.size();
    if (!n) return;
    bool inKids = fly_.item >= 0 && fly_.open.target > 0.5f && fly_.hotKid >= 0;
    if (inKids) {
      int m = (int)fly_.cells.size();
      if (k == NavKey::Next) { fly_.hotKid = (fly_.hotKid + 1) % m; return; }
      if (k == NavKey::Prev) { fly_.hotKid = (fly_.hotKid + m - 1) % m; return; }
      if (k == NavKey::Left) { fly_.hotKid = std::max(0, fly_.hotKid - 1); return; }
      if (k == NavKey::Right) { fly_.hotKid = std::min(m - 1, fly_.hotKid + 1); return; }
      fly_.open.target = 0;
      fly_.hotKid = -1;
      return;
    }
    if (hot_ < 0) { focusOn(k == NavKey::Prev || k == NavKey::Left ? n - 1 : 0); return; }
    NavKey fwd = vertical_ ? NavKey::Down : NavKey::Right, back = vertical_ ? NavKey::Up : NavKey::Left;
    bool openDir = (up_.y < 0 && k == NavKey::Up) || (up_.y > 0 && k == NavKey::Down) || (up_.x > 0 && k == NavKey::Right) || (up_.x < 0 && k == NavKey::Left);
    if (k == NavKey::Next || k == fwd) { focusOn((hot_ + 1) % n); return; }
    if (k == NavKey::Prev || k == back) { focusOn((hot_ + n - 1) % n); return; }
    if (openDir && openKids()) return;
    // other rows
    auto& t = its_[(size_t)hot_];
    int dr = (k == NavKey::Down || k == NavKey::Right) ? 1 : -1;
    int nr = t.row + dr;
    if (nr < 0 || nr >= (int)rows_.size()) return;
    int col = clampi((int)lroundf((t.col + 0.5f) / rows_[(size_t)t.row].second * rows_[(size_t)nr].second - 0.5f), 0, rows_[(size_t)nr].second - 1);
    focusOn(rows_[(size_t)nr].first + col);
  }
  bool openKids() override {
    if (hot_ < 0 || model.items[(size_t)hot_].kids.empty()) return false;
    openFly();
    fly_.hotKid = (int)fly_.cells.size() / 2;
    return true;
  }
  void openFly() {
    auto& it = model.items[(size_t)hot_];
    if (fly_.item != hot_) {
      fly_ = Flyout{};
      fly_.item = hot_;
      fly_.caption = 26.f * s_;
    }
    V2 o = its_[(size_t)hot_].pos;
    float out = icon_ * mag_ * 0.5f + 6.f * s_;
    RectF keep = bounds().inset(8.f * s_);
    keep.b -= fly_.caption;
    V2 org = o + up_ * out;
    if (rows_.size() > 1) org = pt(mainOf(o), 0) + up_ * (crossHalf_ + 2.f * s_);
    if (up_.y < 0) org.y -= fly_.caption;
    fly_.layoutCells((int)it.kids.size(), org, up_, icon_ * 1.42f, icon_ * 0.92f, keep);
    fly_.rect.b += fly_.caption;
    fly_.open.target = 1;
  }
  bool wheel(float) override { return false; }

  // ------------------------------------------------------------ animation
  bool tick(float dt) override {
    tickBase(dt);
    float m = motion();
    bool busy = !open.settled() || closing;
    busy |= tickDots(dt);
    focus_.step(dt, 8.5f * m, 1.f);
    cross_.step(dt, 8.5f * m, 1.f);
    presence_.step(dt, 4.f * m, 0.85f);
    busy |= !focus_.settled(0.05f) || !cross_.settled(0.05f) || !presence_.settled();
    for (size_t i = 0; i < its_.size(); i++) {
      auto& t = its_[i];
      t.in.target = time >= t.delay ? 1.f : 0.f;
      if (cfg.reduceMotion || st.open == OpenAnim::Fade) t.in.step(dt, 8.f, 1.f);
      else t.in.step(dt, 3.6f * st.speed, 0.66f);
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
    if (!t.empty()) { tag_ = t; tagSub_ = sb; }
    float want = t.empty() ? 0.f : 1.f;
    if (tagT_ != want) {
      tagT_ = want > tagT_ ? std::min(1.f, tagT_ + dt * 7.f * m) : std::max(0.f, tagT_ - dt * 9.f * m);
      busy = true;
    }
    place();
    busy |= tickSkin(dt, t, sb);
    tickParticles(dt, c_, 0, mainHalf_ * 0.7f);
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
    return c_;
  }
  bool outside(V2 p) const override {
    if (fly_.contains(p, 20.f * s_)) return false;
    float m = mainOf(p), k = crossOf(p);
    return m < rowsLo_ - 46.f * s_ || m > rowsHi_ + 46.f * s_ || fabsf(k) > crossHalf_ + icon_ * cfg.stripMagnify * 0.6f + 46.f * s_;
  }
  V2 tiltCenter() const override { return c_; }
  V2 home() const override { return c_; }

  float glass(V2 p, V2& n) const override {
    float m = mainOf(p), k = crossOf(p);
    float dm = mainHalf_ - fabsf(m), dk = crossHalf_ - fabsf(k);
    if (dm < 0 || dk < 0) return -1;
    V2 nm = pt(m > 0 ? 1.f : -1.f, 0) - c_, nk = pt(0, k > 0 ? 1.f : -1.f) - c_;
    n = dm < dk ? nm : nk;
    return std::min(dm, dk);
  }

  // ------------------------------------------------------------ drawing
  void draw(Painter& p, const Backdrop* bd) override {
    float alpha = fade();
    float o = cfg.reduceMotion ? 1.f : clampf(open.x, 0.f, 1.12f);
    if (closing) o *= lerp(1.f, 0.96f, smooth01(closeT / 0.17f));
    float lo = std::min(rowsLo_, -mainHalf_ + pad_) - pad_ * 0.8f, hi = std::max(rowsHi_, mainHalf_ - pad_) + pad_ * 0.8f;
    float mid = (lo + hi) * 0.5f, hm = (hi - lo) * 0.5f * lerp(0.55f, 1.f, o), hk = crossHalf_ * lerp(0.7f, 1.f, o);
    V2 a = pt(mid - hm, -hk), b = pt(mid + hm, hk);
    RectF r(std::min(a.x, b.x), std::min(a.y, b.y), std::max(a.x, b.x), std::max(a.y, b.y));
    if (st.shape != SlotShape::None) {
      float corner = std::min((st.corner + 8.f) * s_, hk);
      Geo g = st.shape == SlotShape::Blade ? cutRectGeo(r, 16.f * s_) : rrectGeo(r, corner);
      if (st.shadow > 0.01f) p.glow(g.Get(), Color(0, 0, 0, 0.5f * st.shadow * alpha), 18.f * s_, 0, true, false);
      fillPanel(p, g.Get(), bd, alpha, 0.f);
      auto sheen = p.linear({r.l, r.t}, {r.l, r.b}, {{0, Color(1, 1, 1, 0.09f * alpha)}, {0.5f, Color(1, 1, 1, 0.015f * alpha)}, {1, Color(1, 1, 1, 0.0f)}});
      p.fill(g.Get(), sheen.Get());
      float pr = saturate(presence_.x) * alpha;
      if (pr > 0.01f) {
        V2 f = pt(focus_.x, cross_.x);
        auto hot = p.radial(f, sp_ * 2.2f, sp_ * 2.2f, {{0, st.accent.withA(0.26f * pr)}, {1, st.accent.withA(0)}});
        p.fill(g.Get(), hot.Get());
      }
      strokePanel(p, g.Get(), {r.l, r.t}, {r.r, r.b}, alpha);
      if (st.rim != RimStyle::Off) {
        float ang = (st.rim == RimStyle::Spin && !cfg.reduceMotion) ? time * 1.0f : 0.5f;
        V2 c = r.center(), d{cosf(ang) * r.w() * 0.5f, sinf(ang) * r.h() * 0.5f};
        auto br = p.linear(c - d, c + d, {{0, st.accent.withA(0.95f * alpha)}, {0.5f, st.accent.withA(0.12f * alpha)}, {1, st.accent2.withA(0.95f * alpha)}});
        if (st.glow > 0.05f) {
          auto soft = p.linear(c - d, c + d, {{0, st.accent.withA(0.15f * st.glow * alpha)}, {0.5f, st.accent.withA(0.02f * alpha)}, {1, st.accent2.withA(0.15f * st.glow * alpha)}});
          p.stroke(g.Get(), soft.Get(), 9.f * s_);
        }
        p.stroke(g.Get(), br.Get(), 2.f * s_);
      }
    }
    if (st.particles != Particles::Off) drawParticles(p, alpha * 0.8f);
    drawSkinStage(p, bd, alpha, false);
    bool own = view && skin->hasSlot;

    std::vector<size_t> order(its_.size());
    for (size_t i = 0; i < order.size(); i++) order[i] = i;
    std::sort(order.begin(), order.end(), [&](size_t x, size_t y) { return its_[x].wave < its_[y].wave; });
    for (size_t i : order) {
      auto& t = its_[i];
      float al = alpha * saturate(t.in.x * 1.4f);
      if (al <= 0.01f) continue;
      auto& it = model.items[i];
      float size = t.size;
      if (closing && launched && launchPick.item == (int)i) size *= lerp(1.f, 1.25f, smooth01(closeT / 0.17f));
      if (own) {
        Entry e;
        e.index = (int)i;
        e.count = (int)its_.size();
        e.hot = t.hot.x;
        e.alpha = al;
        e.marks = false;
        drawEntry(p, bd, it, t.pos, size * 0.5f + 5.f * s_, size, e);
      } else {
        drawTile(p, bd, t.pos, size * 0.5f + 5.f * s_, t.hot.x, al);
        drawIcon(p, it, t.pos, size, al, saturate(t.hot.x));
      }
      if (cfg.labels == Labels::Always && (int)i != hot_)
        p.text(it.label, label(10.f * s_, 500, Align::Center, VAlign::Top), RectF::xywh(t.pos.x - sp_ * 0.5f, t.pos.y + size * 0.5f + 2.f * s_, sp_, 14.f * s_), st.text.withA(0.8f * al));
      if (cfg.showRunning && it.windows > 0 && (!own || skin->slot.marks)) {
        V2 q = t.pos - up_ * (size * 0.5f + 5.5f * s_);
        float len = (it.active ? 7.f : 2.f) * s_;
        RectF ir = vertical_ ? RectF::xywh(q.x - 1.6f * s_, q.y - len, 3.2f * s_, len * 2) : RectF::xywh(q.x - len, q.y - 1.6f * s_, len * 2, 3.2f * s_);
        p.rrect(ir, 1.6f * s_, (it.active ? st.accent : st.text.withA(0.7f)).alpha(al));
      }
      if (cfg.showNumbers && i < 9 && !own)
        p.text(std::to_wstring(i + 1), label(10.f * s_, 600), RectF::xywh(t.pos.x - size * 0.5f - 6.f * s_, t.pos.y - size * 0.5f - 6.f * s_, 14.f * s_, 14.f * s_), st.text.withA(0.6f * al));
    }
    bool flyOpen = fly_.item >= 0 && fly_.open.x > 0.02f;
    if (flyOpen) drawFlyout(p, bd, fly_, model.items[(size_t)fly_.item], alpha);
    if (hot_ >= 0 && tagT_ > 0.01f) {
      auto& t = its_[(size_t)hot_];
      float al = tagT_ * alpha * (fly_.item == hot_ ? 1.f - saturate(fly_.open.x * 1.6f) : 1.f);
      float out = t.size * 0.5f + 14.f * s_ - (1.f - easeOutCubic(tagT_)) * 8.f * s_;
      V2 from = t.pos;
      if (rows_.size() > 1) {  // clear of the other rows
        from = pt(mainOf(t.pos), 0);
        out = crossHalf_ + 8.f * s_ - (1.f - easeOutCubic(tagT_)) * 8.f * s_;
      }
      drawTag(p, bd, from + up_ * out, up_, tag_, tagSub_, al, bounds().inset(4.f * s_));
    } else if (model.items.empty()) {
      p.text(L"No pins yet", label(13.f * s_, 600), r, st.text.withA(alpha));
    }
    drawDots(p, bd, s_, alpha);
    drawSkinStage(p, bd, alpha, true);
    if (dotTag_ > 0.01f && dotCount() && hot_ < 0)
      drawTag(p, bd, pt(mainOf(dotTagAt()), 0) + up_ * (crossHalf_ + (10.f - (1.f - easeOutCubic(dotTag_)) * 8.f) * s_), up_, dotName_, dotSub_, dotTag_ * alpha, bounds().inset(4.f * s_));
    if (!sparks_.empty()) {
      auto keep = std::move(bits_);
      bits_.clear();
      drawParticles(p, 1.f);
      bits_ = std::move(keep);
    }
  }
};

}  // namespace

std::unique_ptr<Layout> makeStrip() { return std::make_unique<StripLayout>(); }

}  // namespace rt
