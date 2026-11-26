// The full-screen, transparent, GPU-composited window the launcher lives in.
#pragma once
#include "common.h"
#include "config.h"
#include "gfx.h"
#include "backfx.h"
#include "scene.h"
#include "shellutil.h"

namespace rt {

class App;

class Overlay {
 public:
  explicit Overlay(App& app) : app_(app) {}
  bool create(HINSTANCE inst);
  void destroy();
  HWND hwnd() const { return hwnd_; }
  bool visible() const { return visible_; }
  bool holding() const { return holding_; }

  void open(bool byHotkey);
  enum class Why { Cancel, Launched, Yield };  // Yield: something else took over, keep hands off focus
  void close(Why why = Why::Cancel);
  void hotkeyAgain();                  // pressed while already open
  void steer(UINT vk, bool shift, bool repeat);  // key forwarded by the hold hook
  void switchProfile(int dir);
  int profileOfTab(int tab) const;  // the profile behind a tab of the profile switch, -1 for none
  void switchTo(int index);
  void pinChanged(const Pin& p);       // a picture or name arrived for one item
  void prepare();                      // gets a skin's pictures ready while nothing is on screen
  void reload(int slide = 0);          // config changed while open; slide: which side a new profile comes from

  bool wantsFrame() const { return visible_ && (busy_ || dirty_); }
  HANDLE frameHandle() const { return frameWait_; }
  void frame();
  void invalidate() { dirty_ = true; }
  void dropDevice();

  static constexpr UINT kShotMsg = WM_APP + 40;

  // numbers for the diagnostics line and the self test
  double lastOpenMs = 0, lastFrameMs = 0;

 private:
  static LRESULT CALLBACK proc(HWND h, UINT m, WPARAM w, LPARAM l);
  LRESULT handle(UINT m, WPARAM w, LPARAM l);
  bool tryOpen(bool byHotkey);
  void buildScene(bool animate);
  void startCapture();
  void warmArt(ID2D1Bitmap1* into);
  void captureArrived(void* shot);
  bool createSurfaces();
  void hideNow();
  void commit(Pick p, bool forceNew, bool admin);
  void released();                     // the shortcut was let go
  void onKey(UINT vk, bool shift, bool repeat);
  void endHold();
  void contextMenu(POINT screen);
  void pointerTo(V2 p);
  V2 cursorLocal() const;
  void updateComposition();

  App& app_;
  HWND hwnd_ = nullptr;
  int slow_ = 0;
  bool opening_ = false, visible_ = false, busy_ = false, dirty_ = false, inMenu_ = false;
  bool holding_ = false, moved_ = false, pressed_ = false;
  float wheelAcc_ = 0;
  Pick pressPick_;
  int pressTab_ = -1;
  double openedAt_ = 0, lastTick_ = 0;
  RECT mon_{};
  POINT cursorBefore_{}, cursorStart_{};
  bool warped_ = false;
  HWND prevFg_ = nullptr;
  WindowList wins_;

  std::unique_ptr<Layout> layout_;
  Backdrop backdrop_;
  uint32_t session_ = 0;               // which opening a late capture belongs to
  double frameSum_ = 0, frameMax_ = 0;
  int frames_ = 0;
  RectF area_;                         // drawn part of the monitor
  Spring tiltX_, tiltY_;
  Pick lastPick_;

  ComPtr<IDCompositionTarget> target_;
  ComPtr<IDCompositionVisual> root_, dimVisual_, sceneVisual_, fxVisual_;
  // screensaver-like motion over the darkened desktop
  ComPtr<IDXGISwapChain1> fxSwap_;
  ComPtr<ID2D1Bitmap1> fxBack_;
  BackFx fx_;
  float fxRes_ = 1.f;
  void startFx();
  void stopFx();
  ComPtr<IDCompositionSurface> dimSurface_;
  ComPtr<IDCompositionEffectGroup> dimFx_, sceneFx_;
  ComPtr<IDCompositionMatrixTransform3D> tilt3d_;
  ComPtr<IDXGISwapChain1> swap_;
  ComPtr<ID2D1Bitmap1> back_;
  HANDLE frameWait_ = nullptr;
  uint32_t gen_ = 0;
};

}  // namespace rt
