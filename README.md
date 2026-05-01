# VisualLens (Work In Progress)

VisualLens is an autonomous, AI-powered visual regression and UI testing agent. It crawls web pages, captures screenshots across multiple rendering engines (Chromium, Firefox, WebKit) concurrently, and uses Multimodal Vision LLMs to detect UI/UX bugs, broken layouts, and overlapping elements.

> **Note:** This project is currently a Work in Progress (WIP). The UI and crawling architecture are complete; the Multimodal AI Integration layer is currently under active development.

## Repository Structure

This project uses an industry-standard **Polyglot Monorepo** architecture:
*   `frontend/`: The user interface (React, TypeScript, Vite, TailwindCSS).
*   `backend/`: The crawler and AI router (Python, FastAPI, Playwright, LiteLLM).

Having clearly separated `frontend` and `backend` directories at the root is the most common pattern for fullstack applications that don't share the same programming language (unlike Next.js fullstack apps).

## Getting Started

You can start both the React frontend and the FastAPI backend simultaneously using the provided startup script.

```bash
# Make the script executable (only needed once)
chmod +x start.sh

# Run both servers
./start.sh
```

- **Frontend:** `http://localhost:3000`
- **Backend API:** `http://localhost:8000`
