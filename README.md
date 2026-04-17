# Workspace Manager

An opinionated system for organizing workspaces and projects across machines.

## Quick Start

```bash
# Clone this repo
git clone https://github.com/benlinton/workspace-manager.git
cd workspace-manager

# Set up config (choose one)
./bin/workspace config init                          # copy from example template
./bin/workspace config download <url>                # download a config file from a URL
./bin/workspace config clone git@github.com:you/workspace-configs.git  # clone a private config repo

# Edit config with your repos and machine name
./bin/workspace config edit

# Preview what init would do without making changes
./bin/workspace init --dry-run

# Create directories and clone repos
./bin/workspace init
```

## Example Layout

```
~/Workspace/
├── code/                    # All software projects, grouped by org
│   ├── personal/            #   Personal projects
│   ├── org-1/               #   Work projects for org-1
│   ├── org-2/               #   Work projects for org-2
│   ├── third-party/         #   Third-party repos for reference or contribution
│   └── experiments/         #   Prototypes, experiments, and labs
│
├── knowledge/               # PKM, reference material, and filed documents
│   ├── second-brain/        #   Primary personal knowledge management
│   ├── document-vault/      #   Document retreival system
│   ├── bytebytego/          #   Example system design reference (read-only)
│   └── ...                  #   Documents, guides, runbooks, courses, help, etc.
│
├── research/                # Ephemeral research, analysis, and intelligence gathering
│   ├── market-research/     #   Market research and analysis
│   └── ...                  #   Health analysis, business strategy, deep-dives, etc.
│
├── studio/                  # Creative production
│   ├── productions/         #   Video projects
│   ├── music/               #   Music library
│   ├── sound-effects/       #   Sound effect libraries
│   ├── design/              #   Standalone design work (logos, branding, UI mockups)
│   ├── video-editor/        #   Video editor media cache and proxies
│   └── ...                  #   Video plugins, LUTs, templates, stock footage, etc.
│
├── toolkits/                # AI tools, harnesses, plugins, and shared resources
│   ├── my-mcp-server/       #   Example: an MCP server you built
│   ├── shared-context/      #   Example: reusable context files
│   ├── constitution/        #   Example: a set of rules all AI agents must follow
│   ├── useful-tool/         #   Example: a third-party tool cloned from someone else
│   └── ...                  #   Whatever tools you need — no fixed set
│
└── dotfiles -> <symlinked dotfiles path> 
```

## Commands

| Command | Description |
|---|---|
| **Config** | |
| `workspace config init` | Create config from example template |
| `workspace config clone <url>` | Clone a private config repo into config/ |
| `workspace config download <url>` | Download a config.json from a URL |
| `workspace config show` | Print config.json to stdout (default) |
| `workspace config edit` | Open config.json in $EDITOR |
| `workspace config path` | Print config directory path |
| **Workspace** | |
| `workspace init` | Create directory tree and clone repos (requires config) |
| `workspace init --dry-run` | Preview what init would do |
| `workspace status` | Show what exists and what's missing |
| `workspace pull` | Pull latest changes for all repos (excludes studio) |
| `workspace pull <section>` | Pull only repos in a specific section (code, research, knowledge, toolkits) |
| `workspace validate` | Validate config and check directory tree is in sync |

Existing directories are skipped. Existing repos are not re-cloned. Studio projects are excluded from init and pull — they typically use Git LFS or cloud storage.

## Configuration

Config lives in `config/config.json` (gitignored). See [templates/config.example.json](templates/config.example.json) for the full schema.

<details>
<summary>Expand Key Fields</summary>

- **`machine`** — name of this machine (used to look up per-machine settings)
- **`workspace_root`** — path to workspace root (default: `~/Workspace`)
- **`dotfiles`** — path to your dotfiles directory (default: `~/.local/share/chezmoi`)
- **`bin_link`** — optional path to symlink the `workspace` command (e.g., `~/.local/bin/workspace`)
- **`code.orgs`** — list of org directories to create under `code/`
- **`code.repos`** / **`research.repos`** / **`knowledge.repos`** / **`toolkits.repos`** — repos to clone, each with `url` and `path`
- **`studio.categories`** — subdirectories to create under `studio/`
- **`machines.<name>.skip`** — top-level directories to skip on this machine
- **`machines.<name>.code_orgs`** — limit which code orgs are set up on this machine

