// The wheel: an optional limit per ring, extra rings, a fan that extends from groups, and a hub.
#include "scene.h"

namespace rt {

namespace {

class RadialLayout final : public Layout {
  struct Slot {
    int item = -1, ring = 0;
    float a0 = 0, a1 = 0;
    Spring hot, in;
    float delay = 0;
    float mid() const { return (a0 + a1) * 0.5f; }
  };
  struct Ring {
    float rIn = 0, rOut = 0;
    int first = 0, count = 0;
    bool full = true;
    float s0 = 0, s1 = 0;
    Spring reveal{1.f};
    float mid() const { return (rIn + rOut) * 0.5f; }
  };

  std::vector<Ring> rings_;
  std::vector<Slot> slots_;
  int hot_ = -1;
  float s_ = 1, gap_ = 6, icon_ = 46, hubR_ = 88, outer_ = 180, reach_ = 180, plain_ = 180, rim_ = 0;
  int seenHot_ = -1;
  bool skinned() const { return view && skin->radial; }
  // The outer edge of the wheel as it is now, with the rim a skin puts around it.
  float wheelR() const {
    float R = hubR_;
    for (auto& r : rings_) R = std::max(R, lerp(r.rIn, r.rOut, saturate(r.reveal.x)));
    return R + rim_;
  }

  // the extension that grows out of a group
  int fanSlot_ = -1, hotKid_ = -1, dwellSlot_ = -1;
  Spring fan_;
  std::vector<Slot> fanSlots_;
  float fanIn_ = 0, fanOut_ = 0, fanS0_ = 0, fanS1_ = 0, dwell_ = 0;

  int page_ = 0, pages_ = 1;
  Spring turn_;
  float ptrR_ = 0;
  Spring needle_, needleA_, hubBtn_;
  bool needleInit_ = false;
  std::wstring lab_, sub_, labPrev_, subPrev_;
  float labT_ = 1;
  HubButton hotBtn_ = HubButton::None;

  // profiles along the inside of the hub's rim
  int hotTab_ = -1, dwellTab_ = -1, armedTab_ = -1;
  float tabDwell_ = 0;
  std::vector<Spring> tabHot_;
  bool labTab_ = false, labTabPrev_ = false;  // the caption names a profile, not an item
  struct Tabs {
    float rIn, rOut, a0, per;
  };
  bool tabsOn() const { return cfg.hubProfiles && model.tabs.size() > 1 && hubR_ > 54.f * s_; }
  Tabs tabGeo(float unfolded) const {
    int n = (int)model.tabs.size();
    Tabs g;
    // Up to four sit across the top; more of them use the sides too, leaving room for the buttons below.
    g.per = std::min(kPi * 0.36f, (n <= 4 ? kPi * 1.30f : kPi * 1.53f) / std::max(1, n));
    g.a0 = -g.per * n * 0.5f;
    g.rOut = hubR_ - (8.5f + (skinned() ? skin->tabInset : 0.f)) * s_;
    g.rIn = g.rOut - lerp(3.f, 20.f, clampf(unfolded, 0.f, 1.15f)) * s_;
    return g;
  }

  bool unfold() const { return cfg.overflow == Overflow::Unfold; }

 public:
  void build() override {
    float fit = 1.f;
    for (int pass = 0; pass < 3; pass++) {
      construct(env.s * fit);
      float room = std::min(env.vw, env.vh) * 0.5f - 6.f;
      if (reach_ <= room || room < 40.f) break;
      fit *= room / reach_;
    }
    needle_.snap(0);
    needleA_.snap(0);
    tabHot_.assign(model.tabs.size(), Spring{});
    hotTab_ = dwellTab_ = armedTab_ = -1;
  }

  void construct(float s) {
    s_ = s;
    rings_.clear();
    slots_.clear();
    fanSlots_.clear();
    fanSlot_ = hot_ = hotKid_ = -1;
    fan_.snap(0);
    const SkinWheel* tw = skin ? &skin->wheel : nullptr;
    gap_ = std::max(1.5f * s, (tw && tw->gap >= 0 ? tw->gap : st.gap) * s);
    rim_ = tw ? tw->rim * s : 0.f;
    icon_ = cfg.iconSize * s;
    float th = std::max(cfg.ringThickness * s, icon_ * 1.25f);
    float minArc = icon_ * (tw && tw->crowd > 0 ? tw->crowd : 1.26f) + gap_;
    int n = (int)model.items.size(), limit = cfg.perRing;
    float span = cfg.arc >= 359.f ? kTau : cfg.arc * kPi / 180.f, facing = span >= kTau ? 0.f : cfg.arcAt * kPi * 0.5f;

    int first = 0, visible = n;
    pages_ = 1;
    if (cfg.overflow == Overflow::Pages && n > limit) {
      pages_ = (n + limit - 1) / limit;
      page_ = clampi(page_, 0, pages_ - 1);
      first = page_ * limit;
      visible = std::min(limit, n - first);
    }

    hubR_ = cfg.hubRadius * s;
    float hubGap = std::max(gap_, 5.f * s);
    int n0 = std::min(visible, limit);
    // On every page, and on every profile, the centre keeps the size the fullest one needs, so it does not jump.
    int sizeFor = pages_ > 1 ? limit : std::max(n0, std::min(model.ringFor, limit));
    float rIn0 = std::max(hubR_ + hubGap, sizeFor * minArc / span - th * 0.5f);
    hubR_ = rIn0 - hubGap;
    float rMid0 = rIn0 + th * 0.5f;

    int item = first, rest = visible;
    float rIn = rIn0;
    for (int k = 0; rest > 0 && k < 8; k++) {
      Ring r;
      r.rIn = rIn;
      r.rOut = rIn + th * (k ? 0.95f : 1.f);
      int cap = limit;
      if (k > 0) {
        int dense = (int)floorf(span * r.mid() / minArc);
        cap = clampi((int)floorf(limit * r.mid() / rMid0), limit, std::max(limit, dense));
      }
      if (k == 7) cap = rest;
      r.count = std::min(rest, cap);
      r.first = (int)slots_.size();
      // A part-filled ring lines its slots up with the ring inside it instead of stretching them.
      float w = span / std::max(1, k ? std::max(r.count, rings_.back().count) : r.count);
      r.full = r.count * w > kTau - 0.01f;
      r.s0 = r.full ? -w * 0.5f : facing - w * r.count * 0.5f;
      r.s1 = r.s0 + w * r.count;
      r.reveal.snap(k > 0 && unfold() ? 0.f : 1.f);
      for (int i = 0; i < r.count; i++) {
        Slot q;
        q.item = item++;
        q.ring = k;
        q.a0 = r.s0 + w * i;
        q.a1 = q.a0 + w;
        float order = r.full ? fabsf(wrapAngle(q.mid())) / kPi : fabsf(wrapAngle(q.mid() - facing)) / kPi;
        if (st.open == OpenAnim::Spin || st.open == OpenAnim::Unfold) order = (float)i / std::max(1, r.count);
        q.delay = (order * 0.13f + k * 0.05f) / std::max(0.4f, motion());
        if (st.open == OpenAnim::Zoom || st.open == OpenAnim::Fade || cfg.reduceMotion) q.delay = 0;
        slots_.push_back(q);
      }
      rest -= r.count;
      rIn = r.rOut + (tw && tw->ringGap >= 0 ? tw->ringGap * s : gap_ + (k ? 0.f : 1.f * s));
      rings_.push_back(r);
    }
    outer_ = rings_.empty() ? hubR_ : rings_.back().rOut;
    float ext = 0;
    for (auto& it : model.items)
      if (!it.kids.empty()) ext = (th * 0.88f + gap_ + st.hoverGrow * s) * (env.preview ? 0.12f : 1.f);
    // A fan only ever adds to the reach when it opens beyond the last ring.
    reach_ = plain_ = outer_ + std::max(ext, st.hoverGrow * s) + 34.f * s;
    if (skinned())
      for (float a : skin->wheel.area) reach_ = std::max(reach_, (outer_ + rim_) * a + 4.f * s);
  }

  RectF bounds() const override {
    float r = plain_ + 34.f * s_;
    RectF b(env.anchor.x - r, env.anchor.y - r, env.anchor.x + r, env.anchor.y + r);
    if (skinned()) {
      float R = outer_ + rim_, m = 16.f * s_;
      const float* a = skin->wheel.area;
      b = RectF(std::min(b.l, env.anchor.x - R * a[0] - m), std::min(b.t, env.anchor.y - R * a[1] - m), std::max(b.r, env.anchor.x + R * a[2] + m), std::max(b.b, env.anchor.y + R * a[3] + m));
    }
    return RectF(std::max(0.f, b.l), std::max(0.f, b.t), std::min(env.vw, b.r), std::min(env.vh, b.b));
  }

  float drawScale() const override { return s_; }
  SkinPlace skinPlace() const override {
    SkinPlace q;
    q.center = env.anchor;
    q.wheel = wheelR();
    q.hub = hubR_;
    if (!rings_.empty()) {
      q.ringIn = rings_.front().rIn;
      q.ringOut = std::max(q.wheel - rim_, rings_.front().rOut);
    } else {
      q.ringIn = q.hub;
      q.ringOut = q.wheel;
    }
    q.stage = bounds();
    Pick k = pick();
    q.spot = k.valid() ? spot(k) : env.anchor;
    q.cell = rings_.empty() ? icon_ : (rings_[0].rOut - rings_[0].rIn) * 0.5f;
    return q;
  }
  void skinVars(float* v) const override {
    v[vSel] = needle_.x * 180.f / kPi;
    v[vOn] = saturate(needleA_.x);
    float t = easeOutCubic(labT_);
    v[vIdle] = lab_.empty() ? t : 1.f - t;
    if (hot_ >= 0) v[vSelIndex] = (float)slots_[(size_t)hot_].item;
    v[vPage] = (float)page_;
    v[vPages] = (float)pages_;
    v[vRings] = (float)rings_.size();
    v[vTurn] = turn_.x;
  }

  // ------------------------------------------------------------ input
  int slotInRing(int k, float a) const {
    const Ring& r = rings_[(size_t)k];
    if (!r.count) return -1;
    float w = (r.s1 - r.s0) / r.count;
    float rel = a - r.s0;
    rel -= floorf(rel / kTau) * kTau;
    if (!r.full && rel > r.s1 - r.s0) {
      float past = std::min(rel - (r.s1 - r.s0), kTau - rel);
      if (past > std::min(0.35f, w * 0.6f)) return -1;
      return rel - (r.s1 - r.s0) < kTau - rel ? r.first + r.count - 1 : r.first;
    }
    int i = clampi((int)floorf(rel / w), 0, r.count - 1);
    return r.first + i;
  }

