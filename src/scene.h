// What is drawn when the launcher is open. Independent of any window, so the same code
// renders the overlay, the live preview in Settings and the headless checks.
#pragma once
#include "config.h"
#include "gfx.h"
#include "icons.h"
#include "shellutil.h"
#include "skinview.h"

namespace rt {

struct SceneItem {
  Pin pin;
  std::wstring label, sub, iconKey;
  int windows = 0;             // open windows belonging to this pin
  bool active = false;         // owns the window that was in front
  HWND hwnd = nullptr;         // set when the entry stands for one specific window
  std::vector<SceneItem> kids; // group members, or the open windows of a running app
  bool isGroup() const { return pin.kind == Pin::Kind::Group; }
};

struct SceneModel {
  std::vector<SceneItem> items;
  std::wstring profileName;
  Color profileColor = Color::hex(0x4CA8FF);
  int profileIndex = 0, profileCount = 1;
  struct Tab {
    std::wstring name;
    Color color;
    int items = 0;
  };
  std::vector<Tab> tabs;       // every profile the wheel may show, in order
  std::vector<int> tabProfile; // which profile each tab is
  int ringFor = 0;             // items of the fullest profile: the centre is sized for it, so it never jumps
};
SceneModel buildModel(const Config& cfg, const WindowList* running);

struct SceneEnv {
  float vw = 800, vh = 600;    // viewport in pixels
  float s = 1;                 // dpi scale * user scale
  V2 anchor{400, 300};
  RectF work{0, 0, 800, 600};  // area not covered by the taskbar
  bool anchorIsMouse = false;
  bool preview = false;
};

// Processed picture of what lies behind the launcher (blurred / refracted).
struct Backdrop {
  ComPtr<ID2D1Bitmap1> bmp;
  V2 origin;
  float scale = 1.f;           // viewport px per bitmap px
  float fade = 1.f;            // glass appears softly when its picture arrives late
};

struct Pick {
  int item = -1, kid = -1;
  bool valid() const { return item >= 0; }
  bool operator==(const Pick& o) const { return item == o.item && kid == o.kid; }
  bool operator!=(const Pick& o) const { return !(*this == o); }
};

enum class NavKey { Left, Right, Up, Down, Next, Prev };
enum class HubButton { None, Settings, PinCurrent };

// Groups and running apps open this panel beside their icon in the flow and strip layouts.
struct Flyout {
  int item = -1;
  Spring open;
  RectF rect;
  V2 from;
  std::vector<V2> cells;
  std::vector<Spring> hot;
  float cell = 64, icon = 40;
  int hotKid = -1;
  float dwell = 0;
  float caption = 0;           // extra height for the name line
  void layoutCells(int n, V2 origin, V2 dir, float cellPx, float iconPx, RectF clampTo);
  int hit(V2 p) const;
  bool contains(V2 p, float pad) const { return open.target > 0.5f && rect.inset(-pad).contains(p); }
};

// How an icon is printed.
struct IconLook {
  IconTone tone = IconTone::Original, hot = IconTone::Original;
  Color ink, paper;
  bool round = false;
};

class Layout {
 public:
  virtual ~Layout() = default;
  Config cfg;
  Style st;
  SceneEnv env;
  SceneModel model;
  std::shared_ptr<const Skin> skin;  // the one in use, if any
  std::unique_ptr<SkinView> view;     // draws it
  float press = 0;                     // the button is down on an entry

  virtual void build() = 0;
  virtual RectF bounds() const = 0;
  virtual void pointer(V2 p) = 0;
  virtual void clearHover() = 0;
  virtual void key(NavKey k) = 0;
  virtual void select(int item) = 0;
  virtual bool wheel(float notches) = 0;       // false: not used by this layout
  virtual bool smoothWheel() const { return false; }  // takes fractions of a notch
  virtual bool tick(float dt) = 0;             // true while something is still moving
  virtual void draw(Painter& p, const Backdrop* bd) = 0;
  virtual Pick pick() const = 0;
  virtual V2 spot(Pick k) const = 0;           // centre of an entry, for effects
  virtual bool outside(V2 p) const = 0;        // a click here dismisses
  virtual HubButton hubButton(V2) const { return HubButton::None; }
  virtual bool openKids() { return false; }    // expand the current entry if it has children
  virtual int profileAt(V2) const { return -1; }   // the profile switch under this point
  virtual int hotProfile() const { return -1; }
  virtual bool slideIn(int) { return false; }      // another profile's items arrive from that side
  // Edge distance and outward normal for the refraction map; negative when outside all panels.
  virtual float glass(V2, V2&) const { return -1.f; }
  virtual V2 tiltCenter() const { return env.anchor; }
  virtual V2 home() const { return env.anchor; }   // where the pointer should start
  virtual float keepInside() const { return 0; }   // radius that must stay on screen
  virtual float drawScale() const { return env.s; }  // after shrinking to fit
  virtual SkinPlace skinPlace() const;           // where a skin finds the wheel, the hub and the selection
  virtual void skinVars(float*) const {}          // what only this layout knows

  // animation state shared by all layouts
  Spring open;                 // 0..1
  bool closing = false;
  float closeT = 0;            // seconds since closing began
  bool launched = false;
  Pick launchPick;
  float time = 0;
  bool sticky = true;          // hub buttons are shown only when the wheel stays open
  bool pointerKnown = false;
  V2 ptr;
  Spring tabs;                 // the profile switch: 0 folded to a line, 1 unfolded
  float tabsHold = 0;          // keeps it unfolded for a moment after a change

