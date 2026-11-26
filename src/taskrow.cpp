#include "taskrow.h"

#include <process.h>
#include <uiautomationclient.h>

#include "app.h"
#include "gfx.h"

namespace rt {

static const wchar_t* kButtonClass = L"Taskbar.TaskListButtonAutomationPeer";

// ---------------------------------------------------------------- noticing the menu (resident)
namespace {
// What the resident tells the helper: which menu, who was in front before, where the mouse was pressed.
struct RowJob {
  HWND menu = nullptr, prev = nullptr;
  POINT press{};
};
constexpr ULONG_PTR kRowJob = 0x5256;

std::wstring hostClass() { return RT_ID L"RowHost" + instanceSuffix(); }
std::wstring rowClass() { return RT_ID L"Row" + instanceSuffix(); }
HWND findHost() { return FindWindowExW(HWND_MESSAGE, nullptr, hostClass().c_str(), nullptr); }

HWND g_lastApp = nullptr;
POINT g_press{};
ULONGLONG g_pressAt = 0, g_pendingAt = 0;
HANDLE g_helper = nullptr;
RowJob g_pending;
UINT_PTR g_pendingTimer = 0;

bool isShellMenu(HWND h) {
  wchar_t cls[64] = {}, title[128] = {};
  GetClassNameW(h, cls, 64);
  if (wcscmp(cls, L"Windows.UI.Core.CoreWindow")) return false;
  InternalGetWindowText(h, title, 128);
  if (!wcscmp(title, L"Windows Shell Experience Host")) return false;  // the notification centre and the like
  DWORD pid = 0;
  GetWindowThreadProcessId(h, &pid);
  HANDLE p = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
  if (!p) return false;
  wchar_t path[1024];
  DWORD n = 1024;
  bool ok = QueryFullProcessImageNameW(p, 0, path, &n) && toLower(fileName(path)) == L"shellexperiencehost.exe";
  CloseHandle(p);
  return ok;
}

void wakeHelper() {
  if (findHost()) return;
  if (g_helper) {
    if (WaitForSingleObject(g_helper, 0) == WAIT_TIMEOUT) return;  // on its way
    CloseHandle(g_helper);
  }
  g_helper = startHelper(L"--taskbar-row", true);
}

bool deliver(const RowJob& j) {
  HWND h = findHost();
  if (!h) return false;
  COPYDATASTRUCT cd{kRowJob, sizeof j, (void*)&j};
  DWORD_PTR r = 0;
  return SendMessageTimeoutW(h, WM_COPYDATA, 0, (LPARAM)&cd, SMTO_ABORTIFHUNG, 300, &r) && r;
}

void CALLBACK pendingTick(HWND, UINT, UINT_PTR id, DWORD) {
  if (!deliver(g_pending) && GetTickCount64() - g_pendingAt < 2500) return;
  KillTimer(nullptr, id);
  g_pendingTimer = 0;
}
}  // namespace

void TaskbarWatch::apply(bool on) {
  if (on == (hook_ != nullptr)) return;
  if (on) {
    hook_ = SetWinEventHook(EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_FOREGROUND, nullptr, onForeground, 0, 0, WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS);
    HWND f = GetForegroundWindow();
    if (isAppWindow(f)) g_lastApp = f;
  } else {
    UnhookWinEvent(hook_);
    hook_ = nullptr;
    if (g_pendingTimer) KillTimer(nullptr, g_pendingTimer);
    g_pendingTimer = 0;
  }
}

void CALLBACK TaskbarWatch::onForeground(HWINEVENTHOOK, DWORD, HWND h, LONG obj, LONG, DWORD, DWORD) {
  if (!h || obj != OBJID_WINDOW) return;
  // Reading it every time also clears the "pressed since last asked" mark.
  bool rightPress = (GetAsyncKeyState(GetSystemMetrics(SM_SWAPBUTTON) ? VK_LBUTTON : VK_RBUTTON) & 0x8001) != 0;
  wchar_t cls[64] = {};
  GetClassNameW(h, cls, 64);
  if (!wcscmp(cls, L"Shell_TrayWnd") || !wcscmp(cls, L"Shell_SecondaryTrayWnd")) {
    // Pressing on the taskbar brings it here a moment before its menu: note the place, and get the helper ready.
    GetCursorPos(&g_press);
    g_pressAt = GetTickCount64();
    if (rightPress) wakeHelper();
    return;
  }
  if (isShellMenu(h)) {
    g_pending = RowJob{h, g_lastApp, g_press};
    if (GetTickCount64() - g_pressAt > 1500) GetCursorPos(&g_pending.press);
    g_pressAt = 0;
    if (deliver(g_pending)) return;
    wakeHelper();
    g_pendingAt = GetTickCount64();
    if (!g_pendingTimer) g_pendingTimer = SetTimer(nullptr, 0, 10, pendingTick);
    return;
  }
  if (isAppWindow(h)) g_lastApp = h;
}

// ---------------------------------------------------------------- which button is it
namespace {
std::wstring take(BSTR b) {
  std::wstring s = b ? std::wstring(b, SysStringLen(b)) : std::wstring();
  SysFreeString(b);
  return s;
}

ComPtr<IUIAutomation> automation() {
  ComPtr<IUIAutomation> a;
  CoCreateInstance(__uuidof(CUIAutomation), nullptr, CLSCTX_INPROC_SERVER, __uuidof(IUIAutomation), (void**)a.GetAddressOf());
  return a;
}

// "Window: 0x1a2b" for one window, "Appid: Some.App.Id" for a whole app.
bool parseId(const std::wstring& id, TaskButton& b) {
  if (id.rfind(L"Window: ", 0) == 0) {
    b.hwnd = (HWND)(uintptr_t)wcstoull(id.c_str() + 8, nullptr, 16);
    return b.hwnd != nullptr;
  }
  if (id.rfind(L"Appid: ", 0) == 0) {
    b.appId = id.substr(7);
    return !b.appId.empty();
  }
  return false;
}

std::vector<HWND> taskbars() {
  std::vector<HWND> v;
  for (auto cls : {L"Shell_TrayWnd", L"Shell_SecondaryTrayWnd"})
    for (HWND h = nullptr; (h = FindWindowExW(nullptr, h, cls, nullptr));) v.push_back(h);
  return v;
}

void buttonsOf(IUIAutomation* a, HWND bar, std::vector<TaskButton>& out) {
  ComPtr<IUIAutomationElement> root;
  ComPtr<IUIAutomationCondition> cond;
  ComPtr<IUIAutomationCacheRequest> cache;
  ComPtr<IUIAutomationElementArray> all;
  VARIANT v;
  VariantInit(&v);
  v.vt = VT_BSTR;
  v.bstrVal = SysAllocString(kButtonClass);
  HRESULT hr = a->ElementFromHandle(bar, &root);
  if (SUCCEEDED(hr)) hr = a->CreatePropertyCondition(UIA_ClassNamePropertyId, v, &cond);
  VariantClear(&v);
  if (SUCCEEDED(hr)) hr = a->CreateCacheRequest(&cache);
  if (FAILED(hr) || !root || !cond || !cache) return;
  for (PROPERTYID id : {UIA_AutomationIdPropertyId, UIA_NamePropertyId, UIA_BoundingRectanglePropertyId}) cache->AddProperty(id);
  if (FAILED(root->FindAllBuildCache(TreeScope_Descendants, cond.Get(), cache.Get(), &all)) || !all) return;
  int n = 0;
  all->get_Length(&n);
  for (int i = 0; i < n; i++) {
    ComPtr<IUIAutomationElement> e;
    if (FAILED(all->GetElement(i, &e)) || !e) continue;
    TaskButton b;
    BSTR id = nullptr, nm = nullptr;
    e->get_CachedAutomationId(&id);
    e->get_CachedName(&nm);
    e->get_CachedBoundingRectangle(&b.rc);
    b.name = take(nm);
    if (parseId(take(id), b)) out.push_back(std::move(b));
  }
}

bool readButton(IUIAutomationElement* e, TaskButton& b) {
  BSTR id = nullptr, nm = nullptr;
  if (FAILED(e->get_CurrentAutomationId(&id)) || !parseId(take(id), b)) return false;
  e->get_CurrentName(&nm);
  e->get_CurrentBoundingRectangle(&b.rc);
  b.name = take(nm);
  return true;
}

// The menu opens centred on its button. At the screen's ends it is pushed inward, then the press decides.
bool buttonFor(IUIAutomation* a, RECT menu, POINT press, TaskButton& out) {
  HMONITOR mon = MonitorFromRect(&menu, MONITOR_DEFAULTTONEAREST);
  HWND bar = nullptr;
  for (HWND h : taskbars()) {
    RECT r;
    if (GetWindowRect(h, &r) && MonitorFromRect(&r, MONITOR_DEFAULTTONEAREST) == mon) bar = h;
  }
  if (!bar) return false;
  RECT br;
  GetWindowRect(bar, &br);
  bool flat = br.right - br.left >= br.bottom - br.top;
  // A button's menu sits right against the taskbar. Others (a notification, the menu of the overflow flyout) do not.
  long near_ = (long)(6 * dpiScaleFor(mon));
  long away = flat ? std::min(labs(menu.bottom - br.top), labs(menu.top - br.bottom)) : std::min(labs(menu.right - br.left), labs(menu.left - br.right));
  if (away > near_) return false;
  long mid = flat ? (menu.left + menu.right) / 2 : (menu.top + menu.bottom) / 2;
  long tol = (long)(7 * dpiScaleFor(mon));
  auto centre = [&](const RECT& r) { return flat ? (r.left + r.right) / 2 : (r.top + r.bottom) / 2; };
  auto holds = [&](const RECT& r, long v) { return flat ? v >= r.left && v < r.right : v >= r.top && v < r.bottom; };

  // The quick way: ask for what is at that place.
  POINT at = flat ? POINT{mid, (br.top + br.bottom) / 2} : POINT{(br.left + br.right) / 2, mid};
  ComPtr<IUIAutomationElement> e;
  ComPtr<IUIAutomationTreeWalker> walk;
  a->get_RawViewWalker(&walk);
  if (SUCCEEDED(a->ElementFromPoint(at, &e)) && e && walk) {
    for (int i = 0; i < 6 && e; i++) {
      TaskButton b;
      if (readButton(e.Get(), b)) {
        if (labs(centre(b.rc) - mid) <= tol) {
          out = b;
          return true;
        }
        break;
      }
      ComPtr<IUIAutomationElement> up;
      if (FAILED(walk->GetParentElement(e.Get(), &up))) break;
      e = up;
    }
  }
  std::vector<TaskButton> all;
  buttonsOf(a, bar, all);
  long best = tol + 1;
  bool found = false;
  for (auto& b : all) {
    long d = labs(centre(b.rc) - mid);
    if (d < best) {
      best = d;
      out = b;
      found = true;
    }
  }
  if (found) return true;
  // Pushed inward: only believable when the menu really touches the end of the screen.
  MONITORINFO mi{};
  mi.cbSize = sizeof mi;
  GetMonitorInfoW(mon, &mi);
  long lo = flat ? menu.left - mi.rcMonitor.left : menu.top - mi.rcMonitor.top, hi = flat ? mi.rcMonitor.right - menu.right : mi.rcMonitor.bottom - menu.bottom;
  if (std::min(lo, hi) > 3 * tol || !PtInRect(&br, press)) return false;
  for (auto& b : all)
    if (holds(b.rc, flat ? press.x : press.y) && (flat ? b.rc.right > menu.left && b.rc.left < menu.right : b.rc.bottom > menu.top && b.rc.top < menu.bottom)) {
      out = b;
      return true;
    }
  return false;
}
}  // namespace

std::vector<TaskButton> listTaskButtons() {
  std::vector<TaskButton> v;
  auto a = automation();
  if (a)
    for (HWND bar : taskbars()) buttonsOf(a.Get(), bar, v);
  return v;
}

// Programs without an id of their own are known by their path, with well-known folders written as GUIDs.
static std::wstring pathFromAppId(const std::wstring& id) {
  std::wstring p = id;
  if (!p.empty() && p[0] == L'{') {
    size_t e = p.find(L'}');
    GUID g;
    PWSTR dir = nullptr;
    if (e == std::wstring::npos || FAILED(CLSIDFromString(p.substr(0, e + 1).c_str(), &g)) || FAILED(SHGetKnownFolderPath(g, 0, nullptr, &dir))) {
      CoTaskMemFree(dir);
      return {};
    }
    p = std::wstring(dir) + p.substr(e + 1);
    CoTaskMemFree(dir);
  }
  return p.size() > 4 && p[1] == L':' && fileExists(p) ? p : std::wstring();
}

static AppWindow windowOf(const TaskButton& b) {
  AppWindow w;
  if (b.hwnd) {
    describeWindow(b.hwnd, w);
    return w;
  }
  std::wstring path = pathFromAppId(b.appId);
  if (path.empty()) {
    Pin app;
    app.kind = Pin::Kind::App;
    app.target = b.appId;
    w.aumid = toLower(b.appId);
    w.exe = resolveMatch(app).exe;  // it may have been pinned as a program file
  } else {
    w.exe = toLower(path);
  }
  return w;
}

std::string pinnedAs(const std::vector<Pin>& pins, const TaskButton& b) {
  WindowList one;
  one.wins.push_back(windowOf(b));
  if (one.wins[0].exe.empty() && one.wins[0].aumid.empty()) return {};
  for (auto& p : pins) {
    if (!one.matching(p).empty()) return p.id;
    for (auto& c : p.children)
      if (!one.matching(c).empty()) return c.id;
  }
  return {};
}

bool isOurButton(const TaskButton& b) {
  AppWindow w = windowOf(b);
  return w.aumid == toLower(kAppUserModelId) || toLower(b.appId) == toLower(kAppUserModelId) || toLower(fileName(w.exe)) == L"radialtaskbar.exe";
}

Pin pinFromTaskButton(const TaskButton& b) {
  if (b.hwnd && IsWindow(b.hwnd)) {
    Pin p = pinFromWindow(b.hwnd);
    if (!p.target.empty()) return p;
  }
  if (b.appId.empty()) return {};
  // In the Start menu's list of apps under this very id?
  Pin listed = pinFromAppId(b.appId);
  if (!listed.target.empty()) return listed;
  std::wstring path = pathFromAppId(b.appId);
  if (!path.empty()) return pinFromPath(path);
  // A running window, or a shortcut pinned to the taskbar, that carries the id.
  std::wstring low = toLower(b.appId);
  WindowList wl;
  wl.snapshot();
  for (auto& w : wl.wins)
    if (w.aumid == low) {
      Pin p = pinFromWindow(w.hwnd);
      if (!p.target.empty()) return p;
    }
  for (auto& p : importTaskbarPins())
    if (resolveMatch(p).aumid == low) return p;
  return {};
}

// ---------------------------------------------------------------- the row (helper process)
namespace {
enum class RowState { Add, Remove, Busy, Done, Failed };

struct RowLook {
  COLORREF back = RGB(0xF3, 0xF3, 0xF3);
  bool dark = false;
};

// A profile the app can be added to or removed from.
struct Choice {
  std::string id;
  std::wstring name;
  Color color;
  std::string pinId;                    // set when the app is in it
};

struct Row {
  HWND hwnd = nullptr;
  RowJob job;
  float s = 1.f;
  RECT menuRect{};
  std::wstring menuTitle;
  TaskButton button;
  std::vector<Choice> choices;
  size_t choice = 0;
  mutable RectF chip;                   // the profile's name at the right end, when there is more than one
  bool onChip = false, chipDown = false;
  RowState state = RowState::Add;
  std::wstring line;
  RowLook look;
  bool hover = false, down = false, acted = false, removed = false;
  bool looking = false, known = false;  // working out what exactly to pin
  Pin pin;
  float shown = 0;                      // fade
  ULONGLONG doneAt = 0;
  std::vector<uint32_t> bits;
};

constexpr UINT WM_ROW_READY = WM_APP + 1;   // to a row: its button is known, lParam Resolved*
constexpr UINT WM_ROW_PIN = WM_APP + 2;     // to a row: what to pin is known, lParam Pin*
constexpr UINT WM_ROW_COLOR = WM_APP + 3;   // to a row: wParam the menu's colour, lParam dark
constexpr UINT WM_ROW_GONE = WM_APP + 4;    // to the host: wParam the row's window

struct Resolved {
  bool ok = false;
  TaskButton button;
  std::vector<Choice> choices;
  size_t choice = 0;
};

struct ResolveJob {
  HWND notify = nullptr;
  RECT menu{};
  POINT press{};
};

// The helper process: one hidden window that takes jobs, one thread that talks to the accessibility service.
struct Host {
  HINSTANCE inst = nullptr;
  HWND hwnd = nullptr;
  std::unique_ptr<Row> row;             // at most one
  RowJob waiting;                       // its menu is not on screen yet
  ULONGLONG waitingAt = 0, usedAt = 0;
  bool used = false, oneShot = false, quit = false;
  CRITICAL_SECTION cs;
  HANDLE wake = nullptr;
  ResolveJob next;
  bool hasNext = false;
} g_host;
enum HostTimers : UINT_PTR { kWaitTimer = 1, kIdleTimer };

bool cloaked(HWND h) {
  DWORD c = 0;
  return FAILED(DwmGetWindowAttribute(h, DWMWA_CLOAKED, &c, sizeof c)) || c != 0;
}

bool shellLight() {
  DWORD v = 1, cb = sizeof v;
  RegGetValueW(HKEY_CURRENT_USER, L"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize", L"SystemUsesLightTheme", RRF_RT_REG_DWORD, nullptr, &v, &cb);
  return v != 0;
}

std::wstring lineFor(const Row& r) {
  bool many = r.choices.size() > 1;
  std::wstring where = many ? r.choices[r.choice].name : RT_NAME;
  switch (r.state) {
    case RowState::Add: return L"Add to " RT_NAME;
    case RowState::Remove: return L"Remove from " RT_NAME;
    case RowState::Busy: return L"Adding...";
    case RowState::Done: return (r.removed ? L"Removed from " : L"Added to ") + where;
    default: return L"This one cannot be added";
  }
}

// Draws the row into 32-bit pixels with software Direct2D, so no graphics device is created for it.
bool drawRow(const Row& r, int w, int h, std::vector<uint32_t>& px) {
  auto& g = gfx();
  if (!g.ensureFactories() || w <= 0 || h <= 0) return false;
  BITMAPINFO bi{};
  bi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
  bi.bmiHeader.biWidth = w;
  bi.bmiHeader.biHeight = -h;
  bi.bmiHeader.biPlanes = 1;
  bi.bmiHeader.biBitCount = 32;
  void* bits = nullptr;
  HDC sdc = GetDC(nullptr), dc = CreateCompatibleDC(sdc);
  HBITMAP bm = CreateDIBSection(sdc, &bi, DIB_RGB_COLORS, &bits, nullptr, 0);
  ReleaseDC(nullptr, sdc);
  if (!bm || !dc) {
    if (bm) DeleteObject(bm);
    if (dc) DeleteDC(dc);
    return false;
  }
  HGDIOBJ old = SelectObject(dc, bm);
  auto props = D2D1::RenderTargetProperties(D2D1_RENDER_TARGET_TYPE_SOFTWARE, D2D1::PixelFormat(DXGI_FORMAT_B8G8R8A8_UNORM, D2D1_ALPHA_MODE_IGNORE), 96.f, 96.f);
  ComPtr<ID2D1DCRenderTarget> rt;
  RECT rc{0, 0, w, h};
  bool ok = SUCCEEDED(g.d2d->CreateDCRenderTarget(&props, &rt)) && SUCCEEDED(rt->BindDC(dc, &rc));
  float s = r.s;
  bool dark = r.look.dark;
  Color text = dark ? Color(1, 1, 1) : Color(0.10f, 0.10f, 0.10f);
  RectF icon = RectF::xywh(15.f * s, (float)h * 0.5f - 9.f * s, 18.f * s, 18.f * s);
  bool appIcon = r.state == RowState::Add || r.state == RowState::Busy;
  if (ok) {
    rt->BeginDraw();
    rt->SetTextAntialiasMode(D2D1_TEXT_ANTIALIAS_MODE_GRAYSCALE);
    Color back(GetRValue(r.look.back) / 255.f, GetGValue(r.look.back) / 255.f, GetBValue(r.look.back) / 255.f);
    rt->Clear(back.f());
    ComPtr<ID2D1SolidColorBrush> br;
    rt->CreateSolidColorBrush(text.f(), &br);
    bool click = r.state == RowState::Add || r.state == RowState::Remove;
    auto lit = [&](RectF q, bool press) {
      float a = press ? (dark ? 0.045f : 0.028f) : (dark ? 0.075f : 0.048f);
      br->SetColor((dark ? Color(1, 1, 1, a) : Color(0, 0, 0, a)).f());
      rt->FillRoundedRectangle(D2D1::RoundedRect(q.f(), 4 * s, 4 * s), br.Get());
    };
    if (br && click && (r.hover || r.down) && !r.onChip) lit(RectF(4 * s, 4 * s, w - 4 * s, h - 4 * s), r.down);
    auto put = [&](const std::wstring& t, const wchar_t* family, float size, int weight, RectF q, Color c, Align al) {
      TextStyle ts;
      ts.family = family;
      ts.size = size * s;
      ts.weight = weight;
      ts.align = al;
      auto f = g.format(ts);
      if (!f || !br) return;
      br->SetColor(c.f());
      rt->DrawText(t.c_str(), (UINT32)t.size(), f.Get(), q.f(), br.Get(), D2D1_DRAW_TEXT_OPTIONS_CLIP);
    };
    float right = w - 14 * s;
    r.chip = {};
    if (br && click && r.choices.size() > 1) {
      auto& c = r.choices[r.choice];
      TextStyle small;
      small.size = 12.f * s;
      float nw = 0;  // as wide as the widest name, so it stays put while it is clicked through
      for (auto& q : r.choices) nw = std::max(nw, std::min(62.f * s, g.measure(q.name, small).x + 2.f * s));
      r.chip = RectF(w - 8 * s - (nw + 36 * s), 7 * s, w - 8 * s, h - 7 * s);
      if (r.onChip) lit(r.chip, r.chipDown);
      float cy = h * 0.5f, x = r.chip.l + 8 * s;
      br->SetColor(c.color.f());
      rt->FillEllipse(D2D1::Ellipse(D2D1::Point2F(x + 3.5f * s, cy), 3.5f * s, 3.5f * s), br.Get());
      x += 12 * s;
      put(c.name, L"Segoe UI Variable Text", 12.f, 400, RectF(x, 0, x + nw, h - 1.f * s), text.withA(r.onChip ? 0.9f : 0.62f), Align::Left);
      put(L"\xE70D", L"Segoe Fluent Icons", 8.f, 400, RectF(x + nw, 0, r.chip.r - 2 * s, (float)h), text.withA(r.onChip ? 0.9f : 0.55f), Align::Center);
      right = r.chip.l - 2 * s;
    }
    put(r.line, L"Segoe UI Variable Text", 14.f, 400, RectF(44 * s, 0, right, h - 1.f * s), text.withA(r.state == RowState::Failed ? 0.7f : 0.92f), Align::Left);
    if (!appIcon) {
      const wchar_t* glyph = r.state == RowState::Remove ? L"\xE77A" : r.state == RowState::Done ? L"\xE73E" : L"\xE783";
      Color gc = r.state == RowState::Done ? (dark ? Color::hex(0x6CCB8A) : Color::hex(0x107C41)) : text.withA(0.9f);
      put(glyph, L"Segoe Fluent Icons", 16.f, 400, icon.inset(-4 * s), gc, Align::Center);
    }
    ok = SUCCEEDED(rt->EndDraw());
  }
  if (ok && appIcon) {
    int q = (int)lroundf(icon.w());
    if (HICON hi = (HICON)LoadImageW(GetModuleHandleW(nullptr), MAKEINTRESOURCEW(1), IMAGE_ICON, q, q, LR_DEFAULTCOLOR)) {
      DrawIconEx(dc, (int)icon.l, (int)icon.t, hi, q, q, 0, nullptr, DI_NORMAL);
      DestroyIcon(hi);
    }
  }
  GdiFlush();
  if (ok) {
    px.resize((size_t)w * h);
    memcpy(px.data(), bits, px.size() * 4);
    for (auto& v : px) v |= 0xFF000000u;
  }
  SelectObject(dc, old);
  DeleteObject(bm);
  DeleteDC(dc);
  return ok;
}

void blit(HDC dc, const std::vector<uint32_t>& px, int w, int h) {
  BITMAPINFO bi{};
  bi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
  bi.bmiHeader.biWidth = w;
  bi.bmiHeader.biHeight = -h;
  bi.bmiHeader.biPlanes = 1;
  bi.bmiHeader.biBitCount = 32;
  SetDIBitsToDevice(dc, 0, 0, (DWORD)w, (DWORD)h, 0, 0, 0, (UINT)h, px.data(), &bi, DIB_RGB_COLORS);
}

RECT rowRect(const Row& r) {
  // The menu's window has a clear margin of 12 units around the visible panel.
  float s = r.s;
  int m = (int)lroundf(12 * s), gap = (int)lroundf(8 * s), h = (int)lroundf(40 * s);
  RECT panel{r.menuRect.left + m, r.menuRect.top + m, r.menuRect.right - m, r.menuRect.bottom - m};
  MONITORINFO mi{};
  mi.cbSize = sizeof mi;
  GetMonitorInfoW(MonitorFromRect(&r.menuRect, MONITOR_DEFAULTTONEAREST), &mi);
  int w = std::max<int>(panel.right - panel.left, (int)(232 * s));
  // Above the menu; below it when the taskbar is at the top; beside it when the menu fills the height.
  bool barOnTop = panel.top - mi.rcWork.top < (int)(40 * s) && panel.bottom < mi.rcWork.bottom - (int)(120 * s);
  RECT o{panel.left, panel.top - gap - h, panel.left + w, panel.top - gap};
  if (barOnTop) o = {panel.left, panel.bottom + gap, panel.left + w, panel.bottom + gap + h};
  else if (o.top < mi.rcWork.top + (int)(4 * s)) {
    o = {r.menuRect.right, panel.bottom - h, r.menuRect.right + w, panel.bottom};
    if (o.right > mi.rcWork.right) o = {r.menuRect.left - w, panel.bottom - h, r.menuRect.left, panel.bottom};
  }
  return o;
}

void place(Row& r) {
  RECT q = rowRect(r);
  SetWindowPos(r.hwnd, HWND_TOPMOST, q.left, q.top, q.right - q.left, q.bottom - q.top, SWP_NOACTIVATE);
}

void setState(Row& r, RowState st) {
  r.state = st;
  r.line = lineFor(r);
  InvalidateRect(r.hwnd, nullptr, FALSE);
}

// Takes the menu's own background colour, so the row looks like part of it whatever skin is in use. The menu fades
// in over its first moments, so this follows along for a while. Reading the screen can wait for a frame: own thread.
struct Sampler {
  HWND row;
  RECT menu;
  float s;
};
unsigned __stdcall sampleThread(void* arg) {
  std::unique_ptr<Sampler> q((Sampler*)arg);
  int m = (int)lroundf(12 * q->s);
  int h = q->menu.bottom - q->menu.top - 2 * m - (int)(24 * q->s), x = q->menu.left + m + std::max(2, (int)lroundf(2.5f * q->s)), y = q->menu.top + m + (int)(12 * q->s);
  if (h < 8) return 0;
  BITMAPINFO bi{};
  bi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
  bi.bmiHeader.biWidth = 1;
  bi.bmiHeader.biHeight = -h;
  bi.bmiHeader.biPlanes = 1;
  bi.bmiHeader.biBitCount = 32;
  void* bits = nullptr;
  HDC sdc = GetDC(nullptr), dc = CreateCompatibleDC(sdc);
  HBITMAP bm = CreateDIBSection(sdc, &bi, DIB_RGB_COLORS, &bits, nullptr, 0);
  if (bm && dc) {
    HGDIOBJ old = SelectObject(dc, bm);
    for (int i = 0; i < 12 && IsWindow(q->row); i++) {
      if (i) Sleep(35);
      if (!BitBlt(dc, 0, 0, 1, h, sdc, x, y, SRCCOPY)) break;
      GdiFlush();
      // The median of each channel: a lit entry along the way does not matter.
      std::vector<int> c[3];
      for (int k = 0; k < h; k++) {
        uint32_t v = ((uint32_t*)bits)[k];
        c[0].push_back((int)((v >> 16) & 255));
        c[1].push_back((int)((v >> 8) & 255));
        c[2].push_back((int)(v & 255));
      }
      int med[3];
      for (int k = 0; k < 3; k++) {
        std::nth_element(c[k].begin(), c[k].begin() + h / 2, c[k].end());
        med[k] = c[k][(size_t)h / 2];
      }
      bool dark = 0.2126f * med[0] + 0.7152f * med[1] + 0.0722f * med[2] < 128;
      if (!PostMessageW(q->row, WM_ROW_COLOR, RGB(med[0], med[1], med[2]), dark)) break;
    }
    SelectObject(dc, old);
  }
  if (bm) DeleteObject(bm);
  if (dc) DeleteDC(dc);
  ReleaseDC(nullptr, sdc);
  return 0;
}

// Stays alive between menus, with its connection to the taskbar already made.
unsigned __stdcall resolveThread(void*) {
  CoInitializeEx(nullptr, COINIT_MULTITHREADED);
  auto a = automation();
  if (a)
    for (HWND bar : taskbars()) {
      ComPtr<IUIAutomationElement> e;
      a->ElementFromHandle(bar, &e);
    }
  for (;;) {
    WaitForSingleObject(g_host.wake, INFINITE);
    EnterCriticalSection(&g_host.cs);
    bool has = g_host.hasNext;
    ResolveJob j = g_host.next;
    g_host.hasNext = false;
    bool quit = g_host.quit;
    LeaveCriticalSection(&g_host.cs);
    if (quit) break;
    if (!has) continue;
    auto* out = new Resolved;
    double t0 = nowSec();
    Config cfg;
    out->ok = a && buttonFor(a.Get(), j.menu, j.press, out->button) && !isOurButton(out->button) && cfg.load(4) == Config::Load::Ok;
    double t1 = nowSec();
    if (out->ok) {
      forgetMatches();
      cfg.profile();  // makes sure there is one, and a valid index
      for (auto& p : cfg.profiles) out->choices.push_back({p.id, p.name, p.color, pinnedAs(p.pins, out->button)});
      out->choice = (size_t)cfg.activeProfile;
    }
    logf("row: button %s in %.0f ms, match %.0f ms", out->ok ? "found" : "not found", (t1 - t0) * 1000, (nowSec() - t1) * 1000);
    if (!PostMessageW(j.notify, WM_ROW_READY, 0, (LPARAM)out)) delete out;
  }
  a.Reset();
  CoUninitialize();
  return 0;
}

struct PinJob {
  HWND notify;
  TaskButton button;
};
unsigned __stdcall lookThread(void* arg) {
  std::unique_ptr<PinJob> j((PinJob*)arg);
  CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED | COINIT_DISABLE_OLE1DDE);
  auto* p = new Pin(pinFromTaskButton(j->button));
  if (!PostMessageW(j->notify, WM_ROW_PIN, 0, (LPARAM)p)) delete p;
  CoUninitialize();
  return 0;
}

// Going through the installed apps can take a moment, so it starts when the pointer arrives, not on the click.
void lookUp(Row& r) {
  if (r.looking || r.known || r.state == RowState::Remove) return;
  auto* j = new PinJob{r.hwnd, r.button};
  uintptr_t t = _beginthreadex(nullptr, 0, lookThread, j, 0, nullptr);
  if (t) {
    CloseHandle((HANDLE)t);
    r.looking = true;
  } else {
    delete j;
    r.known = true;
  }
}

void finishRow(Row& r, bool ok) {
  logf("row: %s", ok ? "done" : "failed");
  r.removed = r.state == RowState::Remove;
  setState(r, ok ? RowState::Done : RowState::Failed);
  r.doneAt = GetTickCount64();
}

void addNow(Row& r) { finishRow(r, !r.pin.target.empty() && sendCommand(L"addpin", widen(pinText(r.pin, r.choices[r.choice].id)), true)); }

void nextProfile(Row& r) {
  if (r.acted || r.choices.size() < 2) return;
  r.choice = (r.choice + 1) % r.choices.size();
  setState(r, r.choices[r.choice].pinId.empty() ? RowState::Add : RowState::Remove);
  lookUp(r);
}

void act(Row& r) {
  if (r.acted || r.choices.empty() || (r.state != RowState::Add && r.state != RowState::Remove)) return;
  r.acted = true;
  // The click brought us to the front (and closed Windows' menu): give the focus back to whoever had it before.
  HWND prev = r.job.prev;
  HWND back = prev && IsWindow(prev) && IsWindowVisible(prev) && !IsIconic(prev) ? prev : GetShellWindow();
  if (back) SetForegroundWindow(back);
  if (r.state == RowState::Remove) {
    finishRow(r, sendCommand(L"unpin", widen(r.choices[r.choice].pinId), true));
  } else if (r.known) {
    addNow(r);
  } else {
    setState(r, RowState::Busy);
    lookUp(r);
  }
}

LRESULT CALLBACK rowProc(HWND h, UINT m, WPARAM w, LPARAM l) {
  if (m == WM_NCCREATE) {
    auto* n = (Row*)((CREATESTRUCTW*)l)->lpCreateParams;
    n->hwnd = h;
    SetWindowLongPtrW(h, GWLP_USERDATA, (LONG_PTR)n);
  }
  auto* r = (Row*)GetWindowLongPtrW(h, GWLP_USERDATA);
  if (!r) return DefWindowProcW(h, m, w, l);
  switch (m) {
    case WM_MOUSEACTIVATE: {
      // Losing the focus is what closes Windows' own menu. Picking a profile is not the end yet, so it must not.
      POINT p;
      GetCursorPos(&p);
      ScreenToClient(h, &p);
      return r->chip.contains({(float)p.x, (float)p.y}) ? MA_NOACTIVATE : MA_ACTIVATE;
    }
    case WM_ERASEBKGND: return 1;
    case WM_PAINT: {
      PAINTSTRUCT ps;
      HDC dc = BeginPaint(h, &ps);
      RECT c;
      GetClientRect(h, &c);
      if (drawRow(*r, c.right, c.bottom, r->bits)) blit(dc, r->bits, c.right, c.bottom);
      EndPaint(h, &ps);
      return 0;
    }
    case WM_SETCURSOR:
      SetCursor(LoadCursorW(nullptr, IDC_ARROW));
      return TRUE;
    case WM_MOUSEMOVE: {
      TRACKMOUSEEVENT t{sizeof t, TME_LEAVE, h, 0};
      TrackMouseEvent(&t);
      bool chip = r->chip.contains({(float)GET_X_LPARAM(l), (float)GET_Y_LPARAM(l)});
      if (!r->hover || chip != r->onChip) {
        r->hover = true;
        r->onChip = chip;
        InvalidateRect(h, nullptr, FALSE);
        lookUp(*r);
      }
      return 0;
    }
    case WM_MOUSELEAVE:
      r->hover = r->down = r->onChip = r->chipDown = false;
      InvalidateRect(h, nullptr, FALSE);
      return 0;
    case WM_LBUTTONDOWN:
      r->onChip = r->chip.contains({(float)GET_X_LPARAM(l), (float)GET_Y_LPARAM(l)});
      (r->onChip ? r->chipDown : r->down) = true;
      InvalidateRect(h, nullptr, FALSE);
      return 0;
    case WM_LBUTTONUP: {
      RECT c;
      GetClientRect(h, &c);
      POINT p{GET_X_LPARAM(l), GET_Y_LPARAM(l)};
      bool chip = r->chip.contains({(float)p.x, (float)p.y});
      bool hit = r->down && !chip && PtInRect(&c, p), pick = r->chipDown && chip;
      r->down = r->chipDown = false;
      if (pick) nextProfile(*r);
      else if (hit) act(*r);
      InvalidateRect(h, nullptr, FALSE);
      return 0;
    }
    case WM_ROW_COLOR: {
      bool dark = l != 0;
      if ((COLORREF)w == r->look.back && dark == r->look.dark) return 0;
      if (dark != r->look.dark) {
        BOOL d = dark;
        DwmSetWindowAttribute(h, DWMWA_USE_IMMERSIVE_DARK_MODE, &d, sizeof d);
      }
      r->look.back = (COLORREF)w;
      r->look.dark = dark;
      InvalidateRect(h, nullptr, FALSE);
      return 0;
    }
    case WM_ROW_READY: {
      std::unique_ptr<Resolved> d((Resolved*)l);
      if (!d->ok || cloaked(r->job.menu)) {
        DestroyWindow(h);
        return 0;
      }
      r->button = d->button;
      r->choices = d->choices;
      r->choice = std::min(d->choice, d->choices.size() - 1);
      setState(*r, r->choices[r->choice].pinId.empty() ? RowState::Add : RowState::Remove);
      place(*r);
      SetLayeredWindowAttributes(h, 0, 0, LWA_ALPHA);
      ShowWindow(h, SW_SHOWNOACTIVATE);
      UpdateWindow(h);
      logf("row: shown %s", r->state == RowState::Add ? "add" : "remove");
      SetTimer(h, 1, 15, nullptr);
      return 0;
    }
    case WM_ROW_PIN: {
      std::unique_ptr<Pin> p((Pin*)l);
      r->pin = *p;
      r->known = true;
      if (r->state == RowState::Busy) addNow(*r);
      return 0;
    }
    case WM_TIMER: {
      ULONGLONG now = GetTickCount64();
      bool leaving = false;
      if (r->acted) {
        leaving = r->doneAt && now - r->doneAt > 1100;
      } else if (!r->down && !r->chipDown) {
        wchar_t title[256] = {};
        InternalGetWindowText(r->job.menu, title, 256);
        RECT q{};
        if (!IsWindow(r->job.menu) || cloaked(r->job.menu) || r->menuTitle != title) {
          DestroyWindow(h);
          return 0;
        }
        if (GetWindowRect(r->job.menu, &q) && !EqualRect(&q, &r->menuRect)) {
          r->menuRect = q;
          place(*r);
        }
      }
      float want = leaving ? 0.f : 1.f;
      if (r->shown != want) {
        r->shown = want > r->shown ? std::min(1.f, r->shown + 0.20f) : std::max(0.f, r->shown - 0.12f);
        SetLayeredWindowAttributes(h, 0, (BYTE)lroundf(255 * smooth01(r->shown)), LWA_ALPHA);
        if (leaving && r->shown <= 0.f) DestroyWindow(h);
      }
      return 0;
    }
    case WM_CLOSE:
      if (!r->acted) DestroyWindow(h);
      return 0;
    case WM_NCDESTROY:
      SetWindowLongPtrW(h, GWLP_USERDATA, 0);
      PostMessageW(g_host.hwnd, WM_ROW_GONE, (WPARAM)h, 0);
      return 0;
  }
  return DefWindowProcW(h, m, w, l);
}

// The menu is on screen: make its row and ask which button this is about.
void beginRow() {
  auto row = std::make_unique<Row>();
  row->job = g_host.waiting;
  wchar_t title[256] = {};
  InternalGetWindowText(row->job.menu, title, 256);
  row->menuTitle = title;
  GetWindowRect(row->job.menu, &row->menuRect);
  row->s = dpiScaleFor(MonitorFromRect(&row->menuRect, MONITOR_DEFAULTTONEAREST));
  row->look.dark = !shellLight();
  if (row->look.dark) row->look.back = RGB(0x2C, 0x2C, 0x2C);
  RECT q = rowRect(*row);
  HWND h = CreateWindowExW(WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_LAYERED, rowClass().c_str(), L"Add to " RT_NAME, WS_POPUP, q.left, q.top, q.right - q.left,
                           q.bottom - q.top, nullptr, nullptr, g_host.inst, row.get());
  if (!h) return;
  int corner = 2;  // round, like the menu
  DwmSetWindowAttribute(h, DWMWA_WINDOW_CORNER_PREFERENCE, &corner, sizeof corner);
  BOOL dark = row->look.dark;
  DwmSetWindowAttribute(h, DWMWA_USE_IMMERSIVE_DARK_MODE, &dark, sizeof dark);
  auto* s = new Sampler{h, row->menuRect, row->s};
  uintptr_t t = _beginthreadex(nullptr, 0, sampleThread, s, 0, nullptr);
  if (t) CloseHandle((HANDLE)t);
  else delete s;
  EnterCriticalSection(&g_host.cs);
  g_host.next = ResolveJob{h, row->menuRect, row->job.press};
  g_host.hasNext = true;
  LeaveCriticalSection(&g_host.cs);
  SetEvent(g_host.wake);
  g_host.row = std::move(row);
}

void takeJob(const RowJob& j) {
  if (g_host.row) {
    HWND old = g_host.row->hwnd;
    DestroyWindow(old);
    g_host.row.reset();
  }
  g_host.waiting = j;
  g_host.waitingAt = g_host.usedAt = GetTickCount64();
  g_host.used = true;
  SetTimer(g_host.hwnd, kWaitTimer, 10, nullptr);
}

LRESULT CALLBACK hostProc(HWND h, UINT m, WPARAM w, LPARAM l) {
  switch (m) {
    case WM_COPYDATA: {
      auto* cd = (COPYDATASTRUCT*)l;
      if (!cd || cd->dwData != kRowJob || cd->cbData != sizeof(RowJob)) return FALSE;
      RowJob j;
      memcpy(&j, cd->lpData, sizeof j);
      ReplyMessage(TRUE);
      takeJob(j);
      return TRUE;
    }
    case WM_TIMER:
      if (w == kWaitTimer) {
        // Windows prepares the menu hidden and reveals it once it has its final size.
        HWND menu = g_host.waiting.menu;
        bool gone = !IsWindow(menu) || GetTickCount64() - g_host.waitingAt > 1500;
        if (!gone && cloaked(menu)) return 0;
        KillTimer(h, kWaitTimer);
        if (!gone) beginRow();
        if (!g_host.row && g_host.oneShot) PostQuitMessage(0);
      } else if (w == kIdleTimer) {
        ULONGLONG idle = GetTickCount64() - g_host.usedAt;
        if (!g_host.row && idle > (g_host.used ? 120000u : 30000u)) PostQuitMessage(0);
      }
      return 0;
    case WM_ROW_GONE:
      if (g_host.row && g_host.row->hwnd == (HWND)w) g_host.row.reset();
      g_host.usedAt = GetTickCount64();
      if (g_host.oneShot && !g_host.row) PostQuitMessage(0);
      return 0;
  }
  return DefWindowProcW(h, m, w, l);
}
}  // namespace