  int slotAt(float r, float a) const {
    int k = 0;
    for (int i = 1; i < (int)rings_.size(); i++) {
      if (unfold() && rings_[(size_t)i].reveal.x < 0.45f) break;
      if (r >= rings_[(size_t)i].rIn - gap_ * 0.5f) k = i;
    }
    for (; k >= 0; k--) {
      int q = rings_.empty() ? -1 : slotInRing(k, a);
      if (q >= 0) return q;
    }
    return -1;
  }

  void setHot(int slot, int kid) {
    if (slot != hot_) {
      dwell_ = 0;
      dwellSlot_ = slot;
    }
    hot_ = slot;
    hotKid_ = kid;
    if (slot >= 0) hotTab_ = -1;  // an item is meant now, however it was chosen
    if (fanSlot_ >= 0 && slot != fanSlot_) fan_.target = 0;
  }

  void pointer(V2 p) override {
    ptr = p;
    pointerKnown = true;
    V2 d = p - env.anchor;
    float r = d.len(), a = angleOf(d);
    ptrR_ = r;
    hotBtn_ = hubButton(p);
    int tab = profileAt(p);
    if (tab < 0) {
      dwellTab_ = armedTab_ = -1;
    } else if (!sticky && tab != armedTab_) {
      // While the shortcut is held, a flick passes across the ring: a profile only counts once the pointer rests on it.
      if (tab != dwellTab_) {
        dwellTab_ = tab;
        tabDwell_ = 0;
      }
      armedTab_ = -1;
      tab = -1;
    }
    hotTab_ = tab;
    if (hotTab_ >= 0 || r < hubR_ * 0.80f || rings_.empty()) {
      setHot(-1, -1);
      return;
    }
    if (fanSlot_ >= 0 && fan_.target > 0.5f) {
      float mid = (fanS0_ + fanS1_) * 0.5f, half = (fanS1_ - fanS0_) * 0.5f;
      float rel = wrapAngle(a - mid);
      if (r >= fanIn_ - gap_ - st.hoverGrow * s_ * 0.6f && fabsf(rel) <= half + 0.05f) {
        int m = (int)fanSlots_.size();
        int i = clampi((int)floorf((rel + half) / (2 * half) * m), 0, m - 1);
        setHot(fanSlot_, i);
        return;
      }
    }
    setHot(slotAt(r, a), -1);
  }

  void clearHover() override {
    setHot(-1, -1);
    hotTab_ = dwellTab_ = armedTab_ = -1;
    pointerKnown = false;
    ptrR_ = 0;
  }

  int profileAt(V2 p) const override {
    if (!tabsOn() || closing || tabs.x < 0.35f) return -1;
    V2 d = p - env.anchor;
    float r = d.len();
    Tabs g = tabGeo(1.f);
    if (r < g.rIn - 5.f * s_ || r > hubR_ - 1.f) return -1;
    float rel = angleOf(d) - g.a0;
    int n = (int)model.tabs.size(), i = (int)floorf(rel / g.per);
    return i >= 0 && i < n ? i : -1;
  }
  int hotProfile() const override { return hotTab_; }
  bool slideIn(int dir) override {
    turnIn(dir, 0.45f);
    return true;
  }
  void turnIn(int dir, float from) {
    for (auto& q : slots_) {
      q.in.snap(cfg.reduceMotion ? 0.2f : from);
      q.delay = 0;
    }
    time = std::max(time, 1.f);
    turn_.snap(cfg.reduceMotion ? 0.f : dir > 0 ? 1.f : -1.f);
    turn_.target = 0;
  }

  void select(int item) override {
    if (pages_ > 1) {
      int pg = item / cfg.perRing;
      if (pg != page_ && pg < pages_) flip(pg - page_);
    }
    for (size_t i = 0; i < slots_.size(); i++)
      if (slots_[i].item == item) {
        revealRing(slots_[i].ring);
        setHot((int)i, -1);
      }
  }

  void revealRing(int ring) {
    for (int k = 1; k <= ring && k < (int)rings_.size(); k++) rings_[(size_t)k].reveal.target = 1;
    ptrR_ = rings_.empty() ? 0 : rings_[(size_t)clampi(ring, 0, (int)rings_.size() - 1)].mid();
  }

  int nearestInRing(int ring, float a) const {
    int best = -1;
    float bd = 1e9f;
    const Ring& r = rings_[(size_t)ring];
    for (int i = r.first; i < r.first + r.count; i++) {
      float d = fabsf(wrapAngle(slots_[(size_t)i].mid() - a));
      if (d < bd) { bd = d; best = i; }
    }
    return best;
  }

  void key(NavKey k) override {
    if (slots_.empty()) return;
    if (hot_ < 0) {
      setHot(k == NavKey::Prev || k == NavKey::Left ? rings_[0].first + rings_[0].count - 1 : 0, -1);
      return;
    }
    int n = (int)slots_.size();
    switch (k) {
      case NavKey::Next:
        if (pages_ > 1 && hot_ == n - 1) {
          flip(1);
          setHot(0, -1);
          break;
        }
        setHot((hot_ + 1) % n, -1);
        revealRing(slots_[(size_t)hot_].ring);
        break;
      case NavKey::Prev:
        if (pages_ > 1 && hot_ == 0) {
          flip(-1);
          setHot((int)slots_.size() - 1, -1);
          break;
        }
        setHot((hot_ + n - 1) % n, -1);
        revealRing(slots_[(size_t)hot_].ring);
        break;
      case NavKey::Left:
      case NavKey::Right: {
        int step = k == NavKey::Right ? 1 : -1;
        if (hotKid_ >= 0 && fan_.target > 0.5f) {
          hotKid_ = clampi(hotKid_ + step, 0, (int)fanSlots_.size() - 1);
          break;
        }
        const Ring& r = rings_[(size_t)slots_[(size_t)hot_].ring];
        int i = hot_ - r.first + step;
        if (r.full) i = (i + r.count) % r.count;
        else i = clampi(i, 0, r.count - 1);
        setHot(r.first + i, -1);
        break;
      }
      case NavKey::Up: {
        if (hotKid_ < 0 && openKids()) break;
        if (hotKid_ < 0 && pages_ > 1) {
          flip(1);
          break;
        }
        int ring = slots_[(size_t)hot_].ring;
        if (hotKid_ < 0 && ring + 1 < (int)rings_.size()) {
          revealRing(ring + 1);
          setHot(nearestInRing(ring + 1, slots_[(size_t)hot_].mid()), -1);
        }
        break;
      }
      case NavKey::Down: {
        if (hotKid_ >= 0) {
          hotKid_ = -1;
          fan_.target = 0;
          dwell_ = -10;  // do not reopen straight away
          break;
        }
        if (pages_ > 1) {
          flip(-1);
          break;
        }
        int ring = slots_[(size_t)hot_].ring;
        if (ring > 0) {
          int q = nearestInRing(ring - 1, slots_[(size_t)hot_].mid());
          ptrR_ = rings_[(size_t)ring - 1].rIn;
          setHot(q, -1);
        }
        break;
      }
    }
  }

  bool openKids() override {
    if (hot_ < 0) return false;
    auto& it = model.items[(size_t)slots_[(size_t)hot_].item];
    if (it.kids.empty()) return false;
    openFan(hot_);
    hotKid_ = (int)it.kids.size() / 2;
    return true;
  }

  void openFan(int slot) {
    const Slot& q = slots_[(size_t)slot];
    const Ring& r = rings_[(size_t)q.ring];
    auto& kids = model.items[(size_t)q.item].kids;
    int m = (int)kids.size();
    if (!m) return;
    float th = (rings_[0].rOut - rings_[0].rIn) * 0.86f;
    fanIn_ = r.rOut + gap_ + st.hoverGrow * s_;
    fanOut_ = fanIn_ + th;
    float rMid = (fanIn_ + fanOut_) * 0.5f;
    float w = (icon_ * 1.2f + gap_) / rMid;
    if (w * m > kTau) w = kTau / m;
    float mid = q.mid();
    fanS0_ = mid - w * m * 0.5f;
    fanS1_ = fanS0_ + w * m;
    if (fanSlot_ != slot) {
      fanSlots_.assign((size_t)m, Slot{});
      for (int i = 0; i < m; i++) {
        fanSlots_[(size_t)i].item = i;
        fanSlots_[(size_t)i].a0 = fanS0_ + w * i;
        fanSlots_[(size_t)i].a1 = fanS0_ + w * (i + 1);
      }
      fan_.snap(0);
    }
    fanSlot_ = slot;
    fan_.target = 1;
  }

  bool wheel(float notches) override {
    if (pages_ <= 1 || hotTab_ >= 0) return false;  // over the ring of profiles it turns those
    flip(notches > 0 ? -1 : 1);
    return true;
  }

  void flip(int dir) {
    int np = (page_ + dir % pages_ + pages_) % pages_;
    if (np == page_) return;
    int keep = hot_ >= 0 && hot_ < cfg.perRing ? hot_ : -1;
    page_ = np;
    float s = s_;
    construct(s);
    turnIn(dir, 0.5f);
    if (keep >= 0 && keep < (int)slots_.size()) setHot(keep, -1);
  }

