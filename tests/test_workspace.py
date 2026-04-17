"""Tests for the workspace script.

Uses tempfile directories and mocks to avoid touching the real filesystem.

SAFETY ARCHITECTURE:
  Global guards are installed in setUpModule() and apply to ALL tests:
  1. shutil.move is replaced with safe_shutil_move — blocks any move from
     the real project root, raises RuntimeError if attempted
  2. subprocess.run is replaced with a MagicMock — no test can ever run
     real shell commands (git clone, etc.) unless it explicitly patches
     subprocess.run with its own mock
  3. Individual tests that call cmd_init must ALSO patch PROJECT_ROOT,
     CONFIG_DIR, and CONFIG_FILE to point inside a temp directory

  These guards are removed in tearDownModule(). If a test needs real
  subprocess.run (it shouldn't), it must explicitly opt in.
"""

import importlib.machinery
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch, call

# Import the workspace script as a module (it has no .py extension)
SCRIPT_PATH = Path(__file__).resolve().parent.parent / "bin" / "workspace"
loader = importlib.machinery.SourceFileLoader("workspace", str(SCRIPT_PATH))
spec = importlib.util.spec_from_loader("workspace", loader)
ws = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ws)

# Store the real PROJECT_ROOT so we can verify tests never touch it
REAL_PROJECT_ROOT = ws.PROJECT_ROOT
REAL_WORKSPACE_ROOT = REAL_PROJECT_ROOT.parent.parent.parent  # ~/Workspace

# ---------------------------------------------------------------------------
# Global safety guards — installed for ALL tests
# ---------------------------------------------------------------------------
_original_shutil_move = shutil.move
_original_subprocess_run = subprocess.run
_global_patches = []


def safe_shutil_move(src, dst):
    """A shutil.move replacement that refuses to move anything from the real workspace."""
    src_path = Path(src).resolve()
    if str(src_path).startswith(str(REAL_WORKSPACE_ROOT)):
        raise RuntimeError(
            f"TEST SAFETY: shutil.move tried to move real workspace files!\n"
            f"  src: {src}\n  dst: {dst}"
        )
    # Allow moves within temp directories
    return _original_shutil_move(src, dst)


def safe_subprocess_run(*args, **kwargs):
    """A subprocess.run replacement that blocks all real command execution."""
    raise RuntimeError(
        f"TEST SAFETY: subprocess.run called without being mocked!\n"
        f"  args: {args}\n"
        f"  Mock subprocess.run in your test to control its behavior."
    )


def setUpModule():
    """Install global safety guards before any test runs."""
    _global_patches.extend([
        patch.object(shutil, "move", side_effect=safe_shutil_move),
        patch.object(subprocess, "run", side_effect=safe_subprocess_run),
    ])
    for p in _global_patches:
        p.start()


def tearDownModule():
    """Remove global safety guards after all tests complete."""
    for p in reversed(_global_patches):
        p.stop()
    _global_patches.clear()


def make_config(tmpdir, **overrides):
    """Create a minimal config dict pointing at a temp workspace root."""
    config = {
        "machine": "test-machine",
        "workspace_root": str(tmpdir),
        "code": {
            "orgs": ["personal", "org-1"],
            "repos": [
                {
                    "url": "git@github.com:test/project-a.git",
                    "path": "code/personal/project-a",
                },
                {
                    "url": "git@github.com:test/org-1-app.git",
                    "path": "code/org-1/org-1-app",
                },
            ],
        },
        "research": {
            "repos": [
                {
                    "url": "git@github.com:test/tax-prep.git",
                    "path": "research/tax-prep",
                }
            ]
        },
        "studio": {
            "categories": ["productions", "music"],
        },
        "knowledge": {
            "repos": [
                {
                    "url": "git@github.com:test/second-brain.git",
                    "path": "knowledge/second-brain",
                }
            ]
        },
        "toolkits": {"repos": []},
        "machines": {
            "test-machine": overrides.get("machine_config", {}),
        },
    }
    config.update({k: v for k, v in overrides.items() if k != "machine_config"})
    return config


