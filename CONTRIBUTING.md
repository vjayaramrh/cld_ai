# Contributing

Thanks for contributing to `openshift_lab.assisted_installer`.

**New contributor?** Start with [docs/contributor-quick-start.md](docs/contributor-quick-start.md) for a 4-week tutorial and FAQ. This document is the official reference for requirements and workflow.

## Before you start

Read [CLAUDE.md](CLAUDE.md) (conventions) and [DESIGN.md](DESIGN.md) (scope,
phasing, per-resource idempotency). Every module must follow them.

New to how this repo is built and reviewed? Read
[docs/agentic-sdlc.md](docs/agentic-sdlc.md) — it explains the agent-assisted
workflow (source of truth, rules, executable gates) and how to contribute within
it.

**Claim your work first.** Modules are tracked as issues on the
[project board](https://github.com/users/vjayaramrh/projects/2) (one per module,
labelled `module`). **Assign the issue to yourself before you start** so two people
don't build the same module. No issue for what you want to add? Open one from
[`docs/api-endpoint-map.md`](docs/api-endpoint-map.md) (it maps every endpoint to
its pattern and phase), then claim it.

## Ground rules

- **Idempotency:** re-running a playbook must be safe — the second run should
  report `changed=false` when nothing actually changed. How you achieve that
  depends on the resource, so classify it (read-only / state-based / action) and
  implement the matching pattern (DESIGN.md §4).
- **HTTP:** use `ansible.module_utils.urls.fetch_url` via the shared helpers in
  `plugins/module_utils/` — never `requests`.
- **Secrets:** `no_log=True`; never commit tokens or pull secrets. Full
  secure-coding + testing practices are in [docs/security.md](docs/security.md)
  (to report a vulnerability, see [SECURITY.md](SECURITY.md)).
- **Docs:** `DOCUMENTATION`/`EXAMPLES`/`RETURN` must match the code and the spec.
- **GPLv3+ header** on every file in `plugins/modules/`.

## Contributing with Claude Code

Most modules here are written with [Claude Code](https://claude.com/claude-code),
and the repo is set up so it does the right thing by default:

- **CLAUDE.md is loaded automatically** — its conventions (idempotency pattern,
  `fetch_url` client, `no_log` secrets, GPLv3 header, doc-block rules) apply to
  every generation without you restating them.
- **Use the skills** to scaffold: `/new-ai-endpoint-module` (knows this API's base
  URL, auth, and the shared `plugins/module_utils/assisted_installer.py` client)
  or `/new-ansible-module` (generic). They pick the idempotency skeleton from the
  resource's classification.
- **EXAMPLES must be thorough for the module's kind**, not a single stub — a
  filtered query + register/debug for `_info`; present/update/absent + check-mode
  for state; each verb + its status guard for actions (CLAUDE.md, DESIGN.md §4).
  Review what Claude generates against these before you commit.
- **You own correctness.** Read the diff, run the checks below, and verify against
  the spec (`docs/api-endpoint-map.md` and the OpenAPI doc) — generated code is a
  starting point, not a merge-ready artifact.

## Testing (required)

Every module ships unit tests with the API **mocked** (patch `fetch_url`). Units
prove the *logic*; the required cases are in [DESIGN.md §7](DESIGN.md#7-testing-strategy--unit-vs-integration):
create/act, idempotency (2nd run `changed=False`), check-mode, fail-fast on a
missing token (zero HTTP calls), and non-2xx → `fail_json`. No live calls, no
credentials in CI.

**New to testing?** See [docs/testing-cheat-sheet.md](docs/testing-cheat-sheet.md) for quick reference patterns and examples.

**Integration tests are selective** — add them only for **state** and **action**
modules (to prove the multi-step lifecycle), and only against a local mock via a
`base_url` override, never `api.openshift.com`. `_info` modules need units only.
See DESIGN.md §7 for the matrix and the "when to build it" trigger.

**Coverage ≥90% is enforced** locally and in CI. Run the full check suite:

```bash
./run.sh --check     # builds, sanity, units, coverage report
```

Or individually:

```bash
ansible-test sanity
ansible-test units --coverage
ansible-test coverage report --show-missing
```

All must pass before opening a PR. Keep `meta/runtime.yml`, the CI matrix, and
`tests/sanity/ignore-*.txt` in sync when changing supported ansible-core versions.

## Manual verification against the live API

Automated tests never touch `api.openshift.com`. Before **and** after a module
merges, sanity-check it by hand against the real service with an ad-hoc playbook:

1. Build and install the collection locally:
   ```bash
   ansible-galaxy collection build --force
   ansible-galaxy collection install ./openshift_lab-assisted_installer-*.tar.gz --force
   ```
2. Export a short-lived token — **never** put it in the playbook or a committed
   file:
   ```bash
   export AI_API_TOKEN="$(< /path/to/your/token)"   # or paste; keep it ephemeral
   ```
3. Run a small playbook exercising the module (info: query; state: run twice and
   confirm the 2nd run is `changed=false`; action: check the status guard):
   ```bash
   ansible-playbook adhoc.yml -v          # add -C first to confirm check-mode
   ```

- **Before merge:** confirm the happy path and idempotency behave against real
  responses (mocks can drift from the API).
- **After merge:** re-run once from a clean install of the merged collection to
  catch packaging issues the branch build hid.

Do **not** commit the ad-hoc playbook if it contains anything environment- or
secret-specific, and never paste raw response bodies (they may contain secrets)
into issues or PRs. The module's `EXAMPLES` block is the canonical, committed
usage reference — keep throwaway playbooks out of the PR.

## Linting

`yamllint` and `ansible-lint` run in CI (`.github/workflows/lint.yml`) and must
be green. Run them locally the same way via pre-commit:

```bash
pipx install pre-commit   # or: pip install pre-commit
pre-commit install        # run automatically on git commit
pre-commit run --all-files
```

## Pull requests

- `main` is protected: PRs require passing CI (sanity, units, lint) and one
  approving review before merge. Fill in `.github/pull_request_template.md`.
- **Coverage ≥90%** verified locally via `./run.sh --check` before opening PR.
- **Link the PR to its module issue** with `Closes #<n>` — merging then closes the
  issue and the board moves it to **Done** automatically.
- [CodeRabbit](https://github.com/apps/coderabbitai) reviews PRs automatically
  (config in `.coderabbit.yaml`); treat its comments as advisory.
