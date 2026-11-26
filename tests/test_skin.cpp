// Skins from strangers: formulas, archives and skin.json must survive anything without harm.
// Run with RADIALTASKBAR_DATA pointing at an empty folder; an argument names a skin folder to take apart.
#include <cstdio>

#include "gfx.h"
#include "skin.h"
#include "zip.h"

using namespace rt;

static int bad = 0;
static void check(const std::string& n, bool ok) {
  printf("%s %s\n", ok ? "ok  " : "FAIL", n.c_str());
  if (!ok) bad++;
}

// An archive made by another program, with packed and plain files and two names that must never be used.
static const char* kZip =
    "UEsDBBQAAAAIAF1qeV1ps4GeDgAAAAwAAAAJAAAAc2tpbi5qc29uq1bKS8xNVbJSqlCqBQBQSwMEFAAAAAgAXWp5XaNJSFH8AQAA0AkAAAwAAABzdWIvbG9uZy50eHRtlmtywzAIhK/iq6mJJknrJh"
    "nbnVy/LYvDB9YfPyRYLbBgX3pbptP8OH1Nrzbff7bpfGvz9Lr2Pk9z+35Oz8dy6nO73XcDv30sbV3dcP3z75vjPB+3+9aX912Gl/+D3M5v13Y/H3zKYdo2Z+GsW2/fb/vsDeMA0qKucrYI7XA/5LO/"
    "uq/IIkVV8OzVMpPSllIgqnoWuJ2Z2RJeB+oqBwcf1eESNcuIXhLWx1wVlKcglUA7ZhRZiZO0LYZefCOkYtomEHYyu7dSbA4GfkgzM8B6iLr5INY9SsHoSmqFu5yMmPB0NStpnAqzFbEyCxjLoKC/iw"
    "i9iJKvEBxch4lirWVbkqhFcEJxi2ntPoQgFGdmvtAeM8l8oRZxEiOtq96mKq2dgvBBftQ3O2nvv1BfsI1X9AZGDFahUsQYWwyQ7cRR5c0vWjhgqHUUKOXaXxBUnmKWXbugrj4SDm03FAjHm6uC+kQn"
    "Mq7MYjRZ4ShSlDVDQULHOs64cpJ92KAJIZyYTpySqTCof6BpMU1TJrM2StYeNTBEF02ONBlXOA1gdMNgSGM6sjtTa+z5rN9JaM59y/eF+qZZ7j9ILmWWoyltDDSabpkvM8Qq+lwhpNMKVfHrdTy1RH"
    "uYhqG/pLJiZ7jsJOauOPA/ZPQLwBKmDoecs+nxTwDlSlmv+iMXe/4FUEsDBBQAAAAAAAAAIQBzjAUpAAEAAAABAAAKAAAAc3RvcmVkLmJpbgABAgMEBQYHCAkKCwwNDg8QERITFBUWFxgZGhscHR4f"
    "ICEiIyQlJicoKSorLC0uLzAxMjM0NTY3ODk6Ozw9Pj9AQUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVpbXF1eX2BhYmNkZWZnaGlqa2xtbm9wcXJzdHV2d3h5ent8fX5/gIGCg4SFhoeIiYqLjI2Oj5"
    "CRkpOUlZaXmJmam5ydnp+goaKjpKWmp6ipqqusra6vsLGys7S1tre4ubq7vL2+v8DBwsPExcbHyMnKy8zNzs/Q0dLT1NXW19jZ2tvc3d7f4OHi4+Tl5ufo6err7O3u7/Dx8vP09fb3+Pn6+/z9/v9Q"
    "SwMEFAAAAAgAXWp5XR8oqmcEAAAAAgAAAAsAAAAuLi9ldmlsLnR4dMvLBwBQSwMEFAAAAAgAXWp5XR8oqmcEAAAAAgAAAAcAAABjb24udHh0y8sHAFBLAQIUABQAAAAIAF1qeV1ps4GeDgAAAAwAAA"
    "AJAAAAAAAAAAAAAACAAQAAAABza2luLmpzb25QSwECFAAUAAAACABdanldo0lIUfwBAADQCQAADAAAAAAAAAAAAAAAgAE1AAAAc3ViL2xvbmcudHh0UEsBAhQAFAAAAAAAAAAhAHOMBSkAAQAAAAEA"
    "AAoAAAAAAAAAAAAAAIABWwIAAHN0b3JlZC5iaW5QSwECFAAUAAAACABdanldHyiqZwQAAAACAAAACwAAAAAAAAAAAAAAgAGDAwAALi4vZXZpbC50eHRQSwECFAAUAAAACABdanldHyiqZwQAAAACAA"
    "AABwAAAAAAAAAAAAAAgAGwAwAAY29uLnR4dFBLBQYAAAAABQAFABcBAADZAwAAAAA=";

