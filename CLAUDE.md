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
7. **Python version**: The project runs on **Python 3.14**. Many packages cap `Requires-Python <3.14`. Always check version availability on Python 3.14 before bumping any pip floor — a version may exist on PyPI but be invisible to the local installer.

8. **`backend/requirements.txt` changes — mandatory validation before any commit**:
   - After any edit to `requirements.txt`, run `pip install -r backend/requirements.txt` in the backend venv and confirm zero errors before staging the file.
   - Better: run the full `npm run setup:all` from the repo root, which exercises the actual install path the user runs.
   - CI runs Python 3.12 (`backend-deps` job) and will NOT catch Python 3.14 availability gaps. Local validation on Python 3.14 is required in addition to CI passing.

9. **litellm pins its entire dependency tree exactly** (pydantic, python-dotenv, httpx, aiohttp, openai, jinja2, etc.). These packages are listed in `dependabot.yml` under `ignore` for the pip ecosystem. Do NOT remove those ignore rules. When litellm itself is updated to a version that supports Python 3.14, re-evaluate and update the ignore list and floors together atomically.

10. **Dependabot pip PR review rule**: Before merging any pip dependabot PR, fetch the PyPI metadata for the updated package and check its `requires_dist` for exact pins (`==`). If the package exact-pins anything also present in `requirements.txt`, the floors must be compatible with that exact pin. The pattern to check: `https://pypi.org/pypi/<pkg>/<new-version>/json` → `info.requires_dist`. If there is a conflict, do NOT raise the other package's floor — lower it instead to match the exact pin, or add the other package to the dependabot ignore list.
