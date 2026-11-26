// Built-in looks. Each one changes shape, material and motion as well as colour.
#include "config.h"

namespace rt {

const std::vector<Look>& builtinLooks() {
  static std::vector<Look> all = [] {
    std::vector<Look> v;
    auto add = [&](const char* id, const wchar_t* name, const wchar_t* group, const wchar_t* blurb, auto fn) {
      Look k;
      k.id = id;
      k.name = name;
      k.group = group;
      k.blurb = blurb;
      k.style = Style{};
      fn(k.style);
      k.style.look = id;
      v.push_back(std::move(k));
    };

    // ------------------------------------------------ Stylized
    add("glass", L"Midnight Glass", L"Stylized", L"Dark frosted glass", [](Style& s) {
      s.rim = RimStyle::Off;
    });
    add("liquid", L"Liquid", L"Stylized", L"Clear glass that bends the desktop", [](Style& s) {
      s.material = Material::Liquid;
      s.base = Color::hex(0x1B2430);
      s.accent = Color::hex(0x9FD8FF);
      s.accent2 = Color::hex(0xFFFFFF);
      s.border = Color::hex(0xFFFFFF);
      s.opacity = 0.20f;
      s.blur = 5.f;
      s.refraction = 0.75f;
      s.corner = 22.f;
      s.gap = 8.f;
      s.borderWidth = 1.4f;
      s.borderOpacity = 0.5f;
      s.glow = 0.35f;
      s.hoverGrow = 14.f;
      s.dim = 0.18f;
      s.tilt = 0.5f;
    });
    add("aurora", L"Aurora", L"Stylized", L"Teal to violet with a moving rim", [](Style& s) {
      s.base = Color::hex(0x0B1220);
      s.accent = Color::hex(0x2DE2C5);
      s.accent2 = Color::hex(0x8E5BFF);
      s.opacity = 0.58f;
      s.blur = 34.f;
      s.rim = RimStyle::Spin;
      s.glow = 0.75f;
      s.open = OpenAnim::Unfold;
      s.particles = Particles::Stars;
    });
    add("petal", L"Petal", L"Stylized", L"Soft petals, warm light", [](Style& s) {
      s.shape = SlotShape::Petal;
      s.base = Color::hex(0x2A1526);
      s.accent = Color::hex(0xFF7EB6);
      s.accent2 = Color::hex(0xFFC27E);
      s.text = Color::hex(0xFFF3F8);
      s.opacity = 0.6f;
      s.blur = 30.f;
      s.corner = 18.f;
      s.gap = 5.f;
      s.open = OpenAnim::Bloom;
      s.hoverGrow = 16.f;
      s.glow = 0.55f;
    });

    // ------------------------------------------------ Gamey
    add("tactical", L"Tactical", L"Gamey", L"Amber HUD, cut corners, tick ring", [](Style& s) {
      s.shape = SlotShape::Blade;
      s.material = Material::Outline;
      s.base = Color::hex(0x0C0F0E);
      s.accent = Color::hex(0xFFB02E);
      s.accent2 = Color::hex(0xFF7A1A);
      s.text = Color::hex(0xFFE9C7);
      s.border = Color::hex(0xFFC66B);
      s.opacity = 0.74f;
      s.blur = 0.f;
      s.corner = 12.f;
      s.gap = 7.f;
      s.borderWidth = 1.3f;
      s.borderOpacity = 0.42f;
      s.tone = IconTone::Muted;
      s.font = "Bahnschrift";
      s.open = OpenAnim::Spin;
      s.speed = 1.2f;
      s.hoverGrow = 10.f;
      s.iconZoom = 1.16f;
      s.glow = 0.5f;
      s.ticks = true;
      s.scan = true;
      s.dim = 0.42f;
      s.tilt = 0.25f;
    });
    add("neon", L"Neon Arcade", L"Gamey", L"Cyan and magenta tubes", [](Style& s) {
      s.material = Material::Outline;
      s.base = Color::hex(0x07060F);
      s.accent = Color::hex(0x19E6FF);
      s.accent2 = Color::hex(0xFF2E9A);
      s.text = Color::hex(0xEAFBFF);
      s.border = Color::hex(0x19E6FF);
      s.opacity = 0.72f;
      s.blur = 0.f;
      s.corner = 16.f;
      s.gap = 8.f;
      s.borderWidth = 1.8f;
      s.borderOpacity = 0.6f;
      s.font = "Bahnschrift";
      s.open = OpenAnim::Unfold;
      s.glow = 1.f;
      s.rim = RimStyle::Spin;
      s.pulse = true;
      s.dim = 0.5f;
      s.hoverGrow = 14.f;
    });
    add("hexcore", L"Hex Core", L"Gamey", L"Sci-fi hexagon slots", [](Style& s) {
      s.shape = SlotShape::Hex;
      s.material = Material::Frosted;
      s.base = Color::hex(0x06151B);
      s.accent = Color::hex(0x21F3C2);
      s.accent2 = Color::hex(0x1FA2FF);
      s.text = Color::hex(0xE2FFF8);
      s.border = Color::hex(0x5CFFE0);
      s.opacity = 0.66f;
      s.blur = 18.f;
      s.corner = 6.f;
      s.gap = 8.f;
      s.borderWidth = 1.4f;
      s.borderOpacity = 0.4f;
      s.font = "Bahnschrift";
      s.open = OpenAnim::Zoom;
      s.ticks = true;
      s.glow = 0.7f;
      s.hoverGrow = 12.f;
      s.iconZoom = 1.18f;
      s.dim = 0.38f;
    });
    add("arcane", L"Arcane", L"Gamey", L"Spell orbs on a golden orbit", [](Style& s) {
      s.shape = SlotShape::Orb;
      s.material = Material::Frosted;
      s.base = Color::hex(0x1A0F2E);
      s.accent = Color::hex(0xC58BFF);
      s.accent2 = Color::hex(0xFFD27A);
      s.text = Color::hex(0xFBF3FF);
      s.border = Color::hex(0xFFD9A0);
      s.opacity = 0.66f;
      s.blur = 22.f;
      s.gap = 8.f;
      s.borderWidth = 1.6f;
      s.borderOpacity = 0.5f;
      s.font = "Georgia";
      s.open = OpenAnim::Spin;
      s.ticks = true;
      s.particles = Particles::Stars;
      s.rim = RimStyle::Solid;
      s.glow = 0.85f;
      s.hoverGrow = 14.f;
      s.dim = 0.4f;
    });
    add("inferno", L"Inferno", L"Gamey", L"Black steel, ember sparks", [](Style& s) {
      s.shape = SlotShape::Blade;
      s.material = Material::Solid;
      s.base = Color::hex(0x120907);
      s.accent = Color::hex(0xFF5A1F);
      s.accent2 = Color::hex(0xFFC23D);
      s.text = Color::hex(0xFFEFE3);
      s.border = Color::hex(0xFF7A3D);
      s.opacity = 0.88f;
      s.blur = 0.f;
      s.corner = 14.f;
      s.gap = 5.f;
      s.borderWidth = 1.2f;
      s.borderOpacity = 0.28f;
      s.font = "Bahnschrift";
      s.open = OpenAnim::Bloom;
      s.speed = 1.15f;
      s.particles = Particles::Embers;
      s.glow = 0.85f;
      s.hoverGrow = 16.f;
      s.dim = 0.45f;
    });

    // ------------------------------------------------ Minimal
    add("graphite", L"Graphite", L"Minimal", L"Quiet, solid and dark", [](Style& s) {
      s.material = Material::Solid;
      s.base = Color::hex(0x1C1D21);
      s.accent = Color::hex(0xE8EAF0);
      s.accent2 = Color::hex(0xA9AFBD);
      s.text = Color::hex(0xF2F3F5);
      s.opacity = 0.94f;
      s.blur = 0.f;
      s.corner = 12.f;
      s.gap = 3.f;
      s.borderOpacity = 0.08f;
      s.glow = 0.1f;
      s.tilt = 0.f;
      s.burst = false;
      s.open = OpenAnim::Zoom;
      s.speed = 1.25f;
      s.hoverGrow = 6.f;
      s.iconZoom = 1.12f;
      s.dim = 0.2f;
    });
    add("paper", L"Paper", L"Minimal", L"Light panels, soft shadow", [](Style& s) {
      s.material = Material::Frosted;
      s.base = Color::hex(0xFBFBFD);
      s.accent = Color::hex(0x2F6BFF);
      s.accent2 = Color::hex(0x6AA0FF);
      s.text = Color::hex(0x171A21);
      s.border = Color::hex(0xFFFFFF);
      s.opacity = 0.8f;
      s.blur = 30.f;
      s.corner = 16.f;
      s.gap = 5.f;
      s.borderOpacity = 0.65f;
      s.shadow = 0.5f;
      s.glow = 0.3f;
      s.burst = false;
      s.open = OpenAnim::Zoom;
      s.hoverGrow = 9.f;
      s.dim = 0.12f;
    });
    add("ghost", L"Ghost", L"Minimal", L"Only icons, no panels", [](Style& s) {
      s.shape = SlotShape::None;
      s.material = Material::Solid;
      s.base = Color::hex(0x0B0D12);
      s.accent = Color::hex(0xFFFFFF);
      s.accent2 = Color::hex(0x9CC7FF);
      s.opacity = 0.5f;
      s.blur = 0.f;
      s.borderOpacity = 0.f;
      s.shadow = 0.8f;
      s.glow = 0.5f;
      s.iconZoom = 1.35f;
      s.burst = false;
      s.open = OpenAnim::Fade;
      s.dim = 0.5f;
    });
    return v;
  }();
  return all;
}

const Look* findLook(const std::string& id) {
  for (auto& k : builtinLooks())
    if (k.id == id) return &k;
  return nullptr;
}

}  // namespace rt