static uint32_t seed = 12345;
static uint32_t rnd() {
  seed ^= seed << 13;
  seed ^= seed >> 17;
  seed ^= seed << 5;
  return seed;
}

static float calc(const char* t, const float* v = nullptr, bool* ok = nullptr) {
  Expr e;
  std::string err;
  static float zero[kVarCount] = {};
  bool good = e.parse(t, &err);
  if (ok) *ok = good;
  return good ? e.eval(v ? v : zero) : -12345.f;
}
static bool near_(float a, float b) { return fabsf(a - b) < 1e-3f; }

static void formulas() {
  check("precedence", near_(calc("1+2*3"), 7) && near_(calc("(1+2)*3"), 9) && near_(calc("2^3^1"), 8) && near_(calc("-2*-3"), 6) && near_(calc("10-3-2"), 5) && near_(calc("12/3/2"), 2));
  check("comparison and choice", near_(calc("1<2 ? 10 : 20"), 10) && near_(calc("if(3>4,1,2)"), 2) && near_(calc("1 && 0 || 1"), 1) && near_(calc("!0"), 1) && near_(calc("1!=2"), 1));
  check("functions", near_(calc("clamp(5,0,3)"), 3) && near_(calc("mix(0,10,0.25)"), 2.5f) && near_(calc("smooth(0,1,0.5)"), 0.5f) && near_(calc("mod(-1,4)"), 3) && near_(calc("wrap(350)"), -10) && near_(calc("sin(pi/2)"), 1));
  check("easing ends", near_(calc("outback(1)"), 1) && near_(calc("outelastic(1)"), 1) && near_(calc("outbounce(1)"), 1) && near_(calc("outcubic(0)"), 0));
  check("division by zero is zero", near_(calc("1/0"), 0) && near_(calc("5%0"), 0));
  check("noise stays in range", calc("noise(3.7)") >= 0 && calc("noise(3.7)") <= 1 && calc("rnd(9)") >= 0 && calc("rnd(9)") < 1);
  float v[kVarCount] = {};
  v[vHot] = 0.5f;
  v[vSel] = 90;
  v[vRingOut] = 7;
  check("names", near_(calc("hot*2+sel", v), 91) && near_(calc("RingOut", v), 7) && near_(calc(" hot ", v), 0.5f));
  bool ok = true;
  for (auto t : {"", "1+", "foo", "sin(", "sin()", "sin(1,2)", "1 2", "(1", "1)", "a b", "hot..5+", "@", "\"x\"", "1?2", "1?2:", "clamp(1,2)", "--", "e^"}) {
    bool good = true;
    calc(t, nullptr, &good);
    if (good) printf("     accepted: %s\n", t);
    ok = ok && !good;
  }
  check("nonsense is refused", ok);
  std::string deep(300, '('), longOne;
  deep += "1" + std::string(300, ')');
  for (int i = 0; i < 400; i++) longOne += "hot+";
  longOne += "1";
  bool g1, g2;
  calc(deep.c_str(), nullptr, &g1);
  calc(longOne.c_str(), nullptr, &g2);
  check("too deep and too long are refused", !g1 && !g2);
  std::string rightDeep;
  for (int i = 0; i < 36; i++) rightDeep += "1+(hot*(";
  rightDeep += "1" + std::string(72, ')');
  calc(rightDeep.c_str());
  Expr e;
  check("constants fold", e.parse("2*3+sin(0)", nullptr) && e.constant() && e.parse("2*hot", nullptr) && !e.constant() && e.uses(vHot) && !e.uses(vSel));
  static const char* const bits[] = {"1", "hot", "sel", "+", "-", "*", "/", "(", ")", ",", "sin(", "if(", "clamp(", "?", ":", "<", "&&", "!", "0.5", "time", "^", "%", "noise(", " "};
  int parsed = 0;
  for (int i = 0; i < 200000; i++) {
    std::string t;
    for (int k = (int)(rnd() % 14) + 1; k-- > 0;) t += bits[rnd() % (sizeof bits / sizeof *bits)];
    Expr q;
    if (q.parse(t, nullptr)) {
      float r = q.eval(v);
      if (!(r > -1e10f && r < 1e10f)) bad++;
      parsed++;
    }
  }
  check("200000 random formulas, " + std::to_string(parsed) + " of them valid", parsed > 1000);
}

