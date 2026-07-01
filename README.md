<!--
*** Movinyl README — reference-style links live at the very bottom.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->

<!-- HEADER -->
<div align="center">

  <a href="https://github.com/Pataclop/Movinyl">
    <img src="/logos/movinyl_logo_square_bold.png" alt="Movinyl logo" width="240">
  </a>

  <h1>Movinyl</h1>

  <p><b>Capture the colors and spirit of a movie — as a vinyl-like disk poster.</b></p>

  <p>
    Every frame of a film becomes one concentric ring. Play a whole movie in a single image.
  </p>

  <p>
    <a href="#-how-it-works">How it works</a> ·
    <a href="#-install">Install</a> ·
    <a href="#-usage">Usage</a> ·
    <a href="#-configuration">Configuration</a> ·
    <a href="#-contributing">Contributing</a>
  </p>

  [![Contributors][contributors-shield]][contributors-url]
  [![Forks][forks-shield]][forks-url]
  [![Stargazers][stars-shield]][stars-url]
  [![Issues][issues-shield]][issues-url]
  [![License][license-shield]][license-url]
  ![Platforms][platforms-shield]
  ![Python][python-shield]

</div>

---

## ✨ About

**Movinyl** turns a movie into a poster: it samples thousands of frames across the
runtime and paints each one as a single **1-pixel-wide concentric ring**. The
outermost ring is the opening shot, the innermost is the final frame — so the whole
film's color journey is captured in one vibrant, vinyl-like disk. Pages add the
title, year, director, runtime and an extracted color palette.

<div align="center">
  <img src="https://github.com/Pataclop/Movinyl/blob/master/example_img/3.jpg" alt="Example Movinyl result" width="480">
</div>

Movinyl runs natively on **Linux, macOS and Windows** (and in Docker). A small,
pure-Python front-end drives optimized C++ renderers and `ffmpeg`, with live
progress bars and an interactive dashboard. Rendering is **deterministic** — the
same input yields a bit-identical disk on every machine.

---

## 🎛 How it works

```
 video ──▶ ffmpeg ──▶ 2000 frames ──▶ disk renderer ──▶ 4000×4000 disk ──▶ page
          (extract)   (capped 1080p)   (C++ · OpenMP)      PNG              (title · palette · info)
```

| Stage | Tool | What happens |
|-------|------|--------------|
| **Extract** | `ffmpeg` | Pulls ~2000 evenly-spaced frames in a single pass, capped to 1080p (each frame only colors a 1px ring, so full 4K detail is wasted I/O). |
| **Disk** | C++ + OpenCV | Each frame → one concentric ring, filled in parallel with integer-only geometry for reproducible output. |
| **Palette** | Pillow | Extracts the dominant colors straight from the finished disk. |
| **Info** | TMDB | Looks up the official title, director and runtime (optional; degrades gracefully offline). |
| **Page** | C++ + Pillow | Composes the final poster: centered disk, text layers and palette. |
| **Planche** | Pillow | Optional printable contact sheets (grids of disks). |

---

## 📦 Install

Movinyl needs **Python 3.8+**, plus **CMake**, a **C++ compiler**, **OpenCV** and
**ffmpeg**. The setup scripts handle the Python side and compile the renderers.

```sh
# Linux / macOS
./scripts/setup.sh
#   add --install-system to also install opencv/ffmpeg/cmake via your package manager

# Windows (PowerShell)
./scripts/setup.ps1
```

Check your environment at any time:

```sh
python3 -m movinyl doctor
```

<details>
<summary><b>System libraries per platform</b> (only if <code>doctor</code> reports them missing)</summary>

<br>

| OS | Command |
|----|---------|
| **Debian / Ubuntu** | `sudo apt-get install -y build-essential cmake libopencv-dev ffmpeg` |
| **Fedora** | `sudo dnf install -y gcc-c++ cmake opencv-devel ffmpeg` |
| **Arch** | `sudo pacman -S base-devel cmake opencv ffmpeg` |
| **macOS** | `brew install opencv libomp ffmpeg cmake` |
| **Windows** | `vcpkg install opencv4 ffmpeg` (set `VCPKG_ROOT`), plus CMake + MSVC |

</details>

> [!TIP]
> `setup.sh` / `setup.ps1` create a local `.venv`. Activate it before running Movinyl:
> `source .venv/bin/activate` — on Windows: `.venv\Scripts\activate`.

---

## 🚀 Usage

### The dashboard (recommended)

```sh
python3 -m movinyl tui
```

Drop videos in `PROCESSING_ZONE`, then use the on-screen buttons or shortcuts:

