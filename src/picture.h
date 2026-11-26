// Pictures people give to their pins: decoding, keeping a copy beside the settings, tidying for display.
#pragma once
#include "common.h"
#include "icons.h"

namespace rt {

// PNG, JPEG, WebP, ICO, BMP, GIF, TIFF ... and SVG when allowed (that one needs the graphics device, so UI thread only).
bool decodePicture(const std::string& bytes, int maxSide, IconImage& out, bool allowSvg);
bool encodePng(const IconImage& img, std::string& out);
bool isPictureFile(const std::wstring& path);
extern const wchar_t* const kPictureFilter;

// Stores a copy in the settings folder, so the pin survives the original being moved or deleted.
// Returns the path of the copy, or an empty string when the bytes are not a usable picture.
std::wstring keepPicture(const std::string& bytes, const std::wstring& name);

// Makes any picture sit well next to app icons: squares it, trims plain margins, rounds full-bleed images and
// puts a plate behind logos that would vanish on a dark or light wheel.
void tidyPicture(IconImage& img, PicShape shape, int size);
void squarePicture(IconImage& img);

// Deletes stored pictures and shortcuts that no pin has used for a month. Until then the safety copies of the settings
// still find them.
void sweepKept(const Config& cfg);

// What the clipboard offers: picture bytes, or the address of one.
bool clipboardPicture(HWND owner, std::string& bytes, std::wstring& link);

}  // namespace rt