  // ------------------------------------------------------------ animation
  bool tick(float dt) override {
    tickBase(dt);
    float m = motion();
    bool busy = !open.settled() || closing;

    if (hot_ >= 0 && !closing) {
      auto& it = model.items[(size_t)slots_[(size_t)hot_].item];
      if (!it.kids.empty() && !(fanSlot_ == hot_ && fan_.target > 0.5f)) {
        dwell_ += dt;
        busy = true;
        if (dwell_ > (it.isGroup() ? 0.11f : 0.34f)) openFan(hot_);
      }
    }
    fan_.step(dt, (fan_.target > 0.5f ? 4.4f : 6.5f) * m, 0.78f);
    if (fan_.target < 0.5f && fan_.x < 0.02f && fanSlot_ >= 0) {
      fanSlot_ = -1;
      fanSlots_.clear();
    }
    busy |= !fan_.settled();
    for (size_t i = 0; i < fanSlots_.size(); i++) {
      fanSlots_[i].hot.target = (int)i == hotKid_ ? 1.f : 0.f;
      fanSlots_[i].hot.step(dt, 7.f * m, 0.7f);
      busy |= !fanSlots_[i].hot.settled();
    }

    if (unfold()) {
      for (size_t k = 1; k < rings_.size(); k++) {
        auto& prev = rings_[k - 1];
        float th = prev.rOut - prev.rIn;
        bool prevOpen = prev.reveal.x > 0.6f;
        if (prevOpen && ptrR_ > prev.rOut - th * 0.10f && fan_.target < 0.5f) rings_[k].reveal.target = 1;
        else if (ptrR_ < prev.rIn + th * 0.45f) rings_[k].reveal.target = 0;
        rings_[k].reveal.step(dt, 4.2f * m, 0.72f);
        busy |= !rings_[k].reveal.settled();
      }
    }

    for (size_t i = 0; i < slots_.size(); i++) {
      auto& q = slots_[i];
      q.hot.target = ((int)i == hot_ && !closing) ? (hotKid_ >= 0 ? 0.6f : 1.f) : 0.f;
      if (closing && launched && launchPick.item == q.item) q.hot.target = 1.f;
      q.hot.step(dt, 6.6f * m, 0.66f);
      q.in.target = time >= q.delay ? 1.f : 0.f;
      if (cfg.reduceMotion) q.in.step(dt, 8.f, 1.f);
      else q.in.step(dt, 4.0f * st.speed, 0.68f);
      busy |= !q.hot.settled() || !q.in.settled();
    }
    turn_.step(dt, 4.5f * m, 0.8f);
    busy |= !turn_.settled();

    // needle
    float want = needle_.target;
    bool show = false;
    if (hot_ >= 0) {
      show = true;
      want = hotKid_ >= 0 && hotKid_ < (int)fanSlots_.size() ? fanSlots_[(size_t)hotKid_].mid() : slots_[(size_t)hot_].mid();
    }
    if (show) {
      if (!needleInit_ || needleA_.x < 0.05f) {
        needle_.snap(want);
        needleInit_ = true;
      } else {
        needle_.target = needle_.x + wrapAngle(want - needle_.x);
      }
    }
    needleA_.target = show ? 1.f : 0.f;
    needle_.step(dt, 6.f * m, 0.7f);
    needleA_.step(dt, 7.f * m, 1.f);
    hubBtn_.target = sticky && (hot_ < 0 || hotBtn_ != HubButton::None) && !closing ? 1.f : 0.f;
    hubBtn_.step(dt, 5.f * m, 1.f);
    busy |= !needle_.settled() || !needleA_.settled() || !hubBtn_.settled();

    if (!sticky && !closing && dwellTab_ >= 0 && armedTab_ != dwellTab_) {
      tabDwell_ += dt;
      busy = true;
      if (tabDwell_ > 0.22f) {
        armedTab_ = dwellTab_;
        if (pointerKnown) pointer(ptr);
      }
    }
    // profile switch: unfolded while the pointer rests in the centre
    tabs.target = tabsOn() && !closing && (hot_ < 0 || tabsHold > 0) ? 1.f : 0.f;
    tabs.step(dt, 4.2f * m, 0.80f);
    busy |= !tabs.settled();
    if (tabsHold > 0) {
      tabsHold -= dt;
      busy = true;
    }
    for (size_t i = 0; i < tabHot_.size(); i++) {
      tabHot_[i].target = (int)i == hotTab_ ? 1.f : 0.f;
      tabHot_[i].step(dt, 7.f * m, 0.7f);
      busy |= !tabHot_[i].settled();
    }

    // hub caption
    std::wstring l, sb;
    bool tab = false;
    if (hotTab_ >= 0 && hotTab_ < (int)model.tabs.size()) {
      l = model.tabs[(size_t)hotTab_].name;
      sb = hotTab_ == model.profileIndex ? L"In use now" : countText(model.tabs[(size_t)hotTab_].items);
      tab = true;
    } else if (tabsHold > 0 && tabsOn()) {
      l = model.profileName;
      sb = countText((int)model.items.size());
      tab = true;
    } else if (const SceneItem* it = itemAt(pick())) {
      l = it->label;
      sb = it->sub;
    }
    if (l != lab_ || sb != sub_) {
      labPrev_ = lab_;
      subPrev_ = sub_;
      labTabPrev_ = labTab_;
      lab_ = l;
      sub_ = sb;
      labTab_ = tab;
      labT_ = 0;
    }
    if (labT_ < 1.f) {
      labT_ = std::min(1.f, labT_ + dt * 8.f * m);
      busy = true;
    }

    if (view) {
      view->caption(lab_, sub_);
      if (hot_ != seenHot_) {
        seenHot_ = hot_;
        if (hot_ >= 0 && time > 0.12f && !closing) view->hoverChanged(polar(env.anchor, slots_[(size_t)hot_].mid(), rings_[(size_t)slots_[(size_t)hot_].ring].mid()), icon_ * 0.7f);
      }
      busy |= tickView(dt);
    }
    tickParticles(dt, env.anchor, hubR_, outer_ + 14.f * s_);
    if (!bits_.empty() || !sparks_.empty()) busy = true;
    if (!cfg.reduceMotion && !closing && (st.rim == RimStyle::Spin || st.pulse || st.scan || (st.ticks && st.material == Material::Outline))) busy = true;
    return busy;
  }

  // ------------------------------------------------------------ queries
  Pick pick() const override {
    if (hot_ < 0 || hot_ >= (int)slots_.size()) return {};
    Pick k;
    k.item = slots_[(size_t)hot_].item;
    if (hotKid_ >= 0 && fanSlot_ == hot_ && hotKid_ < (int)fanSlots_.size()) k.kid = hotKid_;
    return k;
  }
  V2 spot(Pick k) const override {
    if (k.kid >= 0 && k.kid < (int)fanSlots_.size()) return polar(env.anchor, fanSlots_[(size_t)k.kid].mid(), (fanIn_ + fanOut_) * 0.5f);
    for (auto& q : slots_)
      if (q.item == k.item) return polar(env.anchor, q.mid(), rings_[(size_t)q.ring].mid());
    return env.anchor;
  }
  bool outside(V2 p) const override {
    float r = (p - env.anchor).len();
    float lim = hubR_;
    for (auto& k : rings_)
      if (k.reveal.x > 0.4f) lim = k.rOut;
    if (fanSlot_ >= 0 && fan_.target > 0.5f) lim = std::max(lim, fanOut_);
    return r > lim + 64.f * s_;
  }
  float keepInside() const override { return reach_; }
  const SkinButton* skinButton(int i) const { return !skinned() ? nullptr : i ? (skin->settingsButton.on ? &skin->settingsButton : nullptr) : (skin->pinButton.on ? &skin->pinButton : nullptr); }
  V2 btnPos(int i) const {
    if (auto* b = skinButton(i)) {
      float u = b->unit == SkinUnit::Px ? s_ : b->unit == SkinUnit::Hub ? hubR_ : wheelR();
      return env.anchor + b->at * u;
    }
    float keep = skinned() ? skin->wheel.hubKeep : 1.f;
    return {env.anchor.x + (i ? 17.f : -17.f) * s_, env.anchor.y + hubR_ * 0.70f * keep};
  }
  float btnR(int i) const {
    auto* b = skinButton(i);
    return (b ? b->size + 3.f : 15.f) * s_;
  }
  bool btnOff(int i) const {
    if (!skinned()) return false;
    auto* b = skinButton(i);
    return (b && b->hidden) || (!skin->ownButtons && !b);
  }
  HubButton hubButton(V2 p) const override {
    if (!sticky) return HubButton::None;
    if (!btnOff(0) && (p - btnPos(0)).len() < btnR(0)) return HubButton::PinCurrent;
    if (!btnOff(1) && (p - btnPos(1)).len() < btnR(1)) return HubButton::Settings;
    return HubButton::None;
  }

  float glass(V2 p, V2& n) const override {
    V2 d = p - env.anchor;
    float r = std::max(0.001f, d.len()), a = angleOf(d);
    V2 rad{d.x / r, d.y / r};
    if (r < hubR_) {
      n = rad;
      return hubR_ - r;
    }
    for (size_t k = 0; k < rings_.size(); k++) {
      const Ring& g = rings_[k];
      if (r < g.rIn || r > g.rOut) continue;
      int i = slotInRing((int)k, a);
      if (i < 0) return -1;
      const Slot& q = slots_[(size_t)i];
      if (st.shape == SlotShape::Orb || st.shape == SlotShape::Hex || st.shape == SlotShape::Petal) {
        V2 c = polar(env.anchor, q.mid(), g.mid());
        V2 e = p - c;
        float l = std::max(0.001f, e.len());
        n = {e.x / l, e.y / l};
        return cellRadius(g, q) - l;
      }
      V2 tan{-rad.y, rad.x};
      float rel = wrapAngle(a - q.mid()), half = (q.a1 - q.a0) * 0.5f;
      float ds[4] = {r - g.rIn, g.rOut - r, 1e9f, 1e9f};
      if (half < kPi * 0.49f) {
        ds[2] = r * sinf(rel + half) - gap_ * 0.5f;
        ds[3] = r * sinf(half - rel) - gap_ * 0.5f;
      }
      V2 ns[4] = {rad * -1.f, rad, tan * -1.f, tan};
      float lens = 26.f * env.s, mn = 1e9f;
      V2 acc;
      for (int e = 0; e < 4; e++) {
        mn = std::min(mn, ds[e]);
        float w = std::max(0.f, lens - ds[e]);
        acc += ns[e] * (w * w);
      }
      float l = acc.len();
      n = l > 0.001f ? acc * (1.f / l) : rad;
      return mn;
    }
    return -1;
  }

  // ------------------------------------------------------------ drawing
 private:
  float cellRadius(const Ring& g, const Slot& q) const {
    float half = std::min((q.a1 - q.a0) * 0.5f, kPi * 0.5f);
    float th = g.rOut - g.rIn;
    if (st.shape == SlotShape::Hex) return std::min(th * 0.56f, g.mid() * sinf(half) * 1.06f - gap_ * 0.5f);
    if (st.shape == SlotShape::Petal) return std::min(th * 0.47f, g.mid() * tanf(std::min(half, 1.1f)) - gap_ * 0.4f);
    return std::min(th * 0.5f, g.mid() * sinf(half) - gap_ * 0.5f);
  }

