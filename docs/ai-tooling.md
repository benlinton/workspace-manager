# AI Tooling

How AI tools integrate with this workspace — what cascades, what doesn't, and how toolkits bridges the gap. The directory hierarchy benefits all AI tools (scoping is universal), but config files are tool-specific. This doc uses Claude Code as the primary example since its behavior is well-documented, but the principles apply to Cursor, Copilot, Windsurf, and others.

## How Claude Code loads context (as a reference model)

Claude Code uses two different mechanisms for configuration, and they work differently. Other AI tools have similar concepts with different implementations.

### CLAUDE.md — walks up the directory tree

When you open Claude Code in a project, it walks **up** the directory tree and loads every `CLAUDE.md` (and `CLAUDE.local.md`) it finds. All discovered files are concatenated into context — they don't override each other, they combine.

If you're in `~/Workspace/code/org-1/project-a/`, Claude Code loads:
1. `~/Workspace/code/org-1/project-a/CLAUDE.md`
2. `~/Workspace/code/org-1/CLAUDE.md`
3. `~/Workspace/code/CLAUDE.md`
4. `~/.claude/CLAUDE.md` (user-level)

At each level, `CLAUDE.local.md` is appended after `CLAUDE.md` for machine-specific overrides.

**This is what makes the directory hierarchy powerful for instructions.** Parent CLAUDE.md files apply to all children automatically.

### settings.json — does NOT cascade

`.claude/settings.json` does **not** walk up the tree. It uses a fixed scope hierarchy:

1. **Managed settings** (highest priority) — system-level policies
2. **Command line arguments**
3. **Local project** — `.claude/settings.local.json` (per-machine, gitignored)
4. **Shared project** — `.claude/settings.json` (in version control)
5. **User** — `~/.claude/settings.json` (lowest)

A `.claude/settings.json` at `code/org-1/` has **no effect** when you're working in `code/org-1/project-a/`. Only the project root's settings file is read.

Array settings (like allowed tools) merge across scopes — user + project settings combine.

### MCP servers — scoped, not cascaded

MCP servers are configured at three levels, none of which inherit from parent directories:

- **Project scope** — `.mcp.json` at project root (shared via git)
- **Local scope** — per-project in `~/.claude.json` (private)
- **User scope** — global in `~/.claude.json` (available everywhere)

A parent directory's `.mcp.json` is not read by child projects. Each project must declare its own MCP servers or rely on user-scope servers.

### @path imports — the bridge to toolkits

CLAUDE.md supports `@path` imports to pull in external files:

```markdown
# Project conventions
@~/Workspace/toolkits/shared-context/typescript-conventions.md
@~/Workspace/toolkits/shared-context/code-review-checklist.md
```

This is how projects reference shared context modules from `toolkits/`. Paths can be relative (to the file containing the import) or absolute. Recursive imports work up to 5 levels deep.

Additionally, `.claude/rules/` can hold modular instruction files that are automatically loaded.

## The cascade in practice

Given these mechanics, here's what the workspace hierarchy actually provides:

```
~/Workspace/code/
├── CLAUDE.md                      # Universal coding preferences (auto-inherited)
│
├── org-1/
│   ├── CLAUDE.md                  # Org-1 conventions (auto-inherited by all org-1 projects)
│   ├── project-a/
│   │   ├── CLAUDE.md              # Project-specific context + @path imports from toolkits
│   │   ├── .claude/
│   │   │   └── settings.json     # Project-level tool permissions
│   │   └── .mcp.json             # Project-level MCP servers
│   └── project-b/
│
├── personal/
│   ├── CLAUDE.md                  # Personal coding conventions (auto-inherited)
│   ├── my-project/
│   └── workspace-manager/
│
└── org-2/
    ├── CLAUDE.md                  # Org-2 architecture (auto-inherited)
    └── ...
```

| Mechanism | Cascades from parents? | How to share across projects |
|---|---|---|
| `CLAUDE.md` | Yes — walks up the tree | Place at org or code/ level |
| `.claude/settings.json` | No — project root only | Use `~/.claude/settings.json` for universal settings |
| `.mcp.json` | No — project root only | Use user-scope MCP servers, or duplicate per project |
| Context modules | N/A — explicit import | Use `@path` imports in CLAUDE.md |

## What goes where

| Level | CLAUDE.md content | Other config |
|---|---|---|
| `code/` | Language preferences, formatting, commit message style | None (settings.json has no effect here) |
| `code/<org>/` | Team norms, API patterns, shared architecture decisions | None (settings.json has no effect here) |
| `code/<org>/<project>/` | Domain model, key abstractions, gotchas, `@path` imports from toolkits | `.claude/settings.json`, `.mcp.json` |

## Non-code directories

Research and studio projects don't benefit from the same org cascade. Each research project is its own self-contained AI working directory — but they can share tooling by importing `toolkits/` context modules via `@path`. A `research/CLAUDE.md` with shared research methodology will auto-inherit into all research projects thanks to the tree walk.

Studio projects are organized by medium (which maps to toolchain, not AI context). Keep them flat or shallow — don't force the org pattern where it doesn't apply.

`knowledge/` holds PKM, reference material, and filed documents as flat peers. A `knowledge/CLAUDE.md` could define how AI interacts with your knowledge base — useful if you want consistent behavior when asking questions across your PKM vault, reference material, and documents.

## The toolkits directory

A growing library of AI tools, harnesses, plugins, skill libraries, and shared resources. Not limited to any single AI tool — this serves Claude Code, Cursor, Copilot, and whatever comes next.

Each entry in `toolkits/` is its own git repo — a mix of your own published tools and third-party tools cloned from others:

```
~/Workspace/toolkits/
├── shared-context/           # Your repo — reusable context files (graduate to a dedicated context manager as needs grow)
├── shared-hooks/             # Your repo — hook scripts shared across projects
├── shared-templates/         # Your repo — project scaffolding templates
├── my-mcp-server/            # Your repo — an MCP server you built
├── useful-tool/              # Third-party — cloned from someone else
├── some-skill-library/       # Third-party — AI agent skills
└── ...                       # Grows as your AI tooling needs evolve
```

## How tools get into toolkits/

**Third-party tools:** Clone them directly.
```bash
cd ~/Workspace/toolkits
git clone https://github.com/someone/useful-tool.git
```

**Your own tools:** Develop in `code/`, publish as a standalone repo, then clone into `toolkits/`. The source stays in `code/` where it gets tested and iterated. The published version in `toolkits/` is what projects reference.

```bash
# Development happens in code/
cd ~/Workspace/code/personal/my-mcp-server
# ... build, test, push to remote ...

# Then clone the published version into toolkits/
cd ~/Workspace/toolkits
git clone git@github.com:you/my-mcp-server.git
```

To update a tool, pull the latest in `toolkits/`:
```bash
cd ~/Workspace/toolkits/my-mcp-server && git pull
```

## How projects consume tools

**Context files** — via `@path` imports in CLAUDE.md (or equivalent for other AI tools):
```markdown
@~/Workspace/toolkits/shared-context/typescript-conventions.md
```

**MCP servers** — via `.mcp.json` or user-scope config:
```json
{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["~/Workspace/toolkits/my-mcp-server/index.js"]
    }
  }
}
```

**Templates** — copied once into a new project:
```bash
cp ~/Workspace/toolkits/shared-templates/new-project-claude.md \
   ~/Workspace/code/org-1/new-project/CLAUDE.md
```

**Hooks** — referenced by path in settings:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": ["~/Workspace/toolkits/shared-hooks/pre-commit-lint.sh"]
      }
    ]
  }
}
```
