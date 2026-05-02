# VisualLens (Work In Progress)

VisualLens is an autonomous, AI-powered visual regression and UI testing agent. It crawls web pages, captures screenshots across multiple rendering engines (Chromium, Firefox, WebKit) concurrently, and uses multimodal vision LLMs to detect UI/UX bugs, broken layouts, and overlapping elements.

## Features

- **Multi-browser crawling** — captures pages screenshots in Chromium, Firefox, and WebKit in parallel.
- **Vision AI analysis** — sends screenshots + simplified DOM to a vision LLM and receives structured bug reports.
- **Bring your own key** — supports OpenAI, Anthropic, Google Gemini, DeepSeek, xAI, and OpenRouter. Enter your API key, verify it, and pick from available vision models.
- **Auth support** — for pages behind login, opens an interactive browser window for manual login before crawling.
- **Dark mode**.

## Repository Structure

Polyglot Monorepo managed by a root `package.json`.

- `frontend/` — React, TypeScript, Vite, TailwindCSS v4.
- `backend/` — Python, FastAPI, Playwright (async), LiteLLM.
  - `providers.py` — single source of truth for supported AI providers and vision models.

## Getting Started

Requires Node.js and Python 3.

### 1. Setup

```bash
npm run setup:all
```

Installs Node and Python dependencies, creates a virtualenv, and downloads Playwright browsers.

### 2. Run

```bash
npm run dev
```

- **Frontend:** `http://localhost:3000`
- **Backend API:** `http://localhost:8000`

### 3. Configure

Open Settings in the UI, select your AI provider, paste your API key, verify it, and choose a vision model.

## Adding a Provider

Edit `backend/providers.py` and add an entry to the `PROVIDERS` dict. No other files need to change.
