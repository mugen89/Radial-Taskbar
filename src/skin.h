// A skin replaces the whole look: artwork, motion, lettering, sounds. This is what a skin file can say; nothing
// here draws. A skin is a folder or a single .rskin file (a ZIP) with skin.json, pictures, sounds and fonts.
// There is no code in a skin, only numbers and formulas, so one from a stranger can do no more than look bad.
#pragma once
#include "config.h"
#include "expr.h"
#include "gfx.h"

namespace rt {

enum class Ease : uint8_t { Linear, Out, InOut, Back, Elastic, Bounce, Quint };
float easeAt(Ease e, float t);

struct SkinColor {
  enum class From : uint8_t { Fixed, Accent, Accent2, Text, Base, Border, Profile, Item };
  From from = From::Fixed;
  Color c{1, 1, 1, 1};
  float a = 1.f;
};

struct SkinPaint {
  enum class Kind : uint8_t { None, Solid, Linear, Radial, Image, Glass };
  Kind kind = Kind::None;
  SkinColor c;
  std::vector<std::pair<float, SkinColor>> stops;
  V2 from{0, -1}, to{0, 1};  // in half sizes of the shape; radial: from is the centre, to.x the radius
  int image = -1;
  bool tile = false, wheel = false;   // wheel: the picture stays with the wheel, each shape shows its own part of it
  Num zoom{1.f}, u, v, turn;
  bool any() const { return kind != Kind::None; }
};

struct SkinImage {
  std::string name, file, mask;
  int cols = 1, rows = 1, frames = 1;
  bool light = false;   // adds light instead of covering
  bool keep = false;    // not touched by the hue and brightness sliders
  bool sharp = false;   // pixel art: never smoothed
};

struct SkinFont {
  std::string name;
  std::vector<std::wstring> families;  // first one that exists
  std::string file;                    // brought along by the skin
  int weight = 400;
};

// How something arrives. Everything is where it starts from; it always ends in place.
struct SkinIntro {
  bool on = false;
  float delay = 0, time = 0.32f, stagger = 0.f;
  Ease ease = Ease::Out;
  enum class Order : uint8_t { Both, Ring, Reverse, Random, Pairs } order = Order::Both;
  float x = 0, y = 0, radius = 0, angle = 0, scale = 1, rotate = 0, opacity = 0;
};

enum class SkinUnit : uint8_t { Wheel, Hub, Ring, Cell, Px };
enum class SkinShape : uint8_t { Circle, Ring, Arc, Rect, Line, Poly, Ticks, Slot, Star };

struct SkinLayer {
  enum class Kind : uint8_t { Image, Text, Shape } kind = Kind::Image;
  SkinUnit unit = SkinUnit::Wheel;
  uint32_t only = 0;               // layouts it belongs to; 0: wherever the group it is in is drawn
  Num x, y, angle, radius, rotate, opacity{1.f}, scaleX{1.f}, scaleY{1.f}, when{1.f}, depth, copies{1.f};
  bool turns = false;              // turned by its own angle (or the entry's)
  bool live = false;               // has a formula that changes while nothing happens
  Num w{1.f}, h;
  bool hasH = false;
  V2 pivot{0.5f, 0.5f};
  SkinIntro intro;

  // image
  int image = -1;
  Num frame;
  float fps = 0, sharpness = 1.f;  // sharpness: extra resolution kept for growing
  bool tinted = false, round = false;
  SkinColor tint;

  // shape
  SkinShape shape = SkinShape::Circle;
  SkinPaint fill, stroke;
  Num width{1.5f}, from, to{360.f}, inner, outer{1.f}, r{1.f}, corner, inset;
  std::vector<std::pair<Num, Num>> points;
  bool closed = false, curve = false, caps = false;
  int count = 12, major = 0;
  float dash[4] = {};
  int dashes = 0;
  Num glow;
  SkinColor glowColor;

