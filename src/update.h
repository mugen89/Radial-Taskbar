// Looking for a newer version and fetching its setup. Nothing happens until the person presses the button.
#pragma once
#include "common.h"

namespace rt {

class Updater {
 public:
  enum class State { Idle, Checking, Latest, Available, Downloading, Ready, Failed };
  struct Now {
    State state = State::Idle;
    std::wstring version;  // the newest one
    std::wstring notes;    // what it says about itself, as plain text without links
    std::wstring error;
    std::wstring file;     // the setup, once downloaded
    uint64_t size = 0, got = 0;
  };
  Updater();
  ~Updater();
  void notify(HWND h, UINT msg);  // posted whenever something changed
  void check();
  void download();                // after check() found one
  Now now() const;

  static std::wstring current;  // this version; checks may pretend to be an older one
  static int compare(const std::wstring& a, const std::wstring& b);  // "1.2.10" against "1.2.9", like strcmp
  static std::wstring plainNotes(const std::string& markdown);

 private:
  struct Shared;
  std::shared_ptr<Shared> s_;
  void start(bool fetch);
};

}  // namespace rt
