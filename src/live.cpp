#include "live.h"

#include <mmdeviceapi.h>
#include <process.h>

namespace rt {

// The header for this one is incomplete in MinGW. It must not be in an unnamed namespace: there the compiler sees every
// class that could implement it (none), takes calls to it for impossible and leaves them out.
struct LevelMeter : public IUnknown {
  virtual HRESULT STDMETHODCALLTYPE GetPeakValue(float* v) = 0;
  virtual HRESULT STDMETHODCALLTYPE GetMeteringChannelCount(UINT* n) = 0;
  virtual HRESULT STDMETHODCALLTYPE GetChannelsPeakValues(UINT32 n, float* v) = 0;
  virtual HRESULT STDMETHODCALLTYPE QueryHardwareSupport(DWORD* mask) = 0;
};
static const GUID kLevelMeter = {0xC02216F6, 0x8C67, 0x4B5B, {0x9D, 0x00, 0xD0, 0x08, 0xE7, 0x3E, 0x00, 0x64}};

Live& live() {
  static Live l;
  return l;
}

Live::~Live() { rest(); }

void Live::rest() {
  if (meter_) {
    SetEvent(stop_);
    WaitForSingleObject(meter_, 1500);
    CloseHandle(meter_);
    meter_ = nullptr;
  }
  if (stop_) CloseHandle(stop_);
  stop_ = nullptr;
  InterlockedExchange(&left_, 0);
  InterlockedExchange(&right_, 0);
}

void Live::startMeter() {
  if (meter_) return;
  stop_ = CreateEventW(nullptr, TRUE, FALSE, nullptr);
  meter_ = (HANDLE)_beginthreadex(nullptr, 0, meterThread, this, 0, nullptr);
  if (!meter_ && stop_) {
    CloseHandle(stop_);
    stop_ = nullptr;
  }
}

unsigned __stdcall Live::meterThread(void* p) {
  auto* self = (Live*)p;
  if (FAILED(CoInitializeEx(nullptr, COINIT_MULTITHREADED))) return 0;
  {
    ComPtr<IMMDeviceEnumerator> en;
    ComPtr<IMMDevice> dev;
    ComPtr<LevelMeter> meter;
    if (SUCCEEDED(CoCreateInstance(__uuidof(MMDeviceEnumerator), nullptr, CLSCTX_INPROC_SERVER, __uuidof(IMMDeviceEnumerator), (void**)en.GetAddressOf())) &&
        SUCCEEDED(en->GetDefaultAudioEndpoint(eRender, eMultimedia, &dev)) &&
        SUCCEEDED(dev->Activate(kLevelMeter, CLSCTX_INPROC_SERVER, nullptr, (void**)meter.GetAddressOf()))) {
      UINT n = 0;
      meter->GetMeteringChannelCount(&n);
      while (WaitForSingleObject(self->stop_, 16) == WAIT_TIMEOUT) {
        float v[16] = {};
        if (n < 1 || n > 16 || FAILED(meter->GetChannelsPeakValues(n, v))) break;
        InterlockedExchange(&self->left_, (LONG)(saturate(v[0]) * 65536.f));
        InterlockedExchange(&self->right_, (LONG)(saturate(v[n > 1 ? 1 : 0]) * 65536.f));
      }
    }
  }
  CoUninitialize();
  InterlockedExchange(&self->left_, 0);
  InterlockedExchange(&self->right_, 0);
  return 0;
}

const LiveValues& Live::sample(float dt, bool system, bool sound) {
  if (staged) {
    v_.hour = 10.16f;
    v_.minute = 9.6f;
    v_.second = v_.tick = 36;
    v_.day = 25;
    v_.month = 11;
    v_.cpu = 0.42f;
    v_.ram = 0.63f;
    v_.battery = 0.8f;
    v_.charging = 0;
    v_.sound = 0.55f;
    v_.soundL = 0.62f;
    v_.soundR = 0.48f;
    v_.beat = 0.4f;
    return v_;
  }
  SYSTEMTIME t;
  GetLocalTime(&t);
  float ms = t.wMilliseconds / 1000.f;
  v_.second = t.wSecond + ms;
  v_.minute = t.wMinute + v_.second / 60.f;
  v_.hour = (t.wHour % 12) + v_.minute / 60.f;
  v_.day = t.wDay;
  v_.month = t.wMonth;
  // a clock hand that jumps and settles
  float k = saturate(ms / 0.22f), back = 1 + 2.70158f * powf(k - 1, 3) + 1.70158f * powf(k - 1, 2);
  v_.tick = t.wSecond - 1 + back;

  if (system) {
    double now = nowSec();
    if (now - sysAt_ > 0.5) {
      bool first = now - sysAt_ > 5;
      sysAt_ = now;
      FILETIME i, kr, us;
      if (GetSystemTimes(&i, &kr, &us)) {
        auto u = [](FILETIME f) { return (uint64_t)f.dwHighDateTime << 32 | f.dwLowDateTime; };
        uint64_t idle = u(i), all = u(kr) + u(us);
        if (!first && all > busy_) cpuTo_ = saturate(1.f - (float)(idle - idle_) / (float)(all - busy_));
        idle_ = idle;
        busy_ = all;
      }
      MEMORYSTATUSEX m{};
      m.dwLength = sizeof m;
      if (GlobalMemoryStatusEx(&m)) v_.ram = m.dwMemoryLoad / 100.f;
      SYSTEM_POWER_STATUS p{};
      if (GetSystemPowerStatus(&p)) {
        v_.battery = p.BatteryLifePercent <= 100 ? p.BatteryLifePercent / 100.f : 1.f;
        v_.charging = p.ACLineStatus == 1;
      }
    }
    v_.cpu += (cpuTo_ - v_.cpu) * (1.f - expf(-dt * 5.f));
  }
  if (sound) {
    startMeter();
    auto follow = [&](float& x, float to) { x += (to - x) * (1.f - expf(-dt * (to > x ? 26.f : 5.5f))); };
    // loudness is heard roughly by its logarithm
    auto curve = [](LONG raw) {
      float a = raw / 65536.f;
      return a < 0.001f ? 0.f : saturate(1.f + 20.f * log10f(a) / 48.f);
    };
    float l = curve(left_), r = curve(right_);
    follow(v_.soundL, l);
    follow(v_.soundR, r);
    float s = std::max(l, r);
    follow(v_.sound, s);
    beatAvg_ += (s - beatAvg_) * (1.f - expf(-dt * 2.2f));
    v_.beat = std::max(v_.beat * expf(-dt * 5.f), saturate((s - beatAvg_) * 4.f));
  }
  return v_;
}

}  // namespace rt
