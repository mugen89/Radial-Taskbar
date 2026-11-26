#include "zip.h"

namespace rt {

// ---------------------------------------------------------------- checksum
uint32_t crc32of(const void* data, size_t n) {
  static const std::vector<uint32_t> table = [] {
    std::vector<uint32_t> t(256);
    for (uint32_t i = 0; i < 256; i++) {
      uint32_t c = i;
      for (int k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320u ^ (c >> 1) : c >> 1;
      t[i] = c;
    }
    return t;
  }();
  uint32_t c = 0xFFFFFFFFu;
  auto* p = (const uint8_t*)data;
  for (size_t i = 0; i < n; i++) c = table[(c ^ p[i]) & 255] ^ (c >> 8);
  return c ^ 0xFFFFFFFFu;
}

// ---------------------------------------------------------------- inflate
namespace {

struct Bits {
  const uint8_t* p;
  size_t n, at = 0;
  uint32_t buf = 0;
  int have = 0;
  bool bad = false;
  uint32_t take(int k) {
    while (have < k) {
      if (at >= n) {
        bad = true;
        return 0;
      }
      buf |= (uint32_t)p[at++] << have;
      have += 8;
    }
    uint32_t v = buf & ((1u << k) - 1);
    buf >>= k;
    have -= k;
    return v;
  }
};

struct Huff {
  uint16_t count[16] = {}, sym[288] = {};
  // False when the code lengths do not describe a usable code.
  bool build(const uint8_t* len, int n) {
    memset(count, 0, sizeof count);
    for (int i = 0; i < n; i++) count[len[i]]++;
    if (count[0] == n) return true;  // no codes at all: only wrong when one is needed
    int left = 1;
    for (int l = 1; l < 16; l++) {
      left = (left << 1) - count[l];
      if (left < 0) return false;
    }
    uint16_t offs[16];
    offs[1] = 0;
    for (int l = 1; l < 15; l++) offs[l + 1] = (uint16_t)(offs[l] + count[l]);
    for (int i = 0; i < n; i++)
      if (len[i]) sym[offs[len[i]]++] = (uint16_t)i;
    return true;
  }
  int decode(Bits& b) const {
    int code = 0, first = 0, index = 0;
    for (int l = 1; l < 16; l++) {
      code |= (int)b.take(1);
      if (b.bad) return -1;
      int c = count[l];
      if (code - c < first) return sym[index + (code - first)];
      index += c;
      first = (first + c) << 1;
      code <<= 1;
    }
    return -1;
  }
};

const uint16_t kLenBase[] = {3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23, 27, 31, 35, 43, 51, 59, 67, 83, 99, 115, 131, 163, 195, 227, 258};
const uint8_t kLenExtra[] = {0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0};
const uint16_t kDistBase[] = {1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193, 257, 385, 513, 769, 1025, 1537, 2049, 3073, 4097, 6145, 8193, 12289, 16385, 24577};
const uint8_t kDistExtra[] = {0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13};

bool codes(Bits& b, const Huff& lit, const Huff& dist, size_t maxOut, std::string& out) {
  for (;;) {
    int s = lit.decode(b);
    if (s < 0) return false;
    if (s < 256) {
      if (out.size() >= maxOut) return false;
      out.push_back((char)s);
      continue;
    }
    if (s == 256) return true;
    s -= 257;
    if (s >= 29) return false;
    size_t len = kLenBase[s] + b.take(kLenExtra[s]);
    int d = dist.decode(b);
    if (d < 0 || d >= 30) return false;
    size_t back = kDistBase[d] + b.take(kDistExtra[d]);
    if (b.bad || back > out.size() || out.size() + len > maxOut) return false;
    size_t from = out.size() - back;
    for (size_t i = 0; i < len; i++) out.push_back(out[from + i]);
  }
}

}  // namespace

bool inflateRaw(const uint8_t* src, size_t n, size_t maxOut, std::string& out) {
  out.clear();
  Bits b{src, n};
  for (;;) {
    uint32_t last = b.take(1), type = b.take(2);
    if (b.bad) return false;
    if (type == 0) {
      b.buf = 0;
      b.have = 0;
      if (b.at + 4 > n) return false;
      size_t len = src[b.at] | (size_t)src[b.at + 1] << 8;
      size_t inv = src[b.at + 2] | (size_t)src[b.at + 3] << 8;
      b.at += 4;
      if ((len ^ 0xFFFF) != inv || b.at + len > n || out.size() + len > maxOut) return false;
      out.append((const char*)src + b.at, len);
      b.at += len;
    } else if (type == 1) {
      struct Fixed {
        Huff lit, dist;
        Fixed() {
          uint8_t len[288];
          for (int i = 0; i < 288; i++) len[i] = (uint8_t)(i < 144 ? 8 : i < 256 ? 9 : i < 280 ? 7 : 8);
          lit.build(len, 288);
          memset(len, 5, 30);
          dist.build(len, 30);
        }
      };
      static const Fixed fixed;
      if (!codes(b, fixed.lit, fixed.dist, maxOut, out)) return false;
    } else if (type == 2) {
      int nlen = (int)b.take(5) + 257, ndist = (int)b.take(5) + 1, ncode = (int)b.take(4) + 4;
      if (b.bad || nlen > 286 || ndist > 30) return false;
      static const uint8_t order[19] = {16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15};
      uint8_t len[320] = {};
      for (int i = 0; i < ncode; i++) len[order[i]] = (uint8_t)b.take(3);
      Huff lit, dist;
      if (!lit.build(len, 19)) return false;
      uint8_t all[320] = {};
      int at = 0;
      while (at < nlen + ndist) {
        int s = lit.decode(b);
        if (s < 0 || b.bad) return false;
        if (s < 16) {
          all[at++] = (uint8_t)s;
          continue;
        }
        uint8_t v = 0;
        int rep;
        if (s == 16) {
          if (!at) return false;
          v = all[at - 1];
          rep = 3 + (int)b.take(2);
        } else if (s == 17) {
          rep = 3 + (int)b.take(3);
        } else {
          rep = 11 + (int)b.take(7);
        }
        if (b.bad || at + rep > nlen + ndist) return false;
        while (rep--) all[at++] = v;
      }
      if (!all[256]) return false;  // a block without an end
      Huff l2, d2;
      if (!l2.build(all, nlen) || !d2.build(all + nlen, ndist)) return false;
      if (!codes(b, l2, d2, maxOut, out)) return false;
    } else {
      return false;
    }
    if (last) return true;
  }
}

// ---------------------------------------------------------------- archive
bool safeInnerPath(std::string_view p) {
  if (p.empty() || p.size() > 200 || p[0] == '/' || p[0] == '\\') return false;
  size_t at = 0;
  while (at <= p.size()) {
    size_t e = p.find('/', at);
    if (e == std::string_view::npos) e = p.size();
    std::string_view part = p.substr(at, e - at);
    if (part.empty() || part == "." || part == ".." || part.back() == '.' || part.back() == ' ') return false;
    for (char c : part)
      if ((unsigned char)c < 32 || strchr("\\:*?\"<>|", c)) return false;
    // device names mean something else to Windows
    std::string stem;
    for (char c : part.substr(0, part.find('.'))) stem.push_back((char)tolower((unsigned char)c));
    static const char* const dev[] = {"con", "prn", "aux", "nul"};
    for (auto d : dev)
      if (stem == d) return false;
    if (stem.size() == 4 && (stem.compare(0, 3, "com") == 0 || stem.compare(0, 3, "lpt") == 0) && isdigit((unsigned char)stem[3])) return false;
    at = e + 1;
  }
  return true;
}

bool Archive::open(std::string bytes, std::string* err) { return open(std::move(bytes), err, Limits{}); }

bool Archive::open(std::string bytes, std::string* err, const Limits& lim) {
  auto fail = [&](const char* m) {
    if (err) *err = m;
    list_.clear();
    data_.clear();
    return false;
  };
  list_.clear();
  lim_ = lim;
  data_ = std::move(bytes);
  if (data_.size() > lim.file) return fail("The file is too big.");
  if (data_.size() < 22) return fail("This is not a skin file.");
  auto* p = (const uint8_t*)data_.data();
  auto u16 = [&](size_t at) { return (uint32_t)p[at] | (uint32_t)p[at + 1] << 8; };
  auto u32 = [&](size_t at) { return u16(at) | u16(at + 2) << 16; };
  // the end record sits at the end, behind at most 64 KB of comment
  size_t end = SIZE_MAX, stop = data_.size() > 65557 ? data_.size() - 65557 : 0;
  for (size_t i = data_.size() - 22 + 1; i-- > stop;)
    if (u32(i) == 0x06054b50u) {
      end = i;
      break;
    }
  if (end == SIZE_MAX) return fail("This is not a skin file.");
  size_t count = u16(end + 10), dirSize = u32(end + 12), dir = u32(end + 16);
  if (count > lim.entries) return fail("The skin has too many files.");
  if (dir > data_.size() || dirSize > data_.size() - dir) return fail("The skin file is damaged.");
  size_t at = dir, total = 0;
  for (size_t i = 0; i < count; i++) {
    if (at + 46 > data_.size() || u32(at) != 0x02014b50u) return fail("The skin file is damaged.");
    Entry e;
    uint32_t flags = u16(at + 8);
    e.method = (uint16_t)u16(at + 10);
    e.crc = u32(at + 16);
    e.packed = u32(at + 20);
    e.size = u32(at + 24);
    size_t nl = u16(at + 28), xl = u16(at + 30), cl = u16(at + 32);
    e.offset = u32(at + 42);
    if (at + 46 + nl + xl + cl > data_.size()) return fail("The skin file is damaged.");
    e.name.assign(data_, at + 46, nl);
    at += 46 + nl + xl + cl;
    for (auto& c : e.name)
      if (c == '\\') c = '/';
    if (e.name.empty() || e.name.back() == '/') continue;  // a folder
    if (!safeInnerPath(e.name)) continue;                  // never anything outside the skin
    if (flags & 1) return fail("The skin file is protected with a password.");
    if (e.method != 0 && e.method != 8) return fail("The skin file uses a compression this program does not know.");
    if (e.size > lim.one) return fail("A file in the skin is too big.");
    // Honest deflate data is never longer than this; a file of empty blocks only wants to keep us busy.
    if (e.method == 8 && e.packed > (uint64_t)e.size + e.size / 64 + 1024) return fail("The skin file is damaged.");
    total += e.size;
    if (total > lim.total) return fail("The skin is too big.");
    list_.push_back(std::move(e));
  }
  return true;
}

const Archive::Entry* Archive::find(std::string_view name) const {
  auto same = [](std::string_view a, std::string_view b) {
    if (a.size() != b.size()) return false;
    for (size_t i = 0; i < a.size(); i++)
      if (tolower((unsigned char)a[i]) != tolower((unsigned char)b[i])) return false;
    return true;
  };
  for (auto& e : list_)
    if (same(e.name, name)) return &e;
  return nullptr;
}

bool Archive::read(const Entry& e, std::string& out) const {
  out.clear();
  auto* p = (const uint8_t*)data_.data();
  size_t at = e.offset;
  if (at > data_.size() || data_.size() - at < 30) return false;
  auto u16 = [&](size_t q) { return (uint32_t)p[q] | (uint32_t)p[q + 1] << 8; };
  if ((u16(at) | u16(at + 2) << 16) != 0x04034b50u) return false;
  size_t body = at + 30 + u16(at + 26) + u16(at + 28);
  if (body > data_.size() || e.packed > data_.size() - body) return false;
  if (e.method == 0) {
    if (e.packed != e.size) return false;
    out.assign(data_, body, e.size);
  } else if (!inflateRaw(p + body, e.packed, e.size, out)) {
    return false;
  }
  return out.size() == e.size && crc32of(out.data(), out.size()) == e.crc;
}

std::string makeZip(const std::vector<std::pair<std::string, std::string>>& files) {
  std::string out, dir;
  auto u16 = [](std::string& s, uint32_t v) {
    s.push_back((char)(v & 255));
    s.push_back((char)(v >> 8 & 255));
  };
  auto u32 = [&](std::string& s, uint32_t v) {
    u16(s, v & 0xFFFF);
    u16(s, v >> 16);
  };
  const uint32_t stamp = 0x21u << 16;  // 1 January 1980, so the same files give the same archive
  for (auto& f : files) {
    uint32_t crc = crc32of(f.second.data(), f.second.size()), n = (uint32_t)f.second.size(), at = (uint32_t)out.size();
    u32(out, 0x04034b50u);
    u16(out, 20);
    u16(out, 0x0800);  // names are UTF-8
    u16(out, 0);
    u32(out, stamp);
    u32(out, crc);
    u32(out, n);
    u32(out, n);
    u16(out, (uint32_t)f.first.size());
    u16(out, 0);
    out += f.first;
    out += f.second;
    u32(dir, 0x02014b50u);
    u16(dir, 20);
    u16(dir, 20);
    u16(dir, 0x0800);
    u16(dir, 0);
    u32(dir, stamp);
    u32(dir, crc);
    u32(dir, n);
    u32(dir, n);
    u16(dir, (uint32_t)f.first.size());
    u16(dir, 0);
    u16(dir, 0);
    u16(dir, 0);
    u16(dir, 0);
    u32(dir, 0);
    u32(dir, at);
    dir += f.first;
  }
  uint32_t start = (uint32_t)out.size();
  out += dir;
  u32(out, 0x06054b50u);
  u16(out, 0);
  u16(out, 0);
  u16(out, (uint32_t)files.size());
  u16(out, (uint32_t)files.size());
  u32(out, (uint32_t)dir.size());
  u32(out, start);
  u16(out, 0);
  return out;
}

}  // namespace rt
