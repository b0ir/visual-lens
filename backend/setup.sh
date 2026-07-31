#!/usr/bin/env bash
# Sets up the backend using uv: installs uv itself if missing, then lets uv
# fetch the pinned Python version (see pyproject.toml/.python-version),
# create/sync backend/.venv, and install Playwright browsers. Invoked via
# `npm run setup:backend`. No manual Python install is required on any
# platform — uv manages the interpreter itself.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

if ! command -v uv >/dev/null 2>&1; then
  if [ -x "$HOME/.local/bin/uv" ]; then
    export PATH="$HOME/.local/bin:$PATH"
  fi
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found — installing (https://astral.sh/uv)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  if ! command -v uv >/dev/null 2>&1; then
    echo "" >&2
    echo "error: uv installation did not put 'uv' on PATH." >&2
    echo "Install it manually: https://docs.astral.sh/uv/getting-started/installation/" >&2
    echo "then re-run this command." >&2
    exit 1
  fi
fi

echo "Using $(uv --version)"

# Removes any pre-uv venv/ directory from before this repo migrated to uv.
if [ -d venv ] && [ ! -d .venv ]; then
  rm -rf venv
fi

uv sync

if ! uv run python -c "from playwright.sync_api import sync_playwright; import os, sys
with sync_playwright() as p:
    sys.exit(0 if all(os.path.exists(b.executable_path) for b in [p.chromium, p.firefox, p.webkit]) else 1)" >/dev/null 2>&1; then
  echo "Installing Playwright browsers (chromium, firefox, webkit)..."
  echo "This can take a few minutes on a first run, and may print nothing for a while."

  uv run playwright install chromium firefox webkit &
  playwright_pid=$!

  elapsed=0
  while kill -0 "$playwright_pid" 2>/dev/null; do
    sleep 15
    elapsed=$((elapsed + 15))
    echo "Still installing Playwright browsers... (${elapsed}s elapsed)"
  done

  wait "$playwright_pid"
  echo "Playwright browsers installed successfully."
fi
