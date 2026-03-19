# CHANGELOG

<!-- version list -->

## v2.10.0 (2026-03-19)

### Features

- Show source project on tribal recall --all results
  ([`be56e8c`](https://github.com/zachary-nguyen/TribalMind/commit/be56e8c12a1e36271059272ea695231b07b7165b))


## v2.9.0 (2026-03-17)

### Bug Fixes

- Avoid curly-brace template errors in prompts and harden LLM response parsing
  ([`7bdc26f`](https://github.com/zachary-nguyen/TribalMind/commit/7bdc26f618907abf44cc3e90cde9039756bd6e48))

### Features

- Add workflow category for storing multi-step processes
  ([`d17f682`](https://github.com/zachary-nguyen/TribalMind/commit/d17f682b923ee54c2a383bad4bbed43ca34afb13))


## v2.8.0 (2026-03-17)

### Features

- Add activity log page to web dashboard
  ([`10669bf`](https://github.com/zachary-nguyen/TribalMind/commit/10669bf9a9d0071491e26efc0b1ed1a700552dfe))

- Add assistant filter to activity log and fix lint issues
  ([`a477eca`](https://github.com/zachary-nguyen/TribalMind/commit/a477eca761f73c04a892a0d8fa965c4a0bb324bc))

- Show target assistant name in activity log
  ([`5307f43`](https://github.com/zachary-nguyen/TribalMind/commit/5307f431fef37aa64451a6d4e6576381cea75f7f))


## v2.7.0 (2026-03-17)

### Bug Fixes

- Convert Backboard distance score to similarity in recall
  ([`2d81be4`](https://github.com/zachary-nguyen/TribalMind/commit/2d81be48658868627c2b7040d90e3e88907e405b))

### Features

- Add --category filter to tribal recall
  ([`e1e3c79`](https://github.com/zachary-nguyen/TribalMind/commit/e1e3c79b0cf0648d6ff34f9f9ba22f25f1928edb))


## v2.6.0 (2026-03-17)

### Bug Fixes

- Add missing shell completion input to init tests
  ([`d1e7e4a`](https://github.com/zachary-nguyen/TribalMind/commit/d1e7e4a2f33b9dedcade19b30f1476bb8ac9ed5d))

- Shorten test comments to satisfy line length lint
  ([`31b2fac`](https://github.com/zachary-nguyen/TribalMind/commit/31b2fac886a3404d02078d65d7a44ab23d51dd2e))

### Features

- Enable and document tab-completion for CLI commands
  ([`7310c20`](https://github.com/zachary-nguyen/TribalMind/commit/7310c20c2388f9afafe59829803f12b6505c9979))


## v2.5.0 (2026-03-17)

### Features

- Auto-update CLAUDE.md and agents.md on tribal upgrade
  ([`dc3fa8d`](https://github.com/zachary-nguyen/TribalMind/commit/dc3fa8dbb963d1a292845cc5a7255ddb7a181c33))


## v2.4.1 (2026-03-17)

### Bug Fixes

- Improve agent prompt reliability for tribal recall/remember
  ([`a2fcda8`](https://github.com/zachary-nguyen/TribalMind/commit/a2fcda8d1b85a3725c1cc1efd943154ea44d9beb))


## v2.4.0 (2026-03-16)

### Features

- Include fastapi and uvicorn in core dependencies
  ([`97d28fe`](https://github.com/zachary-nguyen/TribalMind/commit/97d28fe5c88475f9e71350cdffdf18d765ea0069))


## v2.3.2 (2026-03-16)

### Bug Fixes

- Catch all keyring errors, not just NoKeyringError
  ([`c5febef`](https://github.com/zachary-nguyen/TribalMind/commit/c5febef9336c1d9f8f757ba50e225c5bcc0c12c7))


## v2.3.1 (2026-03-16)

### Bug Fixes

- Gracefully handle missing keyring backend on Linux
  ([`f2302ea`](https://github.com/zachary-nguyen/TribalMind/commit/f2302ea1041d173105495dce77cb70ddf54a42e8))


## v2.3.0 (2026-03-16)

### Features

- Move project config to .tribal/config.yaml and auto-gitignore
  ([`c647f6f`](https://github.com/zachary-nguyen/TribalMind/commit/c647f6f73c289e191982b63109b361c27ef2c11e))


## v2.2.1 (2026-03-16)

### Bug Fixes

- Warn user when running tribal init outside a git repo
  ([`028eeed`](https://github.com/zachary-nguyen/TribalMind/commit/028eeed71efad106904c003325f4d01b8cf35a15))


## v2.2.0 (2026-03-16)

### Bug Fixes

- Sort imports in init_cmd.py
  ([`c0776b0`](https://github.com/zachary-nguyen/TribalMind/commit/c0776b0c8e374ad0aca780bdc00a8eaf445e46b3))

### Features

- Add interactive prompts, provider-specific agent snippets, and polished init flow
  ([`15ff1a0`](https://github.com/zachary-nguyen/TribalMind/commit/15ff1a0ddc30e6bb6494061f701e886644b6bb60))


## v2.1.1 (2026-03-15)

### Bug Fixes

- Check for index.html instead of just static dir existence
  ([`9ca17d6`](https://github.com/zachary-nguyen/TribalMind/commit/9ca17d69b893be47a56cb2b08765172502071beb))


## v2.1.0 (2026-03-15)

### Bug Fixes

- Auto-build frontend when `tribal ui` static assets are missing
  ([`d9ecbc2`](https://github.com/zachary-nguyen/TribalMind/commit/d9ecbc2d1c94b84e33cbb308a4e1600aa12b36b8))

- Include frontend static assets in wheel build
  ([`1dfe084`](https://github.com/zachary-nguyen/TribalMind/commit/1dfe08451c1e3e236bec6ad0569a6aefd7100cfa))

- Let PSR commit and tag the version bump locally
  ([`315cafa`](https://github.com/zachary-nguyen/TribalMind/commit/315cafae9c06e7f52bbf12a9ee1b45161605ef89))

- Use shell=True on Windows for subprocess calls to pnpm/npm
  ([`08d96de`](https://github.com/zachary-nguyen/TribalMind/commit/08d96de2e87854b7431dabb673ec7b6546c2018d))

### Features

- Add cross-repo recall fallback to agent snippet prompt
  ([`de17dfc`](https://github.com/zachary-nguyen/TribalMind/commit/de17dfc6476777094ad80f02c216a0463854a2a7))


## v2.0.0 (2026-03-15)

### Bug Fixes

- Mock set_credential in test_init_api_error for CI
  ([`44847d0`](https://github.com/zachary-nguyen/TribalMind/commit/44847d06f339b01c2faf4d8f2aaedceee9727693))

### Features

- V2.0 stateless CLI architecture
  ([`1da1cb0`](https://github.com/zachary-nguyen/TribalMind/commit/1da1cb01738fd69d2cfcb7a5db20d6060f8ae54c))

### Breaking Changes

- Removed daemon, graph, hooks, upstream modules and all associated CLI commands. The CLI is now
  stateless — use `tribal remember` / `tribal recall` instead of the background agent.


## v1.6.0 (2026-03-15)

### Features

- V2.0.0 — stateless CLI architecture
  ([`62dcd74`](https://github.com/zachary-nguyen/TribalMind/commit/62dcd74540f3360861190e73474031b1b2908b70))


## v1.5.0 (2026-03-14)

### Features

- Update README and enhance CLI aesthetics
  ([`59507a8`](https://github.com/zachary-nguyen/TribalMind/commit/59507a84e706bfe84c20e06ad4b32fe48cd1aa71))


## v1.4.0 (2026-03-14)

### Features

- Add Backboard dashboard UI with assistants, threads, and memory views
  ([`f37e539`](https://github.com/zachary-nguyen/TribalMind/commit/f37e5390fe6c8b466f59228498646dc1aa3ed384))


## v1.3.0 (2026-03-14)

### Features

- Enhance configuration loading and command handling
  ([`ab5a64a`](https://github.com/zachary-nguyen/TribalMind/commit/ab5a64aa3baf3a88bebb509f30be6618ca625e7a))


## v1.2.0 (2026-03-14)


## v1.1.0 (2026-03-14)


## v1.0.0 (2026-03-14)

- Initial Release