| Key | Action |
|:---:|--------|
| **d** | Generate disks from the videos |
| **p** | Build pages from the disks |
| **a** | Assemble contact sheets (planche) |
| **s** | Setup / build the C++ renderers |
| **c** | Cancel the running job |
| **q** | Quit |

Live progress bars, a file list and clean cancellation are built in.

### The command line

Name your videos `Title_Year.ext` (e.g. `Inception_2010.mp4`) and drop them in `PROCESSING_ZONE`:

```sh
python3 -m movinyl disk              # → 4000×4000 PNG disks
python3 -m movinyl page  PAGE_ZONE   # → movie pages (title / year / director / palette)
python3 -m movinyl planche           # → printable contact sheets
python3 -m movinyl doctor            # → environment check
```

### Docker

No local toolchain required — everything builds inside the image:

```sh
docker build -t movinyl .
docker run --rm -v "$(pwd)/PROCESSING_ZONE:/app/PROCESSING_ZONE" movinyl disk
```

Or with Compose (point `MOVIES_DIR` at your video folder):

```sh
docker compose run --rm movinyl disk
```

---

## ⚙️ Configuration

Tuning is done via command-line flags (not env vars):

| Flag | Command | Default | Description |
|------|---------|:-------:|-------------|
| `--n` | `disk` | `2000` | Frames per video (= rings on the disk). |
| `--max-height` | `disk` | `1080` | Cap frame resolution. Sources are **never upscaled**; each frame only paints a 1px ring, so this trades wasted decode/I-O for speed. Use `0` to keep full resolution. |
| `--overwrite` | `disk` | off | Re-render disks that already exist. |
| `--keep-frames` | `disk` | off | Keep the extracted frames instead of cleaning them up. |
| `--jobs` | `page` | CPU count | Number of parallel page workers. |
| `--leave-cores` | `page` | `0` | Keep N cores free so the machine stays responsive. |
| `--tmdb-key` | `page` | bundled | Override the TMDB API key. |

The optional **TMDB API key** (for title/director/runtime) can also be set via the
`TMDB_API_KEY` environment variable — see [`env.example`](env.example). A working
default is bundled, so it's optional.

---

## 🗺 Roadmap

See the [open issues][issues-url] for proposed features and known bugs — contributions welcome!

- [ ] QR code on pages
- [ ] More page layout options
- [ ] Planche (contact sheet) rework
- [x] Faster, resolution-aware extraction
- [x] Cross-platform Python front-end + TUI

---

## 🤝 Contributing

Made a disk you're proud of? Add it to the community album, or send us your
creations by mail — it saves us re-processing movies and helps others discover
new ones. Sharing is greatly appreciated.

📀 [Community album][album-url] · ✉️ project.movinyl@gmail.com  (4000×4000 PNG files)

For code contributions:

1. Fork the project
2. Create your feature branch — `git checkout -b feature/AmazingFeature`
3. Commit your changes — `git commit -m 'Add some AmazingFeature'`
4. Push to the branch — `git push origin feature/AmazingFeature`
5. Open a Pull Request

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`][license-url] for details.

## 📬 Contact

**Movinyl** — project.movinyl@gmail.com
Project link: [https://github.com/Pataclop/Movinyl](https://github.com/Pataclop/Movinyl)


<!-- MARKDOWN LINKS & IMAGES -->
[contributors-shield]: https://img.shields.io/github/contributors/Pataclop/Movinyl.svg?style=for-the-badge
[contributors-url]: https://github.com/Pataclop/Movinyl/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/Pataclop/Movinyl.svg?style=for-the-badge
[forks-url]: https://github.com/Pataclop/Movinyl/network/members
[stars-shield]: https://img.shields.io/github/stars/Pataclop/Movinyl.svg?style=for-the-badge
[stars-url]: https://github.com/Pataclop/Movinyl/stargazers
[issues-shield]: https://img.shields.io/github/issues/Pataclop/Movinyl.svg?style=for-the-badge
[issues-url]: https://github.com/Pataclop/Movinyl/issues
[license-shield]: https://img.shields.io/github/license/Pataclop/Movinyl.svg?style=for-the-badge
[license-url]: https://github.com/Pataclop/Movinyl/blob/master/LICENSE
[platforms-shield]: https://img.shields.io/badge/platforms-Linux%20%7C%20macOS%20%7C%20Windows-informational?style=for-the-badge
[python-shield]: https://img.shields.io/badge/python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white
[album-url]: https://photos.app.goo.gl/TtnD8yMPEKirk46R6
