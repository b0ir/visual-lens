# VisualLens (Work In Progress)

VisualLens is an autonomous, AI-powered visual regression and UI testing agent. It crawls web pages, captures screenshots across multiple rendering engines (Chromium, Firefox, WebKit) concurrently, and uses Multimodal Vision LLMs to detect UI/UX bugs, broken layouts, and overlapping elements.

> **Note:** This project is currently a Work in Progress (WIP). The UI and crawling architecture are complete; the Multimodal AI Integration layer is currently under active development.

## Repository Structure

This project uses an industry-standard **Polyglot Monorepo** architecture managed by a root `package.json` for process management.
*   `frontend/`: The user interface (React, TypeScript, Vite, TailwindCSS).
*   `backend/`: The crawler and AI router (Python, FastAPI, Playwright, LiteLLM).

## Getting Started

To run this application locally, you will need Node.js and Python 3 installed.

### 1. Initial Setup
Run the unified setup script from the root of the repository to install both Python and Node dependencies, as well as the Playwright browsers:
```bash
npm run setup:all
```

### 2. Run Development Servers
Use `concurrently` to spin up both the React frontend and the FastAPI backend in a single terminal with color-coded logs:
```bash
npm run dev
```

- **Frontend:** `http://localhost:3000`
- **Backend API:** `http://localhost:8000`
