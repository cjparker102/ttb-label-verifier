# Project Rules

These rules apply to everyone who works in this repository, including AI coding assistants such as Claude Code.

## Authorship and commits

- Christopher Parker is the author of record. Every commit must be authored and committed by Christopher Parker <cjparker102@gmail.com>.
- AI tools used on this project are listed in the README, not in commit trailers.
- Commits and pull requests carry no Co-Authored-By, Claude-Session, or "Generated with" lines. No AI tool, bot, or other identity appears as author, committer, or co-author.
- Do not change git configuration, skip hooks, force-push, or rewrite history.
- After each step is finished and all tests pass, commit it with a clear message and tell Christopher.
- Push at the end of each day, or when Christopher asks.
- Git hooks in `.githooks/` check these rules on every commit.

## Secrets

- API keys and other secrets come only from environment variables: a local `.env` file in development, Azure secrets in the cloud.
- Never commit `.env` files. AI assistants never read them.
- List every variable in `.env.example` with a placeholder value.

## Way of working

- Plan first. Explain each feature in plain words and wait for approval before building it.
- Work in small steps.
- Ask before adding a dependency or creating a cloud resource.
- If a requirement is unclear, ask instead of guessing.

## AI reads, code decides

- The AI model has one job: read a label image and return its fields as JSON.
- Ordinary, tested code makes every Pass, Needs review, or Fail decision. The AI never makes that call.

## Data handling

- Label images are processed in memory only. They are never written to disk, a database, logs, or cloud storage.

## Testing and honesty

- Every rule has tests.
- Never fake results. Tests exercise real code, and reported results match what actually ran.
- The README honestly lists the tools used to build this project, including Claude Code.
