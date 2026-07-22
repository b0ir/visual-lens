# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## App Objective

Analyze pages of a given URL with AI to detect visual errors like missing buttons, wrongly placed items, text overlapping elements, broken layouts, contrast issues, etc.

Features:

- User selects an AI provider, enters their API key, verifies it, and picks from available vision models.
- Dark mode available.

## Architecture

- **Type**: Polyglot Monorepo (NPM Workspaces managed).
- **Frontend**: React, TypeScript, Vite, TailwindCSS (v4), Lucide React.
- **Backend**: Python, FastAPI, Playwright (async), LiteLLM.

## Setup & Execution

- **Install/Setup All**: `npm run setup:all` (installs node modules, creates python venv, installs requirements, downloads Playwright browsers).
- **Start Dev Servers**: `npm run dev` (Runs concurrently: Frontend on `:3000`, Backend on `:8000` with uvicorn reload).

## Codebase Rules

1. **No Emojis**: Do not use emojis anywhere in the UI or backend logs.
2. **Provider Registry**: All supported AI providers and their vision-capable models are defined in `backend/providers.py`. To add a new provider, add an entry to the `PROVIDERS` dict — no other file changes needed.
3. **API Key Handling**: API keys are stored client-side only (localStorage). The backend receives the active key per-request and passes it directly to LiteLLM via the `api_key` parameter. Never mutate `os.environ` for API keys.
4. **LiteLLM Integration**: All AI calls go through `litellm`. Use the `provider/model` format for model identifiers (e.g., `openai/gpt-4.1`, `anthropic/claude-sonnet-4-6`).
5. **Dark Mode**: Tailwind v4 dark mode via `@variant dark` in `index.css`. Use `dark:` classes everywhere.
6. **Log Files**: All `.log` files are in `.gitignore`. If a log file gets accidentally tracked, remove it with `git rm --cached <file>`.
7. **Python version and tooling**: The project runs on **Python 3.14**, declared as `requires-python = ">=3.14"` in `backend/pyproject.toml`. The backend is set up and managed with [`uv`](https://docs.astral.sh/uv/), not raw `pip`/`venv`. `npm run setup:backend` (`backend/setup.sh`) auto-installs `uv` itself if missing (official installer, no manual step), and `uv` then auto-downloads the pinned Python 3.14 interpreter and creates `backend/.venv` — no contributor ever needs to have the right Python pre-installed or on `PATH`. Do not hand-edit `backend/.venv`; it is fully disposable and gitignored.

   Many packages cap `Requires-Python <3.14`, and some (see rule 9) only ship prebuilt wheels for older Python versions, requiring a from-source build on 3.14 that can fail without a compiler toolchain (e.g. Rust for litellm's native bridge). Always check version availability **and wheel availability** on Python 3.14 before bumping any floor or exact pin — a version may resolve fine on paper but fail to install. Check via `https://pypi.org/pypi/<pkg>/<version>/json` → `info.requires_python` and the `urls` array's per-file `requires_python`/`packagetype`.

   **`uv`'s resolver does not always exclude a candidate version solely because its own `Requires-Python` upper bound excludes the target interpreter** — this differs from `pip`, which does exclude it. Don't assume `uv lock` picking a version means that version is actually 3.14-compatible; verify independently via the PyPI metadata above.

8. **`backend/pyproject.toml` / `backend/uv.lock` changes — mandatory validation before any commit**:
   - After any edit to `pyproject.toml`, run `cd backend && uv lock` and confirm it resolves with no errors before staging the changed files (`pyproject.toml` and `uv.lock` together).
   - Better: run the full `npm run setup:all` from the repo root, which exercises the actual install path the user runs (including a from-scratch `uv sync`).
   - CI now runs on Python 3.14 (`backend` job in `ci.yml`, `backend-deps` job in `pr-automation.yml` — both use `astral-sh/setup-uv`), so it does catch Python 3.14 availability gaps. Still validate locally first — CI failing on a dependency change blocks everyone.

9. **litellm is exact-pinned** (`litellm==1.83.7` in `backend/pyproject.toml`), not given a floor/range. litellm 1.83.7 is the newest release with Python 3.14 wheel support: 1.92.0+ declares `Requires-Python <3.14` and only ships as an sdist requiring a Rust toolchain (`maturin`/`cargo`) to build on 3.14, which fails on a typical contributor machine. litellm 1.83.7 also exact-pins its own dependency tree (pydantic, python-dotenv, httpx, aiohttp, openai, jinja2, etc.) — those packages are listed in `dependabot.yml` under `ignore` for the `uv` ecosystem. Do NOT remove those ignore rules. When a newer litellm release adds Python 3.14 wheel support, re-evaluate and update the pin, the ignore list, and the other floors together atomically (re-run the checks in rule 10 first).

10. **Dependabot uv PR review rule**: Before merging any `uv`-ecosystem dependabot PR, fetch the PyPI metadata for the updated package and check its `requires_dist` for exact pins (`==`) and its `requires_python` for Python 3.14 wheel support (see rule 7). If the package exact-pins anything also present in `pyproject.toml`, the floors must be compatible with that exact pin. The pattern to check: `https://pypi.org/pypi/<pkg>/<new-version>/json` → `info.requires_dist` / `info.requires_python`. If there is a conflict, do NOT raise the other package's floor — lower it instead to match the exact pin, or add the other package to the dependabot ignore list. After merging, run `cd backend && uv lock` to refresh `uv.lock`.