def setup_config(tmpdir, config):
    """Write config into a config/ subdirectory and return the config.json path."""
    config_dir = Path(tmpdir) / "config"
    config_dir.mkdir(exist_ok=True)
    config_path = config_dir / "config.json"
    config_path.write_text(json.dumps(config))
    return config_path


def patch_for_init(tmpdir, config):
    """Return a context manager that patches module globals for cmd_init tests.

    Patches PROJECT_ROOT, CONFIG_DIR, and CONFIG_FILE to point inside the
    temp directory. Global guards (setUpModule) handle shutil.move and
    subprocess.run safety.
    """
    workspace_root = Path(tmpdir)
    config_dir = workspace_root / "config"
    config_file = setup_config(tmpdir, config)

    class _Ctx:
        def __enter__(self):
            self.patches = [
                patch.object(ws, "CONFIG_DIR", config_dir),
                patch.object(ws, "CONFIG_FILE", config_file),
                patch.object(ws, "PROJECT_ROOT", workspace_root / "code/personal/workspace-manager"),
            ]
            for p in self.patches:
                p.__enter__()
            # Pre-create the expected repo path so it doesn't try to move
            repo_dir = workspace_root / "code" / "personal" / "workspace-manager"
            repo_dir.mkdir(parents=True, exist_ok=True)
            return self

        def __exit__(self, *args):
            for p in reversed(self.patches):
                p.__exit__(*args)

    return _Ctx()


class SafeTestCase(unittest.TestCase):
    """Base test class that verifies the real project still exists after every test."""

    def tearDown(self):
        assert REAL_PROJECT_ROOT.exists(), (
            f"TEST DESTROYED THE REAL PROJECT at {REAL_PROJECT_ROOT}"
        )


class TestSafety(SafeTestCase):
    """Verify the global safety mechanisms work."""

    def test_shutil_move_blocks_real_workspace(self):
        """shutil.move should raise if src is inside the real workspace."""
        with self.assertRaises(RuntimeError) as ctx:
            shutil.move(str(REAL_PROJECT_ROOT), "/tmp/evil")
        self.assertIn("TEST SAFETY", str(ctx.exception))

    def test_shutil_move_allows_temp(self):
        """shutil.move should work for paths inside temp directories."""
        with TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "src"
            dst = Path(tmpdir) / "dst"
            src.mkdir()
            shutil.move(str(src), str(dst))
            self.assertTrue(dst.exists())
            self.assertFalse(src.exists())

    def test_subprocess_run_blocks_unpatched(self):
        """subprocess.run should raise if called without a test-level mock."""
        with self.assertRaises(RuntimeError) as ctx:
            subprocess.run(["echo", "hello"])
        self.assertIn("TEST SAFETY", str(ctx.exception))


class TestGetWorkspaceRoot(SafeTestCase):
    def test_expands_tilde(self):
        config = {"workspace_root": "~/Workspace"}
        result = ws.get_workspace_root(config)
        self.assertEqual(result, Path.home() / "Workspace")

    def test_default_when_missing(self):
        config = {}
        result = ws.get_workspace_root(config)
        self.assertEqual(result, Path.home() / "Workspace")

    def test_absolute_path(self):
        config = {"workspace_root": "/tmp/test-workspace"}
        result = ws.get_workspace_root(config)
        self.assertEqual(result, Path("/tmp/test-workspace"))


class TestGetMachineConfig(SafeTestCase):
    def test_returns_machine_config(self):
        config = {
            "machine": "my-machine",
            "machines": {"my-machine": {"skip": ["studio"]}},
        }
        result = ws.get_machine_config(config)
        self.assertEqual(result, {"skip": ["studio"]})

    def test_returns_empty_when_no_machine(self):
        config = {}
        result = ws.get_machine_config(config)
        self.assertEqual(result, {})

    def test_returns_empty_when_machine_not_in_list(self):
        config = {"machine": "unknown", "machines": {}}
        result = ws.get_machine_config(config)
        self.assertEqual(result, {})