  // Hovering gently widens a slot and squeezes its neighbours, like a fluid.
  void liveAngles(const Ring& g, std::vector<std::pair<float, float>>& out) const {
    out.resize((size_t)g.count);
    float total = g.s1 - g.s0, spread = st.hoverGrow * 0.014f;
    if (st.shape != SlotShape::Wedge && st.shape != SlotShape::Blade) spread *= 0.6f;
    float sum = 0, hotSum = 0;
    for (int i = 0; i < g.count; i++) {
      float h = std::max(0.f, slots_[(size_t)(g.first + i)].hot.x);
      sum += 1.f + spread * h;
      hotSum += h;
    }
    float a = g.s0, shift = 0;
    for (int i = 0; i < g.count; i++) {
      const Slot& q = slots_[(size_t)(g.first + i)];
      float h = std::max(0.f, q.hot.x);
      float w = total * (1.f + spread * h) / sum;
      out[(size_t)i] = {a, a + w};
      if (hotSum > 0.001f && g.full) shift += h * (q.mid() - (a + w * 0.5f));
      a += w;
    }
    if (hotSum > 0.001f) shift = shift / hotSum * saturate(hotSum);
    for (auto& e : out) {
      e.first += shift;
      e.second += shift;
    }
  }

  struct Pose {
    float a0, a1, rIn, rOut, scale, alpha;
    float rot = 0;     // degrees, around the entry's own middle
    V2 shift;
  };
  // Where a slot currently sits, taking the opening animation into account.
  Pose pose(const Ring& g, const Slot& q, float a0, float a1) const {
    float in = q.in.x, o = open.x;
    Pose z{a0, a1, g.rIn, g.rOut, 1.f, saturate(in * 1.5f)};
    float th = g.rOut - g.rIn;
    if (view && skin->slot.intro.on) {
      const SkinIntro& I = skin->slot.intro;
      int i = (int)(&q - slots_.data()) - g.first;
      float e = cfg.reduceMotion ? saturate(in) : SkinView::arrived(I, time, SkinView::orderOf(I.order, i, g.count, q.mid(), (uint32_t)(q.item + 1)) + q.ring * 2.f, st.speed);
      float f = cfg.reduceMotion ? 0.f : 1.f - e;
      z.alpha = lerp(I.opacity, 1.f, saturate(e)) * saturate(0.25f + in);
      z.rIn += I.radius * th * f;
      z.rOut += I.radius * th * f;
      z.a0 += I.angle * kPi / 180.f * f;
      z.a1 += I.angle * kPi / 180.f * f;
      z.scale = lerp(I.scale, 1.f, e);
      z.rot = I.rotate * f;
      z.shift = {I.x * wheelR() * f, I.y * wheelR() * f};
    } else if (!cfg.reduceMotion) {
      switch (st.open) {
        case OpenAnim::Bloom: {
          float d = (1.f - in) * th * 0.75f;
          z.rIn -= d;
          z.rOut -= d;
          z.scale = lerp(0.35f, 1.f, in);
          break;
        }
        case OpenAnim::Spin: {
          float rot = (1.f - o) * -1.25f;
          z.a0 += rot;
          z.a1 += rot;
          float d = (1.f - in) * th * 0.4f;
          z.rIn -= d;
          z.rOut -= d;
          z.scale = lerp(0.5f, 1.f, in);
          break;
        }
        case OpenAnim::Unfold: {
          float f = clampf(o, 0.02f, 1.2f);
          z.a0 *= f;
          z.a1 *= f;
          z.scale = lerp(0.5f, 1.f, in);
          break;
        }
        case OpenAnim::Zoom: {
          float k = lerp(0.80f, 1.f, o);
          z.rIn *= k;
          z.rOut *= k;
          z.scale = k;
          break;
        }
        case OpenAnim::Fade: break;
      }
    }
    if (closing && !skinned()) {
      float t = smooth01(closeT / 0.17f);
      float k = launched ? lerp(1.f, 1.06f, t) : lerp(1.f, 0.93f, t);
      if (launched && launchPick.item == q.item) k = lerp(1.f, 1.16f, t);
      z.rIn *= k;
      z.rOut *= k;
    }
    float rot = turn_.x * 0.55f;
    z.a0 += rot;
    z.a1 += rot;
    if (g.reveal.x < 0.999f || g.reveal.target < 0.5f) {
      float f = clampf(g.reveal.x, 0.f, 1.15f);
      z.rOut = z.rIn + (z.rOut - z.rIn) * lerp(0.08f, 1.f, f);
      z.scale *= f;
    }
    return z;
  }

  struct Cell {
    Geo geo;
    V2 center;
    float radius;  // usable half-size around the centre
  };
  Cell cell(const Pose& z, float hot, float th0) const {
    float grow = st.hoverGrow * s_ * hot;
    float rIn = z.rIn + grow * 0.28f, rOut = z.rOut + grow;
    float mid = (z.a0 + z.a1) * 0.5f, half = std::min((z.a1 - z.a0) * 0.5f, kPi * 0.5f);
    float rm = (rIn + rOut) * 0.5f;
    Cell c;
    c.center = polar(env.anchor, mid, rm);
    float th = std::max(1.f, rOut - rIn);
    switch (st.shape) {
      case SlotShape::Wedge:
        c.geo = wedgeGeo(env.anchor, rIn, rOut, z.a0, z.a1, gap_, st.corner * s_);
        c.radius = std::min(th * 0.5f, rm * sinf(half));
        break;
      case SlotShape::Blade:
        c.geo = bladeGeo(env.anchor, rIn, rOut, z.a0, z.a1, gap_, st.corner * s_, 0.045f);
        c.center = polar(env.anchor, mid + 0.02f, rm);
        c.radius = std::min(th * 0.5f, rm * sinf(half));
        break;
      case SlotShape::Orb:
        c.radius = std::max(2.f, std::min(th * 0.5f, rm * sinf(half) - gap_ * 0.5f)) * (1.f + 0.05f * hot) * std::min(1.f, z.scale + 0.15f);
        c.geo = circleGeo(c.center, c.radius);
        break;
      case SlotShape::Hex:
        c.radius = std::max(2.f, std::min(th * 0.56f, rm * sinf(half) * 1.06f - gap_ * 0.5f)) * (1.f + 0.05f * hot) * std::min(1.f, z.scale + 0.15f);
        c.geo = hexGeo(c.center, c.radius, mid, st.corner * s_);
        break;
      case SlotShape::Petal: {
        float w = std::max(2.f, std::min(th * 0.52f, rm * tanf(std::min(half, 1.1f)) - gap_ * 0.25f)) * (1.f + 0.06f * hot);
        c.geo = petalGeo(env.anchor, rIn - th * 0.02f, rOut + th * 0.16f, mid, w);
        c.center = polar(env.anchor, mid, rIn + th * 0.54f);
        c.radius = w * 0.96f;
        break;
      }
      case SlotShape::None:
        c.radius = std::min(th * 0.5f, rm * sinf(half));
        break;
    }
    return c;
  }

  Geo cellGeo(const Pose& z, float hot, float inset) const {
    float grow = st.hoverGrow * s_ * hot, rIn = z.rIn + grow * 0.28f, rOut = z.rOut + grow;
    switch (st.shape) {
      case SlotShape::Wedge: return wedgeGeo(env.anchor, rIn + inset, std::max(rIn + inset + 1.f, rOut - inset), z.a0, z.a1, gap_ + 2 * inset, std::max(0.f, st.corner * s_ - inset));
      case SlotShape::Blade: return bladeGeo(env.anchor, rIn + inset, std::max(rIn + inset + 1.f, rOut - inset), z.a0, z.a1, gap_ + 2 * inset, std::max(0.f, st.corner * s_ - inset), 0.045f);
      default: break;
    }
    Cell c = cell(z, hot, 0);
    float r = std::max(1.f, c.radius - inset), mid = (z.a0 + z.a1) * 0.5f;
    if (st.shape == SlotShape::Hex) return hexGeo(c.center, r, mid, std::max(0.f, st.corner * s_ - inset));
    if (st.shape == SlotShape::Petal) return petalGeo(env.anchor, rIn + inset, rOut + (rOut - rIn) * 0.16f - inset * 1.6f, mid, r);
    return circleGeo(c.center, r);
  }

  struct Where {
    int i = 0, n = 1, ring = 0;
    float beside = 0;
    bool mine = false;  // the one being launched
  };
  void drawSkinnedEntry(Painter& p, const Backdrop* bd, const SceneItem& it, const Pose& z0, float hot, float alpha, float iconPx, int number, bool kid, const Where& w) const {
    float a = z0.alpha * alpha;
    if (a <= 0.004f) return;
    const SkinSlot& S = kid ? skin->kid : skin->slot;
    Pose z = z0;
    z.scale = 1;
    Cell c = cell(z, hot, 0);
    float mid = (z.a0 + z.a1) * 0.5f, h = saturate(hot);
    float* v = view->vars;
    float launchAll = v[vLaunch];
    v[vHot] = hot;
    v[vIn] = saturate(z0.scale);
    v[vI] = (float)w.i;
    v[vN] = (float)w.n;
    v[vA] = mid * 180.f / kPi;
    v[vSpan] = (z.a1 - z.a0) * 180.f / kPi;
    v[vRing] = (float)w.ring;
    v[vRunning] = cfg.showRunning && it.windows > 0 && !it.hwnd ? 1.f : 0.f;
    v[vWindows] = (float)it.windows;
    v[vActive] = cfg.showRunning && it.active ? 1.f : 0.f;
    v[vGroup] = it.isGroup() ? 1.f : 0.f;
    v[vKid] = kid ? 1.f : 0.f;
    v[vNumber] = (float)number;
    v[vSeed] = fmodf((float)(w.i + 1) * 0.6180340f + w.ring * 0.37f, 1.f);
    v[vNear] = w.beside;
    v[vPress] = press * h;
    v[vLaunch] = w.mine ? launchAll : 0.f;
    SkinView::Stage q;
    q.at = c.center;
    q.alpha = a;
    q.turn = mid * 180.f / kPi;
    q.glass = bd;
    q.still = true;
    std::function<Geo(float)> shape = [&](float inset) { return cellGeo(z, hot, inset); };
    q.shape = &shape;
    D2D1_MATRIX_3X2_F base;
    p.dc->GetTransform(&base);
    float k = z0.scale * (w.mine ? lerp(1.f, 1.12f, launchAll) : 1.f);
    if (fabsf(k - 1) > 0.001f || z0.rot != 0 || z0.shift.x != 0 || z0.shift.y != 0)
      p.dc->SetTransform(D2D1::Matrix3x2F::Scale(k, k, c.center.p()) * D2D1::Matrix3x2F::Rotation(z0.rot, c.center.p()) * D2D1::Matrix3x2F::Translation(z0.shift.x, z0.shift.y) *
                         *D2D1::Matrix3x2F::ReinterpretBaseType(&base));
    view->slot(p, S, it, q, c.radius, iconPx, 1.f, hot);
    if (cfg.labels == Labels::Always && !kid && !it.label.empty()) {
      Name nm;
      nm.text = &it.label;
      nm.at = {c.center.x, c.center.y + (S.nameDy != 0 ? S.nameDy * c.radius : c.radius + 6.f * s_)};
      nm.room = w.n > 1 ? std::max(c.radius * 2.f, 2.f * std::max(1.f, (c.center - env.anchor).len()) * sinf(std::min(kPi * 0.5f, (z.a1 - z.a0) * 0.5f)) - 4.f * s_) : c.radius * 3.f;
      nm.room = std::min(nm.room, c.radius * 3.2f);
      nm.alpha = a;
      nm.hot = saturate(hot);
      p.dc->GetTransform(&nm.m);
      names_.push_back(nm);
    }
    drawMarks(p, it, z, c, hot, h, a, number, kid, S.marks, S.chevron, S.badge);
    p.dc->SetTransform(base);
    v[vLaunch] = launchAll;
    v[vPress] = press;
  }

