# CLAUDE.md - VisualLens Developer Guide

## Architecture
- **Type**: Polyglot Monorepo (NPM Workspaces managed).
- **Frontend**: React, TypeScript, Vite, TailwindCSS (v4), Lucide React.
- **Backend**: Python, FastAPI, Playwright (async), LiteLLM.

## Setup & Execution
- **Install/Setup All**: `npm run setup:all` (installs node modules, creates python venv, installs requirements, and downloads Playwright browsers).
- **Start Dev Servers**: `npm run dev` (Runs concurrently: Frontend on `:3000`, Backend on `:8000` with uvicorn reload).

## Codebase Rules
1. **No Emojis**: Do not use emojis anywhere in the UI or backend logs.
2. **Git Protocol**: Always explicitly ask the user for permission before pushing to the remote repository.
3. **AI Provider**: We use the `litellm` package on the backend to standardize calls to Gemini, OpenAI, Anthropic and other LLM providers.
4. **Dark Mode**: Tailwind v4 class strategy is enforced via `@variant dark` in `index.css`. Use `dark:` classes everywhere.
