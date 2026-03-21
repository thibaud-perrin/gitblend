# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**gitblend** is a Blender extension that adds Git/GitHub versioning to `.blend` projects. It is in early development — only scaffolding exists so far. The full product vision is in `BRIEF.md`.

**Core constraint:** All business logic must be testable without Blender. `bpy` is strictly limited to `ui/`, `operators/`, and `bpy_adapters/`.

## Commands

The project uses `uv` for environment and dependency management.

```bash
# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy gitblend

# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/unit/test_git_service.py

# Run tests with coverage
uv run pytest --cov=gitblend

# Package extension
uv run python tools/package_extension.py

# Dev install into Blender
uv run python tools/dev_install.py
```

> Note: most of the above scripts don't exist yet and will need to be created as development progresses.

## Architecture

The codebase follows a strict layered architecture to keep business logic independent of Blender:

```
gitblend/
├── blender_manifest.toml   # Modern Blender extension manifest (not legacy bl_info)
├── __init__.py             # Blender registration entry point
├── registration.py
├── ui/                     # Blender UI only (panels, menus, lists, dialogs, icons)
├── operators/              # Thin Blender operator wrappers (no business logic)
├── domain/                 # Pure data models, enums, errors, Result type
├── services/               # Core business logic (git, github, lfs, snapshots...)
├── infrastructure/         # Low-level I/O (subprocess runner, auth store, parsers)
├── bpy_adapters/           # Blender API wrappers (context, paths, reports, jobs)
├── tests/
│   ├── unit/               # Pure logic tests — no bpy, no subprocess
│   └── integration/        # Git tests against real temp repos
└── resources/
    └── templates/          # .gitignore and .gitattributes templates
```

**Key design patterns:**

- **Dependency injection** — services receive dependencies (subprocess runner, filesystem) so they can be tested without the real I/O
- **Result/Either pattern** — operations return `Result[T, Error]` instead of raising exceptions in the service layer
- **Subprocess isolation** — all `git` calls go through `infrastructure/subprocess_runner.py`, never scattered across the codebase
- **No `bpy` imports** in `domain/`, `services/`, or `infrastructure/` — these layers must import without Blender installed

## Tech Stack

- **Python 3.12** (via `.python-version`, managed by `uv`)
- **Git operations:** `subprocess` calling `git` CLI (no libgit2/pygit2)
- **GitHub API:** direct HTTP calls (no third-party GitHub SDK)
- **Auth:** GitHub PAT + device flow; credentials stored in system keychain via `auth_store.py`
- **Blender extension format:** modern `blender_manifest.toml` (Blender 4.2+)
- **Linting/formatting:** `ruff`
- **Type checking:** `mypy`
- **Testing:** `pytest`

## Agent instructions

When working on this repository:

- prefer safe, explicit changes over broad refactors
- preserve project file safety above all else
- use Context7 for Blender, GitHub, uv, and GitHub Actions documentation lookups
- keep business logic outside Blender UI classes
- add tests for non-trivial behavior changes
- update docs when behavior changes

## Project-Specific Best Practices

### Product and architecture principles

- Treat this project as a **production-quality Blender extension**, not a quick script.
- Prefer **local-first Git workflows**. GitHub integration is important, but the addon must remain useful even without GitHub auth.
- Design for **binary project safety**. `.blend` files are binary files, so never imply text-like merge safety.
- Optimize for **reliability and clarity over cleverness**. Users must always understand what action will happen to their project.
- Never hide destructive operations. Any checkout, reset, restore, overwrite, or conflict resolution action must be explicit and confirmable.
- Keep the architecture layered:
  - `ui/` and Blender operators only for UI/event wiring
  - `services/` for business logic
  - `infrastructure/` for subprocess, filesystem, auth, parsing
  - `domain/` for typed models, enums, errors, results
- Keep most logic **testable outside Blender**. Avoid embedding business logic directly inside `bpy` operators or panels.

### Blender addon rules

- Follow Blender addon conventions and keep registration clean and centralized.
- Minimize direct `bpy` usage outside dedicated adapter/UI layers.
- Keep the UI responsive. Long-running Git operations should not freeze Blender unnecessarily.
- Prefer predictable Blender-native UX:
  - clear panel structure
  - explicit status labels
  - short actionable error messages
  - no surprise background mutation of project files
