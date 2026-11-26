// The settings window: pins and profiles, layout, look, effects, shortcut, general.
#pragma once
#include "common.h"
#include "bgload.h"
#include "config.h"
#include "hotkey.h"
#include "scene.h"
#include "shellutil.h"
#include "ui.h"
#include "update.h"

namespace rt {

class App;
struct LogoAsk;

const wchar_t* layoutTitle(LayoutType t);  // "Radial wheel", "Carousel" ...: for the Layout and Profiles pages

// A live, interactive miniature of the launcher over the person's own wallpaper.
class Preview {
 public:
  bool draw(Ui& ui, RectF r, float scale, const Config& cfg, int revision, int sampleCount);  // true: it moves
  PictureLoader* loader = nullptr;
  void replay() { replay_ = true; }
  std::shared_ptr<const Skin> skin() const { return layout_ ? layout_->skin : nullptr; }
  void drop();
  static bool demoOnly;  // checks must not show the person's wallpaper

 private:
  void rebuild(const Config& cfg, int sampleCount, bool settle);
  std::unique_ptr<Layout> layout_;
  Backdrop bd_;
  void wallpaper(int w, int h, bool again);
  ComPtr<ID2D1Bitmap1> wall_, wallFull_, scene_;
  int wallW_ = 0, wallH_ = 0;
  std::wstring wallPath_;
  int w_ = 0, h_ = 0, rev_ = -1, samples_ = -1;
  uint32_t gen_ = 0;
  float demo_ = 0, scale_ = 1;
  int demoItem_ = 0;
  bool replay_ = false, hovering_ = false, quiet_ = false;
};

class SettingsWindow : public UiWindow {
 public:
  // The numbers stay as they were; the sidebar has an order of its own.
  enum Page { kPins, kLayout, kSkins, kLook, kEffects, kShortcut, kGeneral, kNews, kHelp, kAbout, kProfiles, kPageCount };
  explicit SettingsWindow(App& app);
  void show(int page);
  void appsReady(void* list);
  bool logoArrived(const LogoAsk& ask, const std::wstring& image, const std::wstring& name);
  void setPage(int p) { page_ = p; }
  void touch() { rev_++; }  // as if a setting had changed
  void dropDevice();
  // headless checks
  void loadAppsNow();
  void scrollPage(float y) { ui.scrollTo(ui.id("page", page_), y); contentH_[page_] = 4000; }
  void selectFirstPin(bool group);
  void selectUrl();
  void openUrlForm(const std::wstring& url, const std::wstring& picture);

 protected:
  void paint() override;
  bool hasLive() const override { return true; }
  void paintLive() override;
  void drawFailed() override;
  bool onClose() override;
  void onDrop(const DropData& d, V2 at) override;
  LRESULT onMessage(UINT m, WPARAM w, LPARAM l, bool& handled) override;

 private:
  // column helpers
  struct Col { float x, y, w; } c_{};
  void section(const wchar_t* title, const wchar_t* note = nullptr);
  RectF row(const wchar_t* title, const wchar_t* desc, float ctlW, float h = 0);
  bool sliderRow(const char* key, const wchar_t* title, float& v, float lo, float hi, float step, const wchar_t* fmt, float show = 1.f, const wchar_t* desc = nullptr);
  bool toggleRow(const char* key, const wchar_t* title, const wchar_t* desc, bool& v);
  template <class E>
  bool segRow(const char* key, const wchar_t* title, const wchar_t* desc, E& v, const std::vector<std::wstring>& opts, float w);
  void changed(bool pins = false);

  void sidebar(RectF r);
  void header(RectF r, const wchar_t* title, const wchar_t* sub);
  void previewPanel(RectF r);
  void pageLayout(RectF r);
  void pageSkins(RectF r);
  void pageLook(RectF r);
  void pageEffects(RectF r);
  void pageShortcut(RectF r);
  void pageGeneral(RectF r);
  void pagePins(RectF r);
  void pageProfiles(RectF r);
  void pageNews(RectF r);
  void pageHelp(RectF r);
  void pageAbout(RectF r);
  float para(std::wstring_view s, float size = 13.f, int weight = 400, float indent = 0);  // wrapped text, returns its height
  void skinThumb(RectF r, const std::string& id);

  // skins
  void skinCard(RectF r, const SkinInfo* k);
  ID2D1Bitmap1* skinPreview(const SkinInfo& k, float width);
  void chooseSkin(const std::string& id);
  bool skinBanner(const wchar_t* what);    // says that a skin is in charge
  void pickSkinFiles();
  void copySkin(const std::string& id);
  void shareSkin(const std::string& id);
  void removeSkin(const std::string& id);
  void hideSkin(const std::string& id);
 public:
  void addSkins(const std::vector<std::wstring>& files, bool ask);
 private:
  struct SkinPic {
    ComPtr<ID2D1Bitmap1> bmp;
    int asked = 0;
    bool tried = false;
    double shownAt = 0;
  };
  PictureLoader loader_;
  Updater updater_;
  std::wstring setupFor_;  // the downloaded setup that was started
  void startSetup(const std::wstring& file);
  std::map<std::wstring, SkinPic> skinPics_;
  uint32_t skinPicsGen_ = 0;
  std::shared_ptr<const Skin> skinSeen_;
  double skinListAt_ = -10;
  std::wstring skinSearch_;

