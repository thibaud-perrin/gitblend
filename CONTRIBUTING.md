# Contributing to gitblend

Thank you for contributing to **gitblend**! This document provides developer workflows, commands, and guidelines.

## Table of Contents

- [Development Setup](#development-setup)
- [Common Commands](#common-commands)
- [Version Management](#version-management)
- [Testing](#testing)
- [Building and Packaging](#building-and-packaging)
- [Release Workflow](#release-workflow)
- [Git Workflow](#git-workflow)
- [Code Quality](#code-quality)
- [Architecture Guidelines](#architecture-guidelines)

---

## Development Setup

### Prerequisites

- Python 3.12+ (managed via `.python-version` and `uv`)
- [uv](https://github.com/astral-sh/uv) for dependency management
- Git 2.30+
- Blender 4.2+ (for testing the addon in Blender)

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/hallcyn/gitblend.git
cd gitblend

# Install dependencies with uv
uv sync

# Install pre-commit hooks (recommended)
uv run pre-commit install
```

---

## Common Commands

All commands should be run from the project root using `uv run`.

### Linting and Formatting

```bash
# Check code with ruff
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

### Type Checking

```bash
# Run mypy type checker
uv run mypy gitblend
```

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=gitblend

# Run only unit tests (no subprocess, no bpy)
uv run pytest -m unit

# Run only integration tests (real Git repos)
uv run pytest -m integration

# Run a specific test file
uv run pytest tests/unit/test_git_service.py

# Run tests with verbose output
uv run pytest -v
```

### Packaging

```bash
# Build extension zip for Blender
uv run python tools/package_extension.py
# → Creates dist/gitblend-<version>.zip

# Install extension into Blender for development
uv run python tools/dev_install.py
```

---

## Version Management

**gitblend** uses semantic versioning (`MAJOR.MINOR.PATCH`). Version numbers are stored in 3 places:

- `gitblend/blender_manifest.toml` (string: `"0.1.0"`)
- `pyproject.toml` (string: `"0.1.0"`)
- `gitblend/__init__.py` (tuple: `(0, 1, 0)` in `bl_info`)

### Bumping Version

Use the `bump_version.py` script to update all version locations atomically:

```bash
# Bump patch version (0.1.0 → 0.1.1)
uv run python tools/bump_version.py patch

# Bump minor version (0.1.0 → 0.2.0)
uv run python tools/bump_version.py minor

# Bump major version (0.1.0 → 1.0.0)
uv run python tools/bump_version.py major

# Bump version and create git tag
uv run python tools/bump_version.py patch --tag

# Bump, tag, and push tag to remote
uv run python tools/bump_version.py minor --push
```

The script will:
1. Read current version from `blender_manifest.toml`
2. Increment the specified part (major/minor/patch)
3. Update all 3 files
4. Optionally create and push a git tag
5. Show next steps for committing changes

**Example workflow:**

```bash
# 1. Bump version
uv run python tools/bump_version.py minor

# 2. Commit changes
git add gitblend/blender_manifest.toml pyproject.toml gitblend/__init__.py
git commit -m "chore: bump version to 0.2.0"

# 3. Create and push tag
git tag -a v0.2.0 -m "Release 0.2.0"
git push origin main
git push origin v0.2.0
```

Or use the `--tag` flag to automate tagging:

```bash
uv run python tools/bump_version.py minor --tag
git add gitblend/blender_manifest.toml pyproject.toml gitblend/__init__.py
git commit -m "chore: bump version to 0.2.0"
git push origin main
git push origin v0.2.0
```

---

## Testing

### Writing Tests

- **Unit tests** (`tests/unit/`) — Pure logic tests, no subprocess, no `bpy`
- **Integration tests** (`tests/integration/`) — Git operations with real temporary repos

Mark tests with pytest markers:

```python
import pytest

@pytest.mark.unit
def test_parse_version():
    # Pure logic test
    ...

@pytest.mark.integration
def test_git_commit(tmp_path):
    # Test with real git repo
    ...
```

### Test Coverage

Aim for high coverage of business logic:

```bash
# Generate coverage report
uv run pytest --cov=gitblend --cov-report=html

# Open coverage report
open htmlcov/index.html
```

---

## Building and Packaging

### Build Extension Zip

```bash
uv run python tools/package_extension.py
```

This creates `dist/gitblend-<version>.zip` with the structure required by Blender 4.2+ extensions.

### Install Extension in Blender

#### Method 1: Development Install (recommended for development)

```bash
uv run python tools/dev_install.py
```

This symlinks the extension into Blender's extensions directory for live development.

#### Method 2: Manual Install

1. Build the extension: `uv run python tools/package_extension.py`
2. Open Blender → Edit → Preferences → Add-ons
3. Click "Install from Disk"
4. Select `dist/gitblend-<version>.zip`
5. Enable the addon

---

## Release Workflow

### Pre-release Checklist

- [ ] All tests pass: `uv run pytest`
- [ ] Code is formatted: `uv run ruff format .`
- [ ] No linting errors: `uv run ruff check .`
- [ ] No type errors: `uv run mypy gitblend`
- [ ] Documentation is up to date
- [ ] CHANGELOG.md is updated (when it exists)

### Release Steps

1. **Bump version:**
   ```bash
   uv run python tools/bump_version.py minor --tag
   ```

2. **Commit version bump:**
   ```bash
   git add gitblend/blender_manifest.toml pyproject.toml gitblend/__init__.py
   git commit -m "chore: bump version to X.Y.Z"
   ```

3. **Push changes and tags:**
   ```bash
   git push origin main
   git push origin vX.Y.Z
   ```

4. **Build extension:**
   ```bash
   uv run python tools/package_extension.py
   ```

5. **Create GitHub release:**
   - Go to GitHub → Releases → Draft a new release
   - Select tag `vX.Y.Z`
   - Attach `dist/gitblend-X.Y.Z.zip`
   - Publish release

---

## Git Workflow

### Branching Strategy

- `main` — Stable releases
- `feat/feature-name` — New features
- `fix/bug-name` — Bug fixes
- `docs/topic` — Documentation updates
- `chore/task` — Maintenance tasks

### Commit Message Format

Use conventional commits:

```
type(scope): short description

Longer explanation if needed.

Closes #123
```

**Types:**
- `feat` — New feature
- `fix` — Bug fix
- `docs` — Documentation changes
- `chore` — Maintenance (version bump, dependencies, etc.)
- `refactor` — Code refactoring
- `test` — Test changes
- `perf` — Performance improvements

**Examples:**
```
feat(git): add support for Git LFS detection
fix(ui): prevent panel freeze during long operations
docs(readme): update installation instructions
chore: bump version to 0.2.0
```

---

## Code Quality

### Pre-commit Hooks

We recommend using pre-commit hooks to ensure code quality:

```bash
uv run pre-commit install
```

This automatically runs `ruff` and `mypy` before each commit.

### Code Style

- Follow PEP 8 conventions
- Use type hints everywhere
- Maximum line length: 100 characters
- Prefer explicit over implicit
- Keep functions small and focused
- Use descriptive variable names

### Import Order

Imports are automatically sorted by `ruff`. Order:

1. Standard library
2. Third-party packages
3. Local imports (`gitblend.*`)

---

## Architecture Guidelines

See [CLAUDE.md](./CLAUDE.md) for detailed architecture rules.

### Key Principles

1. **No `bpy` outside UI/operators/adapters** — Business logic must be testable without Blender
2. **Dependency injection** — Services receive dependencies (subprocess runner, filesystem)
3. **Result/Either pattern** — Return `Result[T, Error]` instead of raising exceptions
4. **Subprocess isolation** — All `git` calls through `infrastructure/subprocess_runner.py`
5. **Layered architecture:**
   ```
   ui/ + operators/        → Blender UI only
   services/               → Business logic
   infrastructure/         → Low-level I/O
   domain/                 → Data models, enums, errors
   bpy_adapters/           → Blender API wrappers
   ```

### Adding New Features

1. **Start with domain models** — Define types, enums, errors
2. **Write service logic** — Pure business logic, testable without Blender
3. **Add infrastructure** — Subprocess calls, file I/O, parsing
4. **Create Blender operators** — Thin wrappers calling services
5. **Build UI** — Panels, buttons, lists
6. **Add tests** — Unit tests for services, integration tests for Git workflows

---

## Questions?

- Open an issue: https://github.com/hallcyn/gitblend/issues
- Read the docs: [CLAUDE.md](./CLAUDE.md), [BRIEF.md](./BRIEF.md)

Happy coding! 🚀
