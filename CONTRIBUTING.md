# Contributing

## Just open the PR

Don't talk yourself out of it. Found a bug? Report it. Have an idea? Open an issue. Wrote a fix? Submit the PR. A rough draft that ships is worth more than a polished plan that never does. No contribution is too small.

## Dev setup

See [README.md](README.md) for the full setup guide. Short version:

```bash
npm run setup:all   # install all deps, create Python venv, download Playwright browsers
npm run dev         # frontend on :3000, backend on :8000
```

## Reporting bugs

Open an issue and include:
- Which AI provider and model you used
- What you expected vs. what actually happened
- A screenshot if it helps

## Suggesting features

Open an issue with a short description of the feature and the problem it solves. No spec needed — a sentence is enough to start a conversation.

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

## Say hi

Open source works better when people actually talk to each other. If you have a question, a suggestion, or just want to say something — open an issue or start a discussion. Don't overthink it.
