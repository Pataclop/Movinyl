"""Build a standalone Windows app: dist/Movinyl/Movinyl.exe (PyQt6 GUI).

Re-run it any time you change the code; it rebuilds everything from scratch:

    python scripts/build_exe.py            # build the C++ renderers + the exe
    python scripts/build_exe.py --zip      # ... and also dist/Movinyl.zip
    python scripts/build_exe.py --skip-cpp # reuse the already-built disk/page

Prerequisites: the C++ renderers must build on this machine (CMake + MSVC +
OpenCV: the prebuilt package with ``OpenCV_DIR=C:/opencv/build``, or vcpkg
with ``VCPKG_ROOT`` set) and ffmpeg/ffprobe must be on PATH (or pass
``--ffmpeg-dir``). PyInstaller is installed automatically if missing.

Layout of the result (copy/zip the whole folder, not just the .exe):

    dist/Movinyl/
        Movinyl.exe
        _internal/          Python, Qt, fonts (managed by PyInstaller)
        bin/                disk.exe, page.exe, ffmpeg.exe, ffprobe.exe + DLLs
        PROCESSING_ZONE/    default video folder
        PAGE_ZONE/          default disk/page folder
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from movinyl import bootstrap  # noqa: E402
from movinyl import platforminfo as pf  # noqa: E402

APP_NAME = "Movinyl"
DIST = ROOT / "dist"
WORK = ROOT / "build" / "pyinstaller"
FONTS = ("futura light bt.ttf", "futura medium bt.ttf")
LOGO = ROOT / "logos" / "movinyl_logo_square_bold.png"

# MSVC runtime DLLs the C++ renderers need (vcomp140 = OpenMP). They are often
# already installed system-wide, but bundling them makes the app self-contained.
MSVC_RUNTIME = ("msvcp140.dll", "msvcp140_1.dll", "vcruntime140.dll",
                "vcruntime140_1.dll", "vcomp140.dll", "concrt140.dll")


def step(msg: str) -> None:
    print(f"\n==> {msg}", flush=True)


def run(cmd, **kwargs) -> None:
    print("   $", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], check=True, **kwargs)


def ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        step("Installing PyInstaller")
        run([sys.executable, "-m", "pip", "install", "pyinstaller"])
    try:
        import PyQt6  # noqa: F401
    except ImportError:
        step("Installing PyQt6")
        run([sys.executable, "-m", "pip", "install", "PyQt6"])


def make_icon() -> Optional[Path]:
    """Convert the PNG logo to a .ico for the exe (skipped if Pillow is missing)."""
    if not LOGO.is_file():
        return None
    try:
        from PIL import Image
    except ImportError:
        return None
    ico = WORK / "movinyl.ico"
    WORK.mkdir(parents=True, exist_ok=True)
    Image.open(LOGO).save(ico, sizes=[(16, 16), (32, 32), (48, 48), (64, 64),
                                      (128, 128), (256, 256)])
    return ico


def run_pyinstaller(icon: Optional[Path]) -> Path:
    WORK.mkdir(parents=True, exist_ok=True)
    entry = WORK / "movinyl_gui_entry.py"
    entry.write_text(
        "import sys\nfrom movinyl.gui import run\nsys.exit(run())\n",
        encoding="utf-8",
    )
    cmd = [
        sys.executable, "-m", "PyInstaller", str(entry),
        "--name", APP_NAME,
        "--noconfirm", "--clean",
        "--windowed",                 # no console window behind the GUI
        "--onedir",
        "--distpath", DIST,
        "--workpath", WORK,
        "--specpath", WORK,
        "--paths", ROOT,
        # The GUI does not need the terminal front-ends.
        "--exclude-module", "textual",
        "--exclude-module", "tkinter",
        # PyInstaller refuses to bundle two Qt bindings at once.
        "--exclude-module", "PyQt5",
        "--exclude-module", "PySide2",
        "--exclude-module", "PySide6",
    ]
    for font in FONTS:
        cmd += ["--add-data", f"{ROOT / font}{os.pathsep}."]
    if icon:
        cmd += ["--icon", icon]
    run(cmd, cwd=ROOT)
    return DIST / APP_NAME


def copy_binary_with_dlls(exe: Path, dest: Path) -> None:
    """Copy ``exe`` and every DLL sitting next to it (vcpkg / ffmpeg-shared)."""
    shutil.copy2(exe, dest / exe.name)
    for dll in exe.parent.glob("*.dll"):
        if not (dest / dll.name).exists():
            shutil.copy2(dll, dest / dll.name)
    print(f"   + {exe.name} (from {exe.parent})")


def find_ffmpeg_tool(name: str, ffmpeg_dir: Optional[Path]) -> Path:
    if ffmpeg_dir:
        candidate = ffmpeg_dir / f"{name}.exe"
        if candidate.is_file():
            return candidate
        raise SystemExit(f"{candidate} not found")
    found = shutil.which(name)
    if not found:
        raise SystemExit(
            f"'{name}' not found on PATH. Install ffmpeg (winget install "
            f"Gyan.FFmpeg) or pass --ffmpeg-dir C:\\path\\to\\ffmpeg\\bin")
    # Follow symlinks (winget puts links in ...\WinGet\Links).
    return Path(found).resolve()


def copy_msvc_runtime(dest: Path) -> None:
    system32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    missing = []
    for dll in MSVC_RUNTIME:
        src = system32 / dll
        if src.is_file():
            if not (dest / dll).exists():
                shutil.copy2(src, dest / dll)
        else:
            missing.append(dll)
    if missing:
        print(f"   (not found in System32, skipped: {', '.join(missing)})")


def bundle_binaries(app_dir: Path, ffmpeg_dir: Optional[Path]) -> None:
    bin_dir = app_dir / "bin"
    bin_dir.mkdir(exist_ok=True)

    for name in ("disk", "page"):
        exe = pf.find_binary(name)
        if exe is None:
            raise SystemExit(f"{name}.exe is not built. Run without --skip-cpp.")
        copy_binary_with_dlls(exe, bin_dir)

    for name in ("ffmpeg", "ffprobe"):
        copy_binary_with_dlls(find_ffmpeg_tool(name, ffmpeg_dir), bin_dir)

    copy_msvc_runtime(bin_dir)


def smoke_test(app_dir: Path) -> None:
    """Check that the bundled binaries actually start (catches missing DLLs)."""
    bin_dir = app_dir / "bin"
    for exe, args in (("ffmpeg.exe", ["-version"]), ("ffprobe.exe", ["-version"])):
        res = subprocess.run([str(bin_dir / exe), *args], capture_output=True)
        status = "ok" if res.returncode == 0 else f"FAILED ({res.returncode})"
        print(f"   {exe}: {status}")
    # disk/page have no --version; a missing DLL makes Windows return
    # 0xC0000135 (STATUS_DLL_NOT_FOUND) before main() even runs.
    for exe in ("disk.exe", "page.exe"):
        res = subprocess.run([str(bin_dir / exe)], capture_output=True,
                             cwd=str(WORK))
        if res.returncode & 0xFFFFFFFF == 0xC0000135:
            print(f"   {exe}: FAILED (missing DLL)")
        else:
            print(f"   {exe}: ok (starts)")


def main() -> int:
    if not pf.is_windows():
        print("This script builds the Windows .exe; run it on Windows.")
        return 1

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--skip-cpp", action="store_true",
                    help="Do not rebuild the C++ renderers.")
    ap.add_argument("--ffmpeg-dir", type=Path, default=None,
                    help="Folder containing ffmpeg.exe/ffprobe.exe "
                         "(default: found on PATH).")
    ap.add_argument("--zip", action="store_true",
                    help="Also create dist/Movinyl.zip.")
    args = ap.parse_args()

    ensure_pyinstaller()

    if not args.skip_cpp:
        step("Building C++ renderers")
        bootstrap.build_cpp(log=lambda m: print("   " + m))

    step("Running PyInstaller")
    app_dir = run_pyinstaller(make_icon())

    step("Bundling disk/page/ffmpeg")
    bundle_binaries(app_dir, args.ffmpeg_dir)

    for zone in bootstrap.ZONES:
        (app_dir / zone).mkdir(exist_ok=True)

    step("Smoke test")
    smoke_test(app_dir)

    if args.zip:
        step("Zipping")
        archive = shutil.make_archive(str(DIST / APP_NAME), "zip",
                                      root_dir=DIST, base_dir=APP_NAME)
        print(f"   {archive}")

    step(f"Done: {app_dir / (APP_NAME + '.exe')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