  void drawEntry(Painter& p, const Backdrop* bd, const SceneItem& it, const Pose& z, float hot, float alpha, float iconPx, int number, bool kid, const Where& w) const {
    if (view && skin->hasSlot) {
      drawSkinnedEntry(p, bd, it, z, hot, alpha, iconPx, number, kid, w);
      return;
    }
    float a = z.alpha * alpha;
    if (a <= 0.004f) return;
    float h = clampf(hot, 0.f, 1.25f);
    Cell c = cell(z, hot, 0);
    Color acc = mix(st.accent, st.accent2, 0.5f - 0.5f * cosf((z.a0 + z.a1) * 0.5f));
    if (c.geo) {
      fillPanel(p, c.geo.Get(), bd, a, 0.f);
      float R = z.rOut + st.hoverGrow * s_;
      if (st.material != Material::Outline) {
        auto gloss = p.radial(env.anchor, R, R, {{0.f, Color(1, 1, 1, 0.f)}, {saturate(z.rIn / R), Color(1, 1, 1, 0.f)}, {1.f, Color(1, 1, 1, 0.075f * a)}});
        p.fill(c.geo.Get(), gloss.Get());
      }
      if (h > 0.005f) {
        float hi = st.material == Material::Solid ? 0.42f : 0.50f;
        auto br = p.radial(env.anchor, R, R, {{saturate(z.rIn / R) * 0.96f, acc.withA(0.10f * h * a)}, {1.f, acc.withA(hi * saturate(h) * a)}});
        p.fill(c.geo.Get(), br.Get());
      }
      strokePanel(p, c.geo.Get(), {env.anchor.x - R * 0.6f, env.anchor.y - R}, {env.anchor.x + R * 0.6f, env.anchor.y + R}, a * (1.f - 0.6f * saturate(h)));
      if (h > 0.01f) {
        if (st.glow > 0.01f) p.glow(c.geo.Get(), acc.withA(0.85f * st.glow * saturate(h) * a), (5.f + 9.f * st.glow) * s_, 2.6f * s_);
        p.stroke(c.geo.Get(), acc.withA(0.95f * saturate(h) * a), std::max(1.2f, st.borderWidth) * s_ * 1.15f);
        if (st.shape == SlotShape::Wedge || st.shape == SlotShape::Blade) {
          // The bright selection arc riding the outer rim.
          float sk = st.shape == SlotShape::Blade ? 0.045f : 0.f;
          float r = z.rOut + st.hoverGrow * s_ * hot + 5.f * s_;
          float pad = std::min((z.a1 - z.a0) * 0.30f, (gap_ * 0.5f + st.corner * s_ * 0.9f) / r);
          if (z.a1 - z.a0 < kTau - 0.01f) {
            auto arc = arcGeo(env.anchor, r, z.a0 + pad + sk, z.a1 - pad + sk);
            if (st.glow > 0.01f) p.glow(arc.Get(), acc.withA(st.glow * saturate(h) * a), 6.f * s_, 4.f * s_);
            p.stroke(arc.Get(), mix(acc, Color(1, 1, 1), 0.35f).withA(saturate(h) * a), 3.f * s_, true);
          }
        }
      }
    } else if (h > 0.005f) {
      float R = iconPx * 1.25f;
      auto br = p.radial(c.center, R, R, {{0, acc.withA(0.55f * h * a * (0.4f + 0.6f * st.glow))}, {1, acc.withA(0)}});
      p.circle(c.center, 0, acc);
      p.dc->FillEllipse(D2D1::Ellipse(c.center.p(), R, R), br.Get());
    }

    // icon
    float size = std::min(iconPx, c.radius * 1.62f) * lerp(1.f, st.iconZoom, saturate(h)) * z.scale;
    V2 ic = c.center;
    bool names = cfg.labels == Labels::Always && !kid && c.radius > iconPx * 0.5f + 8.f * s_;
    if (names) ic.y -= 7.f * s_;
    drawIcon(p, it, ic, size, a * lerp(0.92f, 1.f, saturate(h)), saturate(h));
    if (names) {
      float w = c.radius * 2.f - 6.f * s_;
      p.text(it.label, label(10.5f * s_, 500, Align::Center, VAlign::Top), RectF::xywh(ic.x - w * 0.5f, ic.y + size * 0.5f + 1.f * s_, w, 15.f * s_), st.text.withA(0.85f * a));
    }
    drawMarks(p, it, z, c, hot, h, a, number, kid, true, true, true);
  }

  // Artwork comes in all colours, so names that are always shown get a plate of their own, above everything else.
  struct Name {
    const std::wstring* text;
    V2 at;
    float room, alpha, hot;
    D2D1_MATRIX_3X2_F m;
  };
  mutable std::vector<Name> names_;
  void drawNames(Painter& p) const {
    D2D1_MATRIX_3X2_F base;
    p.dc->GetTransform(&base);
    for (auto& n : names_) {
      TextStyle ts = label(10.5f * s_, 600, Align::Center, VAlign::Middle);
      float w = std::min(gfx().measure(*n.text, ts).x + 1.f * s_, std::max(24.f * s_, n.room - 10.f * s_)), h = 15.f * s_;
      RectF r = RectF::xywh(n.at.x - w * 0.5f - 5.f * s_, n.at.y - h * 0.5f, w + 10.f * s_, h);
      p.dc->SetTransform(n.m);
      p.rrect(r, h * 0.5f, st.base.withA(lerp(0.74f, 0.92f, n.hot) * n.alpha));
      p.rrectStroke(r, h * 0.5f, mix(st.border, st.accent, n.hot).withA(lerp(0.35f, 0.95f, n.hot) * n.alpha), 1.f * s_);
      p.text(*n.text, ts, RectF(r.l + 4.f * s_, r.t - 1.f * s_, r.r - 4.f * s_, r.b + 0.5f * s_), st.text.withA(0.96f * n.alpha));
    }
    p.dc->SetTransform(base);
    names_.clear();
  }

  void drawMarks(Painter& p, const SceneItem& it, const Pose& z, const Cell& c, float hot, float h, float a, int number, bool kid, bool running, bool chevron, bool badge) const {
    float mid = (z.a0 + z.a1) * 0.5f;
    Color acc = mix(st.accent, st.accent2, 0.5f - 0.5f * cosf(mid));
    // running marks sit on the hub side
    if (running && cfg.showRunning && it.windows > 0 && !it.hwnd && a > 0.1f) {
      int dots = std::min(3, it.windows);
      float r;
      if (st.shape == SlotShape::Wedge || st.shape == SlotShape::Blade || st.shape == SlotShape::None) r = z.rIn + st.hoverGrow * s_ * hot * 0.28f + 7.f * s_;
      else r = (c.center - env.anchor).len() - c.radius + (st.shape == SlotShape::Petal ? -2.f : 7.f) * s_;
      Color rc = it.active ? acc : st.text;
      float step = 7.f * s_ / std::max(1.f, r);
      if (it.active) {
        float w = 8.f * s_ / std::max(1.f, r);
        auto arc = arcGeo(env.anchor, r, mid - w, mid + w);
        p.stroke(arc.Get(), rc.withA(a), 3.f * s_, true);
      } else {
        for (int i = 0; i < dots; i++) p.circle(polar(env.anchor, mid + (i - (dots - 1) * 0.5f) * step, r), 1.9f * s_, rc.withA(0.75f * a));
      }
    }
    if (chevron && it.isGroup() && !kid) {
      // Chevron: this one extends outward.
      float r = (st.shape == SlotShape::Wedge || st.shape == SlotShape::Blade) ? z.rOut + st.hoverGrow * s_ * hot - 8.f * s_ : (c.center - env.anchor).len() + c.radius * 0.86f;
      V2 t = polar(env.anchor, mid, r + 2.5f * s_);
      float w = 4.f * s_ / std::max(1.f, r);
      Color cc = st.text.withA(lerp(0.45f, 0.95f, saturate(h)) * a);
      p.line(polar(env.anchor, mid - w, r - 2.f * s_), t, cc, 1.6f * s_);
      p.line(polar(env.anchor, mid + w, r - 2.f * s_), t, cc, 1.6f * s_);
    }
    if (badge && cfg.showNumbers && number >= 1 && number <= 9 && !kid) {
      V2 np = polar(env.anchor, z.a0 + std::min(0.13f, (z.a1 - z.a0) * 0.22f), z.rOut - 13.f * s_);
      if (st.shape != SlotShape::Wedge && st.shape != SlotShape::Blade) np = {c.center.x + c.radius * 0.62f, c.center.y - c.radius * 0.62f};
      p.text(std::to_wstring(number), label(10.5f * s_, 600), RectF::xywh(np.x - 10 * s_, np.y - 8 * s_, 20 * s_, 16 * s_), st.text.withA(0.55f * a));
    }
  }