int runTaskbarRow(HINSTANCE inst, const Args& args) {
  std::wstring direct = args.get(L"--taskbar-row");
  g_host.oneShot = !direct.empty() && direct[0] != L'-';  // a check names the menu itself
  if (!g_host.oneShot && findHost()) return 0;
  g_host.inst = inst;
  g_host.usedAt = GetTickCount64();
  InitializeCriticalSection(&g_host.cs);
  g_host.wake = CreateEventW(nullptr, FALSE, FALSE, nullptr);

  WNDCLASSEXW wc{};
  wc.cbSize = sizeof wc;
  wc.lpfnWndProc = hostProc;
  wc.hInstance = inst;
  std::wstring hc = hostClass() + (g_host.oneShot ? L".check" : L"");
  wc.lpszClassName = hc.c_str();
  RegisterClassExW(&wc);
  WNDCLASSEXW rc{};
  rc.cbSize = sizeof rc;
  rc.style = CS_DROPSHADOW;
  rc.lpfnWndProc = rowProc;
  rc.hInstance = inst;
  std::wstring rn = rowClass();
  rc.lpszClassName = rn.c_str();
  RegisterClassExW(&rc);
  uintptr_t t = _beginthreadex(nullptr, 0, resolveThread, nullptr, 0, nullptr);
  if (!t) return 1;
  {
    Row first;  // loads the fonts, so the first real row is drawn at once
    first.line = lineFor(first);
    drawRow(first, 294, 40, first.bits);
    first.state = RowState::Remove;
    drawRow(first, 294, 40, first.bits);
  }
  // Only now can it be found: the resident never has to wait for us.
  g_host.hwnd = CreateWindowExW(0, hc.c_str(), L"", 0, 0, 0, 0, 0, HWND_MESSAGE, nullptr, inst, nullptr);
  if (!g_host.hwnd) return 1;
  SetTimer(g_host.hwnd, kIdleTimer, 5000, nullptr);
  if (g_host.oneShot) {
    RowJob j;
    j.menu = (HWND)(uintptr_t)wcstoull(direct.c_str(), nullptr, 10);
    j.prev = (HWND)(uintptr_t)wcstoull(args.get(L"--prev").c_str(), nullptr, 10);
    j.press = {args.num(L"--x", 0), args.num(L"--y", 0)};
    takeJob(j);
  }
  MSG m;
  while (GetMessageW(&m, nullptr, 0, 0) > 0) {
    TranslateMessage(&m);
    DispatchMessageW(&m);
  }
  if (g_host.row) DestroyWindow(g_host.row->hwnd);
  EnterCriticalSection(&g_host.cs);
  g_host.quit = true;
  LeaveCriticalSection(&g_host.cs);
  SetEvent(g_host.wake);
  WaitForSingleObject((HANDLE)t, 800);
  CloseHandle((HANDLE)t);
  return 0;
}