static void archives() {
  std::string raw, text, err;
  unbase64(kZip, raw);
  Archive a;
  check("opens", a.open(raw, &err));
  check("names that leave the folder or mean a device are dropped", a.entries().size() == 3 && !a.find("../evil.txt") && !a.find("con.txt"));
  auto* e = a.find("SUB/Long.TXT");
  check("packed text", e && a.read(*e, text) && text.size() == 2512 && text.find("porcelain") != std::string::npos);
  e = a.find("stored.bin");
  check("plain file", e && a.read(*e, text) && text.size() == 256 && (unsigned char)text[200] == 200);
  std::string mine = makeZip({{"skin.json", "{}"}, {"a/b.txt", std::string(70000, 'x')}, {"empty", ""}});
  Archive b;
  check("own archives", b.open(mine, &err) && b.entries().size() == 3 && b.read(*b.find("a/b.txt"), text) && text.size() == 70000 && b.read(*b.find("empty"), text) && text.empty());
  check("same files, same archive", mine == makeZip({{"skin.json", "{}"}, {"a/b.txt", std::string(70000, 'x')}, {"empty", ""}}));
  std::string wrong = mine;
  wrong[200] ^= 1;  // inside the packed bytes of the second file
  Archive c;
  check("damage is noticed", c.open(wrong, nullptr) && c.read(*c.find("skin.json"), text) && !c.read(*c.find("a/b.txt"), text));
  Archive::Limits lim;
  lim.one = 1000;
  check("limits", !c.open(mine, &err, lim) && !err.empty() && !c.open("not a zip at all, but long enough to look at", &err));
  int opened = 0, readable = 0;
  for (int i = 0; i < 60000; i++) {
    std::string f = i & 1 ? raw : mine.substr(mine.size() > 3000 ? mine.size() - 400 : 0);
    if (!(i & 1)) f = raw;
    for (int k = (int)(rnd() % 6) + 1; k-- > 0;) {
      size_t at = rnd() % f.size();
      switch (rnd() % 4) {
        case 0: f[at] = (char)rnd(); break;
        case 1: f[at] ^= (char)(1 << rnd() % 8); break;
        case 2: f.erase(at, rnd() % 20 + 1); break;
        default: f.insert(at, 1, (char)rnd()); break;
      }
      if (f.empty()) f = "x";
    }
    Archive z;
    if (!z.open(f, nullptr)) continue;
    opened++;
    for (auto& q : z.entries()) readable += z.read(q, text);
  }
  check("60000 damaged archives (" + std::to_string(opened) + " opened, " + std::to_string(readable) + " files read)", opened > 100);
  for (int i = 0; i < 60000; i++) {
    std::string f((size_t)(rnd() % 200) + 1, 0);
    for (auto& ch : f) ch = (char)rnd();
    inflateRaw((const uint8_t*)f.data(), f.size(), 1 << 16, text);
    if (text.size() > 1 << 16) bad++;
  }
  check("60000 pieces of noise unpacked", true);
  bool ok = true;
  for (auto p : {"", "/a", "\\a", "a/../b", "..", "a//b", "c:x", "a\\b", "con", "NUL.png", "com1.txt", "a./b", "a /b", "x?y", "a\nb", "lpt9"}) ok = ok && !safeInnerPath(p);
  for (auto p : {"a", "a.png", "sub/b.jpg", "a b/c d.png", "console.png", "com.txt", ".hidden"}) ok = ok && safeInnerPath(p);
  check("paths inside a skin", ok);
}

