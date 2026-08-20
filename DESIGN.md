# DESIGN.md — cld_ai

Design notes for the `openshift_lab.assisted_installer` collection. This captures
the decisions made *before* implementation so the coding sessions stay consistent.
Code-level conventions live in [CLAUDE.md](CLAUDE.md).

## 1. How to read the decisions: three kinds of consideration

| Kind | Question it answers | Where it lives | Examples |
|------|--------------------|----------------|----------|
| **Design** | *What* is it / how does it behave? | this file + CLAUDE.md | namespace/FQCN, scope & phasing, per-resource idempotency, module interface, check-mode |
| **Implementation** | *How* is it coded? | CLAUDE.md | `fetch_url` client, shared `module_utils`, timeouts, fail-fast auth, error handling |
| **Project / governance** | How is it governed? | config files | license, ansible-core support matrix, testing posture, CI, repo hygiene |

The design/implementation line is intentionally fuzzy (e.g. "shared `module_utils`
client" is architectural but realized in code) — the table is a guide, not a law.

## 2. Identity

- **FQCN:** `openshift_lab.assisted_installer`.
- **Why `openshift_lab`, not `openshift`:** `openshift` is a claimed/reserved
  Galaxy namespace (Red Hat ships `redhat.openshift`); using it can't be published
  and misleadingly implies an official collection. `openshift_lab` is clearly a
  personal/lab namespace and is legal (lowercase, letters/digits/underscores).

## 3. Scope & phasing

The **API** is `v2` (the `/v2/` path). These phases are *collection release
milestones*, not API versions.

### Phase 1 (`1.0.0`) — solid, tested, idempotent foundation
- Read-only info modules: `openshift_version_info`, `support_level_info`,
  `supported_operator_info`
- Declarative CRUD done properly: `cluster`, `infra_env`
  (idempotent create/update/delete via GET → PATCH), each paired with a
  read-only `cluster_info` / `infra_env_info`

### Phase 2 (`2.0.0`+) — the install lifecycle
- Host management: `host` / `host_info` (register/update/deregister) plus
  `host_action` (bind, unbind, install, reset)
- Cluster actions: `cluster_action` (install, reset, cancel,
  complete-installation, allow-add-hosts, allow-add-workers)
- Download/info helpers: ISO URL, credentials / kubeconfig

Ship Phase 1 correct and green before starting Phase 2.

## 4. Per-resource idempotency model

Idempotency is **not** one recipe applied uniformly. Classify each endpoint:

| Pattern | Resources | Behavior |
|---------|-----------|----------|
| **Read-only / info** | `openshift_version_info`, `support_level_info`, `supported_operator_info`, `event_info` | Never changes state → always `changed=False`. `supports_check_mode=True` for free. |
| **State-based (declarative)** | `cluster`, `infra_env` | `state: present/absent`. GET by name/id → observe; create if missing; PATCH if drifted; delete if present. `changed` = real change. Delete of already-absent = `changed=False`. |
| **RPC-style actions** | `cluster_action`, `host_action` (Phase 2) | Verbs, not desired state — cannot "PATCH to converge." Idempotency = check current status *first* and no-op if already in the target state. |

The Assisted Installer API is designed for the state-based pattern: it exposes
`GET` (list + by-id) and `PATCH` for both `clusters` and `infra-envs`, so
observe→compare→act maps directly onto real endpoints.

## 5. Module naming convention

Names follow Ansible's **published** module conventions so the collection is
Galaxy / Automation-Hub publishable and reads the way Ansible users expect.

- **Managed resources use the singular** (`cluster`, `infra_env`, `host`),
  driven by `state: present/absent`. `cluster: {state: present}` reads correctly;
  a plural `clusters` managing one resource does not.
- **Read-only modules end in `_info` and are singular** — required by the module
  dev guide (info modules MUST be named `<something>_info`, singular, returning
  via the normal result dict, not `ansible_facts`). This covers both queries on
  managed resources (`cluster_info`, `infra_env_info`, `host_info`) and catalog
  lookups (`openshift_version_info`, `support_level_info`,
  `supported_operator_info`, `component_version_info`, `operator_bundle_info`,
  `release_source_info`, `managed_domain_info`, `event_info`). An `_info` module
  that returns a *list* is idiomatic (cf. `kubernetes.core.k8s_info`).
- **RPC-style actions are grouped per resource** into one `*_action` module with
  an `action:` choices param (`cluster_action`, `host_action`) rather than one
  module per verb — the "guard on current status" logic lives in one place and
  the valid verbs self-document via `choices`. Precedent: `ansible.builtin.service`
  folds the imperative `restarted` / `reloaded` into a single module.

References: Ansible module dev guide (`developing_modules_general`,
`developing_modules_best_practices`); real-world examples that follow this scheme —
amazon.aws (`ec2_instance` + `ec2_instance_info`), kubernetes.core (`k8s` +
`k8s_info`), redhat.openshift / community.okd (all singular).

## 6. Key decisions locked in

- **HTTP client:** `fetch_url` (dependency-free, sanity-clean, EE-friendly).
- **License:** GPL-3.0-or-later — GPLv3 headers on module files (the Ansible norm;
  keeps `validate-modules` green without ignore entries).
- **Secrets:** module params with `no_log=True` (and/or env), documented
  consistently; never committed.
- **ansible-core matrix:** `requires_ansible >= 2.17`; CI tests stable-2.17,
  stable-2.18, stable-2.19, and `devel`; sanity ignore files exist per supported
  stable version and stay in sync.
- **Testing:** units always (API mocked); integration selectively — the
  unit/integration mix is defined in [§7](#7-testing-strategy--unit-vs-integration).
  No live calls or credentials in CI, ever.

## 7. Testing strategy — unit vs. integration

**Principle: units prove the *logic*; integration proves the *wiring and the
multi-step lifecycle*.** Both mock the network — the API is never called for real.

### Units — every module, always
Patch `fetch_url` so the real shared client runs (URL building, query encoding,
JSON parsing, status handling) but no HTTP leaves the process. Required cases:

- happy path + **idempotency** (2nd identical run → `changed=False`)
- **check mode** (never mutates; correct `changed`)
- **fail-fast on missing token** (asserts *zero* HTTP calls attempted)
- non-2xx → `fail_json` with status
- for state/action modules: the create/act path sets `changed=True`

Units **own** URL/auth/query-encoding/error-mapping/param-validation — these are
fast and exhaustive here and must **not** be duplicated in integration.

### Integration — selective, and only against a local mock
Add `tests/integration/targets/<module>/` **only where it earns its keep**:

| Module kind | Integration? | Why |
|-------------|:------------:|-----|
| **info** (`*_info`) | ❌ | units cover the full contract; integration is redundant |
| **state** (`cluster`, `infra_env`) | ✅ | prove `present → present(no-op) → absent → absent(no-op)` across real playbook runs |
| **action** (`cluster_action`, `host_action`) | ✅ | prove guard-on-status across sequenced calls / status transitions |
| **download** helpers | ⚠️ optional | a smoke target at most |

**Hard rule:** integration NEVER targets `api.openshift.com`. Modules expose a
`base_url` override; integration points it at a **local mock HTTP server** fixture
returning canned responses, gated so it cannot reach prod. No credentials, no
network egress.

### When to build the integration layer
Not yet. Phase 1's info modules need units only. Introduce the `base_url` param,
the mock-server fixture, the `tests/integration/` targets, and the CI
`Integration` job **together with the first state-based module** (`cluster` /
`infra_env`) — that PR is the trigger. Sanity already validates doc/argspec
consistency at runtime, so that layer is covered independently.
