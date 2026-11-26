// Settings file safety: busy files, damaged files, backups, import and export.
// Run with RADIALTASKBAR_DATA pointing at an empty folder.
#include <cstdio>

#include "config.h"
#include "shellutil.h"
#include "update.h"

using namespace rt;

static int bad = 0;
static void check(const std::string& n, bool ok) {
  printf("%s %s\n", ok ? "ok  " : "FAIL", n.c_str());
  if (!ok) bad++;
}
static std::string slurp(const std::wstring& p) {
  std::string s;
  readFile(p, s);
  return s;
}
static DWORD WINAPI closeLater(void* h) {
  Sleep(500);
  CloseHandle((HANDLE)h);
  return 0;
}

int main() {
  if (!GetEnvironmentVariableW(L"RADIALTASKBAR_DATA", nullptr, 0)) {
    printf("set RADIALTASKBAR_DATA first\n");
    return 99;
  }
  OleInitialize(nullptr);
  std::wstring d = dataDir();
  auto wipe = [&] {
    for (auto f : {L"config.json", L"config.json.bak", L"config.json.broken", L"config.json.before-import"}) DeleteFileW(joinPath(d, f).c_str());
  };
  wipe();
  Config c;
  check("missing file is Missing", c.load() == Config::Load::Missing);
  c.sanitize();

  // held exclusively: must not count as a first run
  Pin p;
  p.id = "x1";
  p.kind = Pin::Kind::File;
  p.name = L"\x0422\x0435\x0441\x0442";
  p.target = L"%WINDIR%\\notepad.exe";
  c.profile().pins.push_back(p);
  check("save", c.save());
  std::string before = slurp(Config::path());
  HANDLE h = CreateFileW(Config::path().c_str(), GENERIC_READ, 0, nullptr, OPEN_EXISTING, 0, nullptr);
  Config busy;
  check("held file is Unreadable, not Missing", busy.load() == Config::Load::Unreadable);
  busy.locked = true;
  check("locked settings refuse to save", !busy.save());
  CloseHandle(h);
  check("file untouched", slurp(Config::path()) == before);
  Config c2;
  check("loads again, Cyrillic intact", c2.load() == Config::Load::Ok && c2.profile().pins.size() == 1 && c2.profile().pins[0].name == p.name);

  // another process has it open for a moment while we save
  h = CreateFileW(Config::path().c_str(), GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING, 0, nullptr);
  HANDLE t = CreateThread(nullptr, 0, closeLater, h, 0, nullptr);
  c2.perRing = 7;
  double t0 = nowSec();
  bool ok = c2.save();
  WaitForSingleObject(t, 3000);
  printf("     save took %.0f ms\n", (nowSec() - t0) * 1000);
  Config c3;
  check("save survives a reader", ok && c3.load() == Config::Load::Ok && c3.perRing == 7);
  check("backup kept", fileExists(Config::path() + L".bak"));

  // damaged and lost files fall back to the backup
  writeFileAtomic(Config::path(), "{\"profiles\": [ this is not json");
  Config c4;
  check("damaged file uses the backup", c4.load() == Config::Load::Ok && c4.profile().pins.size() == 1);
  check("damaged copy kept", fileExists(Config::path() + L".broken"));
  DeleteFileW(Config::path().c_str());
  Config c5;
  check("lost file uses the backup", c5.load() == Config::Load::Ok && c5.profile().pins.size() == 1);

  // export and import, with shortcuts
  std::wstring links = joinPath(d, L"links"), lnk = joinPath(links, L"Pad-1.lnk");
  SHCreateDirectoryExW(nullptr, links.c_str(), nullptr);
  createShortcut(lnk, expandEnv(L"%WINDIR%\\System32\\notepad.exe"), L"", L"t");
  Pin q;
  q.id = "l1";
  q.kind = Pin::Kind::File;
  q.name = L"Pad";
  q.target = lnk;
  c5.profile().pins.push_back(q);
  Pin g;
  g.id = "g1";
  g.kind = Pin::Kind::Group;
  g.name = L"G";
  q.id = "l2";
  g.children.push_back(q);
  c5.profile().pins.push_back(g);
  // a website with a picture of its own, kept in our folder, and one whose picture lives elsewhere
  std::wstring pics = imagesDir(), pic = joinPath(pics, L"tube-1.png");
  SHCreateDirectoryExW(nullptr, pics.c_str(), nullptr);
  std::string png = std::string("\x89PNG\r\n\x1a\n", 8) + std::string(200, 'x');
  writeFileAtomic(pic, png);
  Pin w = pinFromUrl(L"youtube.com");
  w.id = "w1";
  w.icon = pic;
  w.iconShape = PicShape::Circle;
  c5.profile().pins.push_back(w);
  Pin w2 = pinFromUrl(L"example.com");
  w2.id = "w2";
  w2.icon = L"C:\\somewhere\\else.ico";
  c5.profile().pins.push_back(w2);
  c5.hubProfiles = c5.taskbarMenu = c5.siteLogos = false;
  Look sk;
  sk.id = "my-1";
  sk.name = L"Mine";
  sk.style = c5.style;
  c5.customLooks.push_back(sk);
  c5.save();
  std::string exported = c5.exportText(), bytes = slurp(lnk);
  int np = 0, nn = 0;
  check("backup recognised", Config::checkBackup(exported, np, nn) && np == 1 && nn == 5);
  DeleteFileW(lnk.c_str());
  DeleteFileW(pic.c_str());
  wipe();
  Config c6;
  c6.sanitize();
  check("import", c6.importText(exported));
  check("shortcut restored byte for byte", !bytes.empty() && slurp(c6.profile().pins[1].target) == bytes);
  check("shortcut inside a group too", c6.profile().pins[2].children.size() == 1 && slurp(c6.profile().pins[2].children[0].target) == bytes);
  check("own skin came along", c6.customLooks.size() == 1);
  Pin* pw = findPin(c6.profile().pins, "w1");
  check("picture restored byte for byte", pw && slurp(pw->icon) == png && pw->iconShape == PicShape::Circle);
  Pin* pw2 = findPin(c6.profile().pins, "w2");
  check("other icons keep their place", pw2 && pw2->icon == L"C:\\somewhere\\else.ico" && pw2->iconShape == PicShape::Auto);
  check("new switches survive", !c6.hubProfiles && !c6.taskbarMenu && !c6.siteLogos);
  // a backup from elsewhere must not be able to write outside the pictures folder
  Json evil;
  Json::parse(exported, evil);
  for (auto& kv : evil.o)
    if (kv.first == "profiles")
      for (auto& pr : kv.second.a)
        for (auto& pk : pr.o)
          if (pk.first == "pins")
            for (auto& pin : pk.second.a)
              if (pin.str("id") == "w1") pin.set("icon", "C:\\x\\..\\..\\..\\evil.png");
  Config c7;
  c7.sanitize();
  c7.importText(evil.dump());
  Pin* pe = findPin(c7.profile().pins, "w1");
  check("restored pictures stay in their folder", pe && toLower(dirName(pe->icon)) == toLower(pics));
  if (pe) DeleteFileW(pe->icon.c_str());
  Config fresh;
  check("new switches are on by default", fresh.hubProfiles && fresh.taskbarMenu && fresh.siteLogos);
  for (auto s : {"", "[]", "{}", "{\"profiles\":{}}", "{\"profiles\":[]}", "{\"profiles\":[1,2],\"layout\":{},\"style\":{}}", "{\"profiles\":{\"list\":[]},\"schemes\":[]}",
                 "{\"profiles\":[{\"commandName\":\"Project\"}]}"}) {
    Config e = c6;
    size_t had = e.profile().pins.size();
    check(std::string("refuses to import ") + s, !e.importText(s) && e.profile().pins.size() == had);
  }

  // base64
  std::string b;
  bool round = true;
  for (size_t n = 0; n < 60; n++) {
    std::string r;
    for (size_t i = 0; i < n; i++) r += (char)(i * 37 + n);
    round &= unbase64(base64(r), b) && b == r;
  }
  check("base64 round trip", round);
  check("base64 refuses junk", !unbase64("ab$d", b));

  // awkward JSON must never crash
  for (auto s : {"{\"a\":", "{\"a\":1e999}", "{\"a\":\"\\ud83d\"}", "[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[",
                 "{\"profiles\":[null,1,{\"pins\":[null,{\"kind\":\"group\",\"children\":[{\"kind\":\"group\",\"children\":[{}]}]}]}]}",
                 "{\"layout\":{\"perRing\":-5,\"scale\":1e9,\"iconSize\":\"x\"},\"hotkey\":{\"vk\":99999,\"mods\":-1},\"activeProfile\":77}"}) {
    Json j;
    if (Json::parse(s, j) && j.isObj()) {
      Config z;
      z.fromJson(j);
      (void)z.toJson().dump();
      (void)z.profile();
      check("odd values are clamped", z.perRing >= 3 && z.perRing <= 20 && z.scale <= 2.2f && z.hotkey.vk <= 0xFE && z.activeProfile == 0);
    }
  }

  // ids
  Config u = c6;
  check("ungroup keeps the items in place", ungroupPin(u.profile().pins, "g1") && u.profile().pins.size() == 5 && u.profile().pins[2].id == "l2");
  Pin o;
  check("remove a nested pin", removePin(c6.profile().pins, "l2", &o) && o.id == "l2" && c6.profile().pins[2].children.empty());
  Pin back;
  check("pin text round trip", pinParse(pinText(o), back) && back.id == o.id && back.target == o.target);

  // ---- 1.0.0: locked profiles, the main skin, reverse scrolling, removed skins, updates
  {
    Config z;
    z.profiles.clear();
    for (int i = 0; i < 4; i++) {
      Profile p;
      p.id = "p" + std::to_string(i);
      z.profiles.push_back(p);
    }
    z.profiles[1].locked = z.profiles[2].locked = true;
    check("scrolling skips locked profiles", z.wheelStep(0, 1) == 3 && z.wheelStep(3, 1) == 0 && z.wheelStep(0, -1) == 3 && z.wheelStep(3, -1) == 0);
    z.activeProfile = 2;
    check("a locked profile in use: the wheel shows the next one", z.wheelIndex() == 3 && z.unlockedCount() == 2);
    for (auto& p : z.profiles) p.locked = true;
    z.sanitize();
    check("one profile always stays unlocked", z.unlockedCount() == 1 && !z.profiles[0].locked);
    z.profiles[3].locked = true;
    z.reverseScroll = true;
    z.skin = "neon";
    z.profiles[1].skin = "clockwork";
    z.profiles[2].skin = Config::kNoSkin;
    z.hiddenSkins = {"vinyl"};
    Config r;
    r.fromJson(z.toJson());
    check("locks, reverse scrolling and removed skins are kept", r.profiles.size() == 4 && r.profiles[3].locked && !r.profiles[0].locked && r.reverseScroll && r.hidden("vinyl") && !r.hidden("neon"));
    r.activeProfile = 0;
    bool main = r.skinNow() == "neon";
    r.activeProfile = 1;
    bool own = r.skinNow() == "clockwork";
    r.activeProfile = 2;
    bool none = r.skinNow().empty();
    check("main skin, a skin of its own, none", main && own && none);
    r.chooseSkin("arcade");
    bool noneChanged = r.profiles[2].skin == "arcade" && r.skin == "neon";
    r.activeProfile = 0;
    r.chooseSkin("zen");
    check("choosing changes the profile's own skin, or the main one", noneChanged && r.skin == "zen" && r.profiles[0].skin.empty() && r.profiles[1].skin == "clockwork");
    r.activeProfile = 1;
    r.chooseSkin("");
    check("no skin for one profile only", r.skinNow().empty() && r.profiles[1].skin == Config::kNoSkin && r.skin == "zen");
    // settings from before: a profile's skin only counted with "every profile has its own skin" on
    Config o1, o2;
    o1.fromJson(*[] { static Json j; Json::parse(R"({"skin": "neon", "skinPerProfile": true, "profiles": [{"id": "a", "skin": "clockwork"}, {"id": "b", "skin": "clockwork"}, {"id": "c", "skin": ""}, {"id": "d", "skin": "zen"}]})", j); return &j; }());
    check("old per-profile skins: the first one leads", o1.skin == "clockwork" && o1.profiles[0].skin.empty() && o1.profiles[1].skin.empty() && o1.profiles[2].skin == Config::kNoSkin && o1.profiles[3].skin == "zen");
    o2.fromJson(*[] { static Json j; Json::parse(R"({"skin": "neon", "profiles": [{"id": "a", "skin": "clockwork"}, {"id": "b"}]})", j); return &j; }());
    check("old leftovers without per-profile skins are dropped", o2.skin == "neon" && o2.profiles[0].skin.empty() && o2.profiles[1].skin.empty());
    // arrangements work like skins: the main one, or one of a profile's own
    Config w;
    w.profiles.resize(3);
    for (int i = 0; i < 3; i++) w.profiles[(size_t)i].id = "w" + std::to_string(i);
    w.layout = LayoutType::Radial;
    w.profiles[1].layout = (int)LayoutType::Carousel;
    w.profiles[2].layout = 99;  // damaged
    w.sanitize();
    check("a damaged arrangement falls back to the main one", w.profiles[2].layout == -1);
    Config v;
    v.fromJson(w.toJson());
    v.activeProfile = 0;
    bool mainLay = v.layoutNow() == LayoutType::Radial;
    v.activeProfile = 1;
    bool ownLay = v.layoutNow() == LayoutType::Carousel;
    check("the main arrangement and a profile's own are kept", mainLay && ownLay && v.profiles[0].layout == -1 && v.profiles[2].layout == -1);
    v.chooseLayout(LayoutType::Globe);
    bool ownChanged = v.profiles[1].layout == (int)LayoutType::Globe && v.layout == LayoutType::Radial;
    v.activeProfile = 2;
    v.chooseLayout(LayoutType::Drum);
    check("choosing changes the profile's own arrangement, or the main one", ownChanged && v.layout == LayoutType::Drum && v.profiles[2].layout == -1 && v.layoutFor(v.profiles[0]) == LayoutType::Drum);
    check("which arrangements are on show", v.anyLayout(LayoutType::Globe) && v.anyLayout(LayoutType::Drum) && !v.anyLayout(LayoutType::Radial) && !v.onlyLayout(LayoutType::Drum));
    v.profiles[1].layout = -1;
    check("every profile on the main arrangement", v.onlyLayout(LayoutType::Drum));
    Config u;
    u.fromJson(*[] { static Json j; Json::parse(R"({"profiles": [{"id": "a", "layout": "orbit"}, {"id": "b", "layout": "nonsense"}, {"id": "c"}]})", j); return &j; }());
    check("arrangements are read by name; an unknown one means the main", u.profiles[0].layout == (int)LayoutType::Orbit && u.profiles[1].layout == -1 && u.profiles[2].layout == -1);
  }
  check("versions compare by number", Updater::compare(L"1.0.0", L"1.0.0") == 0 && Updater::compare(L"v1.2.10", L"1.2.9") > 0 && Updater::compare(L"1.0", L"1.0.1") < 0 && Updater::compare(L"2", L"1.9.9") > 0);
  {
    std::wstring n = Updater::plainNotes("## What's new\n* [Skins](https://example.com/skins) are **here**\n- Fewer clicks, see https://example.com/more\n\n\n**Full Changelog**: https://github.com/a/b/compare/v1...v2\n");
    check("release notes without links", n.find(L"\x2022 Skins are here") != std::wstring::npos && n.find(L"\x2022 Fewer clicks, see") != std::wstring::npos && n.find(L"http") == std::wstring::npos &&
                                              n.find(L"Changelog") == std::wstring::npos && n.find(L"##") == std::wstring::npos && n.find(L"**") == std::wstring::npos);
  }

  if (bad) printf("FAILED %d\n", bad);
  else printf("all good\n");
  OleUninitialize();
  return bad;
}
