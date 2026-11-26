// Just enough of the ZIP format for skin files, written to be safe with files from strangers.
#pragma once
#include "common.h"

namespace rt {

// Unpacks raw deflate data. False when the data is damaged or would grow past maxOut.
bool inflateRaw(const uint8_t* src, size_t n, size_t maxOut, std::string& out);
uint32_t crc32of(const void* data, size_t n);

class Archive {
 public:
  struct Entry {
    std::string name;    // forward slashes, no leading slash, never ".."
    uint16_t method = 0;
    uint32_t crc = 0, packed = 0, size = 0, offset = 0;
  };
  struct Limits {
    size_t file = 48u << 20, total = 96u << 20, entries = 600, one = 24u << 20;
  };
  // Reads the list of files. The bytes are kept until the archive goes away.
  bool open(std::string bytes, std::string* err);
  bool open(std::string bytes, std::string* err, const Limits& lim);
  const std::vector<Entry>& entries() const { return list_; }
  const Entry* find(std::string_view name) const;      // ignores case
  bool read(const Entry& e, std::string& out) const;   // checked against its checksum

 private:
  std::string data_;
  std::vector<Entry> list_;
  Limits lim_;
};

// Writes an archive. Files are stored as they are: pictures and sounds do not shrink further.
std::string makeZip(const std::vector<std::pair<std::string, std::string>>& files);

// True when a path inside a skin stays inside it.
bool safeInnerPath(std::string_view p);

}  // namespace rt