class TestInitCreatesDirectories(SafeTestCase):
    def test_creates_top_level_dirs(self):
        with TemporaryDirectory() as tmpdir:
            config = make_config(tmpdir)
            workspace_root = Path(tmpdir)
            args = MagicMock(dry_run=False, config_repo=None, config_url=None)

            with patch_for_init(tmpdir, config), \
                 patch("subprocess.run", return_value=MagicMock(returncode=0)):
                ws.cmd_init(args)

            for d in ws.TOP_LEVEL_DIRS:
                self.assertTrue(
                    (workspace_root / d).exists(),
                    f"{d}/ was not created",
                )

    def test_creates_org_dirs(self):
        with TemporaryDirectory() as tmpdir:
            config = make_config(tmpdir)
            workspace_root = Path(tmpdir)
            args = MagicMock(dry_run=False, config_repo=None, config_url=None)

            with patch_for_init(tmpdir, config), \
                 patch("subprocess.run", return_value=MagicMock(returncode=0)):
                ws.cmd_init(args)

            self.assertTrue((workspace_root / "code" / "personal").exists())
            self.assertTrue((workspace_root / "code" / "org-1").exists())

    def test_creates_studio_categories(self):
        with TemporaryDirectory() as tmpdir:
            config = make_config(tmpdir)
            workspace_root = Path(tmpdir)
            args = MagicMock(dry_run=False, config_repo=None, config_url=None)

            with patch_for_init(tmpdir, config), \
                 patch("subprocess.run", return_value=MagicMock(returncode=0)):
                ws.cmd_init(args)

            self.assertTrue((workspace_root / "studio" / "productions").exists())
            self.assertTrue((workspace_root / "studio" / "music").exists())

    def test_skips_dirs_per_machine_config(self):
        with TemporaryDirectory() as tmpdir:
            config = make_config(tmpdir, machine_config={"skip": ["studio", "research"]})
            workspace_root = Path(tmpdir)
            args = MagicMock(dry_run=False, config_repo=None, config_url=None)

            with patch_for_init(tmpdir, config), \
                 patch("subprocess.run", return_value=MagicMock(returncode=0)):
                ws.cmd_init(args)

            self.assertFalse((workspace_root / "studio").exists())
            self.assertFalse((workspace_root / "research").exists())
            self.assertTrue((workspace_root / "code").exists())

    def test_filters_code_orgs_per_machine(self):
        with TemporaryDirectory() as tmpdir:
            config = make_config(tmpdir, machine_config={"code_orgs": ["org-1"]})
            workspace_root = Path(tmpdir)
            args = MagicMock(dry_run=False, config_repo=None, config_url=None)

            with patch_for_init(tmpdir, config), \
                 patch("subprocess.run", return_value=MagicMock(returncode=0)):
                ws.cmd_init(args)

            self.assertTrue((workspace_root / "code" / "org-1").exists())


