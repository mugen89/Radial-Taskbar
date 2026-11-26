// Screensaver-like motion over the darkened desktop while the wheel is open: digital rain, stars, snow and more.
// Drawn as sprites from one small picture, so thousands of them cost very little.
#pragma once
#include <d2d1_3.h>

#include "gfx.h"
#include "skin.h"

namespace rt {

struct Config;

const std::vector<std::pair<std::string, std::wstring>>& backFxKinds();  // id and name, in the order the settings show them
bool backFxKnown(const std::string& kind);
void backFxDefaults(BackFxSpec& s);                                      // the colours that suit the kind
BackFxSpec backFxFor(const Config& cfg, const Skin* skin);               // what to show now; kind empty: nothing

class BackFx {
 public:
  // w, h: pixels of the surface. s: pixels per point at 100%. centre: where the wheel is, in those pixels.
  bool begin(const BackFxSpec& spec, int w, int h, float s, V2 centre);
  void step(float dt);
  void draw(ID2D1DeviceContext* dc, float fade);
  void end();
  bool active() const { return atlas_ != nullptr; }
  const BackFxSpec& spec() const { return spec_; }

 private:
  struct Mote {
    float x = 0, y = 0, z = 0, vx = 0, vy = 0, size = 1, phase = 0, spin = 0, angle = 0, tone = 0;
  };
  struct Drop {
    float y = 0, v = 0, len = 0;
  };
  float rnd() {
    seed_ ^= seed_ << 13;
    seed_ ^= seed_ >> 17;
    seed_ ^= seed_ << 5;
    return (seed_ & 0xFFFFFF) / 16777216.f;
  }
  float rnd(float a, float b) { return a + (b - a) * rnd(); }
  bool makeAtlas();
  void spawn(Mote& m, bool anywhere);
  void sprite(int cell, float x, float y, float size, Color c, float angle = 0.f);

  BackFxSpec spec_;
  int kind_ = 0, w_ = 0, h_ = 0;
  float s_ = 1, t_ = 0, in_ = 0;
  V2 c_;
  uint32_t seed_ = 0x9E3779B9u;
  ComPtr<ID2D1Bitmap1> atlas_;
  int cellPx_ = 64, atlasCols_ = 8;
  // rain
  int cols_ = 0, rows_ = 0;
  float cell_ = 16;
  std::vector<uint8_t> glyphs_;
  std::vector<Drop> drops_;
  float mutate_ = 0;
  // everything else
  std::vector<Mote> motes_;
  // one frame's sprites
  std::vector<D2D1_RECT_F> dst_;
  std::vector<D2D1_RECT_U> src_;
  std::vector<D2D1_COLOR_F> col_;
  std::vector<D2D1_MATRIX_3X2_F> xf_;
  bool turns_ = false;
  ComPtr<ID2D1SpriteBatch> batch_;
};

}  // namespace rt
