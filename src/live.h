// What the instruments of a skin show: the time, how busy the computer is, how loud the sound is.
#pragma once
#include "common.h"

namespace rt {

struct LiveValues {
  float hour = 0, minute = 0, second = 0, tick = 0, day = 1, month = 1;  // hour 0..12, all running smoothly except tick
  float cpu = 0, ram = 0, battery = 1, charging = 1;
  float sound = 0, soundL = 0, soundR = 0, beat = 0;
};

class Live {
 public:
  // Measures only what is asked for. The loudness comes from Windows' own level meter: no sound is recorded.
  const LiveValues& sample(float dt, bool system, bool sound);
  void rest();              // nothing is on screen any more
  bool staged = false;      // invented, steady values for pictures and checks
  ~Live();

 private:
  LiveValues v_;
  double sysAt_ = -10;
  uint64_t idle_ = 0, busy_ = 0;
  float cpuTo_ = 0, beatAvg_ = 0;
  HANDLE meter_ = nullptr, stop_ = nullptr;
  void startMeter();
  static unsigned __stdcall meterThread(void* p);
  volatile LONG left_ = 0, right_ = 0;  // 1/65536
};
Live& live();

}  // namespace rt