class TestCloneRepos(SafeTestCase):
    def test_clones_repos(self):
        with TemporaryDirectory() as tmpdir:
            config = make_config(tmpdir)
            workspace_root = Path(tmpdir)
            mock_run = MagicMock(return_value=MagicMock(returncode=0))

            with patch("subprocess.run", mock_run):
                ws.clone_repos(config, workspace_root, set(), {}, dry_run=False)

            clone_calls = [
                c for c in mock_run.call_args_list
                if c[0][0][0] == "git" and c[0][0][1] == "clone"
            ]
            self.assertEqual(len(clone_calls), 4)

    def test_skips_existing_repos(self):
        with TemporaryDirectory() as tmpdir:
            config = make_config(tmpdir)
            workspace_root = Path(tmpdir)
            (workspace_root / "code" / "personal" / "project-a").mkdir(parents=True)

            mock_run = MagicMock(return_value=MagicMock(returncode=0))

            with patch("subprocess.run", mock_run):
                ws.clone_repos(config, workspace_root, set(), {}, dry_run=False)

            clone_calls = [
                c for c in mock_run.call_args_list
                if c[0][0][0] == "git" and c[0][0][1] == "clone"
            ]
            self.assertEqual(len(clone_calls), 3)

    def test_skips_sections_in_skip_dirs(self):
        with TemporaryDirectory() as tmpdir:
            config = make_config(tmpdir)
            workspace_root = Path(tmpdir)
            mock_run = MagicMock(return_value=MagicMock(returncode=0))

            with patch("subprocess.run", mock_run):
                ws.clone_repos(
                    config, workspace_root, {"research", "knowledge"}, {}, dry_run=False
                )

            clone_calls = [
                c for c in mock_run.call_args_list
                if c[0][0][0] == "git" and c[0][0][1] == "clone"
            ]
            self.assertEqual(len(clone_calls), 2)

    def test_filters_code_repos_by_machine_orgs(self):
        with TemporaryDirectory() as tmpdir:
            config = make_config(tmpdir)
            workspace_root = Path(tmpdir)
            mock_run = MagicMock(return_value=MagicMock(returncode=0))

            with patch("subprocess.run", mock_run):
                ws.clone_repos(
                    config, workspace_root, set(), {"code_orgs": ["org-1"]}, dry_run=False
                )

            clone_calls = [
                c for c in mock_run.call_args_list
                if c[0][0][0] == "git" and c[0][0][1] == "clone"
            ]
            self.assertEqual(len(clone_calls), 3)

    def test_dry_run_does_not_clone(self):
        with TemporaryDirectory() as tmpdir:
            config = make_config(tmpdir)
            workspace_root = Path(tmpdir)
            mock_run = MagicMock()

            with patch("subprocess.run", mock_run):
                ws.clone_repos(config, workspace_root, set(), {}, dry_run=True)

            mock_run.assert_not_called()

    def test_handles_clone_failure(self):
        with TemporaryDirectory() as tmpdir:
            config = make_config(tmpdir)
            workspace_root = Path(tmpdir)
            mock_run = MagicMock(
                return_value=MagicMock(returncode=128, stderr="fatal: repo not found")
            )

            with patch("subprocess.run", mock_run):
                ws.clone_repos(config, workspace_root, set(), {}, dry_run=False)


class TestDryRun(SafeTestCase):
    def test_dry_run_creates_nothing(self):
        with TemporaryDirectory() as tmpdir:
            config = make_config(tmpdir)
            workspace_root = Path(tmpdir)
            args = MagicMock(dry_run=True, config_repo=None, config_url=None)

            with patch_for_init(tmpdir, config):
                ws.cmd_init(args)

            existing = set(p.name for p in workspace_root.iterdir())
            self.assertEqual(existing, {"code", "config"})


class TestConfigInit(SafeTestCase):
    def test_config_init_copies_example(self):
        with TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            templates_dir = Path(tmpdir) / "templates"
            templates_dir.mkdir()
            example_file = templates_dir / "config.example.json"
            example_file.write_text('{"machine": "example"}')

            args = MagicMock(config_action="init", url=None)

            with patch.object(ws, "CONFIG_DIR", config_dir), \
                 patch.object(ws, "CONFIG_FILE", config_dir / "config.json"), \
                 patch.object(ws, "CONFIG_EXAMPLE", example_file):
                ws.cmd_config(args)

            config_file = config_dir / "config.json"
            self.assertTrue(config_file.exists())
            data = json.loads(config_file.read_text())
            self.assertEqual(data["machine"], "example")

    def test_config_init_refuses_if_exists(self):
        with TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            config_file = config_dir / "config.json"
            config_file.write_text('{"machine": "existing"}')

            args = MagicMock(config_action="init", url=None)

            f = io.StringIO()
            with patch.object(ws, "CONFIG_DIR", config_dir), \
                 patch.object(ws, "CONFIG_FILE", config_file), \
                 redirect_stdout(f):
                ws.cmd_config(args)

            self.assertIn("already exists", f.getvalue())

    def test_init_requires_config(self):
        with TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config" / "config.json"
            args = MagicMock(dry_run=False)

            with patch.object(ws, "CONFIG_FILE", config_file), \
                 self.assertRaises(SystemExit) as ctx:
                ws.cmd_init(args)

            self.assertEqual(ctx.exception.code, 1)


