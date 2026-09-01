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

## 2a. Verify the API contract (before coding)

**Do not assume how the API behaves — look it up.** Read the endpoint documentation
(not just path/method) and check edge cases:

- **For actions**: What state transitions are valid? Can you `bind` a host already
  bound to a different cluster, or must you `unbind` first? Can you `install` when
  status is `error`? **Query the spec or API docs to confirm.** Do not guess.
- **For state modules**: What fields are immutable? What happens if you PATCH
  `cpu_architecture` on an existing infra-env? The module should detect and reject
  this *before* making the API call.
- **For all modules**: Which fields are write-only (pull_secret, keys)? These must
  be excluded from drift comparison — the API never returns them.

See `plugins/modules/host_action.py` for an action module that rejects rebinding
(search for "Unbind it first" in `needs_action()`) — this logic came from
verifying the API contract, not guessing.

## 3. Use the shared client — do not reinvent HTTP/auth

`plugins/module_utils/assisted_installer.py` provides:

```python
from ansible_collections.openshift_lab.assisted_installer.plugins.module_utils \
    import assisted_installer as ai

token = ai.resolve_token(module)  # env/param -> bearer, or fail_json
data, info = ai.request(
    module, "GET", "/clusters", token,
    query={"with_hosts": with_hosts},
    timeout=params.get("timeout", 30),
    base_url=params.get("base_url"),  # integration mock override (validated)
)
if info["status"] != 200:
    module.fail_json(msg="...", status=info["status"])
```

Never import `requests`; never build the base URL or Authorization header by hand;
always rely on the client's timeout. `base_url` is validated (HTTPS always allowed;
HTTP only for loopback 127.0.0.1/localhost) to prevent credential leakage.

## 4. Module shape (fill from §1/§2)

Start from the `/new-ansible-module` template (GPLv3 header, three doc blocks
matching `argument_spec` exactly, `author: - Name (@handle)`, `run_module`/`main`).
Then:
- add `no_log=True` on any token / `pull_secret` / key arg
- source secrets via param and/or env (documented consistently)
- implement the classified idempotency pattern using the shared client
- write a **thorough `EXAMPLES`** block for the classified kind (CLAUDE.md rule):
  - *info* → a plain query, a filtered query using this endpoint's real query
    params, and a `register` + `debug` showing the result
    (cf. `openshift_version_info`: list all / `only_latest: true` / `version:`);
  - *state* → `present` create, an update, `absent`, and a check-mode (`-C`) run,
    with a comment that a 2nd identical run is `changed=false`;
  - *action* → each representative `action:` verb and the status it guards on.
  Use the endpoint's real params only (sanity checks EXAMPLES ↔ `argument_spec`);
  never put a literal token — use `"{{ assisted_installer_token }}"` or env.

**State-module patterns** (see `plugins/modules/infra_env.py` as the reference):
1. **Write-only fields** (pull_secret, keys): accept as input (`no_log=True`), send
   on create, but **exclude from drift comparison** (API never returns them).
2. **Immutable fields** (cluster_id, cpu_architecture): **fail before any write** if
   the user tries to change one; list the conflict in the error (current vs. requested).
3. **Partial PATCH**: only send fields the user set AND that differ; never full-object
   replace; unset options never appear in the body (no phantom drift).
4. **Check mode**: `supports_check_mode=True`; always GET (safe), return before any
   POST/PATCH/DELETE when `module.check_mode`; report `changed=True/False` honestly.

## 5. Tests (mock the API — no live calls)

Add `tests/unit/plugins/modules/test_<module>.py`. **Mock at the `fetch_url` layer**
(per CLAUDE.md) so the REAL shared client runs (URL building, auth, JSON parsing):

```python
from ansible_helpers import (
    AnsibleExitJson, AnsibleFailJson, patch_ansible, queue_fetch_url, set_module_args,
)
from ansible_collections.openshift_lab.assisted_installer.plugins.module_utils import (
    assisted_installer as ai,
)

def test_create_posts_and_is_changed(monkeypatch):
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)
    calls = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url(
        [(200, []), (201, {"id": "abc"})],  # GET then POST
        calls=calls,
    ))
    set_module_args({"name": "x", "api_token": "t"})
    <module>.main()  # raises AnsibleExitJson
    assert [c["method"] for c in calls] == ["GET", "POST"]
```

For **state modules**, use `queue_fetch_url(responses, calls)` — pass a list of
`(status, body)` tuples; each request consumes the next. Assert on `calls` to prove
which HTTP verbs fired (the teeth of idempotency/check-mode tests).

**5-category test structure** (see `test_infra_env.py` as the reference):
1. Lifecycle — create, update (drift), delete
2. Idempotency — no-drift present, already-absent delete (changed=False)
3. Check mode — create/update predicts but never writes (`calls == ["GET"]`)
4. Safety guards — immutable conflict, ambiguous match, fail-fast no token
5. API contract — required_if, error mapping (non-2xx → fail_json), base_url override

Every state module should cover all 5 categories.

## 6. Verify (do not stop until green)

```bash
./run.sh --check      # collection build + sanity + units, in-container
```

Keep `meta/runtime.yml`, the CI matrix, and `tests/sanity/ignore-*.txt` in sync.
