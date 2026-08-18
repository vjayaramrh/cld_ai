---
name: new-ai-endpoint-module
description: Scaffold a new Ansible module for the OpenShift Assisted Installer API in the openshift_lab.assisted_installer collection. Knows the API base URL, the Authorization/Bearer auth model, the shared plugins/module_utils/assisted_installer.py client (fetch_url-based), and picks the right idempotency pattern (read-only / state-based GET→PATCH / RPC-action) per endpoint. Use when adding, creating, or generating a module that wraps an Assisted Installer endpoint (clusters, infra-envs, hosts, events, openshift-versions, support-levels, operators). Keywords: assisted installer, openshift, fetch_url, argument_spec, idempotency, check_mode, GET PATCH, ansible-test.
---

# Scaffold an Assisted Installer endpoint module

Project-specific companion to `/new-ansible-module`. Follow **CLAUDE.md** and
**DESIGN.md** in this repo — they define the conventions and the per-resource
idempotency model. This skill wires a new module to *this* API.

## 1. Look up the endpoint in the spec (source of truth)

Spec: `https://api.openshift.com/api/assisted-install/v2/openapi` (Swagger 2.0).
For the target resource, record from the spec:
- path(s) and methods (GET list / GET by-id / POST / PATCH / DELETE / actions)
- **required** request-body fields (e.g. cluster-create needs
  `name`, `openshift_version`, `pull_secret`)
- query parameters for list endpoints
- the response shape (for `RETURN`)

## 2. Classify the resource (drives the skeleton) — see DESIGN.md §4

- **Read-only / info** → always `changed=False`; `supports_check_mode=True`.
- **State-based** (`state: present/absent`) → GET to observe → compare →
  POST/PATCH/DELETE only if needed; a create sets `changed=True`; deleting an
  already-absent resource is `changed=False`.
- **RPC-style action** (install/reset/cancel/bind/unbind) → check current status
  first; no-op if already in the target state.

## 3. Use the shared client — do not reinvent HTTP/auth

`plugins/module_utils/assisted_installer.py` provides:

```python
from ansible_collections.openshift_lab.assisted_installer.plugins.module_utils \
    import assisted_installer as ai

token = ai.resolve_token(module)                         # env/param -> bearer, or fail_json
data, info = ai.request(module, "GET", "/clusters", token, query={"with_hosts": with_hosts})
if info["status"] not in (200,):
    module.fail_json(msg="...", status=info["status"], body=data)
```

Never import `requests`; never build the base URL or Authorization header by hand;
always rely on the client's timeout.

## 4. Module shape (fill from §1/§2)

Start from the `/new-ansible-module` template (GPLv3 header, three doc blocks
matching `argument_spec` exactly, `author: - Name (@handle)`, `run_module`/`main`).
Then:
- add `no_log=True` on any token / `pull_secret` / key arg
- source secrets via param and/or env (documented consistently)
- implement the classified idempotency pattern using the shared client

## 5. Tests (mock the API — no live calls)

Add `tests/unit/plugins/modules/test_<module>.py` mocking the client:

```python
monkeypatch.setattr(<module>.ai, "request", fake_request)
monkeypatch.setattr(<module>.ai, "resolve_token", lambda module: "t")
```

Cover: create/act (`changed=True`), idempotency (2nd run `changed=False`),
check-mode (no side effect). Reuse `set_module_args` + `AnsibleExitJson/FailJson`
helpers from the `/new-ansible-module` skill.

## 6. Verify (do not stop until green)

```bash
./run.sh --check      # collection build + sanity + units, in-container
```

Keep `meta/runtime.yml`, the CI matrix, and `tests/sanity/ignore-*.txt` in sync.