class TestConfigClone(SafeTestCase):
    def test_config_clone_clones_repo(self):
        with TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            args = MagicMock(config_action="clone", url="git@github.com:test/config.git")
            mock_run = MagicMock(return_value=MagicMock(returncode=0))

            with patch.object(ws, "CONFIG_DIR", config_dir), \
                 patch("subprocess.run", mock_run):
                ws.cmd_config(args)

            clone_calls = [
                c for c in mock_run.call_args_list
                if c[0][0][0] == "git" and c[0][0][1] == "clone"
            ]
            self.assertEqual(len(clone_calls), 1)

    def test_config_clone_refuses_if_exists(self):
        with TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            args = MagicMock(config_action="clone", url="git@github.com:test/config.git")
            mock_run = MagicMock()

            f = io.StringIO()
            with patch.object(ws, "CONFIG_DIR", config_dir), \
                 patch("subprocess.run", mock_run), \
                 redirect_stdout(f):
                ws.cmd_config(args)

            mock_run.assert_not_called()
            self.assertIn("already exists", f.getvalue())


class TestConfigDownload(SafeTestCase):
    def test_config_download_fetches_file(self):
        with TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_file = config_dir / "config.json"
            args = MagicMock(config_action="download", url="https://example.com/config.json")

            def fake_download(url, dest):
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text('{"machine": "downloaded"}')
                return True, None

            with patch.object(ws, "CONFIG_DIR", config_dir), \
                 patch.object(ws, "CONFIG_FILE", config_file), \
                 patch.object(ws, "download_url", side_effect=fake_download) as mock_dl:
                ws.cmd_config(args)

            mock_dl.assert_called_once()

    def test_config_download_refuses_if_exists(self):
        with TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            config_file = config_dir / "config.json"
            config_file.write_text("{}")
            args = MagicMock(config_action="download", url="https://example.com/config.json")

            f = io.StringIO()
            with patch.object(ws, "CONFIG_DIR", config_dir), \
                 patch.object(ws, "CONFIG_FILE", config_file), \
                 redirect_stdout(f):
                ws.cmd_config(args)

            self.assertIn("already exists", f.getvalue())


class TestStatus(SafeTestCase):
    def test_status_shows_missing_dirs(self):
        with TemporaryDirectory() as tmpdir:
            config = make_config(tmpdir)
            workspace_root = Path(tmpdir)

            (workspace_root / "code").mkdir()
            (workspace_root / "research").mkdir()

            config_file = setup_config(tmpdir, config)
            config_dir = Path(tmpdir) / "config"
            args = MagicMock()

            f = io.StringIO()
            with patch.object(ws, "CONFIG_FILE", config_file), \
                 patch.object(ws, "CONFIG_DIR", config_dir), \
                 redirect_stdout(f):
                ws.cmd_status(args)

            output = f.getvalue()
            self.assertIn("ok", output)
            self.assertIn("MISSING", output)


