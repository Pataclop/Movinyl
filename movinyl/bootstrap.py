"""Environment diagnostics (``doctor``) and the cross-platform C++ build (``setup``)."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from . import platforminfo as pf

ZONES = ("PROCESSING_ZONE", "PAGE_ZONE")


@dataclass
class Check:
    name: str
    status: str           # "ok" | "warn" | "missing"
    detail: str = ""
    fix: Optional[str] = None


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------

def _cxx_compiler() -> Optional[str]:
    for cc in ("c++", "g++", "clang++", "cl"):
        if pf.which(cc):
            return cc
    return None


def _opencv_present() -> bool:
    """Best-effort OpenCV detection (pkg-config, or an already-built binary)."""
    pkgconfig = pf.which("pkg-config")
    if pkgconfig:
        for name in ("opencv4", "opencv"):
            try:
                if subprocess.run([pkgconfig, "--exists", name]).returncode == 0:
                    return True
            except OSError:
                pass
    # If the binaries are already built, OpenCV was clearly found at build time.
    return pf.disk_binary() is not None


def _module_present(mod: str) -> bool:
    import importlib.util
    return importlib.util.find_spec(mod) is not None


def doctor() -> List[Check]:
    """Run every environment check and return the results."""
    checks: List[Check] = []
    install = pf.system_install_command() or "your package manager"

    # Runtime tools
    for tool, why in (("ffmpeg", "frame extraction"), ("ffprobe", "video duration")):
        path = pf.which(tool)
        checks.append(Check(
            tool, "ok" if path else "missing",
            path or f"required for {why}", None if path else install,
        ))

    # Build toolchain
    cmake = pf.which("cmake")
    checks.append(Check("cmake", "ok" if cmake else "missing",
                        cmake or "required to build the C++ renderers",
                        None if cmake else install))
    cxx = _cxx_compiler()
    checks.append(Check("c++ compiler", "ok" if cxx else "missing",
                        cxx or "g++/clang++/cl needed",
                        None if cxx else install))
    has_cv = _opencv_present()
    checks.append(Check("OpenCV", "ok" if has_cv else "warn",
                        "found" if has_cv else "not detected via pkg-config",
                        None if has_cv else install))

    # Built binaries
    for name in ("disk", "page"):
        binary = pf.find_binary(name)
        checks.append(Check(f"{name} binary", "ok" if binary else "missing",
                            str(binary) if binary else "not built",
                            None if binary else "movinyl setup"))

    # Python modules
    for mod, pip_name in (("rich", "rich"), ("textual", "textual"),
                          ("PIL", "Pillow"), ("tmdbsimple", "tmdbsimple")):
        ok = _module_present(mod)
        checks.append(Check(f"python:{mod}", "ok" if ok else "warn",
                            "installed" if ok else "missing",
                            None if ok else f"pip install {pip_name}"))

    return checks


# ---------------------------------------------------------------------------
# setup / build
# ---------------------------------------------------------------------------

def _brew_prefix(formula: str) -> Optional[str]:
    if pf.which("brew") is None:
        return None
    try:
        out = subprocess.check_output(["brew", "--prefix", formula],
                                      stderr=subprocess.DEVNULL).decode().strip()
        return out or None
    except (OSError, subprocess.CalledProcessError):
        return None


def _cmake_configure_args() -> List[str]:
    args = ["-S", str(pf.PROJECT_ROOT / "src"), "-B", str(pf.BUILD_DIR),
            "-DCMAKE_BUILD_TYPE=Release"]

    # On Windows, wire up a vcpkg toolchain automatically if VCPKG_ROOT is set.
    vcpkg = os.environ.get("VCPKG_ROOT")
    if vcpkg:
        toolchain = Path(vcpkg) / "scripts" / "buildsystems" / "vcpkg.cmake"
        if toolchain.is_file():
            args.append(f"-DCMAKE_TOOLCHAIN_FILE={toolchain}")

    # On macOS, point CMake at the Homebrew OpenCV + libomp so OpenMP works under
    # Apple clang (which otherwise can't find <omp.h> / libomp).
    if pf.system() == "macos":
        prefixes = [p for p in (_brew_prefix("opencv"), _brew_prefix("libomp")) if p]
        if prefixes:
            args.append("-DCMAKE_PREFIX_PATH=" + ";".join(prefixes))
        libomp = _brew_prefix("libomp")
        if libomp:
            args.append(f"-DOpenMP_ROOT={libomp}")
    return args


def build_cpp(log=print) -> None:
    """Configure and build the C++ renderers with CMake. Raises on failure."""
    if pf.which("cmake") is None:
        raise RuntimeError(
            "cmake is required. Install it with:\n    "
            + (pf.system_install_command() or "your package manager")
        )
    if _cxx_compiler() is None:
        raise RuntimeError("No C++ compiler found (need g++, clang++ or MSVC).")

    pf.BUILD_DIR.mkdir(parents=True, exist_ok=True)
    log("Configuring (cmake)...")
    subprocess.run(["cmake", *_cmake_configure_args()], check=True)
    log("Building (cmake --build)...")
    subprocess.run(
        ["cmake", "--build", str(pf.BUILD_DIR), "--config", "Release", "--parallel"],
        check=True,
    )

    missing = [n for n in ("disk", "page") if pf.find_binary(n) is None]
    if missing:
        raise RuntimeError(f"Build finished but binaries missing: {', '.join(missing)}")
    log("Build OK: " + ", ".join(str(pf.find_binary(n)) for n in ("disk", "page")))


def install_python_deps(log=print) -> None:
    req = pf.PROJECT_ROOT / "requirements.txt"
    if not req.is_file():
        return
    log("Installing Python dependencies (pip)...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req)], check=True)


def install_system_deps(log=print) -> None:
    cmd = pf.system_install_command()
    if not cmd:
        log("No known package manager detected; install system deps manually.")
        return
    log(f"Installing system dependencies:\n    {cmd}")
    subprocess.run(cmd, shell=True, check=True)


def create_zones(log=print) -> None:
    for zone in ZONES:
        path = pf.PROJECT_ROOT / zone
        path.mkdir(exist_ok=True)
    log(f"Zones ready: {', '.join(ZONES)}")


def setup(install_system: bool = False, install_python: bool = True, log=print) -> None:
    """Full setup: (optional) system deps, python deps, build C++, create zones."""
    if install_system:
        install_system_deps(log)
    if install_python:
        try:
            install_python_deps(log)
        except subprocess.CalledProcessError as exc:
            log(f"[warn] pip install failed ({exc}); continuing.")
    build_cpp(log)
    create_zones(log)
