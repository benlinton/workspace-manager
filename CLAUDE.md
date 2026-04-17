# Workspace Manager — Development Guide

## Project structure

- `bin/workspace` — Python 3 CLI script (stdlib only, no pip dependencies)
- `config/` — gitignored, holds user's config.json (may be a cloned repo)
- `templates/config.example.json` — committed example config
- `tests/test_workspace.py` — unit tests
- `docs/` — design docs

## Testing rules

**CRITICAL: Always commit and push before running tests.**

Tests previously destroyed the real project by moving files via `shutil.move`. Safety guards are in place but the commit-first rule is non-negotiable.

Test safety architecture:
- `setUpModule()` globally patches `shutil.move` and `subprocess.run`
- `safe_shutil_move()` blocks any move from inside `~/Workspace`
- `safe_subprocess_run()` blocks any unpatched shell command
- `SafeTestCase.tearDown()` asserts the real project still exists after every test
- Tests that call `cmd_init` must patch `PROJECT_ROOT`, `CONFIG_DIR`, and `CONFIG_FILE` to point inside a temp directory

Run tests: `python3 -m unittest tests.test_workspace -v`

## Coding conventions

- Python 3 standard library only — no third-party dependencies
- Use `argparse` for CLI, `pathlib.Path` for filesystem operations
- All filesystem-modifying operations must be mockable for testing
- Never use `rm` or delete files when reorganizing — move instead

## Git workflow

- Commit and push frequently, especially before running tests
- Use descriptive commit messages that explain why, not what
- Force push only when explicitly authorized