static void texts(const char* folder) {
  Skin t;
  std::string err;
  const char* js = R"({
    // remarks are fine
    "name": "Test", "id": "My Test!", "style": {"accent": "#FF0000", "shape": "orb"}, "colors": {"ink": "#102030"},
    "images": {"p": "p.png", "q": {"file": "q.jpg", "mask": "q-mask.png", "light": true}, "evil": "../../x.png"},
    "back": [{"image": "p", "rotate": "time*10", "size": 1.2,}, {"image": "nothere"}, {"shape": "ring", "inner": 0.5, "stroke": "ink/50"}, {"text": "{title}", "px": 14}],
    "slot": {"under": [{"image": "q", "opacity": "hott"}], "icon": {"tone": "engrave", "size": 1.1}, "wrong": 1},
    "sounds": {"open": "open.wav", "move": "..\\x.wav"},
  })";
  check("a skin with mistakes is still read", parseSkin(js, t, &err));
  check("what is right is taken", t.id == "my-test" && t.name == L"Test" && t.back.size() == 3 && t.images.size() == 2 && t.slot.icon.tone == IconTone::Engrave && t.style.shape == SlotShape::Orb && t.alive && !t.ownTitle && t.sounds.size() == 1);
  std::string all;
  for (auto& p : t.problems) all += p + "\n";
  bool told = all.find("evil") != std::string::npos && all.find("nothere") != std::string::npos && all.find("hott") != std::string::npos && all.find("wrong") != std::string::npos && all.find("move") != std::string::npos;
  if (!told) printf("%s", all.c_str());
  check("what is wrong is told, with its place", told && all.find("slot > under 1") != std::string::npos);
  Skin t2;
  check("a broken file says which line", !parseSkin("{\n\"a\": 1,\n\"b\": oops\n}", t2, &err) && err.find("line 3") != std::string::npos);
  Skin t3;
  check("not an object", !parseSkin("[1,2]", t3, &err) && !parseSkin("", t3, &err));
  std::string base = js;
  if (folder) {
    auto f = SkinFiles::open(widen(folder));
    if (f) f->read("skin.json", base);
  }
  int good = 0;
  for (int i = 0; i < 6000; i++) {
    std::string s = base;
    for (int k = (int)(rnd() % 8) + 1; k-- > 0;) {
      size_t at = rnd() % s.size(), from = rnd() % s.size();
      switch (rnd() % 5) {
        case 0: s[at] = (char)(32 + rnd() % 95); break;
        case 1: s.erase(at, rnd() % 40); break;
        case 2: s.insert(at, s.substr(from, rnd() % 60)); break;
        case 3: s[at] = "0123456789-.\"{}[],:"[rnd() % 19]; break;
        default: s.insert(at, std::to_string((int)rnd())); break;
      }
      if (s.empty()) s = "{}";
    }
    Skin q;
    good += parseSkin(s, q, nullptr);
    if (q.problems.size() > 40) bad++;
  }
  check("6000 damaged skin files (" + std::to_string(good) + " still readable)", true);
}

