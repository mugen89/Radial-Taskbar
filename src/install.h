// Shared by the app (uninstalling itself) and the setup program.
#pragma once
#include "common.h"

namespace rt {

constexpr const wchar_t* kAppName = RT_NAME;
constexpr const wchar_t* kExeName = RT_EXE;
constexpr const wchar_t* kUninstallKey = L"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\" RT_ID;

std::wstring knownFolder(REFKNOWNFOLDERID id);
std::wstring defaultInstallDir();
std::wstring installedDir();            // empty when not installed
std::wstring installedVersion();
std::wstring startMenuLink();
std::wstring desktopLink();
std::wstring sendToLink();
bool fileMenuOn(const std::wstring& exe = {});      // "Add to Radial Taskbar" for files and folders in Explorer, through this program
void setFileMenu(bool on, const std::wstring& exe);
// The list of skins that came with the program, kept beside them.
constexpr const wchar_t* kIncluded = L"included.txt";
std::vector<std::wstring> includedSkins(const std::string& list);
void setSkinType(bool on, const std::wstring& exe);   // double-clicking a .rskin file adds it
bool skinTypeIs(const std::wstring& dir);            // it belongs to the program in this folder
std::wstring betaDir();                 // where the test version is installed, if it is
bool betaThere();                       // installed or running
bool removeBeta(DWORD waitMs);          // closes it and lets its own uninstaller remove it; its settings stay for us
bool quitApp(const wchar_t* id, DWORD waitMs);  // asks a running copy to close; false if it refuses
inline bool quitRunningApp(DWORD waitMs) { return quitApp(RT_ID, waitMs); }
constexpr const wchar_t* kUninstaller = L"Uninstall.exe";  // beside the program

int runUninstall(const std::vector<std::wstring>& args);  // "--uninstall"
int runUninstallStage2(const std::wstring& dir, bool silent, bool purge);

}  // namespace rt
