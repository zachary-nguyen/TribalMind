<p align="center">
  <img src="assets/logo.svg" alt="TribalMind" width="180"/>
  <h1 align="center">TribalMind</h1>
  <p align="center">
    <strong>Your team's shared error memory — so nobody debugs the same thing twice.</strong>
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

TribalMind is a **federated developer knowledge agent** that runs quietly in the background, watches your terminal for errors, and builds a shared knowledge base of fixes across your team. Think of it as muscle memory for your entire engineering org — powered by [Backboard](https://docs.backboard.io/).

> **Hit an obscure error at 2 AM?** If anyone on your team has seen it before, TribalMind already knows the fix.

## How It Works

```
  You type a command
        │
        ▼
  Shell hook captures it ──► Daemon processes the error
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
              Local history    Team knowledge    GitHub issues
                    │                │                │
                    └────────────────┼────────────────┘
                                     ▼
                          Fix suggested + stored
                                     │
                                     ▼
                        Promoted to team when trusted
```

1. **Shell hooks** silently capture commands and exit codes as you work
2. A **background daemon** processes errors through a LangGraph state machine
3. Errors are matched against **local history**, **team knowledge**, and **upstream GitHub issues**
4. Validated fixes are stored in [Backboard](https://docs.backboard.io/) and promoted to your team when trust thresholds are met

## Quick Start

Get up and running in under a minute:

```bash
pip install tribalmind
tribal install
tribal start
```

That's it. `tribal install` walks you through everything:

1. **Backboard API key** — prompts for your key and stores it securely in your system keyring
2. **Project assistant** — creates a Backboard assistant scoped to your project
3. **Shell hooks** — detects your shell (bash, zsh, or PowerShell) and installs the appropriate hook
4. **Watch directories** — lets you pick which directories to monitor

## Commands

### Daemon

```bash
tribal start               # Start the background daemon
tribal start --foreground  # Run in foreground (useful for debugging)
tribal stop                # Stop the daemon
tribal status              # Show daemon status (running/stopped, PID, health)
```

### Watched Directories

TribalMind only monitors commands run inside directories you explicitly configure — nothing is watched by default.

```bash
tribal watch add                   # Interactive directory picker
tribal watch add ~/dev/my-project  # Add a specific path
tribal watch list                  # Show all watched directories
tribal watch remove ~/dev/project  # Stop watching a directory
```

### Configuration

```bash
tribal config set llm-provider openai       # Set a config value
tribal config set model-name gpt-4o
tribal config get llm-provider              # Read a single value
tribal config list                          # Show all resolved config (secrets redacted)
```

<details>
<summary>All config keys</summary>

`backboard-base-url` `llm-provider` `model-name` `embedding-provider` `embedding-model` `daemon-host` `daemon-port` `team-sharing-enabled` `org-assistant-id` `project-assistant-id`

</details>

### Secrets

Secrets live in your OS keyring — never in plain-text files.

```bash
tribal config set-secret backboard-api-key        # Prompts for value
tribal config set-secret github-token -v <token>   # Pass value directly
tribal config debug-key                            # Show masked API key for debugging
```

### Team Sharing

```bash
tribal enable-team-sharing --org-id <assistant-id>
```

Links your project to an organization-wide Backboard assistant so validated fixes flow across your entire team.

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

TribalMind ships with a browser-based dashboard for full visibility into your daemon, assistants, threads, and knowledge base.

```bash
pip install 'tribalmind[ui]'
tribal ui
```

Opens `http://localhost:7484` in your browser. Use `--port` to change the port or `--no-browser` to suppress auto-open.

### Logs

Real-time daemon log streaming via SSE. Filter by level (DEBUG / INFO / WARNING / ERROR), search by message or module, toggle auto-scroll, or clear the buffer.

### Assistants

Browse all Backboard assistants on your account — see names, IDs, embedding models, and creation dates. Jump straight to an assistant's memory or delete it entirely.

### Threads

Inspect conversation threads with expandable message history. Each message is tagged with its role (user / assistant) for easy scanning.

### Memory

The star of the show — a semantic knowledge base browser:

- **Pick an assistant** from the dropdown to load its memories
- **Semantic search** across all stored knowledge
- **Filter by category** — error, fix, context, upstream — with dynamic filter buttons
- Each memory card shows parsed tags: category, package, confidence %, trust score, and similarity to your query
- Error text in red, fix suggestions in green — scan in seconds
- Expand any card to see the raw encoded memory
- Delete individual memories or clear all at once

## Architecture

```
Shell Hook (bash/zsh/powershell)
  │  sends JSON over TCP
  ▼
Daemon (asyncio TCP server on localhost:7483)
  │  writes structured logs
  ▼
LangGraph State Machine
  ├── Monitor   → parse stderr, classify errors, generate fingerprints
  ├── Context   → search local/team memories + GitHub upstream
  ├── Inference → suggest fixes (via Backboard LLM)
  ├── Promotion → trust scoring, local → global knowledge promotion
  └── UI        → Rich terminal insight boxes

Dashboard (FastAPI + React on localhost:7484)
  ├── SSE stream from daemon log → live log viewer
  └── Backboard API proxy → assistants, threads, memory browser
```

[**Backboard**](https://docs.backboard.io/) provides the unified backend: vector + relational storage for memories, 2200+ LLM models, and semantic search across your knowledge base.

## Project Structure

```
lib/tribalmind/
  cli/        CLI commands (Typer)
  config/     Settings (pydantic-settings + YAML) and keyring credentials
  backboard/  Async HTTP client for the Backboard API
  graph/      LangGraph state machine (monitor, context, inference, promotion, ui)
  daemon/     Asyncio TCP server and IPC protocol
  hooks/      Shell hooks for bash, zsh, and PowerShell
  upstream/   GitHub integration for issue/release monitoring
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
| `fix:` | patch (0.1.0 → 0.1.1) | `fix: handle missing watch_dirs` |
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