static void store(const char* folder) {
  // a skin goes in, is found, copied, packed and removed
  std::wstring dir = joinPath(dataDir(), L"made");
  SHCreateDirectoryExW(nullptr, dir.c_str(), nullptr);
  std::string zip = makeZip({{"skin.json", "{\"id\": \"probe\", \"name\": \"Probe\", \"author\": \"me\", // x\n \"images\": {\"a\": \"a.png\"}, \"back\": [{\"image\": \"a\"}]}"}, {"sub/x.txt", "1"}});
  std::wstring file = joinPath(dir, L"anything.rskin");
  writeFileAtomic(file, zip);
  std::string id, err;
  check("install", skins().install(file, id, &err) && id == "probe");
  const SkinInfo* i = skins().info("probe");
  check("listed", i && i->name == L"Probe" && i->author == L"me" && !i->builtin);
  auto t = skins().get("probe");
  check("loaded, missing picture told", t && t->problems.size() == 1 && t->problems[0].find("a.png") != std::string::npos);
  check("install again replaces", skins().install(file, id, &err) && skins().list().size() >= 1);
  std::wstring copy;
  check("copy to edit", skins().copyToFolder("probe", L"My Probe", copy, &err) && fileExists(joinPath(copy, L"skin.json")) && fileExists(joinPath(copy, L"sub\\x.txt")));
  std::string text;
  readFile(joinPath(copy, L"skin.json"), text);
  check("the copy has its own name, remarks stay", text.find("\"my-probe\"") != std::string::npos && text.find("// x") != std::string::npos && text.find("\"me\"") == std::string::npos);
  auto c = skins().get("my-probe");
  check("the copy loads", c && c->folder && c->name == L"My Probe");
  Sleep(600);
  writeFileAtomic(joinPath(copy, L"skin.json"), "{\"id\": \"my-probe\", \"name\": \"Changed\"}");
  auto c2 = skins().get("my-probe");
  check("an edit is picked up", c2 && c2 != c && c2->name == L"Changed");
  check("pack", skins().pack("my-probe", joinPath(dir, L"out.rskin"), &err) && fileExists(joinPath(dir, L"out.rskin")));
  std::string junk(200, 'x');
  writeFileAtomic(joinPath(dir, L"junk.rskin"), junk);
  check("junk is refused", !skins().install(joinPath(dir, L"junk.rskin"), id, &err) && !err.empty());
  writeFileAtomic(joinPath(dir, L"nothing.rskin"), makeZip({{"readme.txt", "hello"}}));
  check("an archive that is no skin is refused", !skins().install(joinPath(dir, L"nothing.rskin"), id, &err));
  check("gone skins are gone", !skins().get("never-there"));
  // ---- found by the review of 25 November 2026
  {
    // deflate data of nothing but empty blocks: 13 bytes that claim a megabyte of input
    std::string z, body;
    for (int i = 0; i < 400000; i++) body += std::string("\x02\x04\x08\x10\x20", 5);  // whatever: never looked at
    auto u16 = [&](uint32_t v) { z.push_back((char)(v & 255)); z.push_back((char)(v >> 8 & 255)); };
    auto u32 = [&](uint32_t v) { u16(v & 0xFFFF); u16(v >> 16); };
    u32(0x04034b50u); u16(20); u16(0); u16(8); u32(0); u32(0); u32((uint32_t)body.size()); u32(13); u16(9); u16(0);
    z += "skin.json" + body;
    uint32_t start = (uint32_t)z.size();
    u32(0x02014b50u); u16(20); u16(20); u16(0); u16(8); u32(0); u32(0); u32((uint32_t)body.size()); u32(13); u16(9); u16(0); u16(0); u16(0); u16(0); u32(0); u32(0);
    z += "skin.json";
    uint32_t len = (uint32_t)z.size() - start;
    u32(0x06054b50u); u16(0); u16(0); u16(1); u16(1); u32(len); u32(start); u16(0);
    Archive q;
    check("packed data longer than it can honestly be is refused", !q.open(z, &err) && !err.empty());
  }
  {
    Skin n;
    check("a colour of not-a-number strength", parseSkin("{\"hub\": [{\"shape\": \"circle\", \"size\": 1, \"fill\": \"accent/nan\"}]}", n, &err) && n.hub.size() == 1 && n.hub[0].fill.c.a >= 0 && n.hub[0].fill.c.a <= 1);
  }
  {
    // two people's skins with one id
    auto skinOf = [&](const char* name, const char* author, const char* about) {
      return makeZip({{"skin.json", std::string("{\"id\": \"twin\", \"name\": \"") + name + "\", \"author\": \"" + author + "\", \"about\": \"" + about + "\"}"}});
    };
    std::string id1, id2, id3, id4;
    writeFileAtomic(joinPath(dir, L"t1.rskin"), skinOf("Twin", "Ann", "first"));
    writeFileAtomic(joinPath(dir, L"t2.rskin"), skinOf("Twin", "Bob", "second"));
    writeFileAtomic(joinPath(dir, L"t3.rskin"), skinOf("Twin", "Ann", "newer"));
    writeFileAtomic(joinPath(dir, L"t4.rskin"), skinOf("Twin", "", "nobody's"));
    check("somebody else's skin with the same id gets one of its own", skins().install(joinPath(dir, L"t1.rskin"), id1, &err) && skins().install(joinPath(dir, L"t2.rskin"), id2, &err) && id1 == "twin" && id2 == "twin-2");
    check("both are there", skins().info("twin") && skins().info("twin-2") && skins().info("twin")->author == L"Ann" && skins().info("twin-2")->author == L"Bob");
    check("a newer copy of the same one replaces it", skins().install(joinPath(dir, L"t3.rskin"), id3, &err) && id3 == "twin" && skins().info("twin")->about == L"newer" && skins().info("twin-2")->about == L"second");
    check("without an author nothing is replaced", skins().install(joinPath(dir, L"t4.rskin"), id4, &err) && id4 == "twin-3" && skins().info("twin")->about == L"newer");
    check("the second one loads under its own id", skins().get("twin-2") && skins().get("twin-2")->id == "twin-2");
    // copied into the folder by hand
    writeFileAtomic(joinPath(SkinStore::userDir(), L"a copy of twin.rskin"), skinOf("Twin", "Cleo", "by hand"));
    skins().refresh();
    int twins = 0;
    for (auto& q : skins().list()) twins += q.name == L"Twin";
    check("files that share an id are all listed, and the one called like it keeps it", twins == 4 && skins().info("twin") && skins().info("twin")->about == L"newer");
  }
  {
    // nothing that Explorer would act on is unpacked
    writeFileAtomic(joinPath(dir, L"odd.rskin"), makeZip({{"skin.json", "{\"id\": \"odd\", \"name\": \"Odd\"}"}, {"a.png", "x"}, {"desktop.ini", "[.ShellClassInfo]"}, {"x.lnk", "L"}, {"sub/y.URL", "u"}, {"run.bat", "echo"}, {"z.library-ms", "<a/>"}, {"noending", "n"}}));
    std::string oid;
    std::wstring folder;
    check("a skin with odd files is taken in", skins().install(joinPath(dir, L"odd.rskin"), oid, &err));
    check("only parts of a skin are unpacked", skins().copyToFolder(oid, L"My Odd", folder, &err) && fileExists(joinPath(folder, L"a.png")) && !fileExists(joinPath(folder, L"desktop.ini")) && !fileExists(joinPath(folder, L"x.lnk")) &&
                                                   !fileExists(joinPath(folder, L"sub\\y.URL")) && !fileExists(joinPath(folder, L"run.bat")) && !fileExists(joinPath(folder, L"z.library-ms")) && !fileExists(joinPath(folder, L"noending")));
  }
  {
    // a skin.json nobody should have to read
    writeFileAtomic(joinPath(SkinStore::userDir(), L"huge.rskin"), makeZip({{"skin.json", "{\"id\": \"huge\", \"x\": [" + std::string(3u << 20, '1') + "]}"}}));
    skins().refresh();
    bool told = false;
    for (auto& q : skins().list()) told |= q.id == "huge" && !q.error.empty();
    check("a huge skin.json is not read", told && !skins().get("huge"));
  }
  {
    skins().distrust("probe");
    check("a skin that cannot be drawn is left out", !skins().get("probe"));
    Sleep(800);
    writeFileAtomic(joinPath(SkinStore::userDir(), L"probe.rskin"), makeZip({{"skin.json", "{\"id\": \"probe\", \"name\": \"Mended\", \"author\": \"me\"}"}}));
    skins().refresh();
    auto mended = skins().get("probe");
    check("and tried again when its file changes", mended && mended->name == L"Mended");
  }
}

int main(int argc, char** argv) {
  if (!GetEnvironmentVariableW(L"RADIALTASKBAR_DATA", nullptr, 0)) {
    printf("set RADIALTASKBAR_DATA first\n");
    return 99;
  }
  OleInitialize(nullptr);
  formulas();
  archives();
  texts(argc > 1 ? argv[1] : nullptr);
  store(nullptr);
  printf("%s, %d failed\n", bad ? "FAILED" : "all good", bad);
  return bad ? 1 : 0;
}
