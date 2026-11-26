#include "sound.h"

#include "skinart.h"

#include <mmsystem.h>

namespace rt {

namespace {
constexpr int kRate = 32000;

std::vector<uint8_t> makeWav(const std::vector<float>& pcm) {
  std::vector<uint8_t> w(44 + pcm.size() * 2);
  auto u32 = [&](size_t at, uint32_t v) { memcpy(&w[at], &v, 4); };
  auto u16 = [&](size_t at, uint16_t v) { memcpy(&w[at], &v, 2); };
  memcpy(&w[0], "RIFF", 4);
  u32(4, (uint32_t)(w.size() - 8));
  memcpy(&w[8], "WAVEfmt ", 8);
  u32(16, 16);
  u16(20, 1);
  u16(22, 1);
  u32(24, kRate);
  u32(28, kRate * 2);
  u16(32, 2);
  u16(34, 16);
  memcpy(&w[36], "data", 4);
  u32(40, (uint32_t)(pcm.size() * 2));
  for (size_t i = 0; i < pcm.size(); i++) {
    int16_t s = (int16_t)(clampf(pcm[i], -1.f, 1.f) * 32000.f);
    memcpy(&w[44 + i * 2], &s, 2);
  }
  return w;
}

std::vector<uint8_t> synth(Sound s, float vol) {
  float len = s == Sound::Tick ? 0.024f : s == Sound::Open ? 0.13f : s == Sound::Launch ? 0.17f : 0.09f;
  std::vector<float> p((size_t)(len * kRate));
  float ph = 0, ph2 = 0;
  uint32_t r = 0x1234567;
  for (size_t i = 0; i < p.size(); i++) {
    float t = (float)i / kRate, k = t / len;
    r ^= r << 13; r ^= r >> 17; r ^= r << 5;
    float noise = ((r & 0xFFFF) / 32768.f - 1.f);
    float v = 0;
    switch (s) {
      case Sound::Tick: {
        float f = 1900.f - 500.f * k;
        ph += kTau * f / kRate;
        v = (sinf(ph) * 0.45f + noise * 0.12f) * expf(-t * 210.f);
        break;
      }
      case Sound::Open: {
        float f = lerp(240.f, 620.f, k * k);
        ph += kTau * f / kRate;
        v = (sinf(ph) * 0.30f + noise * 0.10f * (1 - k)) * sinf(kPi * k) * 0.8f;
        break;
      }
      case Sound::Launch: {
        ph += kTau * 660.f / kRate;
        ph2 += kTau * 990.f / kRate;
        v = sinf(ph) * 0.32f * expf(-t * 26.f) + (t > 0.045f ? sinf(ph2) * 0.30f * expf(-(t - 0.045f) * 28.f) : 0.f);
        break;
      }
      default: {
        float f = lerp(420.f, 180.f, k);
        ph += kTau * f / kRate;
        v = sinf(ph) * 0.24f * sinf(kPi * k);
        break;
      }
    }
    p[i] = v * vol;
  }
  return makeWav(p);
}
}  // namespace

// Scales 16-bit samples; anything else is played as it is.
static std::vector<uint8_t> scaled(const std::string& wav, float volume) {
  std::vector<uint8_t> w(wav.begin(), wav.end());
  size_t at = 12;
  bool sixteen = false;
  while (at + 8 <= w.size()) {
    uint32_t n;
    memcpy(&n, &w[at + 4], 4);
    if (n > w.size() - at - 8) break;
    if (!memcmp(&w[at], "fmt ", 4) && n >= 16) {
      uint16_t tag, bits;
      memcpy(&tag, &w[at + 8], 2);
      memcpy(&bits, &w[at + 22], 2);
      sixteen = tag == 1 && bits == 16;
    } else if (!memcmp(&w[at], "data", 4) && sixteen) {
      for (size_t i = at + 8; i + 2 <= at + 8 + n; i += 2) {
        int16_t v;
        memcpy(&v, &w[i], 2);
        v = (int16_t)lroundf(v * volume);
        memcpy(&w[i], &v, 2);
      }
      return w;
    }
    at += 8 + n + (n & 1);
  }
  return w;
}

void playSound(Sound s, float volume) {
  static const char* const names[] = {"open", "move", "launch", "close", "profile"};
  static std::vector<uint8_t> cache[5];
  static float madeFor[5] = {-1, -1, -1, -1, -1};
  static const Skin* skinFor[5] = {};
  int i = (int)s;
  const Skin* now = skinArt().skin();
  if (madeFor[i] != volume || skinFor[i] != now) {
    PlaySoundW(nullptr, nullptr, 0);  // the old buffer must not be playing while it is replaced
    std::string wav;
    if (skinArt().sound(names[i], wav) || (s == Sound::Profile && skinArt().sound("move", wav))) cache[i] = scaled(wav, volume);
    else cache[i] = synth(s == Sound::Profile ? Sound::Tick : s, volume);
    madeFor[i] = volume;
    skinFor[i] = now;
  }
  PlaySoundW((LPCWSTR)cache[i].data(), nullptr, SND_MEMORY | SND_ASYNC | SND_NODEFAULT | SND_NOWAIT);
}

}  // namespace rt