  // text
  std::wstring text;
  int font = -1;
  Num px;                          // 0: use em
  float em = 0;                    // relative to the unit
  int weight = 0;
  bool italic = false, wrap = false, upper = false, marquee = false, fit = true;
  Align align = Align::Center;
  VAlign valign = VAlign::Middle;
  float boxW = 0, boxH = 0;        // in units; 0: no limit
  int pixel = 0;                   // drawn this many times too small and blown up, for screens and pixel art
  float tracking = 0;
  SkinColor color;
  bool shadow = false, outline = false;
  float shadowX = 0, shadowY = 1, shadowBlur = 2, outlineW = 1;
  SkinColor shadowColor, outlineColor;
  bool caption = false;            // shows the name of what is selected, so it fades when that changes
  bool ring = false;               // follows a circle of radius r
};

struct SkinParticles {
  int image = -1;
  SkinColor color;
  bool light = true, tinted = false, outward = false, dot = true;
  Num rate{8.f}, when{1.f};
  int max = 40, count = 24;        // count: how many in a burst
  enum class Area : uint8_t { Wheel, Ring, Hub, Rim, Slot, Stage, Pointer } area = Area::Ring;
  float life[2] = {1, 2}, size[2] = {2, 4}, speed[2] = {10, 30}, dir[2] = {0, 360}, spin[2] = {0, 0};
  float gravity = 0, drag = 0.4f, sway = 0, swayHz = 1, fadeIn = 0.15f, fadeOut = 0.4f, grow = 1, swirl = 0, stretch = 0;
  float opacity = 1;
};

// A frame cut in nine, or a plain panel, for name tags and the other layouts.
struct SkinPanel {
  bool on = false;
  int image = -1;
  float cut[4] = {16, 16, 16, 16}, scale = 1, pad[4] = {0, 0, 0, 0};
  SkinPaint fill, stroke;
  float corner = 10, width = 1;
  bool hasText = false, cutCorner = false;
  SkinColor text;
};

struct SkinIcon {
  Num size{1.22f}, x, y, rotate, opacity{1.f};
  IconTone tone = IconTone::Original, toneHot = IconTone::Original;
  SkinColor ink, paper;
  float zoom = 0;                  // 0: from the style
  bool shadow = false, round = false, turns = false;
  float shadowX = 0, shadowY = 2, shadowBlur = 3;
  SkinColor shadowColor;
  Num glow;
  SkinColor glowColor;
};

struct SkinSlot {
  std::vector<SkinLayer> under, over;
  SkinIcon icon;
  bool marks = true, chevron = true, badge = true;
  SkinIntro intro;
  bool on = false;
  float nameDy = 0;                // where names go when they are always shown
};

struct SkinWheel {
  float hub = 0, thickness = 0, gap = -1, ringGap = -1, icon = 0, crowd = 0, rim = 0, shadow = -1;
  float area[4] = {1, 1, 1, 1};    // how far the artwork reaches: left, top, right, bottom, in wheel radii
  float hubKeep = 1;               // how much of the hub text may use
};

struct SkinButton {
  bool on = false, hidden = false;
  SkinUnit unit = SkinUnit::Hub;
  V2 at;
  float size = 13;
  std::vector<SkinLayer> layers;
};

struct SkinCursor {
  int image = -1;
  float size = 32;
  V2 hot;
};

// Motion over the darkened desktop while the wheel is open (backfx.h): which kind, its colours, how much of it.
struct BackFxSpec {
  std::string kind;  // empty: none
  Color color = Color(1, 1, 1), color2 = Color(1, 1, 1);
  float density = 1, speed = 1, size = 1;
  bool on() const { return !kind.empty(); }
};

struct Skin {
  std::string id;
  std::wstring name, author, version, about, license;
  std::vector<std::wstring> tags;
  std::wstring path;
  bool builtin = false, folder = false;
  uint64_t stamp = 0;

  Style style;
  SkinWheel wheel;
  std::vector<SkinImage> images;
  std::vector<SkinFont> fonts;
  std::vector<SkinLayer> back, ring, fan, over, hub, front;
  SkinSlot slot, kid;
  SkinButton pinButton, settingsButton;
  SkinPanel panel, tag, tile;
  std::vector<SkinParticles> particles;
  std::vector<SkinParticles> burstLaunch, burstHover, burstOpen;
  std::map<std::string, std::string> sounds;   // open, move, launch, close, profile
  SkinCursor cursor;
  BackFxSpec screen;              // its own motion over the darkened desktop
  // what the program still draws by itself
  bool ownTitle = true, ownClock = true, ownButtons = true, ownTabs = true, ownShadow = true, ownFan = true;
  float tabInset = 0;              // moves the ring of profiles inward, past an ornate hub rim
  SkinColor tabText, tabFill, tabOn, hubText;
  bool hasHubText = false;
  bool hasTabText = false, hasTabFill = false, hasTabOn = false;

  bool clock = false, system = false, sound = false;  // which outside values it looks at
  bool alive = false;                                 // moves by itself
  bool radial = false;                                // has artwork for the wheel
  bool hasSlot = false;
  std::vector<std::string> problems;

  int imageIndex(std::string_view n) const;
};

// The files of one skin, wherever they are. Reading is safe from several threads.
class SkinFiles {
 public:
  ~SkinFiles();
  static std::shared_ptr<SkinFiles> open(const std::wstring& path, std::string* err = nullptr);
  static constexpr size_t kJsonMost = 2u << 20;            // skin.json
  bool read(const std::string& name, std::string& out, size_t most = 24u << 20) const;
  std::vector<std::string> list() const;
  void letGo() const;              // closes the archive; it is opened again when needed
  bool folder() const { return folder_; }

 private:
  SkinFiles();
  std::wstring path_;
  bool folder_ = false;
  struct Held;
  std::unique_ptr<Held> held_;
};
uint64_t skinStamp(const std::wstring& path);  // changes when anything inside changes; 0: gone

bool parseSkin(const std::string& json, Skin& out, std::string* err);

struct SkinInfo {
  std::string id, preview;
  std::wstring name, author, about, path;
  std::vector<std::wstring> tags;
  bool builtin = false, folder = false;
  std::string error;
};

class SkinStore {
 public:
  static std::wstring userDir();
  static std::wstring builtinDir();
  const std::vector<SkinInfo>& list();             // what is there now
  void refresh() { listed_ = false; }
  bool refreshIfChanged();                          // true when a skin came, went or changed
  const SkinInfo* info(const std::string& id);
  std::shared_ptr<const Skin> get(const std::string& id);   // read again when it changed on disk
  // Takes in a skin file. Returns its id.
  bool install(const std::wstring& file, std::string& id, std::string* err);
  bool remove(const std::string& id, std::string* err);
  // A copy as a folder that can be edited.
  bool copyToFolder(const std::string& id, const std::wstring& name, std::wstring& folder, std::string* err);
  bool pack(const std::string& id, const std::wstring& file, std::string* err);
  // Drawing it failed: not offered to anybody again until its file changes or the program starts anew.
  void distrust(const std::string& id);

 private:
  std::vector<SkinInfo> list_;
  bool listed_ = false;
  std::map<std::string, std::shared_ptr<const Skin>> loaded_;
  double checkedAt_ = 0, missingAt_ = -100;
  std::string checkedId_, missing_;
  std::map<std::wstring, std::pair<uint64_t, SkinInfo>> infos_;
  double badAt_ = -100;
  std::map<std::string, uint64_t> bad_;             // id, and the stamp of the file that failed
  uint64_t dirStamp_ = 0;
  static uint64_t dirsStamp();
};
SkinStore& skins();

}  // namespace rt
