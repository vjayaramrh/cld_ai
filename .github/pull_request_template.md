<!--
Thanks for contributing to openshift_lab.assisted_installer.
Read CLAUDE.md (conventions) and DESIGN.md (scope, phasing, idempotency) first.
-->

## What & why

<!-- What does this change do, and why? Link any related issue. -->

## Module(s) touched

<!-- e.g. openshift_versions, clusters. Note the DESIGN.md §4 idempotency class:
     read-only / state-based (GET→PATCH) / RPC-action. -->

## Checklist

<!-- Tick everything that applies; explain anything left unticked. -->

- [ ] Idempotency pattern matches the resource class (DESIGN.md §4)
- [ ] HTTP goes through `plugins/module_utils/` (`fetch_url`) — no `requests`,
      no hand-built base URL / Authorization header
- [ ] Every API call has a timeout; auth fails fast (no `Bearer None`)
- [ ] Secrets use `no_log=True`; no tokens / pull secrets committed
- [ ] GPLv3+ header on new files in `plugins/modules/`
- [ ] `DOCUMENTATION` / `EXAMPLES` / `RETURN` present; `options:` matches
      `argument_spec` exactly; `author: - Name (@handle)`
- [ ] Unit tests (mock `fetch_url`): create/act, idempotency (2nd run
      `changed=False`), check-mode
- [ ] `meta/runtime.yml`, CI matrix, and `tests/sanity/ignore-*.txt` stay in sync
- [ ] `./run.sh --check` is green locally (build + sanity + units)
