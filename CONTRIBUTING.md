# Contributing to MyHome

Thanks for your interest in contributing! Please read these guidelines before opening a pull request.

## Ground Rules

1. **Ask in Discussions first** — Before writing any code, pitch your idea in the [Ideas category of GitHub
   Discussions](https://github.com/floco/myhome/discussions/categories/ideas). We'll let you know if the change is
   wanted and give direction. PRs that show up without prior discussion may be closed
2. **One change per PR** — Keep it focused. Don't bundle unrelated fixes or refactors
3. **No breaking changes** — Backwards compatibility is non-negotiable
4. **Target the `main` branch** — All PRs must be opened against `main`
5. **Match the existing style** — No reformatting, no linter config changes, no "while I'm here" cleanups
6. **Tests** — Your changes must include tests covering the new behavior
7. **Branch up to date** — Your branch must be up to date with `main` before submitting a PR

## Pull Requests

### Your PR should include:

- **Summary** — What does this change and why? (1-3 bullet points)
- **Test plan** — How did you verify it works?
- **Linked issue** — Reference the issue (e.g. `Fixes #123`)

### Your PR will be closed if it:

- Wasn't discussed and approved in a GitHub Discussion first
- Introduces breaking changes
- Adds unnecessary complexity or features beyond scope
- Reformats or refactors unrelated code
- Adds dependencies without clear justification

### Commit messages

Use [conventional commits](https://www.conventionalcommits.org/):

```
fix(chores): correct Donetick frequency handling
feat(costs): add CSV export for expenses
```

## Development Environment

MyHome is a monorepo with an npm-workspaces Svelte frontend (`packages/editor`) and a Python/FastAPI backend
(`packages/backend`). See the [README](README.md) for setup instructions, and
[`.github/workflows/ci.yml`](.github/workflows/ci.yml) for how tests are run in CI.

## More Details

For architecture notes and design/implementation history, see [`docs/superpowers/`](docs/superpowers/) and
[`ROADMAP.md`](ROADMAP.md).
