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

## Settings.json duplication across projects

Since `.claude/settings.json` does NOT cascade from parent directories, each project needs its own copy. For an org with 10 projects that all need the same allowed tools and MCP permissions, that's 10 identical settings files.

Options:
- Accept the duplication — it's a small file and rarely changes
- Use a template in `toolkits/shared-templates/` and copy when creating new projects
- Use a script that generates settings.json from a shared config
- Store common settings in `~/.claude/settings.json` (user scope) and only put project-specific overrides in the project

The user-scope approach works for settings shared across ALL projects but doesn't help with org-specific settings.

## MCP server sharing without duplication

`.mcp.json` also doesn't cascade. If 5 Org-1 projects all need the same Jira MCP server, you either:
- Duplicate `.mcp.json` in each project
- Use a user-scope MCP server (but then it's available in ALL projects, not just Org-1 ones)

There's no clean solution today for org-scoped MCP servers. This is a Claude Code limitation, not a layout problem. Worth revisiting as the tool evolves.

## Toolkit update workflow

Each tool in `toolkits/` is its own git repo. Third-party tools are easy — `git pull`. But for your own tools developed in `code/`, the publish flow is manual: push from `code/`, then pull in `toolkits/`. The `workspace pull` command (planned) will automate pulling all repos across the workspace.

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
