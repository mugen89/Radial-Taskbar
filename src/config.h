// Everything the person can configure, plus loading and saving it.
#pragma once
#include "common.h"
#include "json.h"

namespace rt {

enum class LayoutType { Radial, Flow, Strip, Orbit, Comb, Carousel, Globe, Cards, Corner, Galaxy, Board, Drum };
constexpr int kLayoutCount = 12;
const char* layoutId(LayoutType t);
enum class Anchor { Center, Mouse };
enum class Overflow { Rings, Unfold, Pages };  // what happens past the per-ring limit
enum class SlotShape { Wedge, Blade, Orb, Hex, Petal, None };
enum class Material { Frosted, Liquid, Solid, Outline };
enum class IconTone { Original, Muted, Mono, Duo, Ink, Engrave, Neon, Pixel, Sticker, Shadow };  // the last is for our own use
constexpr int kToneCount = 10;
bool toneFromText(const std::string& s, IconTone& out);
enum class OpenAnim { Bloom, Spin, Unfold, Zoom, Fade };
enum class RimStyle { Off, Solid, Spin };
enum class Particles { Off, Embers, Stars };
enum class HubShow { Clock, Profile, Empty };
enum class Activation { Smart, Hold, Toggle };
enum class FlowSide { Right, Left };
enum class StripEdge { Bottom, Top, Left, Right, Center };
enum class Labels { Focused, Always };
enum class MonitorPick { Mouse, Primary };
enum class PicShape { Auto, Plain, Tile, Circle };         // how a chosen picture is fitted

// A look: shape, colours, material and effects. Skins are just named Styles.
struct Style {
  std::string look = "glass";   // the preset it started from
  SlotShape shape = SlotShape::Wedge;
  Material material = Material::Frosted;
  Color base = Color::hex(0x12161F);
  Color accent = Color::hex(0x4CA8FF);
  Color accent2 = Color::hex(0x7B5CFF);
  Color text = Color::hex(0xF4F7FF);
  Color border = Color::hex(0xFFFFFF);
  bool systemAccent = false;
  float opacity = 0.62f;        // tint strength of the panels
  float blur = 26.f;            // backdrop blur radius, px at 100%
  float refraction = 0.5f;      // liquid glass edge bending
  float corner = 14.f;
  float borderWidth = 1.2f;
  float borderOpacity = 0.22f;
  float gap = 6.f;
  float shadow = 0.55f;
  IconTone tone = IconTone::Original;
  std::string font = "Segoe UI Variable Display";
  // effects
  OpenAnim open = OpenAnim::Bloom;
  float speed = 1.f;
  float hoverGrow = 12.f;       // how far the focused slot extends
  float iconZoom = 1.22f;
  float glow = 0.6f;
  float tilt = 0.35f;           // 3D parallax toward the pointer
  bool pointer = true;          // direction needle on the hub
  RimStyle rim = RimStyle::Off;
  bool ticks = false;           // HUD tick ring
  bool scan = false;            // scan lines
  bool pulse = false;           // radar pulse from the hub
  Particles particles = Particles::Off;
  bool burst = true;            // spark burst on launch
  float dim = 0.28f;            // how much the desktop darkens behind
};

struct Look {
  std::string id;
  std::wstring name;
  std::wstring group;  // "Stylized", "Gamey", "Minimal"
  std::wstring blurb;
  Style style;
};
const std::vector<Look>& builtinLooks();
const Look* findLook(const std::string& id);
bool sameLook(const Style& a, const Style& b);
std::string styleText(const Style& s);
void readStyle(const Json& j, Style& s);  // takes over what is there, within limits

struct Pin {
  enum class Kind { App, File, Url, Group };
  std::string id;
  Kind kind = Kind::File;
  std::wstring name;
  std::wstring target;   // App: AppUserModelID, File: path, Url: address
  std::wstring args, workDir;
  std::wstring icon;     // optional override: file path, optionally ",index"
  PicShape iconShape = PicShape::Auto;
  bool admin = false;
  bool folder = false;   // remembered when pinned, so opening never has to touch the disk
  std::vector<Pin> children;
};

struct Profile {
  std::string id;
  std::wstring name = L"Main";
  Color color = Color::hex(0x4CA8FF);
  std::vector<Pin> pins;
  std::string skin;             // empty: the main skin. Config::kNoSkin: none. Otherwise a skin of its own
  int layout = -1;              // -1: the main arrangement. Otherwise a LayoutType of its own
  bool locked = false;          // kept out of the wheel: scrolling and switching pass it by
};

struct Hotkey {
  UINT mods = MOD_WIN;     // MOD_* flags
  UINT vk = VK_OEM_3;      // the ` key, above Tab
  bool takeOver = false;   // use a low-level hook to win over an occupied shortcut
  bool operator==(const Hotkey& o) const { return mods == o.mods && vk == o.vk && takeOver == o.takeOver; }
};
std::wstring hotkeyText(const Hotkey& h);
std::wstring keyName(UINT vk);

struct Config {
  static constexpr int kVersion = 2;  // 2: websites were asked for their logos once
  int version = kVersion;
  bool firstRun = true;

  Hotkey hotkey;
  Activation activation = Activation::Smart;

