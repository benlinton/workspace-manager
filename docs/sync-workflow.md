# Sync Workflow

How the workspace layout stays consistent across machines while allowing each machine to carry only what it needs.

## Strategy

Each project is its own git repo. There is no monorepo or sync daemon. Machines clone what they need.

## What syncs how

| Directory | Sync method | Notes |
|---|---|---|
| `code/<org>/<project>/` | Git clone per project | Each project is an independent repo |
| `research/<project>/` | Git clone per project | Some may be local-only (no remote) |
| `studio/<medium>/<project>/` | Git + LFS, or manual backup | Large binary assets need special handling |
| `toolkits/<tool>/` | Git clone per tool | Mix of your own tools and third-party repos |
| `knowledge/<item>/` | Git, cloud sync, or git clone | PKM vault syncs via cloud or git; reference items cloned via git |
| `dotfiles` | Symlink to dotfiles manager | Path configured in config.json, defaults to chezmoi |

## Per-machine config

Each machine has a different subset of the workspace. The `machines` section of `config.json` controls what gets set up on each machine:

```json
{
  "machine": "macbook-personal",
  "machines": {
    "macbook-personal": {
      "skip": []
    },
    "macbook-work": {
      "skip": ["studio", "research"],
      "code_orgs": ["org-1", "third-party"]
    }
  }
}
```

- **`skip`** — top-level directories to skip entirely on this machine
- **`code_orgs`** — limit which org directories are created and which code repos are cloned

A bootstrap script reads the manifest and clones the repos. This can be as simple as a shell script or as structured as an Ansible playbook.

## Path portability

The workspace root is always `~/Workspace/`. This is a hard convention — no machine-specific prefixes. This means:

- Absolute paths in CLAUDE.md `@path` imports work everywhere: `@~/Workspace/toolkits/shared-context/foo.md`
- Each tool in `toolkits/` is its own git repo — your own tools and third-party tools cloned from others
- If a machine doesn't need a tool, just don't clone it

## Large files and creative assets

`studio/` projects often contain large binary files (video, audio, project files). These don't belong in plain git. Options:

- **Git LFS** for versioned large files
- **External backup** (Time Machine, Backblaze, NAS) for project archives
- **Cloud storage** (Google Drive, iCloud) for active project media

The workspace layout doesn't change — `studio/` always has the same structure. The sync mechanism varies by asset size.
