# CLAUDE.md — cld_ai

Guidance for Claude Code when working in this repository. These instructions
OVERRIDE default behavior; follow them exactly.

## What this is

An Ansible collection wrapping the OpenShift **Assisted Installer** API.

- Spec: Swagger 2.0, served at
  `https://api.openshift.com/api/assisted-install/v2/openapi`
- Base URL: `https://api.openshift.com/api/assisted-install/v2`
- Auth: `Authorization` apiKey header (`userAuth` in the spec) — i.e. `Bearer <token>`
- FQCN: `openshift_lab.assisted_installer` (must match the directory path
  `ansible_collections/openshift_lab/assisted_installer/`)

Scope, phasing, and the per-resource idempotency model are in **DESIGN.md** —
read it before adding a module.

---

## Design considerations (WHAT the collection is / how it behaves)

1. **Idempotency is per-resource — classify first (see DESIGN.md):**
   - *Read-only / info* (`openshift_version_info`, `support_level_info`,
     `supported_operator_info`, `event_info`): never changes state → always
     `changed=False`; set `supports_check_mode=True` trivially.
   - *State-based / declarative* (`cluster`, `infra_env`): `state: present/absent`;
     observe (GET) → compare → reconcile (POST/PATCH/DELETE); `changed` reflects a
     REAL change; deleting an already-absent resource is `changed=False`, not a failure;
     a create MUST set `changed=True`.
   - *RPC-style actions* (`cluster_action`, `host_action` — verbs like `install`,
     `reset`, `cancel`, `bind`, `unbind` via an `action:` param):
     guard on current status before acting (don't re-`install` an installing cluster).
2. **Interface = contract.** Arguments, `state` shape, and RETURN values are the
   public API. Design them before coding; keep them stable.
3. **Check mode** is part of the contract: `supports_check_mode=True`, and never
   mutate when `module.check_mode`.
4. **Secrets are declared, not incidental:** any token / `pull_secret` / key is a
   secret param.

## Implementation considerations (HOW it is coded)

5. **HTTP via `ansible.module_utils.urls.fetch_url`** — never `requests`
   (no external dependency, passes sanity, works in execution environments).
6. **Share cross-cutting code in `plugins/module_utils/`** — auth/token resolution,
   URL building, and a thin request wrapper. Do NOT copy-paste headers / base-URL
   constants / query-param loops into each module.
7. **Every API call sets a timeout** (expose it as a module param; default sane).
8. **Fail fast on auth:** if no token resolves, `module.fail_json(msg=...)` with a
   clear message — never send `Bearer None`.
9. **Finish only** via `module.exit_json(...)` / `module.fail_json(msg=...)`.
   Never raise raw exceptions or `sys.exit`.
10. **Secrets in code:** `no_log=True` on secret args; never echo response bodies
    that may contain secrets.

## Module authoring rules (prevent real sanity failures)

- **Naming (publishable convention — see DESIGN.md §5):** managed resources are
  **singular** (`cluster`, `infra_env`, `host`); read-only modules are **singular
  + `_info`** (`openshift_version_info`, `cluster_info`); RPC-style actions are
  grouped per resource as `*_action` with an `action:` choices param
  (`cluster_action`, `host_action`) — not one module per verb.
- **GPLv3+ header** in the first 20 lines of every file in `plugins/modules/`
  (we chose GPLv3 — do NOT suppress `missing-gplv3-license` in the ignore files).
- **All three doc blocks** — `DOCUMENTATION`, `EXAMPLES`, `RETURN`. `options:` must
  match `argument_spec` EXACTLY; `RETURN` must match what the code returns;
  `EXAMPLES` may only use real parameters **and must be thorough for the module's
  kind (see DESIGN.md §4)**:
  - *info:* a basic query, a filtered query (if it has filter params), and
    register-the-result-then-use it (e.g. a follow-up `debug`).
  - *state:* `present` (create), an update that changes a field, `absent`
    (delete), a check-mode (`-C`) example, and a comment noting a 2nd identical
    run is `changed=False`.
  - *action:* the representative action verbs, each showing the status
    precondition it guards on.
  - *all kinds:* every task has a meaningful `name:`; tokens/secrets come from a
    var or env, never a literal.
  - *Enforcement:* **validity** (real params, parseable YAML) is a hard
    `ansible-test sanity` gate; **thoroughness** is a review-time expectation
    that sanity does NOT check — scale it to the module's complexity (a trivial
    module needs less than `cluster`), and don't duplicate integration coverage.
- **Author**: `- Name (@githubhandle)` (bare names fail sanity).
- Validate params/shapes against the OpenAPI spec — it is the source of truth.

## Project / governance

- **License:** GPL-3.0-or-later (module headers + `galaxy.yml` + LICENSE all agree).
- **ansible-core support matrix** must stay in sync across three places:
  `meta/runtime.yml` (`requires_ansible`), `.github/workflows/ci.yml` (matrix),
  and `tests/sanity/ignore-*.txt` (one file per supported version).
