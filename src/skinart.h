// The pictures, fonts and sounds of the skin in use, loaded on a worker and kept in the size they are drawn.
#pragma once
#include "gfx.h"
#include "skin.h"

namespace rt {

class SkinArt {
 public:
  ~SkinArt();
  // Switches to a skin (or none). Cheap when nothing changed. persist: keep sized pictures on disk for quick openings.
  void use(std::shared_ptr<const Skin> t, const Config::Tune& tune, bool persist);
  const Skin* skin() const { return skin_.get(); }

  struct Pic {
    ID2D1Bitmap1* bmp = nullptr;
    float fade = 1.f;          // rises when a picture arrives late
    int cols = 1, rows = 1, frames = 1;
    float cw = 0, ch = 0;      // size of one frame inside the bitmap
    bool sharp = false, light = false;
  };
  // A picture for drawing one frame `wide` pixels across. False while it is being loaded.
  // moving: the size is not settled, near enough will do. keep: worth a file in the disk cache.
  bool get(int image, float wide, Pic& out, bool moving = false, bool keep = true);
  void quiet(bool on) { quiet_ = on; }  // pictures are only wanted in the disk cache for now
  bool pending() const { return inFlight_ > 0 || fading_; }
  void wait(DWORD ms);         // until everything asked for so far has arrived
  void tick(float dt);
  void dropDevice();
  void rest();                 // frees the decoded leftovers and closes the skin file
  Color tuned(Color c) const { return tuneColor(c, tune_); }
  static Color tuneColor(Color c, const Config::Tune& t);

  std::wstring fontFamily(int font, int* weight) const;
  std::wstring fontByName(const std::string& name) const;   // a family for a font the skin names, or nothing
  bool sound(const char* event, std::string& wav);          // empty when the skin has none
  HCURSOR cursor(float dpi);

 private:
  struct Sized {
    ComPtr<ID2D1Bitmap1> bmp;
    int wide = 0;
    int cw = 0, ch = 0;
    float born = 0, fade = 1;
    bool asked = false, bad = false;
    uint32_t used = 0;
  };
  struct Job {
    std::shared_ptr<const Skin> skin;
    std::shared_ptr<SkinFiles> files;
    Config::Tune tune;
    int image = 0, wide = 0;
    uint32_t round = 0;
    bool persist = false, quiet = false;
  };
  struct Done {
    int image = 0, wide = 0;
    uint32_t round = 0;
    int w = 0, h = 0, cw = 0, ch = 0;
    bool dropped = false;
    std::vector<uint8_t> px;
  };
  std::shared_ptr<const Skin> skin_;
  std::shared_ptr<SkinFiles> files_;
  Config::Tune tune_;
  bool persist_ = false, fading_ = false, inited_ = false, quit_ = false;
  uint32_t round_ = 0, gen_ = 0, tickNo_ = 0;
  std::map<int, std::vector<Sized>> pics_;
  std::map<std::string, std::string> sounds_;
  std::vector<std::pair<std::wstring, int>> fonts_;
  HCURSOR cursor_ = nullptr;
  float cursorDpi_ = 0;
  bool cursorTried_ = false;
  float clock_ = 0;
  size_t bytes_ = 0;         // in use on the graphics card

  CRITICAL_SECTION cs_;
  HANDLE wake_ = nullptr, idle_ = nullptr;
  std::vector<HANDLE> threads_;
  std::vector<Job> queue_;
  std::vector<Done> done_;
  int inFlight_ = 0;
  size_t waiting_ = 0;       // bytes in done_
  bool quiet_ = false;
  void forget();
  void startThreads();
  static unsigned __stdcall threadMain(void* self);
  void run();
  static bool make(IWICImagingFactory* wic, const Job& j, Done& out);
  void drain();
  void loadFonts();
  void dropFonts();
};
SkinArt& skinArt();
void sweepSkinCache(bool all);

}  // namespace rt
