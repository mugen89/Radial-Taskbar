#include "overlay.h"

#include <process.h>

#include "app.h"
#include "live.h"
#include "sound.h"

namespace rt {

bool Overlay::create(HINSTANCE inst) {
  std::wstring cls = RT_ID L"Overlay" + instanceSuffix();
  WNDCLASSEXW wc{};
  wc.cbSize = sizeof wc;
  wc.lpfnWndProc = proc;
  wc.hInstance = inst;
  wc.hCursor = LoadCursorW(nullptr, IDC_ARROW);
  wc.lpszClassName = cls.c_str();
  RegisterClassExW(&wc);
  hwnd_ = CreateWindowExW(WS_EX_NOREDIRECTIONBITMAP | WS_EX_TOPMOST | WS_EX_TOOLWINDOW, cls.c_str(), RT_NAME, WS_POPUP, 0, 0, 10, 10,
                          nullptr, nullptr, inst, this);
  if (!hwnd_) return false;
  BOOL on = TRUE;
  DwmSetWindowAttribute(hwnd_, DWMWA_TRANSITIONS_FORCEDISABLED, &on, sizeof on);
  // Covering a whole monitor must not make Windows treat us as a full-screen app.
  SetPropW(hwnd_, L"NonRudeHWND", (HANDLE)TRUE);
  return true;
}

void Overlay::destroy() {
  hideNow();
  dropDevice();
  if (hwnd_) {
    RemovePropW(hwnd_, L"NonRudeHWND");
    DestroyWindow(hwnd_);
  }
  hwnd_ = nullptr;
}

LRESULT CALLBACK Overlay::proc(HWND h, UINT m, WPARAM w, LPARAM l) {
  if (m == WM_NCCREATE) SetWindowLongPtrW(h, GWLP_USERDATA, (LONG_PTR)((CREATESTRUCTW*)l)->lpCreateParams);
  auto* self = (Overlay*)GetWindowLongPtrW(h, GWLP_USERDATA);
  if (self) {
    self->hwnd_ = h;
    return self->handle(m, w, l);
  }
  return DefWindowProcW(h, m, w, l);
}

// ---------------------------------------------------------------- opening
V2 Overlay::cursorLocal() const {
  POINT p;
  GetCursorPos(&p);
  return {(float)(p.x - mon_.left), (float)(p.y - mon_.top)};
}

void Overlay::buildScene(bool animate) {
  const Config& cfg = app_.cfg;
  if (!layout_ || !animate) layout_ = makeLayout(cfg.layout);
  dressLayout(*layout_, cfg, true);
  if (!systemAnimationsEnabled()) layout_->cfg.reduceMotion = true;
  layout_->model = buildModel(cfg, cfg.showRunning || cfg.switchToRunning || cfg.windowsFan ? &wins_ : nullptr);
  HMONITOR hm = MonitorFromRect(&mon_, MONITOR_DEFAULTTONEAREST);
  MONITORINFO mi{};
  mi.cbSize = sizeof mi;
  GetMonitorInfoW(hm, &mi);
  SceneEnv& e = layout_->env;
  e.vw = (float)(mon_.right - mon_.left);
  e.vh = (float)(mon_.bottom - mon_.top);
  e.s = dpiScaleFor(hm) * cfg.scale;
  e.work = RectF((float)(mi.rcWork.left - mon_.left), (float)(mi.rcWork.top - mon_.top), (float)(mi.rcWork.right - mon_.left), (float)(mi.rcWork.bottom - mon_.top));
  e.anchorIsMouse = cfg.anchor == Anchor::Mouse;
  e.preview = false;
  if (e.anchorIsMouse) e.anchor = {(float)(cursorBefore_.x - mon_.left), (float)(cursorBefore_.y - mon_.top)};
  else e.anchor = cfg.layout == LayoutType::Radial ? V2{e.vw * 0.5f, e.vh * 0.5f} : V2{e.work.cx(), e.work.cy()};
  layout_->sticky = !holding_;
  layout_->build();
  if (e.anchorIsMouse && cfg.layout == LayoutType::Radial) {
    float r = layout_->keepInside();
    V2 a = e.anchor;
    a.x = e.vw > r * 2 ? clampf(a.x, r, e.vw - r) : e.vw * 0.5f;
    a.y = e.vh > r * 2 ? clampf(a.y, r, e.vh - r) : e.vh * 0.5f;
    if (fabsf(a.x - e.anchor.x) > 0.5f || fabsf(a.y - e.anchor.y) > 0.5f) {
      e.anchor = a;
      layout_->build();
    }
  }
  area_ = layout_->bounds();
  area_ = RectF(floorf(area_.l), floorf(area_.t), ceilf(area_.r), ceilf(area_.b));
}

constexpr UINT kOpenAgain = WM_APP + 91;

void Overlay::open(bool byHotkey) {
  if (visible_ && !layout_->closing) return;
  if (visible_) hideNow();
  if (tryOpen(byHotkey)) return;
  // The graphics device can disappear across sleep, docking or a driver update: rebuild and try once more.
  logf("overlay: rebuilding the graphics device");
  hideNow();
  dropDevice();
  gfx().release();
  tryOpen(byHotkey);
}

bool Overlay::tryOpen(bool byHotkey) {
  double t0 = nowSec();
  if (!gfx().ensure()) return false;
  const Config& cfg = app_.cfg;

  GetCursorPos(&cursorBefore_);
  HMONITOR hm = cfg.monitor == MonitorPick::Primary && cfg.anchor != Anchor::Mouse ? MonitorFromPoint(POINT{0, 0}, MONITOR_DEFAULTTOPRIMARY)
                                                                                 : MonitorFromPoint(cursorBefore_, MONITOR_DEFAULTTONEAREST);
  MONITORINFO mi{};
  mi.cbSize = sizeof mi;
  GetMonitorInfoW(hm, &mi);
  mon_ = mi.rcMonitor;

  holding_ = byHotkey && cfg.activation != Activation::Toggle && app_.hotkeys.holdKeysDown();
  // Hold-and-release: the keys are up again already, so there is nothing to hold open.
  if (byHotkey && cfg.activation == Activation::Hold && !holding_) return true;
  prevFg_ = GetForegroundWindow();
  wins_.snapshot(hwnd_, app_.hiddenWindow());
  // Opened from the tray, the window "in front" is ours or the taskbar: use the app behind it.
  // The bare desktop is a legitimate place to return to.
  wchar_t cls[64] = {};
  if (prevFg_) GetClassNameW(prevFg_, cls, 64);
  bool desktop = !wcscmp(cls, L"Progman") || !wcscmp(cls, L"WorkerW");
  if (!desktop && !isAppWindow(prevFg_) && !wins_.wins.empty()) prevFg_ = wins_.wins[0].hwnd;
  wins_.foreground = prevFg_;
  moved_ = pressed_ = false;
  wheelAcc_ = 0;
  lastPick_ = {};
  if (!cfg.startProfile.empty())  // always the same one to begin with
    for (int i = 0; i < (int)cfg.profiles.size(); i++)
      if (cfg.profiles[(size_t)i].id == cfg.startProfile && i != cfg.activeProfile) app_.setProfile(i);
  if (cfg.profile().locked) app_.setProfile(cfg.wheelIndex());  // it was being edited; the wheel never shows it
  buildScene(false);
  double t1 = nowSec();

  backdrop_ = {};
  session_++;
  openedAt_ = nowSec();
  if (wantsBackdrop(layout_->st)) startCapture();
  double t2 = nowSec();
  if (!createSurfaces()) {
    dropDevice();
    layout_.reset();
    return false;
  }
  warmArt(back_.Get());
  startFx();
  layout_->beginOpen();
  tiltX_.snap(0);
  tiltY_.snap(0);
  openedAt_ = lastTick_ = nowSec();
  busy_ = dirty_ = true;
  frames_ = slow_ = 0;
  frameSum_ = frameMax_ = 0;

  SetWindowPos(hwnd_, HWND_TOPMOST, mon_.left, mon_.top, mon_.right - mon_.left, mon_.bottom - mon_.top, SWP_NOACTIVATE);
  visible_ = true;
  opening_ = true;
  frame();  // first frame goes out before the window appears, so nothing stale can flash
  opening_ = false;
  if (!visible_) return false;
  if (layout_->closing) {  // let go during the very first frame
    hideNow();
    return true;
  }
  ShowWindow(hwnd_, SW_SHOWNOACTIVATE);
  focusWindow(hwnd_);
  if (!visible_ || !layout_) return true;

  // Bring the pointer to the launcher so one short flick reaches anything.
  warped_ = false;
  cursorStart_ = cursorBefore_;
  V2 home = layout_->home();
  if (cfg.warpCursor || cfg.anchor == Anchor::Mouse) {
    POINT want{mon_.left + (LONG)lroundf(home.x), mon_.top + (LONG)lroundf(home.y)};
    if (cfg.anchor == Anchor::Mouse && cfg.layout != LayoutType::Radial) want = cursorBefore_;
    if (want.x != cursorBefore_.x || want.y != cursorBefore_.y) {
      SetCursorPos(want.x, want.y);
      warped_ = true;
      cursorStart_ = want;
    }
  }
  if (holding_) app_.hotkeys.beginHold();
  if (cfg.sounds) playSound(Sound::Open, cfg.volume);
  lastOpenMs = (nowSec() - t0) * 1000.0;
  logf("overlay: open %.1f ms (scene %.1f, start capture %.1f, surfaces+first frame %.1f) area %.0fx%.0f", lastOpenMs, (t1 - t0) * 1000.0, (t2 - t1) * 1000.0,
       (nowSec() - t2) * 1000.0, area_.w(), area_.h());
  return true;
}

namespace {
// One grab of the desktop behind the launcher. Reading the screen back can take a whole frame,
// so it happens on a worker while the opening animation is already running.
struct Shot {
  HWND notify;
  uint32_t session;
  int x, y, w, h;
  HBITMAP bm = nullptr;
  void* bits = nullptr;
  ~Shot() {
    if (bm) DeleteObject(bm);
  }
};
unsigned __stdcall shotThread(void* p) {
  auto* s = (Shot*)p;
  BITMAPINFO bi{};
  bi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
  bi.bmiHeader.biWidth = s->w;
  bi.bmiHeader.biHeight = -s->h;
  bi.bmiHeader.biPlanes = 1;
  bi.bmiHeader.biBitCount = 32;
  HDC sdc = GetDC(nullptr), mdc = CreateCompatibleDC(sdc);
  s->bm = CreateDIBSection(sdc, &bi, DIB_RGB_COLORS, &s->bits, nullptr, 0);
  bool ok = false;
  if (s->bm && mdc) {
    HGDIOBJ old = SelectObject(mdc, s->bm);
    ok = BitBlt(mdc, 0, 0, s->w, s->h, sdc, s->x, s->y, SRCCOPY) != FALSE;
    GdiFlush();
    SelectObject(mdc, old);
  }
  if (mdc) DeleteDC(mdc);
  ReleaseDC(nullptr, sdc);
  if (!ok || !PostMessageW(s->notify, Overlay::kShotMsg, 0, (LPARAM)s)) delete s;
  return 0;
}
}  // namespace

void Overlay::prepare() {
  if (visible_ || app_.cfg.skinNow().empty() || !gfx().ensure()) return;
  GetCursorPos(&cursorBefore_);
  MONITORINFO mi{};
  mi.cbSize = sizeof mi;
  if (!GetMonitorInfoW(MonitorFromPoint(cursorBefore_, MONITOR_DEFAULTTONEAREST), &mi)) return;
  mon_ = mi.rcMonitor;
  holding_ = false;
  buildScene(false);
  auto t = gfx().target(16, 16);
  skinArt().quiet(true);   // for the disk cache; nobody looks at them yet
  warmArt(t.Get());
  skinArt().quiet(false);
  layout_.reset();
  sweepSkinCache(false);
  logf("overlay: skin prepared");
}

// A skin's pictures are asked for before the first frame and usually come from the disk cache in no time.
// Whatever is late fades in while the wheel opens.
void Overlay::warmArt(ID2D1Bitmap1* into) {
  if (!layout_->view || !into) return;
  double t0 = nowSec();
  layout_->open.snap(1.f);
  layout_->time = 10.f;
  layout_->tick(0.f);
  layout_->view->warm = true;
  ID2D1DeviceContext* dc = gfx().dc.Get();
  dc->SetTarget(into);
  dc->BeginDraw();
  dc->SetTransform(D2D1::Matrix3x2F::Identity());
  painter().attach(dc);
  layout_->draw(painter(), nullptr);
  dc->EndDraw();
  dc->SetTarget(nullptr);
  layout_->view->warm = false;
  double t1 = nowSec();
  skinArt().wait(60);
  logf("overlay: skin asked in %.1f ms, waited %.1f ms", (t1 - t0) * 1000.0, (nowSec() - t1) * 1000.0);
}

void Overlay::startCapture() {
  int w = (int)area_.w(), h = (int)area_.h();
  if (w <= 0 || h <= 0) return;
  auto* s = new Shot;
  s->notify = hwnd_;
  s->session = session_;
  s->x = mon_.left + (int)area_.l;
  s->y = mon_.top + (int)area_.t;
  s->w = w;
  s->h = h;
  uintptr_t t = _beginthreadex(nullptr, 0, shotThread, s, 0, nullptr);
  if (t) CloseHandle((HANDLE)t);
  else delete s;
}

void Overlay::captureArrived(void* shot) {
  std::unique_ptr<Shot> s((Shot*)shot);
  double late = nowSec() - openedAt_;
  // Too late, or for an opening that is already over: do without rather than show a wrong picture.
  if (!visible_ || !layout_ || layout_->closing || s->session != session_ || s->w != (int)area_.w() || s->h != (int)area_.h() || late > 0.30) {
    logf("overlay: glass picture not used (%.0f ms late)", late * 1000.0);
    return;
  }
  auto src = gfx().bitmap(s->bits, s->w, s->h, s->w * 4, true);
  backdrop_ = makeBackdrop(src.Get(), area_, *layout_);
  backdrop_.fade = 0.f;
  busy_ = true;
  logf("overlay: glass ready after %.1f ms", (nowSec() - openedAt_) * 1000.0);
}

bool Overlay::createSurfaces() {
  auto& g = gfx();
  if (gen_ != g.generation) {
    target_.Reset();
    root_.Reset();
    dimVisual_.Reset();
    sceneVisual_.Reset();
    fxVisual_.Reset();
    fxSwap_.Reset();
    fxBack_.Reset();
    fx_.end();
    dimSurface_.Reset();
    dimFx_.Reset();
    sceneFx_.Reset();
    tilt3d_.Reset();
    gen_ = g.generation;
  }
  HRESULT hr = S_OK;
  if (!target_) {
    hr = g.dcomp->CreateTargetForHwnd(hwnd_, TRUE, &target_);
    if (SUCCEEDED(hr)) hr = g.dcomp->CreateVisual(&root_);
    if (SUCCEEDED(hr)) hr = g.dcomp->CreateVisual(&dimVisual_);
    if (SUCCEEDED(hr)) hr = g.dcomp->CreateVisual(&sceneVisual_);
    if (SUCCEEDED(hr)) hr = g.dcomp->CreateVisual(&fxVisual_);
    if (SUCCEEDED(hr)) hr = g.dcomp->CreateEffectGroup(&dimFx_);
    if (SUCCEEDED(hr)) hr = g.dcomp->CreateEffectGroup(&sceneFx_);
    if (SUCCEEDED(hr)) hr = g.dcomp->CreateMatrixTransform3D(&tilt3d_);
    if (SUCCEEDED(hr)) hr = g.dcomp->CreateSurface(4, 4, DXGI_FORMAT_B8G8R8A8_UNORM, DXGI_ALPHA_MODE_PREMULTIPLIED, &dimSurface_);
    if (SUCCEEDED(hr)) {
      POINT off{};
      ComPtr<IDXGISurface> s;
      hr = dimSurface_->BeginDraw(nullptr, __uuidof(IDXGISurface), (void**)s.GetAddressOf(), &off);
      if (SUCCEEDED(hr)) {
        auto p = D2D1::BitmapProperties1(D2D1_BITMAP_OPTIONS_TARGET | D2D1_BITMAP_OPTIONS_CANNOT_DRAW, D2D1::PixelFormat(DXGI_FORMAT_B8G8R8A8_UNORM, D2D1_ALPHA_MODE_PREMULTIPLIED));
        ComPtr<ID2D1Bitmap1> b;
        g.aux->CreateBitmapFromDxgiSurface(s.Get(), &p, &b);
        if (b) {
          g.aux->SetTarget(b.Get());
          g.aux->SetTransform(D2D1::Matrix3x2F::Identity());
          g.aux->BeginDraw();
          ComPtr<ID2D1SolidColorBrush> br;
          g.aux->CreateSolidColorBrush(D2D1::ColorF(0, 0, 0, 1), &br);
          D2D1_RECT_F r = D2D1::RectF((float)off.x, (float)off.y, off.x + 4.f, off.y + 4.f);
          if (br) g.aux->FillRectangle(r, br.Get());
          g.aux->EndDraw();
          g.aux->SetTarget(nullptr);
        }
        dimSurface_->EndDraw();
      }
      dimVisual_->SetContent(dimSurface_.Get());
      dimVisual_->SetBorderMode(DCOMPOSITION_BORDER_MODE_HARD);
      dimVisual_->SetBitmapInterpolationMode(DCOMPOSITION_BITMAP_INTERPOLATION_MODE_NEAREST_NEIGHBOR);
      dimVisual_->SetEffect(dimFx_.Get());
      root_->AddVisual(dimVisual_.Get(), FALSE, nullptr);
      root_->AddVisual(fxVisual_.Get(), TRUE, dimVisual_.Get());
      root_->AddVisual(sceneVisual_.Get(), TRUE, fxVisual_.Get());
      target_->SetRoot(root_.Get());
    }
    if (FAILED(hr)) {
      logf("overlay: composition setup failed %08lx", hr);
      return false;
    }
  }
  dimVisual_->SetTransform(D2D1::Matrix3x2F::Scale((float)(mon_.right - mon_.left) / 4.f, (float)(mon_.bottom - mon_.top) / 4.f));
  swap_ = g.compositionSwapChain((int)area_.w(), (int)area_.h());
  if (!swap_) return false;
  back_ = g.backBuffer(swap_.Get());
  if (!back_) return false;
  ComPtr<IDXGISwapChain2> s2;
  if (frameWait_) CloseHandle(frameWait_);
  frameWait_ = nullptr;
  if (SUCCEEDED(swap_.As(&s2))) {
    s2->SetMaximumFrameLatency(1);
    frameWait_ = s2->GetFrameLatencyWaitableObject();
  }
  sceneVisual_->SetContent(swap_.Get());
  sceneVisual_->SetOffsetX(area_.l);
  sceneVisual_->SetOffsetY(area_.t);
  return true;
}

// ---------------------------------------------------------------- frames
void Overlay::updateComposition() {
  float a = layout_->fade();
  dimFx_->SetOpacity(layout_->st.dim * a);
  float tilt = layout_->cfg.reduceMotion ? 0.f : layout_->st.tilt;
  if (tilt > 0.01f) {
    float maxRad = 7.f * kPi / 180.f * tilt;
    V2 c = layout_->tiltCenter() - V2{area_.l, area_.t};
    float ax = -tiltY_.x * maxRad, ay = tiltX_.x * maxRad;
    float cx = cosf(ax), sx = sinf(ax), cy = cosf(ay), sy = sinf(ay);
    // rotate about X then Y, then a gentle perspective, all around the launcher's centre
    float R[3][3] = {{cy, 0, -sy}, {sx * sy, cx, sx * cy}, {cx * sy, -sx, cx * cy}};
    float d = 1600.f * layout_->env.s;
    D3DMATRIX m{};
    for (int i = 0; i < 3; i++) {
      m.m[i][0] = R[i][0];
      m.m[i][1] = R[i][1];
      m.m[i][2] = 0.f;
      m.m[i][3] = -R[i][2] / d;
    }
    m.m[2][2] = 1.f;
    // T(-c) * M * T(c)
    float w = 1.f + (-c.x * m.m[0][3] - c.y * m.m[1][3]);
    float tx = -c.x * m.m[0][0] - c.y * m.m[1][0], ty = -c.x * m.m[0][1] - c.y * m.m[1][1];
    for (int i = 0; i < 3; i++) {
      m.m[i][0] += m.m[i][3] * c.x;
      m.m[i][1] += m.m[i][3] * c.y;
    }
    m.m[3][0] = tx + w * c.x;
    m.m[3][1] = ty + w * c.y;
    m.m[3][2] = 0;
    m.m[3][3] = w;
    tilt3d_->SetMatrix(m);
    sceneFx_->SetTransform3D(tilt3d_.Get());
    sceneVisual_->SetEffect(sceneFx_.Get());
  } else {
    sceneVisual_->SetEffect(nullptr);
  }
  gfx().dcomp->Commit();
}

void Overlay::frame() {
  if (!visible_ || !layout_ || !swap_) return;
  double now = nowSec();
  float dt = clampf((float)(now - lastTick_), 0.f, 0.05f);
  lastTick_ = now;

  if (holding_ && !app_.hotkeys.holdKeysDown()) released();
  if (!visible_) return;
  layout_->sticky = !holding_;

  float press = pressed_ && !layout_->closing ? 1.f : 0.f;
  bool pressing = fabsf(layout_->press - press) > 0.004f;
  layout_->press = pressing ? layout_->press + (press - layout_->press) * (1.f - expf(-dt * 28.f)) : press;
  bool moving = layout_->tick(dt) || pressing;
  if (backdrop_.bmp && backdrop_.fade < 1.f) {
    backdrop_.fade = std::min(1.f, backdrop_.fade + dt * 9.f);
    moving = true;
  }
  Pick pk = layout_->pick();
  if (pk != lastPick_) {
    if (pk.valid() && app_.cfg.sounds && !layout_->closing) playSound(Sound::Tick, app_.cfg.volume);
    lastPick_ = pk;
  }
  V2 d = layout_->pointerKnown ? layout_->ptr - layout_->tiltCenter() : V2{};
  float r = 420.f * layout_->env.s;
  tiltX_.target = layout_->closing ? 0.f : clampf(d.x / r, -1.f, 1.f);
  tiltY_.target = layout_->closing ? 0.f : clampf(d.y / r, -1.f, 1.f);
  tiltX_.step(dt, 2.4f, 0.8f);
  tiltY_.step(dt, 2.4f, 0.8f);
  if (layout_->st.tilt > 0.01f && !layout_->cfg.reduceMotion) moving |= !tiltX_.settled(0.004f) || !tiltY_.settled(0.004f);

  if (layout_->finished()) {
    hideNow();
    return;
  }

  auto& g = gfx();
  if (gen_ != g.generation) {  // the device was rebuilt underneath us
    hideNow();
    return;
  }
  ID2D1DeviceContext* dc = g.dc.Get();
  if (fx_.active() && fxBack_) {
    fx_.step(dt);
    dc->SetTarget(fxBack_.Get());
    dc->SetDpi(96, 96);
    dc->BeginDraw();
    dc->SetTransform(D2D1::Matrix3x2F::Identity());
    dc->Clear(D2D1::ColorF(0, 0, 0, 0));
    fx_.draw(dc, layout_->fade());
    HRESULT fh = dc->EndDraw();
    dc->SetTarget(nullptr);
    if (SUCCEEDED(fh)) fxSwap_->Present(0, 0);
    else stopFx();  // never worth losing the wheel over
    moving = true;
  }
  dc->SetTarget(back_.Get());
  dc->SetDpi(96, 96);
  dc->BeginDraw();
  dc->SetTransform(D2D1::Matrix3x2F::Identity());
  dc->Clear(D2D1::ColorF(0, 0, 0, 0));
  dc->SetTransform(D2D1::Matrix3x2F::Translation(-area_.l, -area_.t));
  Painter& p = painter();
  p.attach(dc);
  double drawn = nowSec();
  layout_->draw(p, backdrop_.bmp ? &backdrop_ : nullptr);
  dc->SetTransform(D2D1::Matrix3x2F::Identity());
  HRESULT hr = dc->EndDraw();
  dc->SetTarget(nullptr);
  // Several frames in a row that take this long: no skin should, it would only block the screen.
  slow_ = layout_->skin && nowSec() - drawn > 0.4 ? slow_ + 1 : 0;
  if (slow_ >= 5) hr = E_ABORT;
#ifdef RT_FAILTEST  // a test build: as if the skin could not be drawn
  if (layout_->skin && frames_ > 5) hr = E_FAIL;
#endif
  if (SUCCEEDED(hr)) hr = swap_->Present(1, 0);
  if (FAILED(hr)) {
    logf("overlay: frame failed %08lx", hr);
    // Not the graphics card's fault: something in the skin cannot be drawn. Without it there is still a wheel.
    bool skin = layout_->skin && !gfx().isDeviceError(hr);
    if (skin) skins().distrust(app_.cfg.skinNow());
    hideNow();
    dropDevice();
    gfx().release();
    if (skin) {
      app_.notify(L"Skin left out", L"This skin cannot be drawn, so your style is used. It is tried again when its file changes.");
      if (!opening_) PostMessageW(hwnd_, kOpenAgain, 0, 0);  // the first frame is followed by a second attempt anyway
    }
    return;
  }
  updateComposition();
  lastFrameMs = (nowSec() - now) * 1000.0;
  frames_++;
  frameSum_ += lastFrameMs;
  frameMax_ = std::max(frameMax_, lastFrameMs);
  dirty_ = false;
  busy_ = moving || holding_;  // keep polling the held keys
}

void Overlay::startFx() {
  BackFxSpec spec = backFxFor(app_.cfg, layout_ ? layout_->skin.get() : nullptr);
  if (!spec.on() || !fxVisual_ || !layout_) {
    stopFx();
    return;
  }
  auto& g = gfx();
  fxRes_ = spec.kind == "rain" ? 1.f : 0.5f;  // soft things look the same at half the pixels
  int w = std::max(16, (int)((mon_.right - mon_.left) * fxRes_)), h = std::max(16, (int)((mon_.bottom - mon_.top) * fxRes_));
  DXGI_SWAP_CHAIN_DESC1 d{};
  if (!fxSwap_ || FAILED(fxSwap_->GetDesc1(&d)) || (int)d.Width != w || (int)d.Height != h) {
    fxBack_.Reset();
    fxSwap_ = g.compositionSwapChain(w, h);
    fxBack_ = fxSwap_ ? g.backBuffer(fxSwap_.Get()) : nullptr;
    if (!fxBack_) {
      stopFx();
      return;
    }
    fxVisual_->SetContent(fxSwap_.Get());
    fxVisual_->SetTransform(D2D1::Matrix3x2F::Scale(1.f / fxRes_, 1.f / fxRes_));
    fxVisual_->SetBitmapInterpolationMode(DCOMPOSITION_BITMAP_INTERPOLATION_MODE_LINEAR);
  }
  V2 c = layout_->env.anchor;
  float s = layout_->env.s / std::max(0.5f, app_.cfg.scale);  // the screen's own scale, not the wheel's size
  if (!fx_.begin(spec, w, h, s * fxRes_, {c.x * fxRes_, c.y * fxRes_})) stopFx();
}

void Overlay::stopFx() {
  fx_.end();
  fxBack_.Reset();
  fxSwap_.Reset();
  if (fxVisual_) fxVisual_->SetContent(nullptr);
}

void Overlay::dropDevice() {
  stopFx();
  fxVisual_.Reset();
  backdrop_ = {};
  back_.Reset();
  swap_.Reset();
  if (frameWait_) CloseHandle(frameWait_);
  frameWait_ = nullptr;
  dimSurface_.Reset();
  dimFx_.Reset();
  sceneFx_.Reset();
  tilt3d_.Reset();
  dimVisual_.Reset();
  sceneVisual_.Reset();
  root_.Reset();
  target_.Reset();
  gen_ = 0;
}

// ---------------------------------------------------------------- closing
void Overlay::endHold() {
  if (!holding_) return;
  holding_ = false;
  app_.hotkeys.endHold();
}

void Overlay::close(Why why) {
  if (!visible_ || layout_->closing) return;
  bool launched = why == Why::Launched;
  endHold();
  layout_->beginClose(launched, launched ? layout_->pick() : Pick{});
  busy_ = true;
  bool mine = GetForegroundWindow() == hwnd_;
  if (why == Why::Cancel && mine && prevFg_ && IsWindow(prevFg_)) SetForegroundWindow(prevFg_);
  // On a click elsewhere the button may still be down: moving the pointer then would turn it into a drag.
  if (warped_ && app_.cfg.restoreCursor && why != Why::Yield) SetCursorPos(cursorBefore_.x, cursorBefore_.y);
  warped_ = false;
  if (app_.cfg.sounds) playSound(launched ? Sound::Launch : Sound::Close, app_.cfg.volume);
}

void Overlay::hideNow() {
  endHold();
  if (!visible_) return;
  visible_ = busy_ = dirty_ = false;
  logf("overlay: %d frames, %.2f ms average, %.1f ms worst", frames_, frames_ ? frameSum_ / frames_ : 0.0, frameMax_);
  ShowWindow(hwnd_, SW_HIDE);
  if (sceneVisual_) sceneVisual_->SetContent(nullptr);
  stopFx();
  if (gfx().dcomp) gfx().dcomp->Commit();
  live().rest();
  skinArt().rest();
  back_.Reset();
  swap_.Reset();
  if (frameWait_) CloseHandle(frameWait_);
  frameWait_ = nullptr;
  backdrop_ = {};
  layout_.reset();
  gfx().trim();
  app_.overlayHidden();
}

void Overlay::commit(Pick p, bool forceNew, bool admin) {
  const SceneItem* it = layout_->itemAt(p);
  if (!it) return;
  if (it->isGroup()) {  // a group has nothing to launch itself: extend it instead
    layout_->openKids();
    busy_ = true;
    return;
  }
  SceneItem item = *it;
  if (item.hwnd) {
    focusWindow(item.hwnd);
  } else if (app_.cfg.switchToRunning && !forceNew && !admin && item.windows > 0) {
    auto hits = wins_.matching(item.pin);
    HWND h = nullptr;
    if (!hits.empty()) {
      bool front = wins_.wins[(size_t)hits[0]].hwnd == prevFg_;
      // Already in front: cycle through the app's other windows.
      h = wins_.wins[(size_t)(front && hits.size() > 1 ? hits.back() : hits[0])].hwnd;
    }
    if (h && IsWindow(h)) focusWindow(h);
    else launchPin(item.pin, admin);
  } else {
    launchPin(item.pin, admin);
  }
  close(Why::Launched);
}

void Overlay::released() {
  endHold();
  Pick p = layout_->pick();
  double held = nowSec() - openedAt_;
  // Let go on another profile: switch to it and stay open. On the one in use it is just letting go.
  if (int tab = profileOfTab(layout_->hotProfile()); !p.valid() && tab >= 0 && tab != app_.cfg.activeProfile && moved_) {
    switchTo(tab);
    return;
  }
  if (p.valid() && moved_) {
    bool shift = (GetAsyncKeyState(VK_SHIFT) & 0x8000) && !(app_.cfg.hotkey.mods & MOD_SHIFT);
    commit(p, shift, false);
    return;
  }
  if (app_.cfg.activation == Activation::Hold || held > 0.35) close();
  // otherwise it was a quick tap: stay open until a choice is made
}

void Overlay::hotkeyAgain() {
  if (!visible_ || layout_->closing) {
    open(true);
    return;
  }
  if (holding_) {
    moved_ = true;
    layout_->key((GetAsyncKeyState(VK_SHIFT) & 0x8000) ? NavKey::Prev : NavKey::Next);
    busy_ = true;
  } else {
    close();
  }
}

// ---------------------------------------------------------------- input
void Overlay::pointerTo(V2 p) {
  if (!layout_ || layout_->closing) return;
  POINT sp{mon_.left + (LONG)p.x, mon_.top + (LONG)p.y};
  if (abs(sp.x - cursorStart_.x) + abs(sp.y - cursorStart_.y) > 10) moved_ = true;
  layout_->pointer(p);
  busy_ = true;
}

void Overlay::steer(UINT vk, bool shift, bool repeat) {
  if (visible_) onKey(vk, shift, repeat);
}

void Overlay::onKey(UINT vk, bool shift, bool repeat) {
  if (!layout_ || layout_->closing) return;
  busy_ = true;
  if (holding_ && (app_.cfg.hotkey.mods & MOD_SHIFT)) shift = false;  // it is only down as part of the shortcut
  auto nav = [&](NavKey k) {
    moved_ = true;
    layout_->key(k);
  };
  if (vk == app_.cfg.hotkey.vk && (holding_ || repeat)) {  // the shortcut's own key cycles, whatever else it means
    if (!repeat) nav(shift ? NavKey::Prev : NavKey::Next);
    return;
  }
  if (repeat && !strchr("ADWS", (int)vk) && vk != VK_LEFT && vk != VK_RIGHT && vk != VK_UP && vk != VK_DOWN && vk != VK_TAB) return;
  switch (vk) {
    case VK_ESCAPE: close(); return;
    case VK_RETURN:
    case VK_SPACE:
    case 'F': commit(layout_->pick(), shift, false); return;
    case 'A':
    case VK_LEFT: nav(NavKey::Left); return;
    case 'D':
    case VK_RIGHT: nav(NavKey::Right); return;
    case 'W':
    case VK_UP: nav(NavKey::Up); return;
    case 'S':
    case VK_DOWN: nav(NavKey::Down); return;
    case 'Q': switchProfile(-1); return;
    case 'E': switchProfile(1); return;
    case VK_TAB: nav(shift ? NavKey::Prev : NavKey::Next); return;
  }
  if (vk >= '1' && vk <= '9') {
    int i = (int)(vk - '1');
    if (i < (int)layout_->model.items.size()) {
      moved_ = true;
      layout_->select(i);
      commit(Pick{i, -1}, shift, false);
    }
    return;
  }
  if (vk == app_.cfg.hotkey.vk) nav(shift ? NavKey::Prev : NavKey::Next);
}

int Overlay::profileOfTab(int tab) const {
  auto& v = layout_->model.tabProfile;
  return tab >= 0 && tab < (int)v.size() ? v[(size_t)tab] : -1;
}

void Overlay::switchProfile(int dir) {
  int now = app_.cfg.activeProfile, to = app_.cfg.wheelStep(now, dir);
  if (to == now) return;
  app_.setProfile(to);
  if (app_.cfg.sounds) playSound(Sound::Profile, app_.cfg.volume);
  reload(dir);
}

void Overlay::switchTo(int index) {
  int now = app_.cfg.activeProfile;
  if (index < 0 || index >= (int)app_.cfg.profiles.size() || index == now || app_.cfg.profiles[(size_t)index].locked) return;
  app_.setProfile(index);
  if (app_.cfg.sounds) playSound(Sound::Profile, app_.cfg.volume);
  reload(index > now ? 1 : -1);
}

void Overlay::pinChanged(const Pin& pin) {
  if (!visible_ || !layout_) return;
  auto fix = [&](SceneItem& it) {
    if (it.pin.id != pin.id) return;
    it.iconKey = IconCache::keyFor(pin);
    if (it.hwnd) return;  // a window keeps its own title
    it.pin.icon = pin.icon;
    it.pin.iconShape = pin.iconShape;
    it.pin.name = it.label = pin.name;
  };
  for (auto& it : layout_->model.items) {
    fix(it);
    for (auto& k : it.kids) fix(k);
  }
  dirty_ = true;
}

void Overlay::reload(int slide) {
  if (!visible_ || layout_->closing) return;
  RectF old = area_;
  bool st = layout_->sticky;
  Spring tabs = layout_->tabs;
  float hold = layout_->tabsHold;
  buildScene(false);
  layout_->sticky = st;
  if (area_.l != old.l || area_.t != old.t || area_.r != old.r || area_.b != old.b) {
    // Different footprint: the old glass picture still lines up for the part it covers.
    if (!createSurfaces()) {
      hideNow();
      return;
    }
  }
  warmArt(back_.Get());
  if (fx_.spec().kind != backFxFor(app_.cfg, layout_->skin.get()).kind) startFx();  // another profile may have another skin
  layout_->beginOpen();
  layout_->tabs = tabs;
  layout_->tabsHold = slide ? 1.1f : hold;
  bool slid = slide && layout_->slideIn(slide);
  layout_->open.snap(slid ? 1.f : 0.55f);
  layout_->open.target = 1.f;
  layout_->pointer(cursorLocal());
  lastPick_ = {};
  busy_ = dirty_ = true;
}

void Overlay::contextMenu(POINT sp) {
  endHold();  // frames stop while the menu is up, so letting go could not be noticed
  layout_->sticky = true;
  Pick pk = layout_->pick();
  const SceneItem* it = layout_->itemAt(pk);
  Pin pin;
  HWND win = nullptr;
  bool has = it && !it->isGroup();
  if (it) pin = it->pin;
  if (it) win = it->hwnd;
  enum { kNew = 1, kAdmin, kWhere, kRemove, kClose, kPinCurrent, kSettings, kUngroup, kProfile0 = 100, kSkin0 = 1000 };
  std::vector<std::string> skinIds{std::string()};
  HMENU m = CreatePopupMenu();
  if (has && !win) {
    AppendMenuW(m, MF_STRING, kNew, it->windows ? L"Open new window" : L"Open");
    if (pin.kind != Pin::Kind::Url) AppendMenuW(m, MF_STRING, kAdmin, L"Run as administrator");
    if (pin.kind != Pin::Kind::Url) AppendMenuW(m, MF_STRING, kWhere, L"Open file location");
    AppendMenuW(m, MF_SEPARATOR, 0, nullptr);
  }
  if (win) AppendMenuW(m, MF_STRING, kClose, L"Close window");
  if (it && it->isGroup()) {
    AppendMenuW(m, MF_STRING, kUngroup, L"Ungroup");
    std::wstring t = it->kids.empty() ? L"Remove group" : L"Remove group and its " + std::to_wstring(it->kids.size()) + (it->kids.size() == 1 ? L" item" : L" items");
    AppendMenuW(m, MF_STRING, kRemove, t.c_str());
  } else if (it && !win) {
    AppendMenuW(m, MF_STRING, kRemove, L"Unpin");
  }
  if (it) AppendMenuW(m, MF_SEPARATOR, 0, nullptr);
  AppendMenuW(m, MF_STRING, kPinCurrent, L"Pin the app I was using");
  if (app_.cfg.unlockedCount() > 1) {
    HMENU sub = CreatePopupMenu();
    for (size_t i = 0; i < app_.cfg.profiles.size(); i++)
      if (!app_.cfg.profiles[i].locked) AppendMenuW(sub, MF_STRING | ((int)i == app_.cfg.activeProfile ? MF_CHECKED : 0), kProfile0 + i, app_.cfg.profiles[i].name.c_str());
    AppendMenuW(m, MF_POPUP, (UINT_PTR)sub, L"Profile");
  }
  if (HMENU sub = CreatePopupMenu()) {
    AppendMenuW(sub, MF_STRING | (app_.cfg.skinNow().empty() ? MF_CHECKED : 0), kSkin0, L"No skin");
    AppendMenuW(sub, MF_SEPARATOR, 0, nullptr);
    skins().refreshIfChanged();
    for (auto& k : skins().list()) {
      if (!k.error.empty() || skinIds.size() > 60 || app_.cfg.hidden(k.id)) continue;
      AppendMenuW(sub, MF_STRING | (skinIds.size() % 17 == 0 ? MF_MENUBARBREAK : 0) | (app_.cfg.skinNow() == k.id ? MF_CHECKED : 0), kSkin0 + skinIds.size(), k.name.c_str());
      skinIds.push_back(k.id);
    }
    AppendMenuW(m, MF_POPUP, (UINT_PTR)sub, L"Skin");
  }
  AppendMenuW(m, MF_STRING, kSettings, L"Settings");
  inMenu_ = true;
  UINT cmd = (UINT)TrackPopupMenuEx(m, TPM_RETURNCMD | TPM_RIGHTBUTTON, sp.x, sp.y, hwnd_, nullptr);
  inMenu_ = false;
  DestroyMenu(m);
  if (!visible_ || layout_->closing) return;
  lastTick_ = nowSec();
  busy_ = true;
  switch (cmd) {
    case kNew: commit(pk, true, false); break;
    case kAdmin: commit(pk, true, true); break;
    case kWhere:
      openPinLocation(pin);
      close(Why::Yield);
      break;
    case kClose:
      PostMessageW(win, WM_CLOSE, 0, 0);
      close();
      break;
    case kRemove:
      app_.unpin(pin.id);
      reload();
      break;
    case kUngroup:
      app_.ungroup(pin.id);
      reload();
      break;
    case kPinCurrent: app_.pinWindow(prevFg_); break;
    case kSettings:
      close(Why::Yield);
      app_.openSettings();
      break;
    case 0: {
      // Menu dismissed. If that click landed on another program, get out of the way.
      if (GetForegroundWindow() != hwnd_) close(Why::Yield);
      break;
    }
    default:
      if (cmd >= kSkin0) {
        size_t i = cmd - kSkin0;
        if (i < skinIds.size() && skinIds[i] != app_.cfg.skinNow()) {
          app_.setSkin(skinIds[i]);
          reload();
          if (layout_ && visible_) {  // a new look deserves its entrance
            layout_->beginOpen();
            layout_->pointer(cursorLocal());
          }
        }
      } else if (cmd >= kProfile0) {
        switchTo((int)(cmd - kProfile0));
      }
  }
}

LRESULT Overlay::handle(UINT m, WPARAM w, LPARAM l) {
  auto at = [&] { return V2{(float)GET_X_LPARAM(l), (float)GET_Y_LPARAM(l)}; };
  switch (m) {
    case kOpenAgain:
      open(false);
      return 0;
    case kShotMsg: captureArrived((void*)l); return 0;
    case WM_MOUSEACTIVATE: return MA_ACTIVATE;
    case WM_ERASEBKGND: return 1;
    case WM_PAINT: {
      PAINTSTRUCT ps;
      BeginPaint(hwnd_, &ps);
      EndPaint(hwnd_, &ps);
      return 0;
    }
    case WM_SETCURSOR: {
      HCURSOR own = nullptr;
      if (visible_ && layout_ && layout_->skin && app_.cfg.skinCursor) own = skinArt().cursor(dpiScaleFor(hwnd_));
      SetCursor(own ? own : LoadCursorW(nullptr, IDC_ARROW));
      return TRUE;
    }
    case WM_MOUSEMOVE: pointerTo(at()); return 0;
    case WM_LBUTTONDOWN:
      if (layout_ && !layout_->closing) {
        pointerTo(at());
        if (layout_->hubButton(at()) == HubButton::None && layout_->profileAt(at()) < 0 && layout_->outside(at())) {
          close();
          return 0;
        }
        pressed_ = true;
        pressPick_ = layout_->pick();
        pressTab_ = layout_->profileAt(at());
      }
      return 0;
    case WM_LBUTTONUP:
      if (layout_ && !layout_->closing && pressed_) {
        pressed_ = false;
        pointerTo(at());
        if (pressTab_ >= 0) {
          if (layout_->profileAt(at()) == pressTab_) switchTo(profileOfTab(pressTab_));
          return 0;
        }
        switch (layout_->hubButton(at())) {
          case HubButton::Settings:
            close(Why::Yield);
            app_.openSettings();
            return 0;
          case HubButton::PinCurrent: app_.pinWindow(prevFg_); return 0;
          default: break;
        }
        Pick p = layout_->pick();
        if (p.valid() && p.item == pressPick_.item) commit(p, (w & MK_SHIFT) != 0, (w & MK_CONTROL) && (w & MK_SHIFT));
        else if (!p.valid() && !pressPick_.valid()) close();  // a click on the empty centre backs out
      }
      return 0;
    case WM_MBUTTONUP:
      if (layout_ && !layout_->closing) {
        pointerTo(at());
        commit(layout_->pick(), true, false);
      }
      return 0;
    case WM_RBUTTONUP:
      if (layout_ && !layout_->closing) {
        pointerTo(at());
        POINT sp{GET_X_LPARAM(l), GET_Y_LPARAM(l)};
        ClientToScreen(hwnd_, &sp);
        contextMenu(sp);
      }
      return 0;
    case WM_MOUSEWHEEL:
      if (layout_ && !layout_->closing) {
        float n = GET_WHEEL_DELTA_WPARAM(w) / (float)WHEEL_DELTA;
        if (app_.cfg.reverseScroll) n = -n;
        busy_ = true;
        if (layout_->smoothWheel()) {
          layout_->wheel(n);
          return 0;
        }
        if ((n > 0) != (wheelAcc_ > 0)) wheelAcc_ = 0;
        wheelAcc_ += n;
        if (fabsf(wheelAcc_) >= 0.99f) {
          float step = wheelAcc_ > 0 ? 1.f : -1.f;
          wheelAcc_ = 0;
          if (!layout_->wheel(step)) switchProfile(step > 0 ? -1 : 1);
        }
      }
      return 0;
    case WM_KEYDOWN:
    case WM_SYSKEYDOWN:
      if (w != VK_LWIN && w != VK_RWIN && w != VK_SHIFT && w != VK_CONTROL && w != VK_MENU) {
        onKey((UINT)w, (GetKeyState(VK_SHIFT) & 0x8000) != 0, (l & (1 << 30)) != 0);
        return 0;
      }
      break;
    case WM_SYSCOMMAND:
      if ((w & 0xFFF0) == SC_KEYMENU) return 0;
      break;
    case WM_ACTIVATE:
      if (LOWORD(w) == WA_INACTIVE && visible_ && !inMenu_ && layout_ && !layout_->closing) close(Why::Yield);
      break;
    case WM_DISPLAYCHANGE:
      hideNow();
      return 0;
    case WM_DPICHANGED: return 0;  // we size ourselves per monitor on every opening
    case WM_CLOSE:
      close();
      return 0;
  }
  return DefWindowProcW(hwnd_, m, w, l);
}

}  // namespace rt