- Always save or offer to save the current `.blend` before operations that depend on disk state.
- Never assume the current file is already saved. Handle unsaved `.blend` files gracefully.
- Always consider linked libraries, external textures, caches, and relative vs absolute paths when operating on a project.

### Git and GitHub rules

- Use the system `git` binary through a single service abstraction. Do not scatter raw subprocess calls across the codebase.
- Prefer small, composable Git commands over large opaque wrappers.
- Parse command output in dedicated parser modules.
- Treat Git errors as typed domain errors:
  - repo not initialized
  - dirty working tree
  - detached HEAD
  - merge conflict
  - auth failure
  - missing remote
  - Git LFS unavailable
- Never claim that `.blend` merges are safe by default.
- Prefer Git LFS for large binary assets and guide the user accordingly.
- Never store GitHub tokens in project files or inside `.blend` files.
- Any GitHub operation must fail gracefully and preserve local project safety.

### Safety and file integrity

- Project safety is more important than convenience.
- Before destructive operations, create a safe backup when appropriate.
- Never delete or overwrite user files unless the action is explicit and reversible or clearly acknowledged.
- Prefer additive workflows:
  - duplicate before restore
  - backup before hard reset
  - preview before apply
- Detect and warn about risky conditions:
  - missing assets
  - absolute paths
  - large files not tracked by LFS
  - uncommitted local changes before checkout/pull/reset
- Always surface what files are affected by an operation when possible.

### Code quality

- Use strong typing everywhere practical.
- Prefer small functions with explicit inputs/outputs.
- Use dataclasses or typed models for command results and domain objects.
- Avoid boolean soup. Use enums and typed result objects instead of many loosely related flags.
- Keep functions pure where possible, especially in parsing and domain logic.
- Do not swallow exceptions silently.
- Avoid hidden global state.
- Keep side effects isolated and obvious.

### Error handling and UX

- Error messages must help the user act:
  - what failed
  - why it likely failed
  - what they should do next
- Prefer user-facing errors over raw tracebacks in the UI.
- Keep logs detailed for debugging, but keep UI messages concise.
- Distinguish between:
  - user misconfiguration
  - environment issue
  - network/auth issue
  - repo state issue
  - unexpected internal bug
- Fail safely. If a command fails, leave the repo and Blender state as unchanged as possible.

### Testing expectations

- Add unit tests for all non-UI logic.
- Add integration tests for Git workflows using temporary repos.
- Add smoke tests for Blender registration/import when possible.
- Test edge cases, not just happy paths:
  - unsaved file
  - missing git binary
  - missing git-lfs
  - no remote
  - dirty working tree
  - conflict state
  - detached HEAD
  - offline GitHub API
- When fixing a bug, add or update a test that would have caught it.

### Dependencies and tooling

- Use `uv` for dependency management and reproducible developer workflows.
- Keep runtime dependencies minimal.
- Prefer standard library unless a dependency clearly improves correctness or maintainability.
- Add dev tooling consistently:
  - `ruff`
  - `mypy`
  - `pytest`
  - `pre-commit`
- Do not introduce a dependency without explaining why it is needed.
- Be cautious with packages that are hard to bundle or awkward inside Blender environments.

### Documentation expectations

- Document user-visible limitations honestly.
- Keep README and developer docs aligned with actual behavior.
- When adding a feature, update relevant docs in the same change.
- Document platform-specific caveats for Windows, macOS, and Linux.
- Include examples for common workflows:
  - init repo
  - commit snapshot
  - setup Git LFS
  - connect GitHub
  - restore previous version
  - handle conflicts safely

### Use of Context7

- Use `context7` whenever implementation depends on exact current documentation or API behavior.
- Prefer `context7` before making assumptions about:
  - Blender Python API details
  - Blender extension packaging and manifest format
  - GitHub API endpoints and auth flows
  - `uv` commands and workflow conventions
  - GitHub Actions syntax and recommended setup
- When using `context7`, prefer primary documentation over blog posts or memory.
- If documentation and prior assumptions conflict, follow the current documented behavior.
- For code generation, align names, arguments, and file formats with the documentation retrieved from `context7`.

### What to avoid

- Do not put core logic directly in `__init__.py`.
- Do not mix UI code, subprocess calls, and domain logic in the same function.
- Do not make silent repo changes in the background.
- Do not assume GitHub is always available.
- Do not assume all users understand Git jargon.
- Do not over-engineer around collaboration features that are unsafe for binary files.
- Do not market unsupported behavior as if it works reliably.
