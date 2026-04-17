# Workspace Design

Why the workspace is structured the way it is, and the principles that guide decisions.

## Why not flat?

### AI context boundaries

This is the most important reason today. Claude Code walks up the directory tree and loads every `CLAUDE.md` it finds. If all projects sit in a flat directory, you can't layer shared context without polluting unrelated projects.

Grouping lets you place org-level or domain-level instructions at the grouping directory and project-specific ones at the leaf. A `CLAUDE.md` at `code/org-1/` automatically applies to every project inside it.

Note: this only works for `CLAUDE.md` files. `.claude/settings.json` and `.mcp.json` do NOT cascade — they're only read at the project root. See `docs/ai-tooling.md` for the full picture.

### Security and credential scoping

MCP servers, API keys, and tool permissions should be scoped to the work that needs them. You don't want your personal project's Claude config having access to your employer's Slack MCP server, or vice versa.

Directory hierarchy provides natural isolation. Projects under different orgs have separate `.mcp.json` files and can't accidentally inherit each other's MCP servers. User-scope servers (in `~/.claude.json`) are available everywhere — use them only for truly universal tools.

### Cognitive load when navigating

Tab-completing through 80 flat directories is worse than 8 groups of 10. Two levels to a project root is the sweet spot — deep enough to scope, shallow enough to navigate without friction.

### Selective sync and backup

Different machines get different subtrees. A work laptop only needs `code/org-1/`. A personal machine needs `code/personal/` and `code/org-2/`. The top-level structure stays identical everywhere; only the contents vary by machine.

## Principles

### Group by context-switch boundary

When you switch orgs or clients, you switch mental models, credentials, git configs, and AI configs. That's the natural directory boundary. Everything that changes together should live together. If switching between two projects requires changing your mental model, credentials, or tooling, they belong in different groups.

### Two levels max before you hit a project root

Deeper nesting creates friction. `code/<org>/<project>` is the sweet spot — deep enough to scope AI context and credentials, shallow enough to navigate quickly.

The only exception is `code/` itself, which earns the extra level because the org layer drives context-switching efficiency and scopes tab-completion. `toolkits/` is flat — each entry is a repo at `toolkits/<tool>/`.

### Group by nature of work, not technology

Don't organize by language or framework (`~/go/`, `~/python/`, `~/rust/`). You work on projects, not languages. Technology choices are a property of a project, not a grouping axis.

**Exception: studio/.** Creative production is organized by medium (video, music, design, sound effects). This is intentional — media tools are incompatible across mediums (you can't open a DaVinci Resolve project in Ableton), and a single production typically lives in one medium with assets pulled in from others. This is grouping by toolchain, which we avoid for code but accept for creative work where the toolchain IS the work.

### Group by nature of work, not who it's for

The "who" (org) is a property of code projects and lives one level down inside `code/`. Everything else is grouped by what kind of work it is: research, creative production, knowledge management.

### What qualifies as an "org"

An org is an identity you work under that determines credentials, conventions, and AI tool access. Examples: `org-1/` (employer), `org-2/` (owned company), `personal/` (your own projects).

Two special-purpose directories sit alongside orgs but aren't orgs themselves:
- **`third-party/`** — repos you don't own, from the broader ecosystem. No shared conventions because each upstream project has its own.
- **`experiments/`** — experiments and prototypes. No shared conventions because nothing here is meant to last.

These earn their place as peers because they represent distinct working modes, not because they share the org properties of conventions + credentials + AI access.

### Separate building from consuming

AI tools developed as source code live in `code/`. When ready for use, they get published as standalone repos and cloned into `toolkits/`. Third-party tools are cloned directly. Projects reference `toolkits/`, not source directories. This keeps the consumption layer stable while development continues.

### Groupings are portable

Every top-level directory is activity-based. Not all directories need to be present on every machine — only create what the machine is used for:

- **code/** — present on every dev machine
- **research/** — present wherever you do research and analysis
- **studio/** — present on creative workstations
- **toolkits/** — present wherever you use AI tools
- **knowledge/** — present wherever you manage personal knowledge, reference material, or documents
- **dotfiles** — present wherever you manage config

The top-level structure is a menu, not a mandate. A work laptop might only have `code/`, `toolkits/`, and `dotfiles`. A creative workstation adds `studio/`. The structure is consistent where it exists — the same directories always mean the same thing.

Only the contents inside `code/` vary by machine (your work laptop might only have `org-1/`, your personal machine has `personal/` + `org-2/`).

### Keep active and archive separate

If you accumulate many projects under an org, consider an `_archive/` directory within it. This keeps tab-completion snappy and makes the active working set obvious at a glance.

Archival candidates: projects with no commits in 6+ months. The process is simply `mv project _archive/project`. To reactivate, move it back. The `_archive/` directory should be excluded from AI context loading where possible to avoid noise.

### Don't over-engineer it

The best workspace layout is one you actually maintain. If a structure requires constant gardening to stay organized, it's too complex. The layout should be obvious enough that new projects find their home without deliberation.
