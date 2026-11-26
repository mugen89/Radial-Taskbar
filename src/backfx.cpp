#include "backfx.h"

#include <d2d1_3.h>

#include "config.h"

namespace rt {

namespace {
enum Kind { kNone, kRain, kStars, kSnow, kFireflies, kEmbers, kBubbles, kPetals, kBats };
struct KindInfo {
  const char* id;
  const wchar_t* name;
  uint32_t c1, c2;
  int count;  // motes at density 1
};
const KindInfo kKinds[] = {{"rain", L"Digital rain", 0x3DFF7A, 0xE9FFF0, 0},  {"stars", L"Starfield", 0x9FC8FF, 0xFFFFFF, 420}, {"snow", L"Snowfall", 0xFFFFFF, 0xDDEBFF, 260},
                           {"fireflies", L"Fireflies", 0xD8FF6A, 0xFFF3A0, 90}, {"embers", L"Embers", 0xFF7A1A, 0xFFD35A, 170},  {"bubbles", L"Bubbles", 0xBFE8FF, 0xFFFFFF, 70},
                           {"petals", L"Petals", 0xFFB7D2, 0xFFE6F0, 90},    {"bats", L"Bats", 0x3A1330, 0x5A1D47, 14}};
constexpr int kKindCount = (int)(sizeof kKinds / sizeof kKinds[0]);
int kindOf(const std::string& s) {
  for (int i = 0; i < kKindCount; i++)
    if (s == kKinds[i].id) return i + 1;
  return kNone;
}
enum Cell { cDot, cCore, cRing, cPetal, cBatA, cBatB, cFlake, cCellCount };
// Signs for the rain: digits, letters and symbols, nothing borrowed from a film.
const wchar_t kGlyphs[] = L"0123456789ABCDEFHJKLMNPRSTUVXYZ+-*=<>:;|~^%$#@&?{}[]/\\\x03BB\x03A3\x03A9\x0394\x039E\x03A0\x03A6\x03A8\x0398\x0393";
constexpr int kGlyphCount = (int)(sizeof kGlyphs / sizeof kGlyphs[0]) - 1;
}  // namespace

const std::vector<std::pair<std::string, std::wstring>>& backFxKinds() {
  static const std::vector<std::pair<std::string, std::wstring>> v = [] {
    std::vector<std::pair<std::string, std::wstring>> r;
    for (auto& k : kKinds) r.push_back({k.id, k.name});
    return r;
  }();
  return v;
}

bool backFxKnown(const std::string& kind) { return kindOf(kind) != kNone; }

void backFxDefaults(BackFxSpec& s) {
  int k = kindOf(s.kind);
  if (!k) return;
  s.color = Color::hex(kKinds[k - 1].c1);
  s.color2 = Color::hex(kKinds[k - 1].c2);
}

BackFxSpec backFxFor(const Config& cfg, const Skin* skin) {
  if (!cfg.backFx || cfg.backFxKind == "none") return {};
  if (cfg.backFxKind.empty() || cfg.backFxKind == "skin") return skin ? skin->screen : BackFxSpec{};
  BackFxSpec s;
  s.kind = cfg.backFxKind;
  if (!backFxKnown(s.kind)) return {};
  backFxDefaults(s);
  return s;
}

// ---------------------------------------------------------------- the picture all sprites come from
bool BackFx::makeAtlas() {
  auto& g = gfx();
  if (!g.aux) return false;
  int n = kind_ == kRain ? kGlyphCount : cCellCount;
  cellPx_ = kind_ == kRain ? std::max(8, (int)ceilf(cell_)) : 64;
  atlasCols_ = 8;
  int rows = (n + atlasCols_ - 1) / atlasCols_;
  atlas_ = g.target(cellPx_ * atlasCols_, cellPx_ * rows);
  if (!atlas_) return false;
  ID2D1DeviceContext* dc = g.aux.Get();
  dc->SetTarget(atlas_.Get());
  dc->SetDpi(96, 96);
  dc->BeginDraw();
  dc->SetTransform(D2D1::Matrix3x2F::Identity());
  dc->Clear(D2D1::ColorF(0, 0, 0, 0));
  ComPtr<ID2D1SolidColorBrush> white;
  dc->CreateSolidColorBrush(D2D1::ColorF(1, 1, 1, 1), &white);
  float P = (float)cellPx_;
  auto at = [&](int i) { return D2D1::Point2F((i % atlasCols_) * P, (i / atlasCols_) * P); };
  if (kind_ == kRain) {
    TextStyle ts;
    ts.family = L"Consolas";
    ts.size = P * 0.84f;
    ts.weight = 700;
    ts.align = Align::Center;
    ts.valign = VAlign::Middle;
    ts.ellipsis = false;
    for (int i = 0; i < n && white; i++) {
      wchar_t ch[2] = {kGlyphs[i], 0};
      if (auto l = g.layout(ch, ts, P, P)) dc->DrawTextLayout(at(i), l.Get(), white.Get(), D2D1_DRAW_TEXT_OPTIONS_NONE);
    }
  } else if (white) {
    auto radial = [&](int i, float core, float edge) {
      D2D1_GRADIENT_STOP st[3] = {{0.f, D2D1::ColorF(1, 1, 1, 1)}, {core, D2D1::ColorF(1, 1, 1, 0.55f)}, {1.f, D2D1::ColorF(1, 1, 1, 0)}};
      ComPtr<ID2D1GradientStopCollection> sc;
      dc->CreateGradientStopCollection(st, 3, &sc);
      ComPtr<ID2D1RadialGradientBrush> b;
      D2D1_POINT_2F c = at(i);
      c.x += P / 2;
      c.y += P / 2;
      if (sc) dc->CreateRadialGradientBrush(D2D1::RadialGradientBrushProperties(c, {0, 0}, P / 2 * edge, P / 2 * edge), sc.Get(), &b);
      if (b) dc->FillEllipse(D2D1::Ellipse(c, P / 2, P / 2), b.Get());
    };
    radial(cDot, 0.25f, 1.f);
    radial(cCore, 0.55f, 0.55f);
    {  // a bubble: a thin ring and a gleam
      D2D1_POINT_2F c = at(cRing);
      c.x += P / 2;
      c.y += P / 2;
      white->SetOpacity(0.85f);
      dc->DrawEllipse(D2D1::Ellipse(c, P * 0.44f, P * 0.44f), white.Get(), P * 0.045f);
      white->SetOpacity(0.18f);
      dc->FillEllipse(D2D1::Ellipse(c, P * 0.42f, P * 0.42f), white.Get());
      white->SetOpacity(0.9f);
      dc->FillEllipse(D2D1::Ellipse(D2D1::Point2F(c.x - P * 0.17f, c.y - P * 0.17f), P * 0.08f, P * 0.05f), white.Get());
      white->SetOpacity(1.f);
    }
    auto shape = [&](int i, const std::vector<V2>& pts, bool curve) {
      ComPtr<ID2D1PathGeometry> geo;
      g.d2d->CreatePathGeometry(&geo);
      ComPtr<ID2D1GeometrySink> s;
      if (!geo || FAILED(geo->Open(&s))) return;
      D2D1_POINT_2F o = at(i);
      auto pt = [&](V2 v) { return D2D1::Point2F(o.x + P / 2 + v.x * P / 2, o.y + P / 2 + v.y * P / 2); };
      s->BeginFigure(pt(pts[0]), D2D1_FIGURE_BEGIN_FILLED);
      if (curve)
        for (size_t k = 1; k + 2 < pts.size(); k += 3) s->AddBezier(D2D1::BezierSegment(pt(pts[k]), pt(pts[k + 1]), pt(pts[k + 2])));
      else
        for (size_t k = 1; k < pts.size(); k++) s->AddLine(pt(pts[k]));
      s->EndFigure(D2D1_FIGURE_END_CLOSED);
      s->Close();
      dc->FillGeometry(geo.Get(), white.Get());
    };
    shape(cPetal, {{0, -0.92f}, {0.62f, -0.55f}, {0.55f, 0.45f}, {0, 0.9f}, {-0.55f, 0.45f}, {-0.62f, -0.55f}, {0, -0.92f}}, true);
    // a bat, wings up and wings down
    shape(cBatA, {{0, -0.18f}, {0.12f, -0.34f}, {0.18f, -0.18f}, {0.55f, -0.62f}, {0.98f, -0.40f}, {0.78f, -0.20f}, {0.70f, 0.02f}, {0.48f, -0.06f}, {0.36f, 0.12f}, {0.16f, 0.06f},
                  {0, 0.26f}, {-0.16f, 0.06f}, {-0.36f, 0.12f}, {-0.48f, -0.06f}, {-0.70f, 0.02f}, {-0.78f, -0.20f}, {-0.98f, -0.40f}, {-0.55f, -0.62f}, {-0.18f, -0.18f}, {-0.12f, -0.34f}},
          false);
    shape(cBatB, {{0, -0.16f}, {0.12f, -0.30f}, {0.18f, -0.12f}, {0.50f, 0.02f}, {0.95f, 0.30f}, {0.70f, 0.32f}, {0.62f, 0.50f}, {0.42f, 0.34f}, {0.30f, 0.46f}, {0.14f, 0.20f},
                  {0, 0.34f}, {-0.14f, 0.20f}, {-0.30f, 0.46f}, {-0.42f, 0.34f}, {-0.62f, 0.50f}, {-0.70f, 0.32f}, {-0.95f, 0.30f}, {-0.50f, 0.02f}, {-0.18f, -0.12f}, {-0.12f, -0.30f}},
          false);
    {  // a snowflake
      D2D1_POINT_2F c = at(cFlake);
      c.x += P / 2;
      c.y += P / 2;
      ComPtr<ID2D1StrokeStyle> round;
      g.d2d->CreateStrokeStyle(D2D1::StrokeStyleProperties(D2D1_CAP_STYLE_ROUND, D2D1_CAP_STYLE_ROUND, D2D1_CAP_STYLE_ROUND), nullptr, 0, &round);
      for (int k = 0; k < 6; k++) {
        float a = k * kTau / 6, ca = cosf(a), sa = sinf(a), r = P * 0.44f;
        dc->DrawLine(c, D2D1::Point2F(c.x + sa * r, c.y - ca * r), white.Get(), P * 0.07f, round.Get());
        for (float side : {-1.f, 1.f}) {
          float b = a + side * 0.6f, m = r * 0.55f;
          D2D1_POINT_2F from = D2D1::Point2F(c.x + sa * m, c.y - ca * m);
          dc->DrawLine(from, D2D1::Point2F(from.x + sinf(b) * r * 0.3f, from.y - cosf(b) * r * 0.3f), white.Get(), P * 0.05f, round.Get());
        }
      }
    }
  }
  HRESULT hr = dc->EndDraw();
  dc->SetTarget(nullptr);
  return SUCCEEDED(hr);
}

// ---------------------------------------------------------------- motion
bool BackFx::begin(const BackFxSpec& spec, int w, int h, float s, V2 centre) {
  end();
  spec_ = spec;
  kind_ = kindOf(spec.kind);
  if (!kind_ || w < 16 || h < 16) return false;
  w_ = w;
  h_ = h;
  s_ = clampf(s, 0.25f, 6.f);
  c_ = centre;
  t_ = in_ = mutate_ = 0;
  seed_ = 0x9E3779B9u ^ (uint32_t)GetTickCount();
  float d = clampf(spec.density, 0.1f, 4.f);
  if (kind_ == kRain) cell_ = std::max(8.f, roundf(17.f * clampf(spec.size, 0.3f, 3.f) * s_));
  if (!makeAtlas()) {
    end();
    return false;
  }
  if (kind_ == kRain) {
    cols_ = (int)ceilf(w_ / cell_);
    rows_ = (int)ceilf(h_ / cell_) + 1;
    glyphs_.resize((size_t)cols_ * rows_);
    for (auto& gl : glyphs_) gl = (uint8_t)(rnd() * kGlyphCount);
    drops_.assign((size_t)cols_, Drop{});
    for (auto& dr : drops_) {
      dr.v = rnd(7.f, 24.f) * clampf(spec_.speed, 0.1f, 4.f);
      dr.len = rnd(6.f, 30.f);
      dr.y = rnd(-rows_ * 1.4f / d, rows_ * 1.2f);
    }
  } else {
    int n = std::min(2400, (int)(kKinds[kind_ - 1].count * d));
    motes_.assign((size_t)std::max(1, n), Mote{});
    for (auto& m : motes_) spawn(m, true);
  }
  return true;
}

void BackFx::spawn(Mote& m, bool anywhere) {
  float sp = clampf(spec_.speed, 0.1f, 4.f), sz = clampf(spec_.size, 0.3f, 3.f);
  m.phase = rnd(0, kTau);
  m.tone = rnd();
  m.angle = rnd(0, kTau);
  switch (kind_) {
    case kStars: {
      float a = rnd(0, kTau), r = rnd(0.03f, 1.f);
      m.x = sinf(a) * r;
      m.y = cosf(a) * r;
      m.z = anywhere ? rnd(0.08f, 1.f) : 1.f;
      break;
    }
    case kSnow:
      m.size = rnd(1.5f, 5.5f) * sz * s_;
      m.x = rnd(0, (float)w_);
      m.y = anywhere ? rnd(0, (float)h_) : -rnd(5, 40) * s_;
      m.vy = rnd(22, 55) * sp * s_ * (0.6f + m.size / (5.5f * sz * s_));
      m.vx = rnd(-8, 8) * s_;
      m.spin = rnd(-1, 1);
      break;
    case kFireflies:
      m.size = rnd(6, 12) * sz * s_;
      m.x = rnd(0, (float)w_);
      m.y = rnd(0, (float)h_);
      m.vx = rnd(14, 38) * sp * s_;
      break;
    case kEmbers:
      m.size = rnd(2.6f, 6.f) * sz * s_;
      m.x = rnd(0, (float)w_);
      m.y = anywhere ? rnd(0, (float)h_) : h_ + rnd(0, 60) * s_;
      m.vy = rnd(35, 120) * sp * s_;
      m.vx = rnd(-10, 10) * s_;
      break;
    case kBubbles:
      m.size = rnd(8, 30) * sz * s_;
      m.x = rnd(0, (float)w_);
      m.y = anywhere ? rnd(0, (float)h_) : h_ + m.size + rnd(0, 80) * s_;
      m.vy = rnd(25, 60) * sp * s_ * (0.8f + 6.f * s_ / m.size);
      break;
    case kPetals:
      m.size = rnd(8, 17) * sz * s_;
      m.x = anywhere ? rnd(0, (float)w_) : rnd(-w_ * 0.3f, (float)w_);
      m.y = anywhere ? rnd(0, (float)h_) : -rnd(10, 80) * s_;
      m.vx = rnd(15, 55) * sp * s_;
      m.vy = rnd(30, 70) * sp * s_;
      m.spin = rnd(-1.8f, 1.8f);
      break;
    case kBats: {
      m.size = rnd(26, 58) * sz * s_;
      bool fromLeft = rnd() < 0.5f;
      m.vx = rnd(70, 160) * sp * s_ * (fromLeft ? 1.f : -1.f);
      m.x = anywhere ? rnd(0, (float)w_) : fromLeft ? -m.size * 2 : w_ + m.size * 2;
      m.y = rnd(h_ * 0.08f, h_ * 0.78f);
      break;
    }
    default: break;
  }
}

void BackFx::step(float dt) {
  if (!active()) return;
  dt = clampf(dt, 0.f, 0.05f);
  t_ += dt;
  in_ = std::min(1.f, in_ + dt * 2.5f);
  float W = (float)w_, H = (float)h_;
  switch (kind_) {
    case kRain: {
      float d = clampf(spec_.density, 0.1f, 4.f);
      for (auto& dr : drops_) {
        dr.y += dr.v * dt;
        if (dr.y - dr.len > rows_) {
          dr.v = rnd(7.f, 24.f) * clampf(spec_.speed, 0.1f, 4.f);
          dr.len = rnd(6.f, 30.f);
          dr.y = -rnd(0.f, rows_ * 0.9f / d);
        }
      }
      mutate_ += dt * cols_ * rows_ * 0.03f;  // some signs change all the time
      while (mutate_ >= 1.f && !glyphs_.empty()) {
        mutate_ -= 1.f;
        glyphs_[(size_t)(rnd() * glyphs_.size()) % glyphs_.size()] = (uint8_t)(rnd() * kGlyphCount);
      }
      break;
    }
    case kStars:
      for (auto& m : motes_) {
        m.z -= dt * 0.22f * clampf(spec_.speed, 0.1f, 4.f);
        if (m.z <= 0.03f) spawn(m, false);
      }
      break;
    case kSnow:
      for (auto& m : motes_) {
        m.y += m.vy * dt;
        m.x += (m.vx + sinf(t_ * 0.8f + m.phase) * 14.f * s_) * dt;
        m.angle += m.spin * dt;
        if (m.y > H + 20 * s_) spawn(m, false);
        if (m.x < -20 * s_) m.x += W + 40 * s_;
        if (m.x > W + 20 * s_) m.x -= W + 40 * s_;
      }
      break;
    case kFireflies:
      for (auto& m : motes_) {
        m.angle += (rnd() - 0.5f) * 3.f * dt * 10.f;
        m.x += sinf(m.angle) * m.vx * dt;
        m.y -= cosf(m.angle) * m.vx * dt;
        if (m.x < 0) m.x += W;
        if (m.x > W) m.x -= W;
        if (m.y < 0) m.y += H;
        if (m.y > H) m.y -= H;
      }
      break;
    case kEmbers:
      for (auto& m : motes_) {
        m.y -= m.vy * dt;
        m.x += (sinf(t_ * 1.3f + m.phase) * 18.f * s_ + m.vx) * dt;
        if (m.y < -20 * s_) spawn(m, false);
      }
      break;
    case kBubbles:
      for (auto& m : motes_) {
        m.y -= m.vy * dt;
        m.x += sinf(t_ * 1.7f + m.phase) * 10.f * s_ * dt;
        if (m.y < -m.size) spawn(m, false);
      }
      break;
    case kPetals:
      for (auto& m : motes_) {
        m.x += (m.vx + sinf(t_ + m.phase) * 12.f * s_) * dt;
        m.y += m.vy * dt;
        m.angle += m.spin * dt;
        if (m.y > H + m.size || m.x > W + m.size * 2) spawn(m, false);
      }
      break;
    case kBats:
      for (auto& m : motes_) {
        m.x += m.vx * dt;
        m.y += sinf(t_ * 2.2f + m.phase) * 24.f * s_ * dt;
        if ((m.vx > 0 && m.x > W + m.size * 2) || (m.vx < 0 && m.x < -m.size * 2)) spawn(m, false);
      }
      break;
    default: break;
  }
}

void BackFx::sprite(int cell, float x, float y, float size, Color c, float angle) {
  float h = size * 0.5f;
  dst_.push_back(D2D1::RectF(x - h, y - h, x + h, y + h));
  UINT32 cx = (UINT32)((cell % atlasCols_) * cellPx_), cy = (UINT32)((cell / atlasCols_) * cellPx_);
  src_.push_back(D2D1::RectU(cx, cy, cx + (UINT32)cellPx_, cy + (UINT32)cellPx_));
  float a = clampf(c.a, 0.f, 1.f);
  col_.push_back(D2D1::ColorF(c.r * a, c.g * a, c.b * a, a));  // the picture is premultiplied, so is the tint
  if (turns_) xf_.push_back(angle != 0.f ? D2D1::Matrix3x2F::Rotation(angle * 57.29578f, D2D1::Point2F(x, y)) : D2D1::Matrix3x2F::Identity());
}

void BackFx::draw(ID2D1DeviceContext* dc, float fade) {
  if (!active() || !dc) return;
  float a = clampf(fade, 0.f, 1.f) * in_;
  if (a <= 0.003f) return;
  dst_.clear();
  src_.clear();
  col_.clear();
  xf_.clear();
  turns_ = kind_ == kPetals || kind_ == kSnow;
  Color c1 = spec_.color, c2 = spec_.color2;
  switch (kind_) {
    case kRain:
      for (int c = 0; c < cols_; c++) {
        const Drop& dr = drops_[(size_t)c];
        int head = (int)floorf(dr.y);
        for (int k = 0; k <= (int)dr.len; k++) {
          int r = head - k;
          if (r < 0 || r >= rows_) continue;
          float f = k == 0 ? 1.f : powf(1.f - k / dr.len, 1.5f) * 0.9f;
          Color col = k == 0 ? c2 : k == 1 ? mix(c2, c1, 0.5f) : c1;
          sprite(glyphs_[(size_t)c * rows_ + r], (c + 0.5f) * cell_, (r + 0.5f) * cell_, cell_, col.withA(col.a * f * a));
        }
      }
      break;
    case kStars:
      for (auto& m : motes_) {
        float px = c_.x + m.x / m.z * w_ * 0.18f, py = c_.y + m.y / m.z * w_ * 0.18f;
        if (px < -12 || px > w_ + 12 || py < -12 || py > h_ + 12) {
          m.z = 0.f;  // gone past the edge: a new one next time
          continue;
        }
        float k = clampf((1.f - m.z) * 1.5f, 0.f, 1.f), size = (0.9f + (1.f - m.z) * 3.6f) * clampf(spec_.size, 0.3f, 3.f) * s_;
        sprite(cDot, px, py, size * 2.6f, mix(c1, c2, m.tone).withA(k * a));
      }
      break;
    case kSnow:
      for (auto& m : motes_) sprite(m.size > 4.2f * s_ ? cFlake : cDot, m.x, m.y, m.size * 2.2f, mix(c1, c2, m.tone).withA((0.55f + 0.45f * m.tone) * a), m.angle);
      break;
    case kFireflies:
      for (auto& m : motes_) {
        float blink = powf(0.5f + 0.5f * sinf(t_ * (1.1f + m.tone) + m.phase), 3.f);
        sprite(cDot, m.x, m.y, m.size * 4.5f, c1.withA(0.6f * blink * a));
        sprite(cCore, m.x, m.y, m.size * 1.3f, c2.withA(blink * a));
      }
      break;
    case kEmbers:
      for (auto& m : motes_) {
        float life = clampf(m.y / h_ * 1.4f, 0.f, 1.f), flick = 0.6f + 0.4f * sinf(t_ * 9.f + m.phase * 3.f);
        Color c = mix(c1, c2, m.tone);
        sprite(cDot, m.x, m.y, m.size * 3.8f, c.withA(0.7f * life * flick * a));
        sprite(cCore, m.x, m.y, m.size, mix(c, Color(1, 1, 1), 0.35f).withA(life * flick * a));
      }
      break;
    case kBubbles:
      for (auto& m : motes_) sprite(cRing, m.x, m.y, m.size, mix(c1, c2, m.tone).withA((0.5f + 0.35f * m.tone) * a));
      break;
    case kPetals:
      for (auto& m : motes_) sprite(cPetal, m.x, m.y, m.size, mix(c1, c2, m.tone).withA(0.85f * a), m.angle);
      break;
    case kBats:
      for (auto& m : motes_) {
        bool up = fmodf(t_ * 7.f + m.phase, 2.f) < 1.f;
        sprite(up ? cBatA : cBatB, m.x, m.y, m.size, mix(c1, c2, m.tone).withA(0.92f * a));
      }
      break;
    default: break;
  }
  if (dst_.empty()) return;
  ComPtr<ID2D1DeviceContext3> dc3;
  if (FAILED(dc->QueryInterface(__uuidof(ID2D1DeviceContext3), (void**)dc3.GetAddressOf())) || !dc3) return;
  if (!batch_) dc3->CreateSpriteBatch(&batch_);
  if (!batch_) return;
  batch_->Clear();
  if (FAILED(batch_->AddSprites((UINT32)dst_.size(), dst_.data(), src_.data(), col_.data(), turns_ ? xf_.data() : nullptr, sizeof(D2D1_RECT_F), sizeof(D2D1_RECT_U), sizeof(D2D1_COLOR_F),
                                sizeof(D2D1_MATRIX_3X2_F))))
    return;
  bool adds = kind_ == kFireflies || kind_ == kEmbers || kind_ == kStars;  // light adds up
  D2D1_ANTIALIAS_MODE was = dc3->GetAntialiasMode();
  dc3->SetAntialiasMode(D2D1_ANTIALIAS_MODE_ALIASED);  // sprites ask for it
  if (adds) dc3->SetPrimitiveBlend(D2D1_PRIMITIVE_BLEND_ADD);
  dc3->DrawSpriteBatch(batch_.Get(), 0, (UINT32)dst_.size(), atlas_.Get(), D2D1_BITMAP_INTERPOLATION_MODE_LINEAR, D2D1_SPRITE_OPTIONS_NONE);
  if (adds) dc3->SetPrimitiveBlend(D2D1_PRIMITIVE_BLEND_SOURCE_OVER);
  dc3->SetAntialiasMode(was);
}

void BackFx::end() {
  atlas_.Reset();
  batch_.Reset();
  glyphs_.clear();
  drops_.clear();
  motes_.clear();
  std::vector<D2D1_RECT_F>().swap(dst_);
  std::vector<D2D1_RECT_U>().swap(src_);
  std::vector<D2D1_COLOR_F>().swap(col_);
  std::vector<D2D1_MATRIX_3X2_F>().swap(xf_);
  kind_ = kNone;
}

}  // namespace rt
