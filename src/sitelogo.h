// Gets a website's own logo and name, by asking that site only. Runs in a short-lived copy of the program,
// so nothing that came from the network is ever handled by the part that stays running.
#pragma once
#include "common.h"

namespace rt {

struct SiteInfo {
  std::wstring image;  // path of the stored picture, empty when none was found
  std::wstring name;   // what the site calls itself
};

bool isWebAddress(const std::wstring& url);
std::wstring siteHost(const std::wstring& url);        // "youtube.com"
bool parseSiteInfo(const std::string& json, SiteInfo& out);

// "--logo-worker <request>": first line the address, second the file to write the answer to,
// third "site" (look for the logo) or "image" (the address is the picture itself).
int runLogoHelper(const std::wstring& requestFile);
// Starts that helper and waits for it.
bool askSite(const std::wstring& url, bool isImage, SiteInfo& out);

// Parsing, separate so it can be tested without a network.
struct LogoLink {
  std::wstring url;
  int size = 0;      // declared or guessed
  int score = 0;
};
struct PageFacts {
  std::vector<LogoLink> links;
  std::wstring manifest, name;
};
PageFacts readPage(const std::string& html, const std::wstring& pageUrl, const std::string& contentType = {});
bool privateHost(const std::wstring& host);           // this PC or the local network
void readManifest(const std::string& json, const std::wstring& manifestUrl, PageFacts& facts);
void rankLinks(std::vector<LogoLink>& links);
std::wstring resolveUrl(const std::wstring& base, const std::wstring& ref);

}  // namespace rt
