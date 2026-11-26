cmake_minimum_required(VERSION 3.20)
project(RadialTaskbar VERSION 1.2.0 LANGUAGES CXX RC)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# windres cannot cope with spaces in -I paths or quoted defines, so these are C++ only.
foreach(def UNICODE _UNICODE NOMINMAX WIN32_LEAN_AND_MEAN _WIN32_WINNT=0x0A00 WINVER=0x0A00
        NTDDI_VERSION=0x0A00000C RT_VERSION_STR="${PROJECT_VERSION}")
  add_compile_options($<$<COMPILE_LANGUAGE:CXX>:-D${def}>)
endforeach()

# Lean, self-contained binaries: no runtime DLLs to ship, dead code stripped.
foreach(opt -Wall -Wextra -Wno-unused-parameter -Wno-missing-field-initializers
        -Wno-cast-function-type -Wno-extra -ffunction-sections -fdata-sections -fno-rtti -fno-exceptions)
  add_compile_options($<$<COMPILE_LANGUAGE:CXX>:${opt}>)
endforeach()
set(CMAKE_CXX_FLAGS_RELEASE "-O2 -DNDEBUG")
set(RT_LINK_FLAGS -static -municode -mwindows -Wl,--gc-sections
  -Wl,--dynamicbase -Wl,--nxcompat -Wl,--high-entropy-va)

# GCC for Windows links its own default manifest. An empty stand-in found first keeps ours the only one.
set(RT_STUB "${CMAKE_BINARY_DIR}/nomanifest")
if(NOT EXISTS "${RT_STUB}/default-manifest.o")
  file(MAKE_DIRECTORY "${RT_STUB}")
  file(WRITE "${RT_STUB}/empty.cpp" "")
  execute_process(COMMAND ${CMAKE_CXX_COMPILER} -c empty.cpp -o default-manifest.o WORKING_DIRECTORY "${RT_STUB}")
endif()
list(APPEND RT_LINK_FLAGS "-Bnomanifest/")  # relative: gcc specs split on spaces, and links run in the build folder


set(RT_LIBS d3d11 dxgi d2d1 dwrite dcomp dwmapi windowscodecs shell32 shlwapi
  propsys ole32 oleaut32 uuid dxguid gdi32 user32 advapi32 winmm comctl32
  comdlg32 shcore uxtheme version psapi)

file(GLOB RT_APP_SOURCES CONFIGURE_DEPENDS src/*.cpp)
add_executable(RadialTaskbar ${RT_APP_SOURCES} res/app.rc)
set_source_files_properties(res/app.rc PROPERTIES OBJECT_DEPENDS
  "${CMAKE_SOURCE_DIR}/res/app.ico;${CMAKE_SOURCE_DIR}/res/app.manifest")
target_link_options(RadialTaskbar PRIVATE ${RT_LINK_FLAGS} $<$<CONFIG:Release>:-s>)
target_link_libraries(RadialTaskbar PRIVATE ${RT_LIBS})

# Every folder below skins/ becomes one .rskin file, and all of them one archive for the setup program. The finished
# program does the packing, so nothing else has to be installed.
file(GLOB_RECURSE RT_SKIN_FILES CONFIGURE_DEPENDS skins/*)
add_custom_command(OUTPUT "${CMAKE_BINARY_DIR}/skins.pak"
  COMMAND ${CMAKE_COMMAND} "-DEXE=$<TARGET_FILE:RadialTaskbar>" "-DSRC=${CMAKE_SOURCE_DIR}" "-DOUT=${CMAKE_BINARY_DIR}" -P "${CMAKE_SOURCE_DIR}/tools/pack_skins.cmake"
  DEPENDS RadialTaskbar ${RT_SKIN_FILES} "${CMAKE_SOURCE_DIR}/SKINS.md" "${CMAKE_SOURCE_DIR}/tools/pack_skins.cmake" VERBATIM)
add_custom_target(skins_pak DEPENDS "${CMAKE_BINARY_DIR}/skins.pak")

# Uninstall.exe beside the program: it hands over to the program's own uninstaller.
add_executable(RadialTaskbarUninstall setup/uninstall_main.cpp setup/uninstall.rc)
set_source_files_properties(setup/uninstall.rc PROPERTIES OBJECT_DEPENDS "${CMAKE_SOURCE_DIR}/res/app.ico;${CMAKE_SOURCE_DIR}/res/app.manifest")
target_include_directories(RadialTaskbarUninstall PRIVATE $<$<COMPILE_LANGUAGE:CXX>:${CMAKE_SOURCE_DIR}/src>)
target_link_options(RadialTaskbarUninstall PRIVATE ${RT_LINK_FLAGS} $<$<CONFIG:Release>:-s>)
target_link_libraries(RadialTaskbarUninstall PRIVATE shell32 user32)
set_target_properties(RadialTaskbarUninstall PROPERTIES OUTPUT_NAME "Uninstall")

# The setup program embeds the finished app as a resource, so it is built after it.
add_executable(RadialTaskbarSetup setup/setup_main.cpp src/common.cpp src/gfx.cpp src/ui.cpp src/json.cpp
  src/config.cpp src/shellutil.cpp src/install.cpp src/zip.cpp setup/setup.rc)
add_dependencies(RadialTaskbarSetup skins_pak)
set_source_files_properties(setup/setup.rc PROPERTIES OBJECT_DEPENDS
  "${CMAKE_BINARY_DIR}/RadialTaskbar.exe;${CMAKE_BINARY_DIR}/Uninstall.exe;${CMAKE_BINARY_DIR}/skins.pak;${CMAKE_SOURCE_DIR}/res/app.ico;${CMAKE_SOURCE_DIR}/res/app.manifest")
add_dependencies(RadialTaskbarSetup RadialTaskbar RadialTaskbarUninstall)
target_include_directories(RadialTaskbarSetup PRIVATE $<$<COMPILE_LANGUAGE:CXX>:${CMAKE_SOURCE_DIR}/src>)
target_link_options(RadialTaskbarSetup PRIVATE ${RT_LINK_FLAGS} $<$<CONFIG:Release>:-s>)
target_link_libraries(RadialTaskbarSetup PRIVATE ${RT_LIBS})
set_target_properties(RadialTaskbarSetup PROPERTIES OUTPUT_NAME "RadialTaskbar-Setup")

# Regression tests: cmake -S . -B build -DRT_TESTS=ON, then run them with RADIALTASKBAR_DATA set to an empty folder.
option(RT_TESTS "Build the regression tests" OFF)
if(RT_TESTS)
  add_executable(test_hook tests/test_hook.cpp src/common.cpp src/config.cpp src/json.cpp)
  add_executable(test_config tests/test_config.cpp src/common.cpp src/config.cpp src/json.cpp src/shellutil.cpp src/update.cpp)
  add_executable(test_picture tests/test_picture.cpp src/common.cpp src/config.cpp src/json.cpp src/gfx.cpp src/icons.cpp
    src/picture.cpp src/sitelogo.cpp src/shellutil.cpp src/icontone.cpp)
  add_executable(test_skin tests/test_skin.cpp src/common.cpp src/config.cpp src/json.cpp src/gfx.cpp src/expr.cpp src/zip.cpp src/skin.cpp src/looks.cpp src/backfx.cpp)
  foreach(t test_hook test_config test_picture test_skin)
    target_include_directories(${t} PRIVATE $<$<COMPILE_LANGUAGE:CXX>:${CMAKE_SOURCE_DIR}/src>)
    target_link_options(${t} PRIVATE -static)
    target_link_libraries(${t} PRIVATE ${RT_LIBS})
  endforeach()
endif()
