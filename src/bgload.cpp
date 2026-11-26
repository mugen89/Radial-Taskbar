#include "bgload.h"

#include <process.h>
#include <wincodec.h>

#include <deque>

namespace rt {

struct PictureLoader::Shared {
  struct Job {
    uint64_t key;
    Read read;
    int w, h;
    bool cover;
  };
  SRWLOCK lock = SRWLOCK_INIT;
  std::deque<Job> jobs;
  std::unordered_map<uint64_t, Picture> done;
  uint64_t current = 0;
  bool running = false, quit = false;
  HWND hwnd = nullptr;
  UINT msg = 0;
};

PictureLoader::PictureLoader() : s_(std::make_shared<Shared>()) {}

// The worker keeps its own hold on what is shared and stops after the picture it is at.
PictureLoader::~PictureLoader() {
  AcquireSRWLockExclusive(&s_->lock);
  s_->quit = true;
  s_->hwnd = nullptr;
  s_->jobs.clear();
  ReleaseSRWLockExclusive(&s_->lock);
}

void PictureLoader::notify(HWND h, UINT msg) {
  AcquireSRWLockExclusive(&s_->lock);
  s_->hwnd = h;
  s_->msg = msg;
  ReleaseSRWLockExclusive(&s_->lock);
}

void PictureLoader::ask(uint64_t key, Read read, int w, int h, bool cover) {
  AcquireSRWLockExclusive(&s_->lock);
  bool have = s_->current == key || s_->done.count(key);
  for (auto& j : s_->jobs) have |= j.key == key;
  if (!have) {
    s_->jobs.push_back({key, std::move(read), w, h, cover});
    if (!s_->running) {
      auto* hold = new std::shared_ptr<Shared>(s_);
      if (uintptr_t t = _beginthreadex(nullptr, 0, work, hold, 0, nullptr)) {
        s_->running = true;
        CloseHandle((HANDLE)t);
      } else {
        delete hold;
      }
    }
  }
  ReleaseSRWLockExclusive(&s_->lock);
}

bool PictureLoader::waiting(uint64_t key) {
  AcquireSRWLockExclusive(&s_->lock);
  bool have = s_->current == key;
  for (auto& j : s_->jobs) have |= j.key == key;
  ReleaseSRWLockExclusive(&s_->lock);
  return have;
}

bool PictureLoader::take(uint64_t key, Picture& out) {
  AcquireSRWLockExclusive(&s_->lock);
  auto it = s_->done.find(key);
  bool ok = it != s_->done.end();
  if (ok) {
    out = std::move(it->second);
    s_->done.erase(it);
  }
  ReleaseSRWLockExclusive(&s_->lock);
  return ok;
}

bool PictureLoader::decode(const std::string& bytes, int w, int h, bool cover, Picture& out) {
  out = {};
  ComPtr<IWICImagingFactory> wic;
  ComPtr<IWICStream> st;
  ComPtr<IWICBitmapDecoder> dec;
  ComPtr<IWICBitmapFrameDecode> fr;
  ComPtr<IWICBitmapScaler> sc;
  ComPtr<IWICFormatConverter> cv;
  UINT iw = 0, ih = 0;
  if (bytes.size() < 16 || bytes.size() > 160u << 20 || FAILED(CoCreateInstance(CLSID_WICImagingFactory, nullptr, CLSCTX_INPROC_SERVER, __uuidof(IWICImagingFactory), (void**)wic.GetAddressOf())) ||
      FAILED(wic->CreateStream(&st)) || FAILED(st->InitializeFromMemory((BYTE*)bytes.data(), (DWORD)bytes.size())) ||
      FAILED(wic->CreateDecoderFromStream(st.Get(), nullptr, WICDecodeMetadataCacheOnDemand, &dec)) || FAILED(dec->GetFrame(0, &fr)) || FAILED(fr->GetSize(&iw, &ih)) || !iw || !ih || iw > 30000 || ih > 30000 || (uint64_t)iw * ih > 64u * 1000 * 1000)
    return false;
  double k = cover ? std::max((double)w / iw, (double)h / ih) : (double)w / iw;
  k = std::min(k, 1.0);
  UINT tw = std::max(1u, (UINT)lround(iw * k)), th = std::max(1u, (UINT)lround(ih * k));
  if ((uint64_t)tw * th > 24u * 1000 * 1000) return false;
  if (FAILED(wic->CreateBitmapScaler(&sc)) || FAILED(sc->Initialize(fr.Get(), tw, th, WICBitmapInterpolationModeFant)) || FAILED(wic->CreateFormatConverter(&cv)) ||
      FAILED(cv->Initialize(sc.Get(), GUID_WICPixelFormat32bppPBGRA, WICBitmapDitherTypeNone, nullptr, 0, WICBitmapPaletteTypeCustom)))
    return false;
  out.px.resize((size_t)tw * th * 4);
  if (FAILED(cv->CopyPixels(nullptr, tw * 4, (UINT)out.px.size(), out.px.data()))) {
    out = {};
    return false;
  }
  out.w = (int)tw;
  out.h = (int)th;
  return true;
}

unsigned __stdcall PictureLoader::work(void* p) {
  std::unique_ptr<std::shared_ptr<Shared>> hold((std::shared_ptr<Shared>*)p);
  Shared& s = **hold;
  bool com = SUCCEEDED(CoInitializeEx(nullptr, COINIT_MULTITHREADED));
  SetThreadPriority(GetCurrentThread(), THREAD_PRIORITY_BELOW_NORMAL);
  for (;;) {
    AcquireSRWLockExclusive(&s.lock);
    if (s.quit || s.jobs.empty()) {
      s.running = false;
      ReleaseSRWLockExclusive(&s.lock);
      break;
    }
    Shared::Job j = std::move(s.jobs.front());
    s.jobs.pop_front();
    s.current = j.key;
    ReleaseSRWLockExclusive(&s.lock);
    Picture pic;
    std::string bytes;
    if (j.read(bytes)) decode(bytes, j.w, j.h, j.cover, pic);
    AcquireSRWLockExclusive(&s.lock);
    s.current = 0;
    if (!s.quit) s.done[j.key] = std::move(pic);
    if (s.hwnd) PostMessageW(s.hwnd, s.msg, 0, 0);
    ReleaseSRWLockExclusive(&s.lock);
  }
  if (com) CoUninitialize();
  return 0;
}

}  // namespace rt