  void drawHub(Painter& p, const Backdrop* bd, float alpha) {
    V2 c = env.anchor;
    float k = 1.f;
    bool art = skinned();
    const Color ink = art && skin->hasHubText ? view->color(skin->hubText) : st.text;
    if (!cfg.reduceMotion && !art) k = st.open == OpenAnim::Fade ? 1.f : lerp(0.6f, 1.f, open.x);
    if (closing && !art) k *= lerp(1.f, launched ? 1.04f : 0.94f, smooth01(closeT / 0.17f));
    float R = hubR_ * k;
    bool bare = st.shape == SlotShape::None;
    bool halos = !art && (bare || (st.opacity < 0.45f && st.material != Material::Solid));  // keep text readable over anything
    if (!bare && !art) {
      Geo g;
      if (st.shape == SlotShape::Hex) g = hexGeo(c, R * 1.04f, kPi / 6.f, 14.f * s_);
      else g = circleGeo(c, R);
      fillPanel(p, g.Get(), bd, alpha, 0.10f);
      auto in = p.radial(c, R, R, {{0.f, st.base.withA(0.32f * alpha)}, {0.75f, st.base.withA(0.10f * alpha)}, {1.f, Color(1, 1, 1, 0.05f * alpha)}});
      p.fill(g.Get(), in.Get());
      strokePanel(p, g.Get(), {c.x - R * 0.5f, c.y - R}, {c.x + R * 0.5f, c.y + R}, alpha);
      if (st.material == Material::Outline || st.ticks) p.circleStroke(c, R - 7.f * s_, st.border.withA(0.16f * alpha), 1.f * s_);
    }

    if (st.pointer && !art && needleA_.x > 0.01f && !rings_.empty()) {
      float a = needle_.x, na = needleA_.x * alpha;
      Color acc = mix(st.accent, st.accent2, 0.5f - 0.5f * cosf(a));
      Color tip = mix(acc, Color(1, 1, 1), 0.35f).withA(na);
      if (!bare) {
        auto arc = arcGeo(c, R - 4.5f * s_, a - 0.24f, a + 0.24f);
        if (st.glow > 0.01f) p.glow(arc.Get(), acc.withA(0.8f * st.glow * na), 5.f * s_, 4.f * s_);
        p.stroke(arc.Get(), tip, 3.f * s_, true);
      }
      float r = R + 1.5f * s_, hw = 6.5f * s_ / std::max(1.f, r);
      std::vector<V2> tri = {polar(c, a, r + 8.5f * s_), polar(c, a + hw, r), polar(c, a, r + 1.2f * s_), polar(c, a - hw, r)};
      auto tg = polyGeo(tri, true, false);
      if (st.glow > 0.01f) p.glow(tg.Get(), acc.withA(0.5f * st.glow * na), 4.f * s_, 2.f * s_);
      p.fill(tg.Get(), tip);
    }

    if (art) R *= skin->wheel.hubKeep;
    bool ring = tabsOn() && (!art || skin->ownTabs);
    float innerR = ring ? lerp(R, (tabGeo(1.f).rIn - 2.f * s_) * k, saturate(tabs.x)) : R;  // what the ring leaves free
    if (ring) drawTabs(p, k, alpha);

    // caption
    auto caption = [&](const std::wstring& name, const std::wstring& sub, float a, float dy, bool tab) {
      if (name.empty() || a <= 0.01f) return;
      float w = tab ? (tabGeo(1.f).rIn - 4.f * s_) * k * 1.78f : R * 1.62f;
      TextStyle ts = label(16.5f * s_, 600);
      ts.wrap = true;
      V2 m = gfx().measure(name, ts, w);
      float maxH = 2.f * 22.5f * s_;
      if (m.y > maxH) {  // long window titles: smaller type, three lines at most
        ts.size = 13.f * s_;
        maxH = 3.f * 18.f * s_;
        m = gfx().measure(name, ts, w);
      }
      float th = std::min(m.y, maxH), gap = 3.f * s_, sh = sub.empty() ? 0.f : 16.f * s_;
      float y = c.y - (th + (sub.empty() ? 0 : gap + sh)) * 0.5f + dy;
      RectF tr = RectF::xywh(c.x - w * 0.5f, y, w, th + 1.f);
      RectF sr = RectF::xywh(c.x - w * 0.5f, y + th + gap, w, sh);
      TextStyle ss = label(11.5f * s_, 500);
      if (halos) {
        p.textHalo(name, ts, tr, ink.withA(a), halo(a), 5.f * s_);
        p.textHalo(sub, ss, sr, ink.withA(0.75f * a), halo(a), 4.f * s_);
      } else {
        p.text(name, ts, tr, ink.withA(a));
        p.text(sub, ss, sr, mix(ink, st.accent, 0.45f).withA(0.85f * a));
      }
    };
    float t = easeOutCubic(labT_);
    bool titles = !art || skin->ownTitle;
    if (titles && labT_ < 1.f) caption(labPrev_, subPrev_, (1.f - t) * alpha * 0.9f, -5.f * s_ * t, labTabPrev_);
    if (titles && !lab_.empty()) caption(lab_, sub_, t * alpha, 6.f * s_ * (1.f - t), labTab_);

    float idle = lab_.empty() ? t : 1.f - t;
    if (idle > 0.01f) {
      float a = idle * alpha;
      // Text shrinks to what the ring of profiles leaves free at that height, then ends in dots.
      auto put = [&](const std::wstring& s, float size, int weight, float dy, float op) {
        float y = fabsf(dy) + size * 0.5f, room = std::max(20.f * s_, 2.f * sqrtf(std::max(1.f, innerR * innerR - y * y)) - 6.f * s_);
        float w = gfx().measure(s, label(size, weight)).x;
        if (w > room) size *= std::max(0.6f, room / w);
        RectF r = RectF::xywh(c.x - room * 0.5f - 1.f, c.y + dy - size, room + 2.f, size * 2);
        if (halos) p.textHalo(s, label(size, weight), r, ink.withA(op * a), halo(a), 5.f * s_);
        else p.text(s, label(size, weight), r, ink.withA(op * a));
      };
      if (model.items.empty()) {
        if (innerR > 78.f * s_) {
          put(L"No pins yet", 16.f * s_, 600, -10.f * s_, 1.f);
          put(L"Open settings to add some", 11.f * s_, 400, 12.f * s_, 0.7f);
        } else {
          put(L"No pins yet", 16.f * s_, 600, -16.f * s_, 1.f);
          put(L"Open settings", 11.f * s_, 400, 4.f * s_, 0.7f);
          put(L"to add some", 11.f * s_, 400, 18.f * s_, 0.7f);
        }
      } else if (cfg.hub == HubShow::Clock && (!art || skin->ownClock)) {
        SYSTEMTIME lt;
        GetLocalTime(&lt);
        wchar_t tm[32] = {}, dt[64] = {};
        GetTimeFormatEx(LOCALE_NAME_USER_DEFAULT, TIME_NOSECONDS, &lt, nullptr, tm, 32);
        GetDateFormatEx(LOCALE_NAME_USER_DEFAULT, 0, &lt, L"ddd d MMM", dt, 64, nullptr);
        put(tm, 29.f * s_, 600, -8.f * s_, 1.f);
        put(dt, 12.f * s_, 500, 17.f * s_, 0.7f);
      } else if (cfg.hub == HubShow::Profile && (!art || skin->ownClock)) {
        put(model.profileName, 18.f * s_, 600, 0, 1.f);
      }
    }
    // profile name and position
    if (!ring && (!art || skin->ownTabs) && model.profileCount > 1 && cfg.hub != HubShow::Empty && R > 60.f * s_) {
      float a = alpha * 0.8f;
      if (!(cfg.hub == HubShow::Profile && lab_.empty()))
        p.text(model.profileName, label(10.5f * s_, 600), RectF::xywh(c.x - R * 0.6f, c.y - R * 0.74f, R * 1.2f, 14.f * s_), mix(model.profileColor, ink, 0.25f).withA(a));
      float pw = 9.f * s_;
      for (int i = 0; i < model.profileCount && model.profileCount < 10; i++) {
        V2 q{c.x + (i - (model.profileCount - 1) * 0.5f) * pw, c.y - R * 0.80f};
        p.circle(q, (i == model.profileIndex ? 2.6f : 1.8f) * s_, (i == model.profileIndex ? model.profileColor : ink.withA(0.35f)).alpha(a));
      }
    }
    if (pages_ > 1) {
      float pw = 9.f * s_;
      for (int i = 0; i < pages_ && pages_ < 14; i++) {
        V2 q{c.x + (i - (pages_ - 1) * 0.5f) * pw, c.y + R * 0.88f};
        p.circle(q, (i == page_ ? 2.6f : 1.8f) * s_, (i == page_ ? st.accent : ink.withA(0.4f)).alpha(alpha));
      }
    }
    if (hubBtn_.x > 0.01f && hubR_ > 56.f * s_) {
      const wchar_t* glyph[2] = {L"\xE718", L"\xE713"};
      for (int i = 0; i < 2; i++) {
        if (btnOff(i)) continue;
        V2 q = btnPos(i);
        if (auto* b = skinButton(i); b && !b->layers.empty()) {
          bool over = hotBtn_ == (i ? HubButton::Settings : HubButton::PinCurrent);
          SkinUnits u = view->units;
          u.cell = b->size * s_;
          view->vars[vHot] = over ? 1.f : 0.f;
          SkinView::Stage sg;
          sg.at = q;
          sg.alpha = hubBtn_.x * alpha;
          sg.still = true;
          SceneItem none;
          sg.item = &none;
          view->layers(p, b->layers, sg, u);
          continue;
        }
        bool hv = (i == 0 && hotBtn_ == HubButton::PinCurrent) || (i == 1 && hotBtn_ == HubButton::Settings);
        float a = hubBtn_.x * alpha;
        p.circle(q, 13.f * s_, ink.withA((hv ? 0.22f : 0.09f) * a));
        TextStyle ts;
        ts.family = L"Segoe Fluent Icons";
        ts.size = 12.5f * s_;
        ts.align = Align::Center;
        p.text(glyph[i], ts, RectF::xywh(q.x - 13 * s_, q.y - 13 * s_, 26 * s_, 26 * s_), (hv ? (art && skin->hasHubText ? ink : st.accent) : ink).withA((hv ? 1.f : 0.75f) * a));
      }
    }
  }