class TestPull(SafeTestCase):
    def test_pull_runs_git_pull_on_each_repo(self):
        with TemporaryDirectory() as tmpdir:
            config = make_config(tmpdir)
            workspace_root = Path(tmpdir)

            # Create repo dirs with .git inside
            for repo in config["code"]["repos"] + config["research"]["repos"] + config["knowledge"]["repos"]:
                repo_path = workspace_root / repo["path"]
                repo_path.mkdir(parents=True, exist_ok=True)
                (repo_path / ".git").mkdir()

            config_file = setup_config(tmpdir, config)
            args = MagicMock(section=None)
            mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout="Already up to date."))

            with patch.object(ws, "CONFIG_FILE", config_file), \
                 patch("subprocess.run", mock_run):
                ws.cmd_pull(args)

            pull_calls = [
                c for c in mock_run.call_args_list
                if "pull" in c[0][0]
            ]
            self.assertEqual(len(pull_calls), 4)

    def test_pull_filters_by_section(self):
        with TemporaryDirectory() as tmpdir:
            config = make_config(tmpdir)
            workspace_root = Path(tmpdir)

            for repo in config["code"]["repos"]:
                repo_path = workspace_root / repo["path"]
                repo_path.mkdir(parents=True, exist_ok=True)
                (repo_path / ".git").mkdir()

            config_file = setup_config(tmpdir, config)
            args = MagicMock(section="code")
            mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout="Already up to date."))

            with patch.object(ws, "CONFIG_FILE", config_file), \
                 patch("subprocess.run", mock_run):
                ws.cmd_pull(args)

            pull_calls = [
                c for c in mock_run.call_args_list
                if "pull" in c[0][0]
            ]
            self.assertEqual(len(pull_calls), 2)

    def test_pull_continues_on_failure_then_exits_1(self):
        with TemporaryDirectory() as tmpdir:
            config = make_config(tmpdir)
            workspace_root = Path(tmpdir)

            # Create all repo dirs with .git
            all_repos = config["code"]["repos"] + config["research"]["repos"] + config["knowledge"]["repos"]
            for repo in all_repos:
                repo_path = workspace_root / repo["path"]
                repo_path.mkdir(parents=True, exist_ok=True)
                (repo_path / ".git").mkdir()

            config_file = setup_config(tmpdir, config)
            args = MagicMock(section=None)

            # First repo fails, rest succeed
            call_count = [0]
            def mock_run_side_effect(*a, **kw):
                call_count[0] += 1
                if call_count[0] == 1:
                    return MagicMock(returncode=1, stderr="CONFLICT: merge conflict in file.txt")
                return MagicMock(returncode=0, stdout="Already up to date.")

            mock_run = MagicMock(side_effect=mock_run_side_effect)

            f = io.StringIO()
            with patch.object(ws, "CONFIG_FILE", config_file), \
                 patch("subprocess.run", mock_run), \
                 redirect_stdout(f), \
                 self.assertRaises(SystemExit) as ctx:
                ws.cmd_pull(args)

            # Exits with code 1
            self.assertEqual(ctx.exception.code, 1)

            # But still pulled all repos (didn't stop at first failure)
            pull_calls = [
                c for c in mock_run.call_args_list
                if "pull" in c[0][0]
            ]
            self.assertEqual(len(pull_calls), 4)

            # Output mentions the error
            output = f.getvalue()
            self.assertIn("CONFLICT", output)
            self.assertIn("1 errors", output)

    def test_pull_skips_missing_repos(self):
        with TemporaryDirectory() as tmpdir:
            config = make_config(tmpdir)
            config_file = setup_config(tmpdir, config)
            args = MagicMock(section=None)
            mock_run = MagicMock()

            with patch.object(ws, "CONFIG_FILE", config_file), \
                 patch("subprocess.run", mock_run):
                ws.cmd_pull(args)

            mock_run.assert_not_called()