  void beginOpen();
  void beginClose(bool didLaunch, Pick p);
  bool finished() const { return closing && closeT > 0.20f; }
  float fade() const;          // overall alpha
  const SceneItem* itemAt(Pick k) const;
  Color accent() const { return st.accent; }
  void drawIconAs(Painter& p, const SceneItem& it, V2 c, float size, float alpha, float hot, const IconLook& look) const;
  void iconShadow(Painter& p, const SceneItem& it, V2 c, float size, Color col, float blur) const;
  float motion() const { return st.speed * (cfg.reduceMotion ? 2.6f : 1.f); }

 protected:
  void tickBase(float dt);
  bool tickView(float dt);
  bool tickSkin(float dt, const std::wstring& title, const std::wstring& sub);  // the same for layouts without a hub
  void drawSkinStage(Painter& p, const Backdrop* bd, float alpha, bool front) const;
  int seenPick_ = -1;
  // drawing helpers
  void drawIcon(Painter& p, const SceneItem& it, V2 c, float size, float alpha, float hot) const;
  void drawTileIcon(Painter& p, const SceneItem& it, V2 c, float size, float alpha, float hot, int depth, const IconLook& look) const;
  // One entry outside the wheel: its plate (or the skin's artwork), its icon and its marks.
  struct Entry {
    int index = 0, count = 1;
    float hot = 0, alpha = 1, scale = 1, turn = 0;  // turn in degrees
    bool kid = false, marks = true;
    float clock = -1;
  };
  void drawEntry(Painter& p, const Backdrop* bd, const SceneItem& it, V2 c, float half, float iconPx, const Entry& e) const;
  void entryVars(const SceneItem& it, const Entry& e) const;
  void fillPanel(Painter& p, ID2D1Geometry* g, const Backdrop* bd, float alpha, float tintBoost = 0.f) const;
  void strokePanel(Painter& p, ID2D1Geometry* g, V2 a, V2 b, float alpha) const;
  static std::wstring countText(int n) { return n == 0 ? L"Empty" : std::to_wstring(n) + (n == 1 ? L" item" : L" items"); }
  Color halo(float a) const { return st.text.luma() > 0.5f ? Color(0, 0, 0, 0.85f * a) : Color(1, 1, 1, 0.9f * a); }
  TextStyle label(float size, int weight, Align al = Align::Center, VAlign va = VAlign::Middle) const;
  // Name tag beside an icon. `dir` points from the icon toward the tag.
  void drawTag(Painter& p, const Backdrop* bd, V2 at, V2 dir, const std::wstring& title, const std::wstring& sub, float alpha, RectF keepIn) const;
  void drawFlyout(Painter& p, const Backdrop* bd, const Flyout& f, const SceneItem& owner, float alpha) const;
  // Small plate behind an icon for the skins that use individual slots.
  bool plates_ = false;        // every entry stands on a plate of its own
  bool hexPlates_ = false;     // ... a hexagonal one
  Geo tileGeo(V2 c, float half) const;
  void drawTile(Painter& p, const Backdrop* bd, V2 c, float half, float hot, float alpha) const;

  // The profile switch of the flow and strip layouts: a capsule of dots.
  std::vector<Spring> dotHot_;
  int hotDot_ = -1;
  float dotTag_ = 0;
  std::wstring dotName_, dotSub_;
  int dotCount() const { return model.tabs.size() > 1 && model.tabs.size() <= 12 ? (int)model.tabs.size() : 0; }
  virtual V2 dotPos(int) const { return {}; }
  int dotAt(V2 p, float s) const;
  bool tickDots(float dt);
  void drawDots(Painter& p, const Backdrop* bd, float s, float alpha) const;
  V2 dotTagAt() const { return dotPos(clampi(hotDot_ >= 0 ? hotDot_ : model.profileIndex, 0, std::max(0, dotCount() - 1))); }

  // ambient particles and the launch burst
  struct Bit { V2 pos, vel; float life, age, size, seed; };
  std::vector<Bit> bits_, sparks_;
  void tickParticles(float dt, V2 c, float rMin, float rMax);
  void drawParticles(Painter& p, float alpha) const;
  void burst(V2 at, V2 dir);
  mutable uint32_t rng_ = 0x9E3779B9u;
  float rnd() const {
    rng_ ^= rng_ << 13;
    rng_ ^= rng_ >> 17;
    rng_ ^= rng_ << 5;
    return (rng_ & 0xFFFFFF) / 16777216.f;
  }
};

// Gives a layout its settings, its look and its skin. Call before build().
void dressLayout(Layout& l, const Config& cfg, bool persistArt);

std::unique_ptr<Layout> makeLayout(LayoutType t);
std::unique_ptr<Layout> makeFree(LayoutType t);
std::unique_ptr<Layout> makeRadial();
std::unique_ptr<Layout> makeFlow();
std::unique_ptr<Layout> makeStrip();

// Resolves skin colours that depend on Windows (accent following).
Style effectiveStyle(const Config& cfg);

// Builds the frosted / refracted material from a picture of the desktop behind `area`.
Backdrop makeBackdrop(ID2D1Bitmap1* src, RectF area, const Layout& layout);
bool wantsBackdrop(const Style& st);

}  // namespace rt