  // Text that follows the rim, one cluster at a time. The letters keep their angles whatever the hub is doing: every new
  // angle would cost the text renderer a new picture of each letter.
  void arcText(Painter& p, const std::wstring& s, TextStyle ts, float r, float scale, float mid, float maxLen, bool initial, Color col) const {
    auto lay = gfx().layout(s, ts, 4000.f, 100.f);
    UINT32 n = 0;
    if (!lay) return;
    lay->GetClusterMetrics(nullptr, 0, &n);
    std::vector<DWRITE_CLUSTER_METRICS> m(n);
    if (!n || FAILED(lay->GetClusterMetrics(m.data(), n, &n))) return;
    float total = 0;
    for (auto& q : m) total += q.width;
    if (!initial && total > maxLen && maxLen > total * 0.78f) {  // nearly fits: a little smaller beats cutting it short
      float f = maxLen / total;
      ts.size *= f;
      for (auto& q : m) q.width *= f;
      total = maxLen;
    }
    size_t take = m.size();
    bool cut = false;
    if (initial) {
      take = 1;
      total = m[0].width;
    } else if (total > maxLen) {
      float dot = ts.size * 0.55f, sum = 0;
      take = 0;
      while (take < m.size() && sum + m[take].width + dot <= maxLen) sum += m[take++].width;
      cut = true;
      total = sum + dot;
      if (!take) return;
    }
    // Along the lower half the letters stand the other way round, so nothing has to be read upside down.
    bool flip = fabsf(mid) > kPi * 0.56f;
    D2D1_MATRIX_3X2_F old;
    p.dc->GetTransform(&old);
    TextStyle one = ts;
    one.align = Align::Center;
    one.ellipsis = false;
    float x = -total * 0.5f;
    auto put = [&](std::wstring_view g, float w) {
      float off = (x + w * 0.5f) / r, a = flip ? mid - off : mid + off;
      V2 q = polar(env.anchor, a, r * scale);
      p.dc->SetTransform(D2D1::Matrix3x2F::Rotation(a * 180.f / kPi + (flip ? 180.f : 0.f), q.p()) * *D2D1::Matrix3x2F::ReinterpretBaseType(&old));
      p.text(g, one, RectF::xywh(q.x - 40.f * s_, q.y - ts.size, 80.f * s_, ts.size * 2.f), col);
      x += w;
    };
    size_t at = 0;
    for (size_t i = 0; i < take; i++) {
      put(std::wstring_view(s).substr(at, m[i].length), m[i].width);
      at += m[i].length;
    }
    if (cut) put(L"\x2026", ts.size * 0.55f);
    p.dc->SetTransform(old);
  }

  void drawTabs(Painter& p, float k, float alpha) const {
    float u = saturate(tabs.x), names = smooth01((u - 0.35f) / 0.65f);
    Tabs g = tabGeo(tabs.x);
    V2 c = env.anchor;
    bool line = st.material == Material::Outline;
    Tabs full = tabGeo(1.f);
    float textR = (full.rIn + full.rOut) * 0.5f, room = full.per * full.rIn - 9.f * s_;
    bool initials = room < 27.f * s_;  // all of them or none, so the ring stays calm
    for (size_t i = 0; i < model.tabs.size(); i++) {
      auto& t = model.tabs[i];
      bool on = (int)i == model.profileIndex;
      float h = i < tabHot_.size() ? clampf(tabHot_[i].x, 0.f, 1.2f) : 0.f;
      float a0 = g.a0 + g.per * (float)i, a1 = a0 + g.per, mid = (a0 + a1) * 0.5f;
      float rIn = (g.rIn - 2.5f * s_ * h * u) * k, rOut = (g.rOut + 1.5f * s_ * h * u) * k;
      float th = rOut - rIn;
      auto geo = wedgeGeo(c, rIn, rOut, a0, a1, 3.f * s_, std::min(th * 0.42f, 6.f * s_));
      Color fill, mine = t.color;
      if (skinned() && skin->hasTabOn && skin->tabOn.from != SkinColor::From::Profile) mine = view->color(skin->tabOn);
      if (on) fill = mine.withA((line ? lerp(0.95f, 0.50f, u) : 0.92f) * alpha);
      else if (skinned() && skin->hasTabFill) { fill = view->color(skin->tabFill); fill.a *= lerp(0.8f, 0.6f + 0.4f * saturate(h), u) * alpha; }
      else fill = mix(st.text, mine, lerp(0.35f, 0.70f, saturate(h))).withA(lerp(0.26f, 0.11f + 0.30f * saturate(h), u) * alpha);
      // Two wide, faint strokes pass for a glow at this size and cost next to nothing.
      if (float gl = st.glow * alpha * std::max(on ? 0.8f : 0.f, saturate(h)); gl > 0.02f) {
        p.stroke(geo.Get(), mine.withA(0.13f * gl), 9.f * s_);
        p.stroke(geo.Get(), mine.withA(0.20f * gl), 4.5f * s_);
      }
      p.fill(geo.Get(), fill);
      if (u > 0.05f) {
        Color edge = on ? mix(mine, Color(1, 1, 1), 0.35f).withA(0.65f * u * alpha) : mix(st.border, t.color, saturate(0.25f + h)).withA((0.16f + 0.55f * saturate(h)) * u * alpha);
        p.stroke(geo.Get(), edge, 1.f * s_);
      }
      if (names > 0.02f && st.shape != SlotShape::None) {
        bool onDark = !on || line || mine.luma() < 0.52f;
        Color tc = on && !line ? (onDark ? Color(1, 1, 1) : Color(0.05f, 0.06f, 0.08f)) : st.text;
        if (!on && skinned() && skin->hasTabText) tc = view->color(skin->tabText);
        arcText(p, t.name, label(10.5f * s_, on ? 700 : 600), textR, k, mid, room, initials, tc.withA((on ? 1.f : lerp(0.72f, 1.f, saturate(h))) * names * alpha));
      } else if (names > 0.02f) {
        Color tc = on && t.color.luma() >= 0.52f ? Color(0.05f, 0.06f, 0.08f) : Color(1, 1, 1);
        arcText(p, t.name, label(10.5f * s_, 700), textR, k, mid, room, initials, tc.withA(names * alpha));
      }
    }
  }

  void drawDecor(Painter& p, float alpha) const {
    V2 c = env.anchor;
    float R = hubR_;
    for (auto& r : rings_) R = std::max(R, lerp(r.rIn, r.rOut, saturate(r.reveal.x)));
    float k = cfg.reduceMotion ? 1.f : lerp(0.86f, 1.f, open.x);
    if (st.ticks) {
      float rt = (R + 13.f * s_) * k + (st.shape == SlotShape::Wedge || st.shape == SlotShape::Blade ? st.hoverGrow * s_ * 0.5f : 0.f);
      float rot = cfg.reduceMotion ? 0.f : (1.f - open.x) * 0.8f;
      const int n = 72;
      float half = cfg.arc >= 359.f ? kTau : cfg.arc * kPi / 360.f + 0.06f;
      for (int i = 0; i < n; i++) {
        float a = i * kTau / n + rot;
        if (half < kPi && fabsf(wrapAngle(a - cfg.arcAt * kPi * 0.5f)) > half) continue;
        bool major = i % 6 == 0;
        float lit = needleA_.x * std::max(0.f, 1.f - fabsf(wrapAngle(a - needle_.x)) / 0.42f);
        float len = (major ? 7.f : 3.5f) * s_ + lit * 4.f * s_;
        Color col = mix(st.border, st.accent, 0.35f + 0.65f * lit).withA((major ? 0.66f : 0.36f) * alpha + lit * 0.45f * alpha);
        p.line(polar(c, a, rt), polar(c, a, rt + len), col, (major ? 1.5f : 1.1f) * s_, false);
      }
      if (st.material == Material::Outline) {
        float spin = cfg.reduceMotion ? 0.f : time * 0.16f;
        for (int i = 0; i < 3; i++) {
          float a = spin + i * kTau / 3.f;
          auto g = arcGeo(c, rt + 13.f * s_, a, a + 0.5f);
          p.stroke(g.Get(), st.accent.withA(0.5f * alpha), 1.8f * s_);
        }
      }
    }
    if (st.rim != RimStyle::Off) {
      float rr = (R + 7.f * s_) * k;
      float ang = (st.rim == RimStyle::Spin && !cfg.reduceMotion) ? time * 1.1f : 0.6f;
      V2 d{cosf(ang) * rr, sinf(ang) * rr};
      auto br = p.linear(c - d, c + d, {{0, st.accent.withA(0.95f * alpha)}, {0.5f, mix(st.accent, st.accent2, 0.5f).withA(0.30f * alpha)}, {1, st.accent2.withA(0.95f * alpha)}});
      float mid = cfg.arcAt * kPi * 0.5f, half = cfg.arc * kPi / 360.f + 0.05f;
      auto g = cfg.arc >= 359.f ? circleGeo(c, rr) : arcGeo(c, rr, mid - half, mid + half);
      if (st.glow > 0.05f) {
        auto soft = p.linear(c - d, c + d, {{0, st.accent.withA(0.16f * st.glow * alpha)}, {0.5f, st.accent.withA(0.03f * alpha)}, {1, st.accent2.withA(0.16f * st.glow * alpha)}});
        p.stroke(g.Get(), soft.Get(), 10.f * s_);
        p.stroke(g.Get(), soft.Get(), 5.f * s_);
      }
      p.stroke(g.Get(), br.Get(), 2.f * s_);
    }
    if (st.pulse && !cfg.reduceMotion) {
      for (int i = 0; i < 2; i++) {
        float t = fmodf(time * 0.5f + i * 0.5f, 1.f);
        float r = lerp(hubR_, R + 24.f * s_, easeOutCubic(t));
        p.circleStroke(c, r, st.accent.withA(0.28f * (1.f - t) * (1.f - t) * alpha), lerp(2.6f, 0.8f, t) * s_);
      }
    }
  }

  void drawScan(Painter& p, float alpha) const {
    if (!st.scan) return;
    uint32_t px[4] = {};
    auto pm = [](Color c, float a) {
      auto q = [&](float v) { return (uint32_t)lroundf(saturate(v * a) * 255.f); };
      return q(c.b) | (q(c.g) << 8) | (q(c.r) << 16) | ((uint32_t)lroundf(a * 255.f) << 24);
    };
    px[0] = pm(st.accent, 0.085f * alpha);
    px[1] = pm(st.accent, 0.03f * alpha);
    auto bmp = gfx().bitmap(px, 1, 4, 4);
    if (!bmp) return;
    ComPtr<ID2D1BitmapBrush1> br;
    float off = cfg.reduceMotion ? 0.f : fmodf(time * 9.f, 4.f);
    p.dc->CreateBitmapBrush(bmp.Get(), D2D1::BitmapBrushProperties1(D2D1_EXTEND_MODE_WRAP, D2D1_EXTEND_MODE_WRAP, D2D1_INTERPOLATION_MODE_LINEAR),
                            D2D1::BrushProperties(1.f, D2D1::Matrix3x2F::Translation(0, off)), &br);
    if (!br) return;
    for (auto& r : rings_) {
      float f = saturate(r.reveal.x) * saturate(open.x);
      auto g = r.full ? ringGeo(env.anchor, r.rIn, lerp(r.rIn + 1.f, r.rOut, f)) : wedgeGeo(env.anchor, r.rIn, lerp(r.rIn + 1.f, r.rOut, f), r.s0, r.s1, 0, 0);
      p.fill(g.Get(), (ID2D1Brush*)br.Get());
    }
    auto hub = circleGeo(env.anchor, hubR_);
    p.fill(hub.Get(), (ID2D1Brush*)br.Get());
  }

