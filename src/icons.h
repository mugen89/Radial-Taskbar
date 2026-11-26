// Icon loading on a background thread, with tone variants, cached for drawing.
#pragma once
#include "common.h"
#include "config.h"
#include "gfx.h"

namespace rt {

struct IconImage {
  int w = 0, h = 0;
  std::vector<uint8_t> px;      // premultiplied BGRA
  D2D1_RECT_F crop{};           // visible area, so every icon gets the same optical size
};

class IconCache {
 public:
  // Direct: extract in this process. Helper: a short-lived copy of the program does it and leaves the
  // result in a disk cache, so shell extensions never load into the resident process.
  enum class Mode { Direct, Helper };
  void start(HWND notify, UINT message, int pixels = 144, Mode mode = Mode::Direct);
  void stop();
  // Key for a pin's picture; empty when the pin is drawn as a lettered tile or group.
  static std::wstring keyFor(const Pin& pin);
  // Returns the bitmap when loaded, queues it otherwise.
  ID2D1Bitmap1* get(const std::wstring& key, IconTone tone, Color ink, D2D1_RECT_F* crop, Color paper = Color(1, 1, 1));
  Color tint(const std::wstring& key, Color otherwise);  // the colour the icon is known by
  bool failed(const std::wstring& key) const;
  void request(const std::wstring& key);
  void waitIdle(DWORD ms);      // for headless rendering
  void drain();                 // moves finished loads into the cache (UI thread)
  size_t memoryUse() const;
  void dropDevice();            // frees the GPU copies, keeps the pictures
  void keepOnly(std::vector<std::wstring> keys);  // lets go of pictures nothing uses any more

 private:
  struct Entry {
    bool queued = false, done = false, bad = false;
    double badAt = 0;
    IconImage img;
    // The same icon can be on the wheel and in a group, in different colours.
    struct Made {
      IconTone tone;
      Color ink, paper;
      ComPtr<ID2D1Bitmap1> bmp;
      D2D1_RECT_F crop{};
      uint32_t used = 0;
    };
    std::vector<Made> made;
    Color tint;
    bool tinted = false;
    uint32_t gen = 0;
  };
  std::unordered_map<std::wstring, Entry> map_;
  uint32_t clock_ = 0;
  static unsigned __stdcall threadMain(void* self);
  void run();

  CRITICAL_SECTION cs_{};
  HANDLE wake_ = nullptr, thread_ = nullptr;
  bool quit_ = false, inited_ = false;
  std::vector<std::wstring> queue_;
  std::vector<std::pair<std::wstring, IconImage>> ready_;
  int inFlight_ = 0;
  HWND notify_ = nullptr;
  UINT msg_ = 0;
  int px_ = 144;
  Mode mode_ = Mode::Direct;
  void serveFromHelper(const std::vector<std::wstring>& keys);
  void deliver(const std::wstring& key, IconImage img);
};
IconCache& icons();

bool loadIcon(const std::wstring& key, int size, IconImage& out);  // blocking
void finishIcon(IconImage& img);                                   // works out the visible area
bool toneIcon(const IconImage& in, IconTone tone, Color ink, Color paper, IconImage& out);
Color iconColor(const IconImage& in);
constexpr float kShadowInset = 0.14f;  // free space around a blurred shadow, for each side
int runIconHelper(const std::wstring& requestFile);                // the "--icon-worker" process

}  // namespace rt
