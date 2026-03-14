# TribalMind

[![CI](https://github.com/zachary-nguyen/TribalMind/actions/workflows/ci.yml/badge.svg)](https://github.com/zachary-nguyen/TribalMind/actions/workflows/ci.yml)
[![Release](https://github.com/zachary-nguyen/TribalMind/actions/workflows/release.yml/badge.svg)](https://github.com/zachary-nguyen/TribalMind/actions/workflows/release.yml)
[![PyPI](https://img.shields.io/pypi/v/tribalmind)](https://pypi.org/project/tribalmind/)

Federated Developer Knowledge Agent — an autonomous, background-running agent that observes terminal activity, correlates local errors with upstream library health, and shares validated fixes across your team.

## How It Works

1. **Shell hooks** capture commands and exit codes as you work
2. A **background daemon** processes errors through a LangGraph state machine
3. Errors are matched against **local history**, **team knowledge**, and **upstream GitHub issues**
4. Validated fixes are stored in [Backboard](https://docs.backboard.io/) and promoted to your team when trust thresholds are met

## Installation

```bash
pip install tribalmind
tribal install
```

`tribal install` will:
- Prompt for your Backboard API key (stored in your system keyring)
- Detect your shell (bash, zsh, or PowerShell) and install the appropriate hook
- Prompt for directories to monitor

## Usage

```bash
# Start the background daemon
tribal start

# Check daemon status
tribal status

# Stop the daemon
tribal stop

# Enable team-wide knowledge sharing
tribal enable-team-sharing --org-id <your-org-assistant-id>
```

### Watched Directories

TribalMind only monitors commands run inside directories you explicitly configure. Nothing is monitored by default.

```bash
# Add current directory to the watch list
tribal watch add

# Add a specific path
tribal watch add ~/dev/my-project

# See what's being watched
tribal watch list

# Remove a directory
tribal watch remove ~/dev/my-project
```

### Configuration

```bash
# Set a config value (writes to tribal.yaml)
tribal config set llm-provider openai
tribal config set model-name gpt-4o

# Store secrets in the system keyring
tribal config set-secret backboard-api-key
tribal config set-secret github-token

# View all resolved configuration
tribal config list
```

Copy `tribal.yaml.example` to `tribal.yaml` in your project root to customize settings. Values can also be set via `TRIBAL_*` environment variables.

## Live Log UI

A browser-based log viewer streams daemon activity in real time.

```bash
# Install UI dependencies
pip install 'tribalmind[ui]'

# Launch (opens browser automatically)
tribal ui
```

`tribal ui` opens your browser automatically. Use `--no-browser` to suppress this, or `--port` to change the port.

## Architecture

```
Shell Hook (bash/zsh/powershell)
  │  sends JSON over TCP
  ▼
Daemon (asyncio TCP server on localhost:7483)
  │  writes logs to ~/Library/Application Support/tribalmind/daemon.log
  ▼
LangGraph State Machine
  ├── Monitor   → parse stderr, classify errors, generate fingerprints
  ├── Context   → search local/team memories + GitHub upstream
  ├── Inference → suggest fixes (via Backboard LLM)
  ├── Promotion → trust scoring, local → global knowledge promotion
  └── UI        → Rich terminal insight boxes

Live Log UI (FastAPI + React on localhost:7484)
  └── SSE stream from daemon log file → browser log viewer
```

**Backboard** provides the unified backend: vector + relational storage for memories, 2200+ LLM models, and semantic search across your knowledge base.

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check lib/ tests/
```

### Commit Convention

This project uses [Conventional Commits](https://www.conventionalcommits.org/) for automatic semantic versioning. Every push to `master` is evaluated and a release is created automatically if the commits warrant one.

| Commit prefix | Example | Version bump |
|---|---|---|
| `fix:` | `fix: handle missing watch_dirs` | patch `0.1.0 → 0.1.1` |
| `feat:` | `feat: add log export command` | minor `0.1.0 → 0.2.0` |
| `feat!:` or `BREAKING CHANGE:` | `feat!: rename config keys` | major `0.1.0 → 1.0.0` |
| `chore:`, `docs:`, `ci:`, `test:` | `chore: update deps` | no release |

### Release Flow

```
git commit -m "feat: add new command"
git push origin master
  → CI runs (lint + tests)
  → PSR detects releasable commit
  → bumps version in pyproject.toml
  → builds wheel with bundled UI
  → publishes to PyPI
  → creates GitHub release + CHANGELOG
```

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
  web/        FastAPI server for the live log UI

ui/           React + shadcn log viewer frontend
```

## License

MIT
