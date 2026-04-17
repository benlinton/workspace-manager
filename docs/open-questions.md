# Open Questions

Design decisions that are worth revisiting as the workspace evolves.

## Does experiments earn its keep as a separate directory?

`experiments/` currently lives alongside orgs as a peer under `code/`. But experiments usually belong to a specific context — a personal side project, a proof-of-concept for a client. Should experiments just start in `personal/` (or the relevant org) and get deleted when they die?

Arguments for keeping `experiments/`:
- Clear signal that nothing here is permanent
- No org affiliation needed for pure experiments
- Easy to bulk-delete or ignore

Arguments against:
- Experiments that graduate need to be moved
- Adds a grouping that doesn't map to an AI context boundary
- Most experiments are personal anyway

## Should third-party be one bucket?

Contributions to a specific org's ecosystem could live under that org instead of in a generic `third-party/` directory. For example, contributing to a library your Org-1 project depends on might make more sense under `org-1/` where the AI context (conventions, MCP servers) is already configured.

Counter-argument: upstream open source projects have their own conventions, not your org's. Keeping them separate avoids inheriting org-level `CLAUDE.md` rules that don't apply. In fact, Claude Code's CLAUDE.md tree walk means a third-party repo under `org-1/` would automatically inherit Org-1 conventions — probably wrong for upstream work.

A possible middle ground: `third-party/` for pure upstream work, but forks-for-work live under the org that needs them.

## Multiple AI tools strategy

The design currently assumes Claude Code. What about Cursor (`.cursor/`), Windsurf, Copilot, or future AI tools? Each has its own config format and directory conventions.

The directory hierarchy helps all tools (scoping is universal), but config files are tool-specific. Questions:
- Should `toolkits/shared-context/` have tool-specific variants (e.g., `typescript-conventions.cursor.md`)?
- Or should context modules be tool-agnostic markdown that each tool can consume?
- How do you avoid maintaining parallel configs (`.claude/settings.json` + `.cursor/settings.json` + ...)?

For now, the layout doesn't need to change — each tool gets its own config directory at the project level. But this could become a maintenance burden at scale.

## Sharing AI config across projects

AI tools like Claude Code don't cascade `.claude/settings.json` or `.mcp.json` from parent directories. Each project needs its own copy. For an org with 10 projects that all need the same permissions, that's 10 identical files.

A potential solution: keep shared configs in a toolkit repo (e.g., `toolkits/ai-settings/`) and symlink into each project:

```bash
ln -s ~/Workspace/toolkits/ai-settings/org-1/settings.json \
      ~/Workspace/code/org-1/project-a/.claude/settings.json

ln -s ~/Workspace/toolkits/ai-settings/org-1/mcp.json \
      ~/Workspace/code/org-1/project-a/.mcp.json
```

One source of truth, many projects. The `workspace init` script could automate this if the config specified which settings to symlink per org. Not implemented yet.

## Pinned versions for toolkits

Currently `workspace init` clones the default branch and `workspace pull` pulls latest. There's no way to pin a tool to a specific version. A `ref` field in config would enable this:

```json
{
  "url": "https://github.com/someone/useful-tool.git",
  "path": "toolkits/useful-tool",
  "ref": "v1.2.0"
}
```

The script would `git checkout` the specified ref after cloning, and `workspace pull` would respect it (pull + checkout ref, or skip pulling pinned repos entirely). Worth building when stability of third-party tools becomes a concern.

## Multiple `bin_link` entries in config

Currently `bin_link` is a single path that symlinks the `workspace` binary. As more standalone tools appear in `toolkits/` (e.g., `placeholder-cli`), each one needs a symlink into `~/.local/bin/`. Doing this manually per machine is fine for one or two tools but doesn't scale.

### What it could look like

Replace the single `bin_link` string with a list:

```json
{
  "bin_links": [
    {
      "source": "code/personal/workspace-manager/bin/workspace",
      "target": "~/.local/bin/workspace"
    },
    {
      "source": "toolkits/placeholder-cli/bin/placeholder",
      "target": "~/.local/bin/placeholder"
    }
  ]
}
```

`workspace init` would create all symlinks in one pass. `workspace status` could report broken or missing links.

### Questions

- **When does this earn its keep?** One symlink is trivial. Two is fine. At three or four tools this starts saving real time on new machine setup.
- **Should the target default to `~/.local/bin/<basename>`?** That would shorten most entries to just a source path, since the target is almost always the same pattern.
- **Backwards compatibility.** The existing single `bin_link` string would need to keep working or be migrated.

## Should the workspace have a top-level scratch/tmp directory?

A place for unsorted, ephemeral, or throwaway content. Lives inside `~/Workspace/` so it's portable and manageable by toolkits (unlike `/tmp` or `~/Downloads`). Reduces friction when starting quick throwaway work or when you don't know where to put something yet.

### Name candidates

