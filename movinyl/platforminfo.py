"""Platform detection helpers: OS, CPU count, binary locations, package managers.

Everything OS-specific is funnelled through this module so the rest of the code
base stays platform-agnostic.
"""
from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path
from typing import List, Optional

# Repository root = parent of the ``movinyl`` package directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

BUILD_DIR = PROJECT_ROOT / "build"

# Video container extensions we accept as input (lower-case, no dot).
VIDEO_EXTENSIONS = {
    "mp4", "mkv", "avi", "mov", "flv", "wmv", "webm", "mpg", "mpeg",
    "3gp", "ogv", "mts", "m2ts", "ts", "m4v", "divx", "vob",
}


def system() -> str:
    """Return a normalized OS name: ``'linux'``, ``'macos'`` or ``'windows'``."""
    s = platform.system().lower()
    if s.startswith("darwin"):
        return "macos"
    if s.startswith("win"):
        return "windows"
    return "linux"


def is_windows() -> bool:
    return system() == "windows"


def exe_suffix() -> str:
    return ".exe" if is_windows() else ""


def cpu_count() -> int:
    return os.cpu_count() or 1


def default_jobs(leave_cores: int = 0) -> int:
    """How many parallel page jobs to run by default.

    Uses every core but lets the caller keep ``leave_cores`` free so the machine
    stays responsive.
    """
    return max(1, cpu_count() - max(0, leave_cores))


def which(name: str) -> Optional[str]:
    """Locate an executable on PATH (cross-platform ``which``)."""
    return shutil.which(name)


def _candidate_binaries(name: str) -> List[Path]:
    suffix = exe_suffix()
    stem = f"{name}{suffix}"
    return [
        BUILD_DIR / stem,
        BUILD_DIR / "Release" / stem,
        BUILD_DIR / "Debug" / stem,
        BUILD_DIR / "RelWithDebInfo" / stem,
        PROJECT_ROOT / stem,                       # legacy: binary copied to root
        PROJECT_ROOT / "src" / name / stem,        # legacy: in-tree build
    ]


def find_binary(name: str) -> Optional[Path]:
    """Return the path to a built C++ binary (``disk`` / ``page``), or None."""
    for candidate in _candidate_binaries(name):
        if candidate.is_file():
            return candidate
    return None


def disk_binary() -> Optional[Path]:
    return find_binary("disk")


def page_binary() -> Optional[Path]:
    return find_binary("page")


# --- Package-manager guidance ----------------------------------------------

def detect_package_manager() -> Optional[str]:
    """Best-effort detection of the system package manager."""
    if is_windows():
        for pm in ("vcpkg", "winget", "choco"):
            if which(pm):
                return pm
        return None
    if system() == "macos":
        return "brew" if which("brew") else None
    for pm in ("apt-get", "dnf", "pacman", "zypper"):
        if which(pm):
            return pm
    return None


# System packages needed to build/run the C++ renderers + ffmpeg, per manager.
_SYSTEM_PACKAGES = {
    "apt-get": "sudo apt-get update && sudo apt-get install -y "
               "build-essential cmake libopencv-dev ffmpeg",
    "dnf": "sudo dnf install -y gcc-c++ cmake opencv-devel ffmpeg",
    "pacman": "sudo pacman -S --needed base-devel cmake opencv ffmpeg",
    "zypper": "sudo zypper install -y gcc-c++ cmake opencv-devel ffmpeg",
    "brew": "brew install opencv libomp ffmpeg cmake",
    "vcpkg": "vcpkg install opencv4 ffmpeg",
    "winget": "winget install Kitware.CMake FFmpeg.FFmpeg  "
              "(then install OpenCV via vcpkg: vcpkg install opencv4)",
    "choco": "choco install cmake ffmpeg opencv",
}


def system_install_command(pm: Optional[str] = None) -> Optional[str]:
    """Return the shell command that installs the build/runtime system deps."""
    pm = pm or detect_package_manager()
    if pm is None:
        return None
    return _SYSTEM_PACKAGES.get(pm)