- **Testing posture — units prove logic, integration proves wiring:**
  - **Units (every module, always):** API **mocked** at `fetch_url` — never live
    calls, never real credentials in CI. Required cases: create/act, idempotency
    (2nd run `changed=False`), check-mode, fail-fast on no token, non-2xx →
    `fail_json`. Units own URL/auth/query-encoding/error-mapping — do NOT
    re-cover those in integration.
  - **Integration (selective — see DESIGN.md §7):** add it for **state-based**
    (`cluster`, `infra_env`) and **action** (`cluster_action`, `host_action`)
    modules to prove the multi-step lifecycle across real playbook runs
    (`present → present(no-op) → absent → absent(no-op)`; action guard-on-status).
    **info** modules don't need it (units suffice). Integration NEVER hits
    `api.openshift.com`: it runs against a **local mock server** via a `base_url`
    override, gated so it cannot reach prod. Add the `tests/integration/` targets
    and the CI `Integration` job **when the first state-based module lands**, not
    before.
  - **Coverage (≥90% enforced):** `./run.sh --check` runs `ansible-test units --coverage`
    and enforces a 90% minimum (total coverage, with branch coverage tracked).
    Shows missing lines and partially-covered branches. Branch coverage catches
    untested conditional paths (e.g., a check-mode branch that never fires).
    Execution-based coverage complements CodeRabbit's pattern-based review.
- **Secrets never committed** (tokens, `pull_secret`) — see `.gitignore`.

## Before you commit: verification checklist

Run through this **BEFORE** marking your PR ready. This catches what automated
tools might miss:

### 1. Documentation completeness
- [ ] **RETURN documents EVERY field from `exit_json`** — Run your module, capture
  the actual result dict, compare it to your RETURN block. Don't document only
  the domain object; include `changed`, `msg`, and any other fields you return.
- [ ] **EXAMPLES cover all major paths** — Not just the happy path. Include:
  - *info*: basic query + filtered query + register/debug usage
  - *state*: create, update (drift), delete, check-mode, comment that 2nd run is `changed=false`
  - *action*: each action verb + the status it guards on
- [ ] **Author format is valid** — `author:\n  - Name (@githubhandle)` (bare names fail sanity)

### 2. API contract verification
- [ ] **Read the OpenAPI spec** for edge cases you might have missed. Don't assume;
  look it up in `docs/api-endpoint-map.md` and the upstream spec.
- [ ] **For actions: verify valid state transitions** — Can you `bind` a host that's
  already bound to a different cluster? Can you `install` when status is `error`?
  Query the API docs to confirm. For executable checks, use a local mock server
  through `base_url`; never contact the production API. **Don't guess.**
- [ ] **For state: test immutable fields** — What happens if you PATCH `cpu_architecture`
  on an existing infra-env? The module should fail before the write, not send
  a request that the API rejects.
- [ ] **Write-only fields are excluded from drift** — `pull_secret`, keys, tokens:
  send on create, never compare (API doesn't return them).

### 3. Test pattern verification
- [ ] **Idempotency tests run the action TWICE** — Not "start already in target state."
  The test should: state A → action → state B → **same action again** → still B
  (changed=False, no second POST). See `test_bind_twice_second_is_noop` in
  `test_host_action.py` as the reference.
- [ ] **Check-mode tests verify NO write** — Count HTTP calls: should be only GET,
  never POST/PATCH/DELETE when `check_mode=True`.
- [ ] **Safety guards test the REAL error** — If testing "install when not bound,"
  the mock host must actually have `cluster_id=None`. Don't test "close enough"
  conditions that happen to trigger a different error.
- [ ] **All 5 test categories covered** — Lifecycle, idempotency, check-mode,
  safety guards, API contract (see DESIGN.md §7 and `docs/testing-cheat-sheet.md`).

### 4. Run the verification suite
```bash
./run.sh --check    # Must pass: build, sanity, units, coverage ≥90%
```

If sanity or units fail, **read the error**. If coverage is <90%, **add tests for
the missing branches** (not just lines). The coverage report shows you exactly
which conditional paths are untested.

This checklist prevents "CodeRabbit caught what we missed" situations. The automated
tools (sanity, units, coverage) verify structure and execution; this checklist
verifies **correctness against the API contract and idempotency model**.

## Container workflow

Everything runs in a container (Docker or Podman) — no host deps. Verify with:

```bash
./run.sh --check     # collection build + sanity + units + coverage report (≥90%)
./run.sh --full      # also the collection install round-trip
```

Inside the container, `ansible-test` runs WITHOUT `--docker` (already containerized);
CI uses `--docker`. Coverage report shows missing lines and partial branches.

## Git workflow

**NEVER commit directly to `main`.** All changes must go through feature branches and PRs.

Before every commit:
1. **Check your branch:** `git branch --show-current`
2. **If it says `main`:** STOP. Create a feature branch first:
   ```bash
   git checkout -b <type>/<description>
   # Examples:
   #   git checkout -b feature/add-support-level-info
   #   git checkout -b docs/testing-guide
   #   git checkout -b fix/token-validation
   ```
3. **Then commit:** `git commit -m "..."`

**Install the pre-commit hook** to prevent accidents:
```bash
./scripts/install-hooks.sh
```

The hook blocks commits to `main` locally. Branch protection blocks pushes to `main`
remotely. Together they enforce the PR-only workflow.

## Golden rule

Keep `main` green: `ansible-test sanity`, `ansible-test units`, and **coverage ≥90%**
must pass before merge (`./run.sh --check`). This must remain a buildable, installable
collection (`ansible-galaxy collection build`).

## Fastest way to add a module

Use the bundled skill: `/new-ansible-module` (generic scaffold) or
`/new-ai-endpoint-module` (this API's base URL, auth, and GET→PATCH idempotency).