| Name | Pros | Cons |
|---|---|---|
| `tmp/` | 3 chars, universally understood, lowest friction | System `/tmp` association (but context makes it clear) |
| `scratch/` | Well-understood by developers, implies throwaway work | Implies active work, not "dump and sort later" |
| `inbox/` | Universal metaphor, carries "process it" expectation | Implies triage workflow, more structure than needed |
| `unsorted/` | Completely honest, no metaphor to misinterpret | Could become "permanently unsorted" |
| `drop/` | 4 chars, action-oriented | Less universally understood |
| `fleeting/` | PKM terminology, implies short-lived | Niche, 8 chars |
| `ephemeral/` | Precise meaning | 9 chars, overwrought |

### One directory or two?

Alternative: separate inbox and scratch with distinct purposes:
- **inbox/** — things that arrived and need sorting. Triage-oriented. Items should leave within a week.
- **scratch/** or **tmp/** — active throwaway work. Items get deleted when done.

This avoids mixing "stuff I haven't sorted" with "stuff I'm actively messing with." But adds two top-level directories for what might be a minor need. If one can serve both purposes, prefer one.

### Design rules (once decided)

- Top-level in `~/Workspace/` — a peer of `code/`, `research/`, etc.
- Flat — no subdirectories, no organization inside it
- Portable — syncs across machines like any other top-level directory
- Manageable — toolkits can include scripts to list stale items or prompt cleanup

## Stale repo detection and archival

A command or skill that finds repos you haven't touched in a while and offers to archive them. Over time workspaces accumulate cloned repos that served a short-lived purpose — a one-off PR, a spike that went nowhere, a dependency you read once. These add noise to directory listings and AI context.

### What "untouched" means

Several signals could contribute:
- **Last commit date** — no commits from you in N months
- **Last filesystem access** — no recent `git checkout`, `git pull`, or file edits
- **Branch state** — still on `main` with no local branches (never started real work)
- **Relationship to other repos** — no other project depends on it (not a toolkit in active use)

A composite staleness score is probably better than any single metric. The threshold should be configurable.

### What "archive" means

Options from least to most aggressive:
1. **Report only** — list stale repos, let the user decide
2. **Move to an archive directory** — e.g., `~/Workspace/archive/code/org/repo`, preserving the original path structure so it can be restored
3. **Remove and re-clone on demand** — delete the local clone but keep it in config so `workspace init` can bring it back (only works for repos with no unpushed local work)

Option 2 is the safest default. Moving preserves history and local branches. The archive directory could be gitignored or excluded from AI context walks.

### Interface questions

- Should this be a subcommand (`workspace archive`, `workspace stale`) or a standalone skill/hook?
- Interactive or batch? Listing candidates and prompting per-repo is safest. A `--dry-run` flag is non-negotiable.
- Should archived repos be tracked in config so `workspace status` can report them?
- Could this run on a schedule (e.g., monthly prompt) rather than only on demand?

## `placeholder` — standalone tool for large file references

Large files (raw footage, ML model weights, sample libraries, test fixtures) often live on external storage (NFS, S3) as a single source of truth. Projects that need these files typically copy them locally, duplicating storage for no benefit. A 200GB footage library used by three productions is 600GB of local disk for the same bytes.

`placeholder` is a standalone CLI tool (`bin/placeholder`) that creates lightweight local references to files on external storage — similar to how Git LFS uses pointer files instead of storing large content directly.

### What it does

```bash
placeholder add ~/Workspace/studio/productions/short-film/footage \
  --from nfs://nas/footage/short-film-raw

placeholder add ~/Workspace/code/org-1/ml-project/models \
  --from s3://bucket/models/v2

placeholder list
placeholder status
```

The local path looks normal to whatever tool opens it (DaVinci Resolve, Python training script, etc.) but points at the canonical external location instead of duplicating the data.

### Design principles

- **Standalone tool** — its own binary in `bin/`, not a workspace subcommand. Different concern, different tool.
- **Storage-agnostic** — NFS, S3, and whatever comes next. The pointer abstraction shouldn't be tied to one backend.
- **Python 3 stdlib only** — consistent with workspace-manager conventions. S3 support may need `boto3` or shelling out to `aws` CLI — open question.

### Open sub-questions

- **Pointer mechanism.** Symlinks work for NFS but not S3. S3 needs a fetch/cache step. Should the tool use symlinks for local/NFS and a download-on-demand model for cloud storage? Or a unified approach (e.g., FUSE mount, stub files with metadata)?
- **Mount path resolution across machines.** NFS mount points differ between machines (`/Volumes/NAS` on macOS vs. `/mnt/nas` on Linux). The config should store a logical storage name that resolves per-machine, not a hardcoded path.
- **Offline access.** When external storage is unavailable, symlinks dangle and S3 is unreachable. Should there be a `placeholder cache` subcommand for selective local copies when working offline?
- **Config location.** Does `placeholder` maintain its own config file, or does it integrate with the workspace-manager config? Leaning toward its own config — it's a separate tool.
- **Scope boundary.** This tool creates and manages pointers. It does NOT catalog, tag, version, or deduplicate files. If it starts wanting those features, it's becoming a different tool.
- **Tool compatibility.** Which creative/dev tools handle symlinked directories gracefully? Needs testing per tool (DaVinci Resolve, Ableton, PyTorch data loaders, etc.).