 public:
  void draw(Painter& p, const Backdrop* bd) override {
    float alpha = fade();
    V2 c = env.anchor;
    bool art = skinned();
    D2D1_MATRIX_3X2_F base;
    p.dc->GetTransform(&base);
    if (art && closing) {  // the whole object leaves as one
      float t = smooth01(closeT / 0.17f), k = lerp(1.f, launched ? 1.035f : 0.95f, t);
      p.dc->SetTransform(D2D1::Matrix3x2F::Scale(k, k, c.p()) * *D2D1::Matrix3x2F::ReinterpretBaseType(&base));
    }

    // shadow under the whole wheel
    float shown = hubR_;
    for (auto& r : rings_)
      if (r.full) shown = std::max(shown, lerp(r.rIn, r.rOut, saturate(r.reveal.x)));
    if (art) shown = std::max(shown, wheelR());
    if (st.shadow > 0.01f && (!art || skin->ownShadow)) {
      float R = shown + 46.f * s_;
      float core = saturate((shown - 16.f * s_) / R);
      float sa = st.shadow * 0.75f * alpha;
      if (st.shape == SlotShape::None) sa *= 0.8f;
      auto br = p.radial({c.x, c.y + 6.f * s_}, R, R, {{0, Color(0, 0, 0, sa * 0.75f)}, {core, Color(0, 0, 0, sa * 0.62f)}, {lerp(core, 1.f, 0.4f), Color(0, 0, 0, sa * 0.22f)}, {1, Color(0, 0, 0, 0)}});
      p.dc->FillEllipse(D2D1::Ellipse(D2D1::Point2F(c.x, c.y + 6.f * s_), R, R), br.Get());
    }

    SkinView::Stage stage;
    stage.at = c;
    stage.alpha = alpha;
    stage.glass = bd;
    if (art) {
      view->layers(p, skin->back, stage, view->units);
    } else {
      if (st.particles != Particles::Off) drawParticles(p, alpha * 0.8f);
      drawDecor(p, alpha);
      if (st.shape == SlotShape::Orb || st.shape == SlotShape::Hex) {
        for (auto& r : rings_)
          if (r.reveal.x > 0.2f) p.circleStroke(c, r.mid(), st.border.withA(0.16f * alpha * saturate(r.reveal.x) * saturate(open.x)), 1.2f * s_);
      }
    }

    // rings, outermost first, with the focused slot drawn last
    std::vector<std::vector<std::pair<float, float>>> ang(rings_.size());
    for (size_t k = 0; k < rings_.size(); k++) liveAngles(rings_[k], ang[k]);
    auto ringAlpha = [&](size_t k) {
      float a = alpha;
      if (fanSlot_ >= 0 && fan_.x > 0.01f && (int)k > slots_[(size_t)fanSlot_].ring) a *= 1.f - 0.86f * saturate(fan_.x);
      return a * (1.f - 0.75f * fabsf(turn_.x)) * smooth01(rings_[k].reveal.x * 1.6f);
    };
    if (art) {
      float* v = view->vars;
      for (size_t k = rings_.size(); k-- > 0;) {
        const Ring& g = rings_[k];
        SkinUnits u = view->units;
        u.ring = lerp(g.rIn, g.rOut, saturate(g.reveal.x)) + rim_;
        u.moving |= g.reveal.x > 0.002f && g.reveal.x < 0.998f;
        v[vRing] = (float)k;
        v[vRingIn] = g.rIn / s_;
        v[vRingOut] = g.rOut / s_;
        v[vN] = (float)g.count;
        v[vSpan] = g.count ? (g.s1 - g.s0) / g.count * 180.f / kPi : 360.f;
        v[vA] = g.count ? (ang[k][0].first + ang[k][0].second) * 90.f / kPi : 0.f;
        SkinView::Stage q = stage;
        q.alpha = alpha * smooth01(g.reveal.x * 1.6f);
        view->layers(p, skin->ring, q, u);
      }
      view->particles(p, alpha, true);
    }
    auto drawSlotAt = [&](size_t i) {
      const Slot& q = slots_[i];
      const Ring& g = rings_[(size_t)q.ring];
      auto& aa = ang[(size_t)q.ring][(size_t)((int)i - g.first)];
      Pose z = pose(g, q, aa.first, aa.second);
      Where w;
      w.i = (int)i - g.first;
      w.n = g.count;
      w.ring = q.ring;
      w.beside = saturate(needleA_.x) * smooth01(1.f - fabsf(wrapAngle(q.mid() - needle_.x)) / std::max(0.05f, (q.a1 - q.a0) * 3.f));
      w.mine = closing && launched && launchPick.item == q.item && launchPick.kid < 0;
      drawEntry(p, bd, model.items[(size_t)q.item], z, q.hot.x, ringAlpha((size_t)q.ring), icon_ * (q.ring ? 0.94f : 1.f), (int)q.item + 1, false, w);
    };
    std::vector<size_t> late;
    for (size_t k = rings_.size(); k-- > 0;)
      for (int i = rings_[k].first; i < rings_[k].first + rings_[k].count; i++) {
        if (slots_[(size_t)i].hot.x > 0.03f) late.push_back((size_t)i);
        else drawSlotAt((size_t)i);
      }
    std::sort(late.begin(), late.end(), [&](size_t a, size_t b) { return slots_[a].hot.x < slots_[b].hot.x; });
    for (size_t i : late) drawSlotAt(i);

    if (unfold()) {
      for (size_t k = 1; k < rings_.size(); k++) {
        if (rings_[k - 1].reveal.x < 0.5f) break;
        float a = (1.f - saturate(rings_[k].reveal.x * 2.f)) * alpha * saturate(open.x);
        if (a < 0.01f) continue;
        float r = rings_[k].rIn + 5.f * s_;
        for (int i = rings_[k].first; i < rings_[k].first + rings_[k].count; i++) {
          const Slot& q = slots_[(size_t)i];
          float pad = std::min((q.a1 - q.a0) * 0.2f, 7.f * s_ / r);
          auto g = arcGeo(c, r, q.a0 + pad, q.a1 - pad);
          p.stroke(g.Get(), mix(st.text, st.accent, 0.4f).withA(0.6f * a), 2.6f * s_, true);
        }
      }
    }
    if (fanSlot_ >= 0 && fan_.x > 0.01f) drawFan(p, bd, alpha);
    if (art) {
      view->layers(p, skin->over, stage, view->units);
      view->layers(p, skin->hub, stage, view->units);
      drawHub(p, bd, alpha);
      view->layers(p, skin->front, stage, view->units);
      drawNames(p);
      view->particles(p, alpha, false);
      p.dc->SetTransform(base);
    } else {
      drawScan(p, alpha);
      drawHub(p, bd, alpha);
      drawNames(p);
      if (view) view->particles(p, alpha, false);
    }
    if (!sparks_.empty()) {
      auto keep = std::move(bits_);
      bits_.clear();
      drawParticles(p, 1.f);
      bits_ = std::move(keep);
    }
  }

 private:
  void drawFan(Painter& p, const Backdrop* bd, float alpha) {
    const Slot& owner = slots_[(size_t)fanSlot_];
    auto& kids = model.items[(size_t)owner.item].kids;
    float f = clampf(fan_.x, 0.f, 1.12f), mid = owner.mid();
    float al = alpha * saturate(f * 1.3f);
    Color acc = mix(st.accent, st.accent2, 0.5f - 0.5f * cosf(mid));
    float half = (fanS1_ - fanS0_) * 0.5f * lerp(0.2f, 1.f, f);
    if (skinned() && !skin->fan.empty()) {
      float* v = view->vars;
      v[vA] = mid * 180.f / kPi;
      v[vSpan] = 2.f * half * 180.f / kPi;
      v[vIn] = f;
      v[vN] = (float)kids.size();
      v[vRingIn] = (fanIn_ - (1.f - f) * 30.f * s_) / s_;
      v[vRingOut] = lerp(fanIn_ + 4.f * s_, fanOut_, f) / s_;
      SkinView::Stage q;
      q.at = env.anchor;
      q.alpha = al;
      q.glass = bd;
      view->layers(p, skin->fan, q, view->units);
    }
    if (!skinned() || skin->ownFan) {
      // rail joining the group to its extension
      auto rail = arcGeo(env.anchor, fanIn_ - gap_ * 0.5f - 1.5f * s_, mid - half + 0.02f, mid + half - 0.02f);
      if (st.glow > 0.01f) p.glow(rail.Get(), acc.withA(0.7f * st.glow * al), 5.f * s_, 3.f * s_);
      p.stroke(rail.Get(), acc.withA(0.85f * al), 2.f * s_, true);
    }
    std::vector<size_t> order;
    for (size_t i = 0; i < fanSlots_.size() && i < kids.size(); i++) order.push_back(i);
    std::sort(order.begin(), order.end(), [&](size_t a, size_t b) { return fanSlots_[a].hot.x < fanSlots_[b].hot.x; });
    for (size_t i : order) {
      const Slot& q = fanSlots_[i];
      float squeeze = lerp(0.30f, 1.f, f);
      Pose z{mid + (q.a0 - mid) * squeeze, mid + (q.a1 - mid) * squeeze, fanIn_ - (1.f - f) * 30.f * s_, lerp(fanIn_ + 4.f * s_, fanOut_, f), lerp(0.4f, 1.f, f), 1.f};
      if (closing) {
        float t = smooth01(closeT / 0.17f), k = launched ? lerp(1.f, launchPick.kid == (int)i ? 1.12f : 1.04f, t) : lerp(1.f, 0.95f, t);
        z.rIn *= k;
        z.rOut *= k;
      }
      Where w;
      w.i = (int)i;
      w.n = (int)kids.size();
      w.beside = saturate(q.hot.x);
      w.mine = closing && launched && launchPick.kid == (int)i;
      drawEntry(p, bd, kids[i], z, q.hot.x, al, icon_ * 0.88f, 0, true, w);
    }
  }
};

}  // namespace

std::unique_ptr<Layout> makeRadial() { return std::make_unique<RadialLayout>(); }

}  // namespace rt