</details>

## Principles

Why the layout is structured this way — depth limits, portability, and grouping logic.

<details>
<summary>Expand Details</summary>

### Two levels to any project, three where it earns its keep

The target depth is `Workspace/<grouping>/<project>/`. The only exception is `code/`, which uses `Workspace/code/<org>/<project>/` — the org layer drives context-switching efficiency and scopes tab-completion.

| Path pattern | Depth | Why |
|---|---|---|
| `code/<org>/<project>` | 3 | Org grouping maps to how you switch between clients/employers |
| `research/<project>` | 2 | Flat — no sub-grouping needed |
| `studio/<category>` or `studio/<category>/<project>` | 2–3 | Categories organize by medium; some (productions/) have sub-projects |
| `knowledge/<item>` | 2 | Flat — PKM, reference material, and documents side by side |
| `toolkits/<tool>` | 2 | Flat — each entry is its own repo |

### Groupings are portable

Every top-level directory is activity-based and universal:

- **code/** — present on every dev machine
- **research/** — present wherever you do research and analysis
- **studio/** — present on creative workstations
- **toolkits/** — present wherever you use AI tools
- **knowledge/** — present wherever you manage personal knowledge, reference material, or documents
- **dotfiles** — present wherever you manage system config

Only the contents inside `code/` vary by machine (your work laptop might only have `org-1/`, your personal machine has `personal/` + `org-2/`). The top-level structure is identical everywhere.

### Groupings are by nature of work, not who it's for

The "who" (org) is a property of code projects and lives one level down inside `code/`. Everything else is grouped by what kind of work it is.

</details>

## Conventions

Per-directory rules for what goes where and how each section is used.

<details>
<summary>Expand Details</summary>

### code/

- Organized by org/context. New repos go under the appropriate org directory.
- `third-party/` repos sit flat — no sub-grouping by contribution vs reference.
- `experiments/` is for prototypes and experiments. When one graduates, move it to the appropriate org. When one dies, delete it.
- AI tool source code is developed here like any other project. When ready for consumption, tools are published as standalone repos and cloned into `toolkits/`.

### research/

- Each subdirectory is a focused research or analysis project.
- These are non-code projects: tax analysis, health research, business strategy, data synthesis, multi-step investigations.
- The work involves gathering data, scraping, synthesizing, finding insights, and making sense of documents.
- Many of these are Claude Code working directories — the project structure is whatever the work requires.

### studio/

- Organized by medium/category at the first level.
- `productions/` contains named video projects (e.g., `my-film-2026/`).
- `design/` is for standalone design work not tied to a specific production.
- Production-related design assets stay with their production, not in `design/`.
- `video-editor/` holds video editor media cache and proxies.
- Studio projects are not auto-cloned by the workspace script — they typically use Git LFS, cloud storage, or manual backup due to large binary assets.

### knowledge/

- Everything you know, have learned, or have on file — flat, with names that do the work.
- Entries can be git repos, document stores, synced folders, or any other format.
- PKM vaults, reference material, context libraries, filed documents — all live here as peers.
- The distinction between types is obvious from the item name — no subdirectory wrappers needed.
- Not for active development — if you start contributing significantly to a reference repo, move it to `code/third-party/`.

### toolkits/

- A growing library of AI tools, harnesses, plugins, and shared resources consumed by projects across the workspace.
- Each entry is its own git repo — a mix of your own published tools and third-party tools cloned from others.
- Your own tools are developed in `code/`, published as standalone repos, then cloned here. Third-party tools are cloned directly.
- Projects reference tools by path (e.g., `@path` imports, `.mcp.json` entries, hook paths in settings).
- This directory grows as your AI tooling needs evolve — there's no fixed set of categories.

### dotfiles

- Symlink to your dotfiles directory, configured via `dotfiles` in config.json.
- Defaults to `~/.local/share/chezmoi` if not set.
- Works with any dotfiles manager (chezmoi, yadm, bare git repo, etc.).

</details>

## Additional Docs

- [workspace-design](docs/workspace-design.md) — Design principles and rationale
- [ai-tooling](docs/ai-tooling.md) — AI tool integration and toolkits
- [sync-workflow](docs/sync-workflow.md) — Multi-machine sync strategy

## License

MIT
