// Icon treatments: the same icon printed in ink, stamped into metal, bent from neon tube, drawn in pixels ...
#include "icons.h"

namespace rt {

namespace {

struct Plane {
  int n = 0;
  std::vector<float> v;
  explicit Plane(int size, float fill = 0) : n(size), v((size_t)size * size, fill) {}
  float& at(int x, int y) { return v[(size_t)y * n + x]; }
  float get(int x, int y) const { return v[(size_t)clampi(y, 0, n - 1) * n + clampi(x, 0, n - 1)]; }
};

void blur(Plane& p, int r, int times = 2) {
  std::vector<float> row((size_t)p.n);
  for (int t = 0; t < times; t++)
    for (int pass = 0; pass < 2; pass++)
      for (int k = 0; k < p.n; k++) {
        float sum = 0;
        auto ref = [&](int i) -> float& { return pass ? p.at(k, i) : p.at(i, k); };
        for (int i = -r; i <= r; i++) sum += ref(clampi(i, 0, p.n - 1));
        for (int i = 0; i < p.n; i++) {
          row[(size_t)i] = sum / (2 * r + 1);
          sum += ref(std::min(p.n - 1, i + r + 1)) - ref(std::max(0, i - r));
        }
        for (int i = 0; i < p.n; i++) ref(i) = row[(size_t)i];
      }
}

// The visible part of an icon, resampled to n x n: straight colours 0..1 and coverage.
void sample(const IconImage& in, int n, float inset, std::vector<Color>& col) {
  col.assign((size_t)n * n, Color(0, 0, 0, 0));
  float side = in.crop.right - in.crop.left;
  if (side < 1) side = (float)std::min(in.w, in.h);
  float span = n - 2 * inset, step = side / span;
  int taps = clampi((int)ceilf(step), 1, 8);
  for (int y = 0; y < n; y++)
    for (int x = 0; x < n; x++) {
      float r = 0, g = 0, b = 0, a = 0;
      for (int j = 0; j < taps; j++)
        for (int i = 0; i < taps; i++) {
          float sx = in.crop.left + (x - inset + (i + 0.5f) / taps) * step - 0.5f, sy = in.crop.top + (y - inset + (j + 0.5f) / taps) * step - 0.5f;
          int x0 = (int)floorf(sx), y0 = (int)floorf(sy);
          float fx = sx - x0, fy = sy - y0;
          for (int q = 0; q < 4; q++) {
            int px = x0 + (q & 1), py = y0 + (q >> 1);
            if (px < 0 || py < 0 || px >= in.w || py >= in.h) continue;
            if (px < in.crop.left - 1 || py < in.crop.top - 1 || px > in.crop.right || py > in.crop.bottom) continue;
            float w = ((q & 1) ? fx : 1 - fx) * ((q >> 1) ? fy : 1 - fy);
            const uint8_t* s = &in.px[((size_t)py * in.w + px) * 4];
            b += w * s[0];
            g += w * s[1];
            r += w * s[2];
            a += w * s[3];
          }
        }
      float k = 1.f / (taps * taps * 255.f);
      a *= k;
      Color& c = col[(size_t)y * n + x];
      if (a > 0.002f) c = Color(saturate(r * k / a), saturate(g * k / a), saturate(b * k / a), saturate(a));
    }
}

// Stretches brightness over the whole range, unless the icon is all of one tone anyway.
void stretch(const std::vector<Color>& col, Plane& l) {
  float hist[64] = {}, total = 0;
  for (size_t i = 0; i < col.size(); i++) {
    l.v[i] = col[i].luma();
    if (col[i].a > 0.3f) {
      hist[clampi((int)(l.v[i] * 63.f), 0, 63)] += 1;
      total += 1;
    }
  }
  if (total < 1) return;
  auto at = [&](float q) {
    float sum = 0;
    for (int i = 0; i < 64; i++) {
      sum += hist[i];
      if (sum >= q * total) return i / 63.f;
    }
    return 1.f;
  };
  float lo = at(0.04f), hi = at(0.96f);
  if (hi - lo < 0.10f) return;
  for (auto& v : l.v) v = saturate((v - lo) / (hi - lo));
}

void store(IconImage& out, int n, const std::vector<Color>& c) {
  out.w = out.h = n;
  out.px.resize((size_t)n * n * 4);
  out.crop = D2D1::RectF(0, 0, (float)n, (float)n);
  for (size_t i = 0; i < c.size(); i++) {
    float a = saturate(c[i].a);
    out.px[i * 4] = (uint8_t)lroundf(saturate(c[i].b) * a * 255.f);
    out.px[i * 4 + 1] = (uint8_t)lroundf(saturate(c[i].g) * a * 255.f);
    out.px[i * 4 + 2] = (uint8_t)lroundf(saturate(c[i].r) * a * 255.f);
    out.px[i * 4 + 3] = (uint8_t)lroundf(a * 255.f);
  }
}

}  // namespace

bool toneIcon(const IconImage& in, IconTone tone, Color ink, Color paper, IconImage& out) {
  if (in.w < 1 || in.h < 1 || in.px.size() < (size_t)in.w * in.h * 4) return false;
  if (tone == IconTone::Muted || tone == IconTone::Mono) {
    out = in;
    for (size_t i = 0; i + 3 < out.px.size(); i += 4) {
      uint8_t* px = &out.px[i];
      // Premultiplied, so luminance is already scaled by alpha.
      float l = (0.114f * px[0] + 0.587f * px[1] + 0.299f * px[2]);
      if (tone == IconTone::Muted) {
        px[0] = px[1] = px[2] = (uint8_t)clampf(l * 0.95f, 0.f, 255.f);
      } else {
        float a = px[3];
        float v = a > 0 ? 0.35f + 0.65f * (l / a) : 0.f;  // keep dark icons visible
        px[0] = (uint8_t)clampf(ink.b * v * a, 0.f, a);
        px[1] = (uint8_t)clampf(ink.g * v * a, 0.f, a);
        px[2] = (uint8_t)clampf(ink.r * v * a, 0.f, a);
      }
    }
    return true;
  }
  if (tone == IconTone::Pixel) {
    const int n = 24;
    std::vector<Color> c;
    sample(in, n, 0, c);
    for (auto& q : c) {
      q.a = q.a > 0.42f ? 1.f : 0.f;
      auto five = [](float v) { return roundf(saturate(v) * 7.f) / 7.f; };
      Hsv h = toHsv(q);
      h.s = saturate(h.s * 1.15f);
      q = fromHsv(h, q.a);
      q.r = five(q.r);
      q.g = five(q.g);
      q.b = five(q.b);
    }
    store(out, n, c);
    return true;
  }
  if (tone == IconTone::Shadow) {
    const int n = 96;
    std::vector<Color> c;
    sample(in, n, kShadowInset * n, c);
    Plane a(n);
    for (size_t i = 0; i < c.size(); i++) a.v[i] = c[i].a;
    blur(a, 3, 3);
    for (size_t i = 0; i < c.size(); i++) c[i] = Color(1, 1, 1, a.v[i]);
    store(out, n, c);
    return true;
  }
  const int n = 128;
  std::vector<Color> c;
  if (tone == IconTone::Sticker) {
    const float border = 7.f, line = 9.2f;
    sample(in, n, 11.f, c);
    Plane grown(n), edge(n);
    for (int y = 0; y < n; y++)
      for (int x = 0; x < n; x++) {
        float best = 1e9f;
        int R = 11;
        for (int j = -R; j <= R; j++)
          for (int i = -R; i <= R; i++) {
            int px = x + i, py = y + j;
            if (px < 0 || py < 0 || px >= n || py >= n) continue;
            float a = c[(size_t)py * n + px].a;
            if (a < 0.06f) continue;
            float d = sqrtf((float)(i * i + j * j)) + (1.f - a) * 0.9f;
            best = std::min(best, d);
          }
        grown.at(x, y) = saturate(border + 0.5f - best);
        edge.at(x, y) = saturate(line + 0.5f - best);
      }
    std::vector<Color> o((size_t)n * n);
    for (size_t i = 0; i < o.size(); i++) {
      Color base = mix(ink, paper, grown.v[i]);
      float a = edge.v[i];
      o[i] = mix(base, c[i], c[i].a);
      o[i].a = std::max(a, c[i].a);
    }
    store(out, n, o);
    return true;
  }
  sample(in, n, tone == IconTone::Neon ? 5.f : 1.f, c);
  Plane l(n);
  stretch(c, l);
  std::vector<Color> o((size_t)n * n);
  if (tone == IconTone::Duo) {
    for (size_t i = 0; i < o.size(); i++) o[i] = mix(ink, paper, smooth01(l.v[i])).withA(c[i].a);
  } else if (tone == IconTone::Ink) {
    for (size_t i = 0; i < o.size(); i++) {
      float t = l.v[i];
      o[i] = ink.withA(c[i].a * saturate(0.06f + 1.02f * (1.f - t) * (1.f - t * 0.25f)));
    }
  } else if (tone == IconTone::Engrave) {
    // Coverage and brightness become a relief, lit from the upper left.
    Plane h(n), soft(n);
    for (size_t i = 0; i < o.size(); i++) h.v[i] = c[i].a * (0.55f + 0.45f * l.v[i]);
    blur(h, 1, 2);
    soft = h;
    blur(soft, 5, 2);
    for (int y = 0; y < n; y++)
      for (int x = 0; x < n; x++) {
        size_t i = (size_t)y * n + x;
        float gx = h.get(x + 1, y) - h.get(x - 1, y), gy = h.get(x, y + 1) - h.get(x, y - 1);
        float lit = -(gx * 0.62f + gy * 0.78f) * 2.6f;
        float cav = saturate((soft.v[i] - h.v[i]) * 1.6f);
        float base = 0.60f + 0.36f * l.v[i] - 0.35f * cav;
        Color m = mix(paper, ink, saturate(base));
        m = lit > 0 ? mix(m, mix(ink, Color(1, 1, 1), 0.75f), saturate(lit)) : mix(m, mix(paper, Color(0, 0, 0), 0.55f), saturate(-lit));
        o[i] = m.withA(saturate(h.v[i] * 2.6f) * std::max(c[i].a, saturate(h.v[i] * 1.6f)));
      }
  } else {  // Neon: outlines only, with a bright core
    Plane a(n), g(n);
    for (size_t i = 0; i < o.size(); i++) {
      a.v[i] = c[i].a;
      g.v[i] = c[i].a * (0.30f + 0.70f * l.v[i]);
    }
    blur(a, 1, 2);
    blur(g, 1, 2);
    Plane e(n);
    for (int y = 0; y < n; y++)
      for (int x = 0; x < n; x++) {
        auto mag = [&](const Plane& p) {
          float gx = p.get(x + 1, y) - p.get(x - 1, y), gy = p.get(x, y + 1) - p.get(x, y - 1);
          return sqrtf(gx * gx + gy * gy);
        };
        e.at(x, y) = saturate(std::max(mag(a) * 1.9f, mag(g) * 2.3f) - 0.10f);
      }
    Plane core = e, halo = e;
    blur(core, 1, 1);
    blur(halo, 4, 2);
    for (size_t i = 0; i < o.size(); i++) {
      float k = saturate(core.v[i] * 1.7f), w = saturate(core.v[i] * 2.2f - 0.75f);
      o[i] = mix(ink, Color(1, 1, 1), w).withA(saturate(k + halo.v[i] * 0.9f));
    }
  }
  store(out, n, o);
  return true;
}

// The colour somebody would name when asked about the icon.
Color iconColor(const IconImage& in) {
  float best = 0, wsum[12] = {}, r[12] = {}, g[12] = {}, b[12] = {}, gr = 0, gw = 0;
  for (size_t i = 0; i + 3 < in.px.size(); i += 4) {
    float a = in.px[i + 3] / 255.f;
    if (a < 0.4f) continue;
    Color c(saturate(in.px[i + 2] / 255.f / a), saturate(in.px[i + 1] / 255.f / a), saturate(in.px[i] / 255.f / a));
    Hsv h = toHsv(c);
    float w = h.s * h.s * h.v;
    int k = clampi((int)(h.h * 12.f), 0, 11);
    wsum[k] += w;
    r[k] += c.r * w;
    g[k] += c.g * w;
    b[k] += c.b * w;
    gr += c.luma();
    gw += 1;
  }
  int at = -1;
  for (int k = 0; k < 12; k++)
    if (wsum[k] > best) {
      best = wsum[k];
      at = k;
    }
  if (at < 0 || best < gw * 0.015f) {
    float v = gw > 0 ? 0.55f + 0.45f * gr / gw : 0.8f;
    return Color(v, v, v);
  }
  Hsv h = toHsv(Color(r[at] / best, g[at] / best, b[at] / best));
  h.v = std::max(h.v, 0.75f);
  h.s = std::max(h.s, 0.45f);
  return fromHsv(h);
}

}  // namespace rt