class TestValidate(SafeTestCase):
    def test_validate_passes_when_in_sync(self):
        with TemporaryDirectory() as tmpdir:
            config = make_config(tmpdir)
            workspace_root = Path(tmpdir)

            # Create all expected directories
            for d in ws.TOP_LEVEL_DIRS:
                (workspace_root / d).mkdir(exist_ok=True)
            for org in config["code"]["orgs"]:
                (workspace_root / "code" / org).mkdir(parents=True, exist_ok=True)
            for repo in (config["code"]["repos"] + config["research"]["repos"] + config["knowledge"]["repos"]):
                (workspace_root / repo["path"]).mkdir(parents=True, exist_ok=True)

            config_file = setup_config(tmpdir, config)
            args = MagicMock()

            f = io.StringIO()
            with patch.object(ws, "CONFIG_FILE", config_file), \
                 redirect_stdout(f):
                ws.cmd_validate(args)

            self.assertIn("in sync", f.getvalue())

    def test_validate_reports_missing_dirs_as_errors(self):
        with TemporaryDirectory() as tmpdir:
            config = make_config(tmpdir)
            workspace_root = Path(tmpdir)
            # Create nothing

            config_file = setup_config(tmpdir, config)
            args = MagicMock()

            f = io.StringIO()
            with patch.object(ws, "CONFIG_FILE", config_file), \
                 redirect_stdout(f), \
                 self.assertRaises(SystemExit) as ctx:
                ws.cmd_validate(args)

            self.assertEqual(ctx.exception.code, 1)
            output = f.getvalue()
            self.assertIn("Errors", output)
            self.assertIn("Missing directory", output)

    def test_validate_warns_on_extra_dirs(self):
        with TemporaryDirectory() as tmpdir:
            config = make_config(tmpdir)
            workspace_root = Path(tmpdir)

            # Create all expected directories
            for d in ws.TOP_LEVEL_DIRS:
                (workspace_root / d).mkdir(exist_ok=True)
            for org in config["code"]["orgs"]:
                (workspace_root / "code" / org).mkdir(parents=True, exist_ok=True)
            for repo in (config["code"]["repos"] + config["research"]["repos"] + config["knowledge"]["repos"]):
                (workspace_root / repo["path"]).mkdir(parents=True, exist_ok=True)

            # Add an extra directory not in config
            (workspace_root / "code" / "mystery-org").mkdir()

            config_file = setup_config(tmpdir, config)
            args = MagicMock()

            f = io.StringIO()
            with patch.object(ws, "CONFIG_FILE", config_file), \
                 redirect_stdout(f):
                ws.cmd_validate(args)

            output = f.getvalue()
            self.assertIn("Warnings", output)
            self.assertIn("mystery-org", output)

    def test_validate_warns_but_exits_zero_for_extras_only(self):
        with TemporaryDirectory() as tmpdir:
            config = make_config(tmpdir)
            workspace_root = Path(tmpdir)

            # Create all expected + extra
            for d in ws.TOP_LEVEL_DIRS:
                (workspace_root / d).mkdir(exist_ok=True)
            for org in config["code"]["orgs"]:
                (workspace_root / "code" / org).mkdir(parents=True, exist_ok=True)
            for repo in (config["code"]["repos"] + config["research"]["repos"] + config["knowledge"]["repos"]):
                (workspace_root / repo["path"]).mkdir(parents=True, exist_ok=True)
            (workspace_root / "code" / "extra-org").mkdir()

            config_file = setup_config(tmpdir, config)
            args = MagicMock()

            # Should NOT raise SystemExit — warnings only
            f = io.StringIO()
            with patch.object(ws, "CONFIG_FILE", config_file), \
                 redirect_stdout(f):
                ws.cmd_validate(args)

            # If we got here without SystemExit, exit code is 0


class TestErrorHandling(SafeTestCase):
    def test_load_config_fails_on_bad_json(self):
        with TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config" / "config.json"
            config_file.parent.mkdir()
            config_file.write_text("{invalid json}")

            f = io.StringIO()
            with patch.object(ws, "CONFIG_FILE", config_file), \
                 redirect_stdout(f), \
                 self.assertRaises(SystemExit) as ctx:
                ws.load_config()

            self.assertEqual(ctx.exception.code, 1)
            self.assertIn("invalid JSON", f.getvalue())

    def test_load_config_fails_on_missing_repo_fields(self):
        with TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config" / "config.json"
            config_file.parent.mkdir()
            config_file.write_text(json.dumps({
                "code": {"repos": [{"path": "code/org-1/project"}]}
            }))

            f = io.StringIO()
            with patch.object(ws, "CONFIG_FILE", config_file), \
                 redirect_stdout(f), \
                 self.assertRaises(SystemExit) as ctx:
                ws.load_config()

            self.assertEqual(ctx.exception.code, 1)
            self.assertIn("missing 'url' or 'path'", f.getvalue())

    def test_workspace_root_must_be_absolute(self):
        config = {"workspace_root": "relative/path"}

        f = io.StringIO()
        with redirect_stdout(f), \
             self.assertRaises(SystemExit) as ctx:
            ws.get_workspace_root(config)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("absolute path", f.getvalue())

    def test_pull_rejects_invalid_section(self):
        with TemporaryDirectory() as tmpdir:
            config = make_config(tmpdir)
            config_file = setup_config(tmpdir, config)
            args = MagicMock(section="invalid-section")

            f = io.StringIO()
            with patch.object(ws, "CONFIG_FILE", config_file), \
                 redirect_stdout(f), \
                 self.assertRaises(SystemExit) as ctx:
                ws.cmd_pull(args)

            self.assertEqual(ctx.exception.code, 1)
            self.assertIn("unknown section", f.getvalue())


if __name__ == "__main__":
    unittest.main()