int runRowShot(const Args& a) {
  Row r;
  r.s = a.real(L"--dpi", 1.f);
  r.look.dark = a.has(L"--dark");
  r.look.back = r.look.dark ? RGB(0x2C, 0x2C, 0x2C) : RGB(0xD9, 0xD9, 0xD9);
  r.state = (RowState)clampi(a.num(L"--state", 0), 0, 4);
  if (a.has(L"--profile")) {
    r.choices.push_back({"a", a.get(L"--profile"), Color::hex(0x4CA8FF), ""});
    r.choices.push_back({"b", L"Games", Color::hex(0xFF8A4C), ""});
  }
  r.removed = a.has(L"--removed");
  r.line = lineFor(r);
  r.hover = a.has(L"--hover");
  r.onChip = a.has(L"--chip");
  int w = (int)(294 * r.s), h = (int)(40 * r.s);
  std::vector<uint32_t> px;
  if (!drawRow(r, w, h, px) || !gfx().ensure()) return 1;
  auto b = gfx().bitmap(px.data(), w, h, w * 4);
  auto t = gfx().target(w, h);
  if (!b || !t) return 2;
  auto* dc = gfx().dc.Get();
  dc->SetTarget(t.Get());
  dc->BeginDraw();
  dc->DrawBitmap(b.Get());
  dc->EndDraw();
  dc->SetTarget(nullptr);
  return savePng(t.Get(), a.get(L"--row-shot")) ? 0 : 3;
}

std::string describeTaskButtons(const Config& cfg) {
  std::string out = "TASKBAR BUTTONS\n";
  double t0 = nowSec();
  auto all = listTaskButtons();
  out += "listed in " + std::to_string((int)((nowSec() - t0) * 1000)) + " ms\n";
  for (auto& b : all) {
    double t1 = nowSec();
    std::string id = pinnedAs(cfg.profile().pins, b);
    double t2 = nowSec();
    Pin p = pinFromTaskButton(b);
    static const char* kinds[] = {"app", "file", "url", "group"};
    // Window titles can be private, so only the program is written down.
    out += (b.hwnd ? "window " : "app " + narrow(b.appId)) + " | " + (isOurButton(b) ? "OURS" : id.empty() ? "not pinned" : "pinned") + " | " + kinds[(int)p.kind] + " '" + narrow(p.name) +
           "' -> " + narrow(p.target) + " | match " + std::to_string((int)((t2 - t1) * 1000)) + " ms, pin " + std::to_string((int)((nowSec() - t2) * 1000)) + " ms\n";
  }
  return out;
}

}  // namespace rt
