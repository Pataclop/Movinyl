# Cross-platform build for Movinyl's C++ renderers (disk, page, disk_mono).
#
#   cmake -S src -B build -DCMAKE_BUILD_TYPE=Release
#   cmake --build build -j
#
# On Windows, point CMake at a vcpkg toolchain so OpenCV is found, e.g.:
#   cmake -S src -B build -DCMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake
#
# The Python front-end (`movinyl setup`) runs these two commands for you.

cmake_minimum_required(VERSION 3.16)
project(movinyl LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Default to an optimized build. We deliberately do NOT enable -march=native or
# -ffast-math: keeping IEEE float semantics is what makes the output reproducible
# across machines and operating systems.
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

if(MSVC)
  add_compile_options($<$<CONFIG:Release>:/O2> $<$<CONFIG:Release>:/DNDEBUG>)
else()
  add_compile_options($<$<CONFIG:Release>:-O3> $<$<CONFIG:Release>:-DNDEBUG>)
endif()

find_package(OpenCV REQUIRED)
find_package(OpenMP)   # optional: disk falls back to single-thread without it

include_directories(${OpenCV_INCLUDE_DIRS})

# --- disk (the heavy renderer, OpenMP-parallel) ----------------------------
add_executable(disk disk/disk.cpp)
target_link_libraries(disk PRIVATE ${OpenCV_LIBS})
if(OpenMP_CXX_FOUND)
  target_link_libraries(disk PRIVATE OpenMP::OpenMP_CXX)
endif()

# --- page (compose the final movie page) -----------------------------------
add_executable(page page/page.cpp)
target_link_libraries(page PRIVATE ${OpenCV_LIBS})

# --- disk_mono (optional fast/low-quality variant: one color per frame) -----
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/disk_mono/disk_mono.cpp")
  add_executable(disk_mono disk_mono/disk_mono.cpp)
  target_link_libraries(disk_mono PRIVATE ${OpenCV_LIBS})
endif()

# Drop the binaries straight into the build directory root (build/disk,
# build/page, ...) so the Python layer finds them with one predictable glob,
# including under MSVC multi-config generators.
set_target_properties(disk page PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY                "${CMAKE_BINARY_DIR}"
  RUNTIME_OUTPUT_DIRECTORY_RELEASE        "${CMAKE_BINARY_DIR}"
  RUNTIME_OUTPUT_DIRECTORY_DEBUG          "${CMAKE_BINARY_DIR}"
  RUNTIME_OUTPUT_DIRECTORY_RELWITHDEBINFO "${CMAKE_BINARY_DIR}")
if(TARGET disk_mono)
  set_target_properties(disk_mono PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY                "${CMAKE_BINARY_DIR}"
    RUNTIME_OUTPUT_DIRECTORY_RELEASE        "${CMAKE_BINARY_DIR}"
    RUNTIME_OUTPUT_DIRECTORY_DEBUG          "${CMAKE_BINARY_DIR}"
    RUNTIME_OUTPUT_DIRECTORY_RELWITHDEBINFO "${CMAKE_BINARY_DIR}")
endif()
