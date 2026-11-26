// Settings: profiles and their skins, news and updates, help, and about.
#include "app.h"
#include "settings.h"
#include "skin.h"

namespace rt {

namespace {
// What changed, newest first. Plain words: no links.
struct Change {
  const wchar_t* version;
  const wchar_t* when;
  std::vector<const wchar_t*> lines;
};
const Change kChanges[] = {
    {L"1.0.0", L"November 2026",
     {L"The first public version, and the first with skins: 30 come with it, each with its own artwork, motion, lettering and sounds. More can be imported as .rskin files, tuned in hue, saturation and brightness, and removed again.",
      L"Every profile can use the main skin, no skin, or a skin of its own. Layout, size and effects stay the same for all of them, and the centre keeps its size from one profile to the next.",
      L"Profiles can be locked: the wheel and scrolling skip them until you unlock them. One always stays unlocked.",
      L"Items move or copy to another profile from their right-click menu, or by dragging them onto that profile.",
      L"Apps, files and websites added while a group is open go straight into it, and pinned items move in with one click.",
      L"Twelve layouts, from the wheel to a dock strip, a carousel, a galaxy and a drum.",
      L"The wheel opens at the mouse pointer, and the scrolling direction can be reversed.",
      L"News, Help and About in the settings, and Uninstall.exe in the program folder.",
      L"It replaces the first Radial Taskbar and the test version Radial Taskbar 2, and takes over their pins."}},
};

void copyText(HWND h, const std::wstring& s) {
  if (!OpenClipboard(h)) return;
  EmptyClipboard();
  size_t cb = (s.size() + 1) * sizeof(wchar_t);
  if (HGLOBAL g = GlobalAlloc(GMEM_MOVEABLE, cb)) {
    if (void* q = GlobalLock(g)) {
      memcpy(q, s.c_str(), cb);
      GlobalUnlock(g);
      if (!SetClipboardData(CF_UNICODETEXT, g)) GlobalFree(g);
    }
  }
  CloseClipboard();
}

const wchar_t* const kSupportName = L"Radoslav Stefanov";
const wchar_t* const kSupportMail = L"RadoslavStefanov89@gmail.com";
}  // namespace

// Wrapped text in the column, moving it down.
float SettingsWindow::para(std::wstring_view s, float size, int weight, float indent) {
  float w = std::max(40.f, c_.w - 4 - indent);
  float h = ui.textHeight(s, size, w, weight);
  ui.text(RectF(c_.x + 2 + indent, c_.y, c_.x + 2 + indent + w, c_.y + h + 4), s, size, ui.pal.text, weight, Align::Left, VAlign::Top, true);
  c_.y += h + 7;
  return h;
}

// A small picture of a skin, or of the own style for none.
void SettingsWindow::skinThumb(RectF r, const std::string& id) {
  const SkinInfo* k = id.empty() ? nullptr : skins().info(id);
  ID2D1Bitmap1* b = k ? skinPreview(*k, r.w() * 1.5f) : nullptr;
  if (b) {
    D2D1_SIZE_F z = b->GetSize();
    float q = std::max(r.w() / z.width, r.h() / z.height);
    auto br = ui.p->image(b, {r.cx() - z.width * q * 0.5f, r.cy() - z.height * q * 0.5f}, q, 1.f);
    ui.p->rrect(r, 6, br.Get());
  } else if (k) {
    auto bg = ui.p->linear({r.l, r.t}, {r.r, r.b}, {{0, Color::hex(0x3A4660)}, {1, Color::hex(0x22283A)}});
    ui.p->rrect(r, 6, bg.Get());
    ui.glyph(r, L"\xE771", 16.f, Color(1, 1, 1, 0.6f));
  } else {
    thumb(ui.id("rowlook", rev_), r, 2, [&] { drawLookThumb(r, app_.cfg.style, 0); });
  }
  ui.p->rrectStroke(r.inset(0.5f), 6, ui.pal.stroke, 1);
}

// ---------------------------------------------------------------- profiles
void SettingsWindow::pageProfiles(RectF) {
  Config& k = app_.cfg;
  if (nowSec() - skinListAt_ > 1.5 && !headless_) {
    skinListAt_ = nowSec();
    if (skins().refreshIfChanged()) skinPics_.clear();
  }
  std::vector<std::string> ids;
  std::vector<std::wstring> names;
  for (auto& q : skins().list())
    if (q.error.empty() && !k.hidden(q.id)) {
      ids.push_back(q.id);
      names.push_back(q.name);
    }
  auto indexOf = [&](const std::string& id) {
    for (size_t i = 0; i < ids.size(); i++)
      if (ids[i] == id) return (int)i;
    return -1;
  };
  auto nameOf = [&](const std::string& id) -> std::wstring {
    if (id.empty()) return L"No skin";
    int i = indexOf(id);
    return i >= 0 ? names[(size_t)i] : widen(id);
  };
  float cw = std::min(270.f, c_.w * 0.42f);

  section(L"Main skin", L"Every profile set to Use main shows it. Layout, size and effects are the same for all profiles.");
  {
    RectF r = RectF::xywh(c_.x, c_.y, c_.w, 68);
    c_.y += 72;
    ui.card(r, 8);
    RectF pic = RectF::xywh(r.l + 10, r.t + 9, 66, 50);
    skinThumb(pic, k.skin);
    RectF cb(r.r - 14 - cw, r.cy() - 17, r.r - 14, r.cy() + 17);
    int users = 0;
    for (auto& p : k.profiles) users += p.skin.empty();
    ui.text(RectF(pic.r + 14, r.t + 12, cb.l - 12, r.t + 34), nameOf(k.skin), 14.f, ui.pal.text, 600);
    std::wstring sub = users == (int)k.profiles.size() ? L"Used by every profile" : users == 0 ? L"No profile uses it now" : L"Used by " + std::to_wstring(users) + L" of " + std::to_wstring(k.profiles.size()) + L" profiles";
    ui.text(RectF(pic.r + 14, r.t + 34, cb.l - 12, r.b - 10), sub, 12.f, ui.pal.dim);
    std::vector<std::wstring> opts{L"No skin"};
    opts.insert(opts.end(), names.begin(), names.end());
    int idx = k.skin.empty() ? 0 : indexOf(k.skin) >= 0 ? 1 + indexOf(k.skin) : -1;
    if (ui.combo(ui.id("mainskin"), cb, idx, opts) && idx >= 0) {
      k.skin = idx == 0 ? std::string() : ids[(size_t)idx - 1];
      changed();
    }
  }

  section(L"Profiles", L"Each can use the main skin, no skin, or one of its own. A locked profile stays off the wheel.");
  for (int i = 0; i < (int)k.profiles.size(); i++) {
    Profile& p = k.profiles[(size_t)i];
    RectF r = RectF::xywh(c_.x, c_.y, c_.w, 68);
    c_.y += 72;
    if (r.b < ui.view.t - 100 || r.t > ui.view.b + 100) continue;
    ui.card(r, 8);
    if (i == k.activeProfile) ui.p->rrect(RectF(r.l, r.t + 12, r.l + 3, r.b - 12), 1.5f, p.color);
    RectF pic = RectF::xywh(r.l + 10, r.t + 9, 66, 50);
    skinThumb(pic, k.skinFor(p));
    RectF cb(r.r - 14 - cw, r.cy() - 17, r.r - 14, r.cy() + 17);
    RectF lock(cb.l - 44, r.cy() - 17, cb.l - 10, r.cy() + 17);
    float tx = pic.r + 14;
    ui.p->circle({tx + 5, r.t + 23}, 5, p.locked ? p.color.withA(0.45f) : p.color);
    ui.text(RectF(tx + 16, r.t + 12, lock.l - 8, r.t + 34), p.name, 14.f, ui.pal.text, 600);
    size_t items = 0;
    for (auto& q : p.pins) items += q.kind == Pin::Kind::Group ? q.children.size() : 1;
    std::wstring sub = std::to_wstring(items) + (items == 1 ? L" item" : L" items");
    if (p.locked) sub += L"  \x00B7  locked, the wheel skips it";
    if (i == k.activeProfile) sub += L"  \x00B7  in use";
    ui.text(RectF(tx, r.t + 34, lock.l - 8, r.b - 10), sub, 12.f, ui.pal.dim);
    bool onlyOpen = !p.locked && k.unlockedCount() < 2;
    if (p.locked) ui.p->rrect(lock, 6, ui.pal.accent.withA(0.16f));
    if (ui.iconButton(ui.id("plk", i), lock, p.locked ? L"\xE72E" : L"\xE785",
                      p.locked ? L"Locked. Click to put it back on the wheel" : onlyOpen ? L"The wheel needs one profile that is not locked" : L"Lock: keep it off the wheel", p.locked || !onlyOpen))
      after([this, i, on = !p.locked] { setLocked(i, on); });
    std::vector<std::wstring> opts{L"Use main (" + nameOf(k.skin) + L")", L"No skin"};
    opts.insert(opts.end(), names.begin(), names.end());
    int idx = p.skin.empty() ? 0 : p.skin == Config::kNoSkin ? 1 : indexOf(p.skin) >= 0 ? 2 + indexOf(p.skin) : -1;
    if (ui.combo(ui.id("pskin", i), cb, idx, opts) && idx >= 0) {
      p.skin = idx == 0 ? std::string() : idx == 1 ? std::string(Config::kNoSkin) : ids[(size_t)idx - 2];
      changed();
    }
  }

  section(L"Switching");
  toggleRow("revscroll", L"Reverse scroll direction", L"Turning the mouse wheel down goes back a profile instead of forward", k.reverseScroll);
  toggleRow("hubp2", L"Profiles around the centre", L"Click one to switch to it. Q and E switch too", k.hubProfiles);
}

// ---------------------------------------------------------------- news
void SettingsWindow::startSetup(const std::wstring& file) {
  HINSTANCE r = ShellExecuteW(hwnd_, nullptr, file.c_str(), nullptr, dirName(file).c_str(), SW_SHOWNORMAL);
  say((INT_PTR)r > 32 ? L"The setup is starting" : L"The setup could not be started");
}

void SettingsWindow::pageNews(RectF) {
  Updater::Now u = updater_.now();
  using S = Updater::State;
  if (u.state == S::Ready && setupFor_ != u.file) {  // downloaded: the setup takes over, once
    setupFor_ = u.file;
    after([this, f = u.file] { startSetup(f); });
  }
  section(L"Updates", L"Only looks when you press the button. Your pins and settings stay when you update.");
  {
    RectF r = RectF::xywh(c_.x, c_.y, c_.w, 88);
    c_.y += 92;
    ui.card(r, 8);
    float bw = 200;
    RectF b(r.r - bw - 16, r.cy() - 18, r.r - 16, r.cy() + 18);
    bool busy = u.state == S::Checking || u.state == S::Downloading;
    if (busy) {
      spinner({r.l + 34, r.cy()}, 12);
      ui.animating = true;
    } else {
      ui.glyph(RectF(r.l + 14, r.t, r.l + 54, r.b), u.state == S::Available ? L"\xE896" : u.state == S::Failed ? L"\xE7BA" : L"\xE895", 22.f, u.state == S::Failed ? ui.pal.danger : ui.pal.accent);
    }
    auto mb = [](uint64_t n) {
      wchar_t t[32];
      swprintf(t, 32, L"%.1f MB", n / 1048576.0);
      return std::wstring(t);
    };
    std::wstring line;
    switch (u.state) {
      case S::Idle: line = L"You have version " + widen(RT_VERSION_STR) + L". Press the button to look for a newer one."; break;
      case S::Checking: line = L"Looking for a newer version..."; break;
      case S::Latest: line = L"You have the newest version."; break;
      case S::Available: line = u.error.empty() ? L"Version " + u.version + L" is ready" + (u.size ? L" (" + mb(u.size) + L")" : L"") + L"." : u.error; break;
      case S::Downloading: line = L"Downloading version " + u.version + (u.size ? L": " + mb(u.got) + L" of " + mb(u.size) : L"..."); break;
      case S::Ready: line = L"Downloaded. The setup takes it from here: it closes this window and updates."; break;
      case S::Failed: line = u.error; break;
    }
    ui.text(RectF(r.l + 62, r.t + 16, b.l - 14, r.t + 40), RT_NAME L" " + widen(RT_VERSION_STR), 15.f, ui.pal.text, 600);
    ui.text(RectF(r.l + 62, r.t + 40, b.l - 14, r.b - 14), line, 12.5f, u.state == S::Failed || (u.state == S::Available && !u.error.empty()) ? ui.pal.danger : ui.pal.dim, 400,
            Align::Left, VAlign::Top, true);
    if (u.state == S::Downloading && u.size) {
      RectF bar(r.l + 62, r.b - 14, b.l - 14, r.b - 10);
      ui.p->rrect(bar, 2, ui.pal.text.withA(0.12f));
      ui.p->rrect(RectF(bar.l, bar.t, lerp(bar.l, bar.r, saturate((float)u.got / (float)u.size)), bar.b), 2, ui.pal.accent);
    }
    if (u.state == S::Available) {
      if (ui.button(ui.id("upget"), b, L"Download and install", Btn::Accent, L"\xE896")) updater_.download();
    } else if (u.state == S::Ready) {
      if (ui.button(ui.id("uprun"), b, L"Open the setup", Btn::Accent)) after([this, f = u.file] { startSetup(f); });
    } else {
      if (ui.button(ui.id("upcheck"), b, busy ? L"Please wait" : u.state == S::Latest ? L"Look again" : L"Check for updates", Btn::Standard, L"\xE895", !busy)) updater_.check();
    }
  }
  if ((u.state == S::Available || u.state == S::Downloading || u.state == S::Ready) && !u.notes.empty()) {
    section((L"New in " + u.version).c_str());
    para(u.notes, 13.f);
  }
  section(L"What is new");
  for (auto& ch : kChanges) {
    c_.y += 2;
    ui.text(RectF::xywh(c_.x + 2, c_.y, c_.w, 22), std::wstring(L"Version ") + ch.version, 14.f, ui.pal.text, 600);
    ui.text(RectF::xywh(c_.x + 2 + ui.textWidth(std::wstring(L"Version ") + ch.version, 14.f, 600) + 12, c_.y + 1, 200, 22), ch.when, 12.5f, ui.pal.dim);
    c_.y += 28;
    for (auto* l : ch.lines) {
      ui.text(RectF::xywh(c_.x + 6, c_.y, 12, 20), L"\x2022", 13.f, ui.pal.accent, 600);
      para(l, 13.f, 400, 16);
    }
    c_.y += 8;
  }
}

// ---------------------------------------------------------------- help
void SettingsWindow::pageHelp(RectF) {
  std::wstring key = hotkeyText(app_.cfg.hotkey);
  struct Part {
    const wchar_t* title;
    std::vector<std::wstring> lines;
  };
  std::vector<Part> parts = {
      {L"Opening it",
       {L"Press " + key + L" (you can choose another shortcut on the Shortcut page). The wheel opens at the mouse pointer; the Layout page can put it in the middle of the screen instead.",
        L"Tap the shortcut and the wheel stays open until you click something. Or hold it, flick the mouse toward an item and let go: that opens it right away. The Shortcut page has the other ways to open it.",
        L"Open it now (bottom left here) and the tray icon open it too."}},
      {L"Opening apps",
       {L"Point at an item, or just move the mouse toward it: the nearest one lights up. Click to open it.",
        L"With the keyboard: A and D (or the arrow keys) turn, W and S reach out and back in, Space or F opens, 1 to 9 open by number, Esc closes.",
        L"Hold Shift while opening, or click with the middle button, to start a new window even when the app is running already.",
        L"Running apps carry a mark. Point at one with several windows and they fan out, so you can pick the window you want.",
        L"Right-click an item for more: run as administrator, open the file location, unpin. The same menu switches profiles and skins."}},
      {L"Profiles",
       {L"Each profile is a wheel of its own. Turn the mouse wheel over the wheel, press Q and E, or click one of the profiles around the centre to switch.",
        L"Lock a profile you only need now and then: the padlock on the Pins or Profiles page. The wheel skips it until you unlock it.",
        L"On the Profiles page every profile can use the main skin, no skin, or one of its own. The scrolling direction can be reversed there too."}},
      {L"Adding and arranging",
       {L"On the Pins page, pick installed apps on the right, or use File, Folder, Website, Group and Taskbar. Dropping files, shortcuts or links on this window adds them as well.",
        L"In Explorer, right-click a file or folder and choose Add to " RT_NAME L" (on Windows 11 under Show more options). Right-clicking a button on the taskbar offers the same.",
        L"Drag items in the list to change their order. Drop one on a group to put it inside, or on another profile at the top to move it there; hold Ctrl to copy instead. Right-click an item for the same choices.",
        L"A group shows its items when you point at it on the wheel. While a group is open on the right, everything you add goes straight into it.",
        L"Click an item to change its name, its picture, or how it starts."}},
      {L"Skins and looks",
       {L"A skin replaces the whole look: artwork, motion, lettering and sounds. Choose one on the Skins page. Import skin adds .rskin files, and double-clicking one does the same.",
        L"Under the gallery, hue, saturation and brightness tune the skin you chose. The bin on a card removes a skin: the ones you added go to the recycle bin, the others can be brought back.",
        L"Without a skin, the Look and Effects pages shape everything yourself, and the Layout page chooses the arrangement.",
        L"To make your own skin, copy one to edit on the Skins page. The guide SKINS.md in the program folder explains every part of it."}},
      {L"Your data",
       {L"Everything is saved as you go. General > Your data makes a backup file and reads one back.",
        L"News looks for a newer version when you ask. To uninstall, use Settings > Apps in Windows, or Uninstall.exe in the program folder."}},
  };
  for (auto& p : parts) {
    section(p.title);
    for (auto& l : p.lines) {
      ui.text(RectF::xywh(c_.x + 6, c_.y, 12, 20), L"\x2022", 13.f, ui.pal.accent, 600);
      para(l, 13.f, 400, 16);
    }
  }
}

// ---------------------------------------------------------------- about
void SettingsWindow::pageAbout(RectF) {
  c_.y += 6;
  {
    RectF r = RectF::xywh(c_.x, c_.y, c_.w, 96);
    c_.y += 104;
    ui.card(r, 10);
    V2 c{r.l + 50, r.cy()};
    thumb(ui.id("aboutmark"), RectF::xywh(c.x - 30, c.y - 30, 60, 60), 2, [&] {
      for (int i = 0; i < 8; i++) {
        float a = i * kTau / 8;
        bool lit = i == 1;
        auto g = wedgeGeo(c, 10.f, lit ? 28.f : 26.f, a - kTau / 16, a + kTau / 16, 3.f, 2.5f);
        if (lit) {
          auto br = ui.p->linear({c.x, c.y - 28}, {c.x + 28, c.y}, {{0, Color::hex(0x2DD4FF)}, {1, Color::hex(0x805CFF)}});
          ui.p->fill(g.Get(), br.Get());
        } else {
          ui.p->fill(g.Get(), ui.pal.text.withA(0.30f));
        }
      }
    });
    ui.text(RectF(r.l + 96, r.t + 16, r.r - 16, r.t + 44), RT_NAME, 22.f, ui.pal.text, 600);
    ui.text(RectF(r.l + 96, r.t + 44, r.r - 16, r.t + 64), L"Version " + widen(RT_VERSION_STR), 13.f, ui.pal.dim);
    ui.text(RectF(r.l + 96, r.t + 64, r.r - 16, r.t + 84), L"Your apps in a wheel, one press away.", 13.f, ui.pal.dim);
  }

  section(L"Support", L"Questions, ideas and problems are all welcome.");
  {
    RectF r = RectF::xywh(c_.x, c_.y, c_.w, 84);
    c_.y += 88;
    ui.card(r, 8);
    ui.glyph(RectF(r.l + 14, r.t, r.l + 50, r.b), L"\xE715", 20.f, ui.pal.accent);
    float bw = 136;
    RectF copy(r.r - 16 - bw, r.cy() - 17, r.r - 16, r.cy() + 17), mail(copy.l - 8 - bw, copy.t, copy.l - 8, copy.b);
    bool narrow = mail.l < r.l + 300;
    if (narrow) mail = copy;
    ui.text(RectF(r.l + 60, r.t + 14, mail.l - 12, r.t + 36), kSupportName, 14.f, ui.pal.text, 600);
    ui.text(RectF(r.l + 60, r.t + 36, mail.l - 12, r.t + 56), kSupportMail, 13.f, ui.pal.text);
    ui.text(RectF(r.l + 60, r.t + 56, mail.l - 12, r.b - 8), L"Please say which version you have: " + widen(RT_VERSION_STR) + L".", 12.f, ui.pal.dim);
    if (ui.button(ui.id("mailto"), mail, L"Write an email", Btn::Accent, L"\xE715")) {
      std::wstring to = std::wstring(L"mailto:") + kSupportMail + L"?subject=" RT_NAME L" " + widen(RT_VERSION_STR);
      for (size_t at; (at = to.find(L' ')) != std::wstring::npos;) to.replace(at, 1, L"%20");
      ShellExecuteW(hwnd_, nullptr, to.c_str(), nullptr, nullptr, SW_SHOWNORMAL);
    }
    if (!narrow && ui.button(ui.id("mailcopy"), copy, L"Copy address", Btn::Standard, L"\xE8C8")) {
      copyText(hwnd_, kSupportMail);
      say(L"Address copied");
    }
  }

  section(L"This copy");
  {
    std::wstring prog = dirName(modulePath());
    RectF r = row(L"Program folder", prog.c_str(), 110);
    if (ui.button(ui.id("openprog"), r, L"Open")) ShellExecuteW(hwnd_, nullptr, prog.c_str(), nullptr, nullptr, SW_SHOWNORMAL);
    std::wstring data = dataDir();
    RectF d = row(L"Settings folder", data.c_str(), 110);
    if (ui.button(ui.id("opendata"), d, L"Open")) ShellExecuteW(hwnd_, nullptr, data.c_str(), nullptr, nullptr, SW_SHOWNORMAL);
  }
  c_.y += 10;
  para(L"Made with Direct2D and DirectComposition, with nothing else to install. It only goes online when you ask: for the logo of a website you add, or to look for an update.", 12.f);
}

}  // namespace rt
