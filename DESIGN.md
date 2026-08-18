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
- Read-only info modules: `openshift_versions`, `support_levels`,
  `supported_operators`
- Declarative CRUD done properly: `clusters`, `infra_envs`
  (idempotent create/update/delete via GET → PATCH)

### Phase 2 (`2.0.0`+) — the install lifecycle
- Host management: `infra-envs/{id}/hosts/...` (register, bind, unbind, install, reset)
- Cluster actions: `install`, `reset`, `cancel`, `complete-installation`
- Download/info helpers: ISO URL, credentials / kubeconfig

Ship Phase 1 correct and green before starting Phase 2.

## 4. Per-resource idempotency model

Idempotency is **not** one recipe applied uniformly. Classify each endpoint:

| Pattern | Resources | Behavior |
|---------|-----------|----------|
| **Read-only / info** | `openshift_versions`, `support_levels`, `supported_operators`, `events` | Never changes state → always `changed=False`. `supports_check_mode=True` for free. |
| **State-based (declarative)** | `clusters`, `infra_envs` | `state: present/absent`. GET by name/id → observe; create if missing; PATCH if drifted; delete if present. `changed` = real change. Delete of already-absent = `changed=False`. |
| **RPC-style actions** | `install`, `reset`, `cancel`, `bind`, `unbind` (Phase 2) | Verbs, not desired state — cannot "PATCH to converge." Idempotency = check current status *first* and no-op if already in the target state. |

The Assisted Installer API is designed for the state-based pattern: it exposes
`GET` (list + by-id) and `PATCH` for both `clusters` and `infra-envs`, so
observe→compare→act maps directly onto real endpoints.

## 5. Key decisions locked in

- **HTTP client:** `fetch_url` (dependency-free, sanity-clean, EE-friendly).
- **License:** GPL-3.0-or-later — GPLv3 headers on module files (the Ansible norm;
  keeps `validate-modules` green without ignore entries).
- **Secrets:** module params with `no_log=True` (and/or env), documented
  consistently; never committed.
- **ansible-core matrix:** `requires_ansible >= 2.17`; CI tests stable-2.17,
  stable-2.18, stable-2.19, and `devel`; sanity ignore files exist per supported
  stable version and stay in sync.
- **Testing:** API mocked (`fetch_url` patched); create / idempotency / check-mode
  cases; no live calls or credentials in CI.