  // drawn once and kept
  void thumb(uint32_t key, RectF r, float margin, const std::function<void()>& draw);
  std::unordered_map<uint32_t, ComPtr<ID2D1Bitmap1>> thumbs_;
  uint32_t thumbsGen_ = 0;
  bool thumbsDark_ = false;
  float thumbsScale_ = 0;
  static constexpr float kSide = 214.f;
  bool previewOn_ = false;
  RectF previewBox_;

  // look
  void lookCard(RectF r, const Look& k, bool custom);
  void drawLookThumb(RectF r, const Style& s, float hover);
  void layoutThumb(RectF r, int kind, bool on, float hover);

  // pins
  struct RowRef { int top = -1, kid = -1; };
  float profileBar(RectF r);  // returns where it ends: it takes more lines when there are many profiles
  struct TabRect { RectF r; int index; };
  std::vector<TabRect> tabRects_;  // where the profiles were drawn, for dropping items on them
  void setLocked(int index, bool on);
  void pinList(RectF r);
  void pinMenu(const std::string& id);
  void movePin(const std::string& id, int toProfile, bool copy);
  void moveIntoGroup(const std::string& id, const std::string& group);
  void addPanel(RectF r);
  void addArea(RectF in, RectF zone, const Pin* group);
  bool inGroup(const AppEntry& a, const Pin& g);
  void editPanel(RectF r, Pin& pin);
  void groupPanel(RectF r, RectF in, Pin& pin);
  void drawPinIcon(const Pin& pin, V2 c, float size, float alpha = 1.f);
  void ensureApps();
  bool appPinned(const AppEntry& a);
  void addPins(std::vector<Pin> pins);
  void profileMenu(int index);
  void removeProfile(int index);
  void removeAsking(const std::string& id);
  Pin* pinById(const std::string& id);
  void say(const std::wstring& line);

  // pictures
  // The website being added is not a pin yet. Every form gets an id of its own, so an answer to a question asked
  // from an earlier one cannot land in it.
  static bool isDraft(const std::string& id) { return id.compare(0, 6, "draft-") == 0; }
  void newDraft();
  void dropDraft();
  float picturePanel(float x, float y, float w, const Pin& pin);  // returns its height
  void pictureWell(RectF well, const Pin& pin);
  void choosePicture(const std::string& id);
  void pastePicture(const std::string& id);
  void takePicture(const std::string& id, const std::string& bytes, const std::wstring& name);
  void askForLogo(const std::string& id);
  void spinner(V2 c, float r);

  // shortcut
  void keycap(RectF& at, const std::wstring& s, float h, Color fill);
  float keycapsWidth(const Hotkey& h, float size);
  void drawKeycaps(float x, float cy, const Hotkey& h, float size, float alpha);
  void startRecording();
  void stopRecording();
  void refreshIdeas();

  App& app_;
  int page_ = kPins;
  int rev_ = 0;
  float contentH_[kPageCount] = {};
  Preview preview_;
  int sample_ = 0;  // 0: own pins, otherwise a sample count

  std::string selected_;             // pin being edited
  std::map<std::string, bool> expanded_;
  std::string dragId_, pressId_;
  V2 pressAt_, dragGrab_;
  bool dragging_ = false;
  std::wstring search_;
  std::vector<AppEntry> apps_;
  bool appsLoading_ = false, appsLoaded_ = false;
  std::vector<int> found_;
  std::wstring foundFor_ = L"\x01";
  int pinnedRev_ = -1;
  std::vector<MatchInfo> pinnedMatch_;
  std::vector<std::wstring> pinnedTargets_;
  int naming_ = -1;                  // profile being renamed
  std::wstring nameBuf_;
  std::wstring urlBuf_, urlName_;
  Pin draft_;
  RectF pictureZone_;                // where a dropped picture belongs to pictureFor_
  std::string pictureFor_;
  std::string editFor_;
  float editH_ = 0;
  bool addingUrl_ = false;
  std::wstring flash_;
  double flashAt_ = -10;

  bool recording_ = false, triedTaken_ = false;
  Hotkey tried_;
  std::vector<HotkeyIdea> ideas_;
  bool ideasOk_ = false;
  bool autostart_ = false, fileMenu_ = false;
  double autostartAt_ = -10;
  std::wstring lookName_;
  bool namingLook_ = false;
};

template <class E>
bool SettingsWindow::segRow(const char* key, const wchar_t* title, const wchar_t* desc, E& v, const std::vector<std::wstring>& opts, float w) {
  int i = (int)v;
  bool tight = c_.w < w + 170.f;  // stack when the column is narrow
  bool ch;
  if (tight) {
    RectF r = RectF::xywh(c_.x, c_.y, c_.w, 82.f);
    c_.y += 86;
    ui.card(r, 8);
    ui.text(RectF(r.l + 16, r.t + 7, r.r - 12, r.t + 31), title, 13.5f, ui.pal.text);
    ch = ui.segmented(ui.id(key), RectF(r.l + 14, r.t + 37, r.r - 14, r.t + 70), i, opts);
  } else {
    RectF r = row(title, desc, w);
    ch = ui.segmented(ui.id(key), r, i, opts);
  }
  if (ch) {
    v = (E)i;
    changed();
  }
  return ch;
}

}  // namespace rt
