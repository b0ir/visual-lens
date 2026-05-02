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
2. **Git Protocol**: Always explicitly ask the user for permission before pushing to the remote repository.
3. **Provider Registry**: All supported AI providers and their vision-capable models are defined in `backend/providers.py`. To add a new provider, add an entry to the `PROVIDERS` dict — no other file changes needed.
4. **API Key Handling**: API keys are stored client-side only (localStorage). The backend receives the active key per-request and passes it directly to LiteLLM via the `api_key` parameter. Never mutate `os.environ` for API keys.
5. **LiteLLM Integration**: All AI calls go through `litellm`. Use the `provider/model` format for model identifiers (e.g., `openai/gpt-4.1`, `anthropic/claude-sonnet-4-6`).
6. **Dark Mode**: Tailwind v4 dark mode via `@variant dark` in `index.css`. Use `dark:` classes everywhere.
7. **Log Files**: All `.log` files are in `.gitignore`. If a log file gets accidentally tracked, remove it with `git rm --cached <file>`.
