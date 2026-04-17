# Workspace Manager — Development Guide

All memories and preferences should be stored in this file, not in Claude's memory system, so they work across all machines.

## Rules

- **Always commit and push before running tests.** Tests previously destroyed this project via `shutil.move`. Safety guards exist but the commit-first rule is non-negotiable.
- **Always run `git status` before claiming the tree is clean.** The user edits files outside of Claude. Never say "already pushed" or "nothing to commit" without checking first.
- **Never use `rm` when reorganizing.** Move files to their new location with `mv` or `git mv`. Removing and recreating loses git history.
- **Python 3 stdlib only.** No third-party dependencies.

## Project structure

- `bin/workspace` — Python 3 CLI script (stdlib only, no pip dependencies)
- `config/` — gitignored, holds user's config.json (may be a cloned repo)
- `templates/config.example.json` — committed example config
- `tests/test_workspace.py` — unit tests
- `docs/` — design docs

## Testing

Run tests: `python3 -m unittest tests.test_workspace -v`

Test safety architecture:
- `setUpModule()` globally patches `shutil.move` and `subprocess.run`
- `safe_shutil_move()` blocks any move from inside `~/Workspace`
- `safe_subprocess_run()` blocks any unpatched shell command
- `SafeTestCase.tearDown()` asserts the real project still exists after every test
- Tests that call `cmd_init` must patch `PROJECT_ROOT`, `CONFIG_DIR`, and `CONFIG_FILE` to point inside a temp directory