  // layout
  LayoutType layout = LayoutType::Radial;
  Anchor anchor = Anchor::Mouse;
  MonitorPick monitor = MonitorPick::Mouse;
  float scale = 1.15f;
  float iconSize = 48.f;
  // radial
  int perRing = 10;             // item limit before another ring appears
  Overflow overflow = Overflow::Rings;
  float hubRadius = 80.f;
  float ringThickness = 84.f;
  HubShow hub = HubShow::Clock;
  bool hubProfiles = true;      // switch profiles on the rim of the inner circle
  bool showNumbers = false;
  float arc = 360.f;            // how much of a circle the wheel uses, in degrees
  int arcAt = 0;                // where its middle points: 0 up, 1 right, 2 down, 3 left
  // side flow
  FlowSide flowSide = FlowSide::Right;
  float flowCurve = 0.55f;
  float flowSpacing = 20.f;
  float flowMagnify = 1.7f;
  // strip
  StripEdge stripEdge = StripEdge::Bottom;
  float stripMagnify = 1.6f;
  float stripSpacing = 14.f;
  Labels labels = Labels::Focused;

  // the other arrangements
  float spread = 1.f;           // how far apart things are
  float drift = 0.5f;           // how lively they are by themselves
  float lens = 1.5f;            // how much the focused one grows
  int columns = 0;              // board: 0 finds a good number
  int cornerAt = 0;             // corner fan: 0 bottom left, 1 bottom right, 2 top left, 3 top right

  Style style;
  std::vector<Look> customLooks;

  // The arrangement works like the skin: the main one (`layout`) is for every profile that uses it, and a profile
  // can have one of its own. Its settings (rings, sizes, edges ...) are shared by every profile that shows it.
  LayoutType layoutFor(const Profile& p) const { return p.layout >= 0 && p.layout < kLayoutCount ? (LayoutType)p.layout : layout; }
  LayoutType layoutNow() const { return layoutFor(profile()); }
  void chooseLayout(LayoutType t);         // for the profile in use: the main arrangement when it uses that
  bool anyLayout(LayoutType t) const;      // some profile shows it
  bool onlyLayout(LayoutType t) const;     // every profile shows it

  // A skin replaces the style; hue, saturation and brightness tune its artwork. The main skin is for every profile
  // that uses it; a profile can have one of its own or none. Everything else is the same for all profiles.
  static constexpr const char* kNoSkin = "-";
  std::string skin;             // the main skin
  std::vector<std::string> hiddenSkins;  // skins that came with the program and were removed from the list
  bool hidden(const std::string& id) const { return std::find(hiddenSkins.begin(), hiddenSkins.end(), id) != hiddenSkins.end(); }
  const std::string& skinFor(const Profile& p) const;
  const std::string& skinNow() const { return skinFor(profile()); }
  void chooseSkin(const std::string& id);  // for the profile in use: the main skin when it uses that
  struct Tune {
    float hue = 0, sat = 1, light = 1;
    bool plain() const { return hue == 0 && sat == 1 && light == 1; }
  };
  std::map<std::string, Tune> tunes;
  bool skinCursor = true;
  Tune tune() const {
    auto it = tunes.find(skinNow());
    return it == tunes.end() ? Tune{} : it->second;
  }

  // behaviour
  bool warpCursor = true;
  bool restoreCursor = true;
  bool switchToRunning = true;
  bool showRunning = true;
  bool windowsFan = true;       // fan out the open windows of a running app
  bool blockFullscreen = true;
  bool sounds = false;
  float volume = 0.5f;
  bool lowMemory = true;
  bool reduceMotion = false;
  bool trayIcon = true;
  bool taskbarMenu = true;      // offer "Add to Radial Taskbar" beside the menu of a taskbar button
  bool siteLogos = true;        // ask a website for its logo when it is added
  bool reverseScroll = false;   // scrolling down goes to the previous profile
  std::string startProfile;     // the wheel always opens on this one; empty: the one used last
  bool backFx = true;           // motion over the darkened desktop
  std::string backFxKind = "skin";  // "skin": the skin's own, or one of backFxKinds()
  std::string helpLang;         // the Help page in another language: "bg"

  int activeProfile = 0;
  std::vector<Profile> profiles;

  Profile& profile();
  const Profile& profile() const { return const_cast<Config*>(this)->profile(); }
  Profile& profileById(const std::string& id);  // the one in use when there is no such profile
  // Locked profiles stay out of the wheel. There is always one that is not locked.
  int wheelStep(int from, int dir) const;       // the next one the wheel may show that way; `from` when there is none
  int wheelIndex() const;                       // the one in use, or the next one that is not locked
  int unlockedCount() const;

  static std::wstring path();
  enum class Load { Ok, Missing, Unreadable };
  Load load(int tries = 24);    // Missing: nothing saved yet. Unreadable: it exists but cannot be opened now
  bool save() const;
  bool locked = false;          // never write: what is on disk was not readable and must not be replaced
  bool intact = false;          // read from the file itself, not from a safety copy
  std::string exportText() const;                                   // includes the shortcuts and pictures pins use
  static bool checkBackup(const std::string& text, int& profiles, int& pins);
  bool importText(const std::string& text);
  Json toJson() const;
  void fromJson(const Json& j);
  void sanitize();
};

std::wstring imagesDir();  // copies of the pictures people chose
std::wstring linksDir();   // copies of the shortcuts pins point to
Pin* findPin(std::vector<Pin>& pins, const std::string& id);
std::string pinText(const Pin& p, const std::string& profileId = {});  // profileId: where it should go
bool pinParse(const std::string& text, Pin& p, std::string* profileId = nullptr);
bool removePin(std::vector<Pin>& pins, const std::string& id, Pin* out = nullptr);
bool ungroupPin(std::vector<Pin>& pins, const std::string& id);

}  // namespace rt
