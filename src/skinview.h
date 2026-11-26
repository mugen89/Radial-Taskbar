// Draws a skin: its layers, entries, lettering and particles, for one layout on screen.
#pragma once
#include "gfx.h"
#include "skin.h"
#include "skinart.h"

namespace rt {

class Layout;
struct SceneItem;
struct Backdrop;

struct SkinUnits {
  float wheel = 1, hub = 1, ring = 1, cell = 1, px = 1;
  bool moving = false;   // they change from frame to frame: no reason to make pictures for every step
  float of(SkinUnit u) const {
    switch (u) {
      case SkinUnit::Hub: return hub;
      case SkinUnit::Ring: return ring;
      case SkinUnit::Cell: return cell;
      case SkinUnit::Px: return px;
      default: return wheel;
    }
  }
};

// Where things are, for particles and for the numbers a formula can use.
struct SkinPlace {
  V2 center, spot;
  float wheel = 100, hub = 50, ringIn = 60, ringOut = 100, cell = 30;
  RectF stage;
};

class SkinView {
 public:
  SkinView(const Layout& owner, std::shared_ptr<const Skin> t) : L(owner), skin(std::move(t)) {}
  const Layout& L;
  std::shared_ptr<const Skin> skin;
  mutable float vars[kVarCount] = {};
  bool warm = false;   // only ask for the pictures, draw nothing
  SkinUnits units;

  // Once per frame, before drawing.
  bool tick(float dt, const SkinPlace& at);
  void caption(const std::wstring& title, const std::wstring& sub);
  void hoverChanged(V2 at, float cell);
  void launched(V2 at, float cell, V2 dir);
  void openedNow();

  struct Stage {
    V2 at;
    float alpha = 1;
    float turn = 0;                                // degrees, for layers that turn with their entry
    const SceneItem* item = nullptr;
    const std::function<Geo(float inset)>* shape = nullptr;
    const Backdrop* glass = nullptr;
    float clock = -1;                              // seconds since the entry began to arrive; negative: the layout's time
    bool still = false;                            // no arrival animations
  };
  void layers(Painter& p, const std::vector<SkinLayer>& list, const Stage& s, const SkinUnits& u) const;
  // One entry. `hot` and the rest are in vars already.
  void slot(Painter& p, const SkinSlot& S, const SceneItem& it, const Stage& s, float cell, float iconPx, float iconScale, float hot) const;
  void particles(Painter& p, float alpha, bool behind) const;
  bool panel(Painter& p, const SkinPanel& P, RectF r, float s, float alpha, const Backdrop* glass, const SceneItem* it = nullptr) const;

  ComPtr<ID2D1Brush> panelBrush(Painter& p, const SkinPaint& f, V2 c, V2 half, float alpha) const;

  // How far along the arrival of something is: 0 not yet, 1 in place.
  static float arrived(const SkinIntro& in, float time, float order, float speed);
  static float orderOf(SkinIntro::Order o, int i, int n, float angle, uint32_t seed);
  Color color(const SkinColor& c, const SceneItem* it = nullptr) const;
  bool usesOnly(const std::vector<SkinLayer>& list) const;
  std::wstring expand(const std::wstring& t, const SceneItem* it, bool old = false) const;

 private:
  friend class Layout;
  struct Bit {
    V2 pos, vel;
    float age, life, size, rot, spin, seed;
    int frame;
  };
  struct Emitter {
    const SkinParticles* p;
    std::vector<Bit> bits;
    float owed = 0;
  };
  std::vector<Emitter> emit_, bursts_;
  SkinPlace at_;
  std::wstring title_, sub_, titleOld_, subOld_;
  float swap_ = 1, dt_ = 0;
  mutable uint32_t rng_ = 0x51F15EEDu;
  float rnd() const {
    rng_ ^= rng_ << 13;
    rng_ ^= rng_ >> 17;
    rng_ ^= rng_ << 5;
    return (rng_ & 0xFFFFFF) / 16777216.f;
  }
  float rnd(const float r[2]) const { return lerp(r[0], r[1], rnd()); }
  Bit born(const SkinParticles& q, V2 where, float outAngle) const;
  void burst(const std::vector<SkinParticles>& list, V2 at, float spread, float outAngle);

  struct Put {
    V2 pos;
    float rot = 0, sx = 1, sy = 1, alpha = 1, unit = 1;
    bool moving = false;
  };
  void drawImage(Painter& p, const SkinLayer& y, const Put& q, const Stage& s) const;
  void drawShape(Painter& p, const SkinLayer& y, const Put& q, const Stage& s, const SkinUnits& u) const;
  void drawText(Painter& p, const SkinLayer& y, const Put& q, const Stage& s) const;
  void textLine(Painter& p, const SkinLayer& y, const std::wstring& text, V2 at, float unit, float alpha, const SceneItem* it) const;
  ComPtr<ID2D1Brush> brush(Painter& p, const SkinPaint& f, V2 half, float unit, float alpha, const Stage& s, V2 origin) const;

  struct PixelText {
    std::wstring key;
    ComPtr<ID2D1Bitmap1> bmp;
    float w = 0, h = 0;
    uint32_t used = 0, gen = 0;
  };
  mutable std::vector<PixelText> pixel_;
  struct Grad {
    ComPtr<ID2D1LinearGradientBrush> lin;
    ComPtr<ID2D1RadialGradientBrush> rad;
  };
  mutable std::map<const SkinPaint*, Grad> grads_;
  mutable uint32_t gradGen_ = 0;
  mutable uint32_t frameNo_ = 0;
  mutable int budget_ = 0;  // what a skin may draw in one frame, so that a bad one cannot stall the program
  bool spend(int cost) const { return (budget_ -= cost) > 0; }
};

}  // namespace rt
