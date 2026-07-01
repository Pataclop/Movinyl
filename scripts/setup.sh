#!/usr/bin/env bash
# Movinyl one-shot setup for Linux and macOS.
#
#   ./scripts/setup.sh                    # venv + pip deps + build the C++ renderers
#   ./scripts/setup.sh --install-system   # also install opencv/ffmpeg/cmake first
#
# A local virtual environment (.venv) is used so `pip install` works everywhere,
# including on the externally-managed Python builds from Homebrew (PEP 668).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
    echo "ERROR: Python 3 is required but was not found on PATH." >&2
    exit 1
fi

VENV="$ROOT/.venv"
if [ ! -d "$VENV" ]; then
    echo "Creating virtual environment in .venv ..."
    "$PY" -m venv "$VENV"
fi
VPY="$VENV/bin/python"

echo "Installing Python dependencies ..."
"$VPY" -m pip install --upgrade pip >/dev/null
"$VPY" -m pip install -r requirements.txt

# Build the C++ renderers and create the working zones (deps already handled).
"$VPY" -m movinyl setup --no-python "$@"

echo
echo "Done. Activate the environment and launch the dashboard:"
echo "    source .venv/bin/activate"
echo "    python -m movinyl tui"
