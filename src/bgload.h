// Reads and shrinks pictures away from the window's own thread, so that a page full of them opens at once.
#pragma once
#include "common.h"

namespace rt {

class PictureLoader {
 public:
  struct Picture {
    int w = 0, h = 0;          // 0: it could not be read
    std::vector<uint8_t> px;   // BGRA, premultiplied
  };
  using Read = std::function<bool(std::string& bytes)>;  // runs on the worker

  PictureLoader();
  ~PictureLoader();
  // Asking again for something that is on its way does nothing. cover: fills w by h; otherwise only w counts.
  void ask(uint64_t key, Read read, int w, int h, bool cover);
  bool waiting(uint64_t key);
  bool take(uint64_t key, Picture& out);
  void notify(HWND h, UINT msg);     // posted when something is ready
  static bool decode(const std::string& bytes, int w, int h, bool cover, Picture& out);

 private:
  struct Shared;
  std::shared_ptr<Shared> s_;
  static unsigned __stdcall work(void* p);
};

}  // namespace rt
