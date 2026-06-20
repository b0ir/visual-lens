# Contributing

## Collaboration is welcome

I really value feedback, ideas, comments, and code contributions. No contribution is too small. Found a bug? [Report it](https://github.com/b0ir/visual-lens/issues). Have an idea? Open an [issue](https://github.com/b0ir/visual-lens/issues). Wrote a fix? Submit a [PR](https://github.com/b0ir/visual-lens/pulls). Even if you're not sure about the format or approach, I prefer getting it anyway. Don't talk yourself out of it.

## Dev setup

See [README.md](README.md) for the full setup guide. Short version:

```bash
npm run setup:all   # install all deps, create Python venv, download Playwright browsers
npm run dev         # frontend on :3000, backend on :8000
```

## Reporting bugs

Open an [issue](https://github.com/b0ir/visual-lens/issues) and include:

- Which AI provider and model you used.
- What you expected vs. what actually happened.
- A screenshot if it helps.

## Suggesting features

Open an [issue](https://github.com/b0ir/visual-lens/issues) with a short description of the feature and the problem it solves.

## Submitting a PR

1. Branch off `main` with a descriptive prefix:
   - `fix/` — bug fixes
   - `feat/` — new features
   - `chore/` — tooling, deps, CI
   - `docs/` — documentation only
2. Keep changes focused. One logical change per PR makes review and revert easier.
3. Run `npm run dev` and verify your change works before pushing.

## Licensing

By submitting a pull request, you agree that your contribution will be licensed under the same [Elastic License 2.0](LICENSE) terms as this project.
