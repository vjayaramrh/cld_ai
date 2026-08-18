# Contributing

Thanks for contributing to `openshift_lab.assisted_installer`.

## Before you start

Read [CLAUDE.md](CLAUDE.md) (conventions) and [DESIGN.md](DESIGN.md) (scope,
phasing, per-resource idempotency). Every module must follow them.

## Ground rules

- **Idempotency:** classify the resource (read-only / state-based / action) and
  implement the matching pattern (DESIGN.md §4).
- **HTTP:** use `ansible.module_utils.urls.fetch_url` via the shared helpers in
  `plugins/module_utils/` — never `requests`.
- **Secrets:** `no_log=True`; never commit tokens or pull secrets.
- **Docs:** `DOCUMENTATION`/`EXAMPLES`/`RETURN` must match the code and the spec.
- **GPLv3+ header** on every file in `plugins/modules/`.

## Testing (required)

Every module ships unit tests with the API **mocked** (patch `fetch_url`) covering
create/act, idempotency (2nd run `changed=False`), and check-mode. No live calls,
no credentials in CI.

```bash
ansible-test sanity
ansible-test units
```

Both must pass before opening a PR. Keep `meta/runtime.yml`, the CI matrix, and
`tests/sanity/ignore-*.txt` in sync when changing supported ansible-core versions.

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
- [CodeRabbit](https://github.com/apps/coderabbitai) reviews PRs automatically
  (config in `.coderabbit.yaml`); treat its comments as advisory.
