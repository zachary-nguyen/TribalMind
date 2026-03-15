<p align="center">
  <img src="assets/logo.svg" alt="TribalMind" width="180"/>
  <h1 align="center">TribalMind</h1>
  <p align="center">
    <strong>Shared memory for AI development agents — remember, recall, and share knowledge across projects and teams.</strong>
  </p>
</p>

<p align="center">
  <a href="https://github.com/zachary-nguyen/TribalMind/actions/workflows/ci.yml"><img src="https://github.com/zachary-nguyen/TribalMind/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/zachary-nguyen/TribalMind/actions/workflows/release.yml"><img src="https://github.com/zachary-nguyen/TribalMind/actions/workflows/release.yml/badge.svg" alt="Release"></a>
  <a href="https://pypi.org/project/tribalmind/"><img src="https://img.shields.io/pypi/v/tribalmind" alt="PyPI"></a>
  <a href="https://pypi.org/project/tribalmind/"><img src="https://img.shields.io/pypi/pyversions/tribalmind" alt="Python"></a>
  <a href="https://github.com/zachary-nguyen/TribalMind/blob/master/LICENSE"><img src="https://img.shields.io/github/license/zachary-nguyen/TribalMind" alt="License"></a>
</p>

---

TribalMind is a **CLI knowledge base** that any AI agent (or human) can use to persist and retrieve knowledge. Store what you learn, recall it later, share it across your team — all through simple shell commands powered by [Backboard](https://docs.backboard.io/).

> **Any agent that can run shell commands can use TribalMind.** Pipe in via stdin, get structured JSON back, and build on top of shared team knowledge.

## How It Works

```
  tribal remember "pytest needs -p no:cacheprovider on CI"
        │
        ▼
  LLM parses → structured memory → stored in Backboard
        │
        ▼
  tribal recall "pytest CI issues"
        │
        ▼
  Semantic search → ranked results with relevance scores
```

1. **`tribal remember`** — store knowledge in natural language; an LLM parses it into structured fields (category, package, error, fix, confidence)
2. **`tribal recall`** — semantic search across your project's memory, ranked by relevance
3. **`tribal forget`** — remove outdated or incorrect knowledge
4. Every command supports **`--json`** for machine consumption and **stdin piping** for agent workflows

## Setup

### Individual Developer

One-time setup — works across all your repos:

```bash
pip install tribalmind

# 1. Store your API key and create a global config
tribal init --global

# 2. In any repo, set up agent integration files
cd your-project
tribal setup-agents
```

That's it. Your agents will now use `tribal remember` and `tribal recall` automatically. The assistant for each repo is created on first use (matched by git remote URL), so you never need to run `tribal init` per repo.

Start using it right away:

```bash
tribal remember "Running migrations on PG 15 requires --no-lock flag to avoid deadlocks"
tribal recall "postgres migration"
```

### Team Setup

Teams share knowledge by using the same [Backboard](https://backboard.io) account. Two options:

**Option A: Shared API key** (simplest) — generate one key, share it with the team. Everyone uses the same key in their `tribal init --global`.

**Option B: Backboard organization** — create an org in the Backboard dashboard, invite members, and each person gets their own API key under that org.

Either way, each member runs the individual setup above with their key. Same account/org = shared assistants. Same repo = same assistant (matched by git remote URL).

```
Alice ──┐                              ┌── tribal remember "fix: use --no-lock"
        ├── same Backboard account ────┤
Bob   ──┘                              └── tribal recall "migration issues"
                                            → sees Alice's fix
```

### Per-Repo Override

If a specific repo needs its own config (different LLM, custom settings), run `tribal init` inside it:

```bash
cd special-project
tribal init                   # creates a project-specific tribal.yaml
```

**Config resolution order** (highest priority wins):
1. `./tribal.yaml` (CWD)
2. `<git-root>/tribal.yaml`
3. `~/.config/tribalmind/tribal.yaml` (global)

## Commands

### Memory

```bash
tribal remember "knowledge to store"       # LLM-parsed memory
tribal remember --raw "exact text"          # Store as-is, skip LLM
echo "piped input" | tribal remember        # Stdin support

tribal recall "search query"               # Semantic search
tribal recall --limit 5 "query"            # Limit results
tribal recall --list                       # Browse all memories (free)
tribal recall --all "auth token format"    # Search across ALL repos

tribal forget "outdated info"              # Search and delete
tribal forget --id mem_abc123              # Delete by ID
tribal forget --all --yes                  # Clear everything

tribal activity                            # View recent activity feed
tribal activity -a remember               # Filter by action
```

All memory commands accept **`--json`** for structured output.

### Project

```bash
tribal init                    # Set up project (API key + assistant)
tribal init --global           # User-level default for all repos
tribal init --api-key <key>    # Non-interactive / agent setup
tribal status                  # Show project info, memory count, config
tribal status --json           # Machine-readable status
```

### Agent Integration

Set up AI coding agents to automatically use TribalMind:

```bash
tribal setup-agents                         # Auto-detect or prompt
tribal setup-agents -a CLAUDE.md            # Just Claude Code
tribal setup-agents -a CLAUDE.md -a .cursorrules
tribal setup-agents --all                   # All supported agents
tribal setup-agents --list                  # Show supported agents
```

Writes a TribalMind usage snippet into agent instruction files so agents recall before working and remember after solving problems. Supported agents:

| File | Agent |
|---|---|
| `CLAUDE.md` | Claude Code |
| `.cursorrules` | Cursor |
| `.windsurfrules` | Windsurf |
| `.github/copilot-instructions.md` | GitHub Copilot |
| `AGENTS.md` | Generic convention |

### Configuration

```bash
tribal config set llm-provider openai       # Set a config value
tribal config set model-name gpt-4o
tribal config get llm-provider              # Read a single value
tribal config list                          # Show all resolved config (secrets redacted)
```

<details>
<summary>All config keys</summary>

`backboard-base-url` `llm-provider` `model-name` `project-assistant-id`

</details>

### Secrets

Secrets live in your OS keyring — never in plain-text files.

```bash
tribal config set-secret backboard-api-key          # Prompts for value
tribal config set-secret backboard-api-key -v <key> # Pass value directly
tribal config debug-key                             # Show masked API key for debugging
```

### Backboard Helpers

```bash
tribal config assistants            # List all Backboard assistants
tribal config clear-memory          # Wipe memories for the project assistant
tribal config clear-memory -a <id>  # Wipe memories for a specific assistant
```

### Upgrade

```bash
tribal upgrade    # Upgrade to the latest version from PyPI
tribal --version  # Show installed version
```

## Dashboard UI

TribalMind ships with a browser-based dashboard for exploring your assistants and knowledge base.

```bash
pip install 'tribalmind[ui]'
tribal ui
```

Opens `http://localhost:7484` in your browser. Use `--port` to change the port or `--no-browser` to suppress auto-open.

### Memory

A semantic knowledge base browser:

- **Pick an assistant** from the dropdown to load its memories
- **Semantic search** across all stored knowledge
- **Filter by category** — error, fix, context, upstream — with dynamic filter buttons
- Each memory card shows parsed tags: category, package, confidence %, trust score, and similarity
- Expand any card to see the raw encoded memory
- Delete individual memories or clear all at once

### Assistants

Browse all Backboard assistants on your account — see names, IDs, and creation dates.

## Architecture

```
tribal CLI (Typer + Rich)
  │
  ├── remember / recall / forget
  │     └── Backboard API (httpx async)
  │           ├── LLM parsing (structured memory encoding)
  │           ├── Vector search (semantic recall)
  │           └── Memory CRUD
  │
  ├── config / init / status
  │     ├── tribal.yaml (project settings)
  │     ├── pydantic-settings (resolution)
  │     └── keyring (secrets)
  │
  └── ui → FastAPI + React dashboard
        └── Backboard API proxy → assistants, memory browser
```

[**Backboard**](https://docs.backboard.io/) provides the unified backend: vector + relational storage for memories, 2200+ LLM models, and semantic search across your knowledge base.

## Project Structure

```
lib/tribalmind/
  cli/        CLI commands (Typer)
  config/     Settings (pydantic-settings + YAML) and keyring credentials
  backboard/  Async HTTP client, memory encoding/parsing, assistant management
  web/        FastAPI server + Backboard API proxy

ui/           React + Tailwind + shadcn dashboard frontend
```

## Contributing

```bash
# Clone and install with dev + ui dependencies
git clone https://github.com/zachary-nguyen/TribalMind.git
cd TribalMind
pip install -e ".[dev,ui]"

# Run tests
pytest

# Lint
ruff check lib/ tests/
```

### Commit Convention

This project uses [Conventional Commits](https://www.conventionalcommits.org/) for automatic semantic versioning. Every push to `master` triggers CI and, if warranted, an automatic release to [PyPI](https://pypi.org/project/tribalmind/).

| Commit prefix | Version bump | Example |
|---|---|---|
| `fix:` | patch (0.1.0 → 0.1.1) | `fix: handle missing config` |
| `feat:` | minor (0.1.0 → 0.2.0) | `feat: add memory search to UI` |
| `feat!:` / `BREAKING CHANGE:` | major (0.1.0 → 1.0.0) | `feat!: rename config keys` |
| `chore:`, `docs:`, `ci:`, `test:` | no release | `chore: update deps` |

### Release Flow

```
git commit -m "feat: add new command"
git push origin master
  → CI runs (lint + tests)
  → Semantic Release detects releasable commit
  → Bumps version, builds wheel with bundled UI
  → Publishes to PyPI
  → Creates GitHub release + changelog
```

## License

MIT
