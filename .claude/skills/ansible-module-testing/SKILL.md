---
name: ansible-module-testing
description: Comprehensive guide to testing Ansible modules - sanity tests, unit tests, and integration tests. Covers ansible-test commands, mocking patterns, coverage requirements, test structure, and CI integration. Use when writing tests for modules or debugging test failures.
---

# Ansible Module Testing Guide

Complete reference for testing Ansible modules, based on the [official Ansible testing guide](https://docs.ansible.com/projects/ansible/latest/dev_guide/testing.html).

## Overview

Ansible modules require three types of tests:
1. **Sanity tests** - Code quality, documentation, imports
2. **Unit tests** - Module logic with mocked dependencies
3. **Integration tests** - End-to-end workflows (for state/action modules)

**This project requires ≥90% test coverage.**

---

## Sanity Tests

### What They Check

- Python syntax and imports
- Documentation format (DOCUMENTATION/EXAMPLES/RETURN)
- GPLv3 license header presence
- Author format validity
- File naming conventions
- Deprecation warnings
- Code style (pylint)

### Running Sanity Tests

```bash
# In containerized environment (CI)
./run.sh --check  # Runs build + sanity + units + coverage

# Directly with ansible-test
ansible-test sanity --docker
```

### Common Sanity Failures

#### 1. Missing GPLv3 Header
```
ERROR: plugins/modules/my_module.py: missing-gplv3-license
```
**Fix:** Add GPLv3 comment in first 20 lines

#### 2. Invalid Author Format
```
ERROR: plugins/modules/my_module.py: author field must include GitHub handle
```
**Fix:** Use `author:\n  - Name (@githubhandle)`

#### 3. Documentation Mismatch
```
ERROR: options in DOCUMENTATION don't match argument_spec
```
**Fix:** Ensure DOCUMENTATION options exactly match argument_spec dict

#### 4. Import Violations
```
ERROR: ansible-bad-import-from: Do not import from ansible.module_utils.six
```
**Fix:** Remove six imports (Python 3 only)

---

## Unit Tests

### Purpose

Test module logic **without** network calls or external dependencies. Mock all side effects.

### Test Structure

```
tests/unit/plugins/modules/
├── ansible_helpers.py      # Mock helpers (AnsibleExitJson, set_module_args,
│                           #   patch_ansible, fake_fetch_url, queue_fetch_url)
├── conftest.py             # pytest configuration
└── test_my_module.py       # Test cases
```

### Mock at the shared client, not at the module

**CRITICAL:** Modules in this collection do not import `fetch_url` directly —
they call the shared client `plugins/module_utils/assisted_installer.py`
(`ai.request()`), which imports `fetch_url`. So patch it **where it lives**:

```python
from ansible_collections.openshift_lab.assisted_installer.plugins.module_utils import (
    assisted_installer as ai,
)
monkeypatch.setattr(ai, "fetch_url", ...)      # ✅ the shared client's fetch_url
# monkeypatch.setattr("my_module.fetch_url", ...)   # ❌ the module never imports it
```

Patching `my_module.fetch_url` silently fails to apply (the name doesn't exist on
the module), so the "mock" is a no-op and the test would hit the network. Mocking
at `ai.fetch_url` also means the tests exercise the REAL client — URL building,
query encoding, JSON parsing, status handling — which is exactly what you want.

Use the ready-made helpers from `ansible_helpers.py` instead of hand-rolling a
mock:

- `fake_fetch_url(status=200, body=None, calls=None)` — one canned `(resp, info)`
  response; on status ≥ 400 it returns `(None, info)` with the body in
  `info["body"]`, mirroring real `fetch_url`.
- `queue_fetch_url(responses, calls=None)` — a **list** of `(status, body)`
  tuples consumed in order (GET, then POST/PATCH/DELETE). Pass a `calls` list and
  each invocation records `{url, method, data, headers, timeout, ...}` so you can
  assert exactly which verbs fired — the teeth of idempotency/check-mode tests.

### Required Test Categories

Every module must test these scenarios. Import the helpers once:

```python
import pytest
from ansible_helpers import (
    AnsibleExitJson, AnsibleFailJson, patch_ansible,
    set_module_args, fake_fetch_url, queue_fetch_url,
)
from ansible_collections.openshift_lab.assisted_installer.plugins.modules import my_module
from ansible_collections.openshift_lab.assisted_installer.plugins.module_utils import (
    assisted_installer as ai,
)
```

#### 1. Lifecycle Tests
Test the main workflow. A state create observes (GET) then creates (POST), so
drive it with a **queue** of responses, not a single one:

```python
def test_creates_resource(monkeypatch):
    """Test creating a resource returns changed=True."""
    patch_ansible(monkeypatch)
    calls = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url(
        [(200, []),                          # GET: no match -> absent
         (201, {"id": "uuid", "name": "test"})],  # POST: created
        calls=calls,
    ))
    set_module_args({"name": "test", "state": "present", "api_token": "token"})

    with pytest.raises(AnsibleExitJson) as exc:
        my_module.main()

    assert exc.value.result["changed"] is True
    assert exc.value.result["resource"]["id"] == "uuid"
    assert [c["method"] for c in calls] == ["GET", "POST"]
```

#### 2. Idempotency Tests
Test no-op when already in desired state. Run the module **twice**, each with its
own queued responses:

```python
def test_idempotent_when_exists(monkeypatch):
    """Second run with same state returns changed=False and makes no write."""
    patch_ansible(monkeypatch)

    # First run: absent -> create (GET then POST)
    calls1 = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url(
        [(200, []), (201, {"id": "uuid", "name": "test"})], calls=calls1,
    ))
    set_module_args({"name": "test", "state": "present", "api_token": "token"})
    with pytest.raises(AnsibleExitJson) as exc:
        my_module.main()
    assert exc.value.result["changed"] is True
    assert [c["method"] for c in calls1] == ["GET", "POST"]

    # Second run: already present -> GET only, no POST/PATCH
    calls2 = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url(
        [(200, [{"id": "uuid", "name": "test"}])], calls=calls2,
    ))
    set_module_args({"name": "test", "state": "present", "api_token": "token"})
    with pytest.raises(AnsibleExitJson) as exc:
        my_module.main()
    assert exc.value.result["changed"] is False       # ← idempotent
    assert [c["method"] for c in calls2] == ["GET"]    # ← no write fired
```

#### 3. Check Mode Tests
Ensure no mutations when `check_mode=True`. Assert on the recorded verbs — only a
GET may fire:

```python
def test_check_mode_no_side_effect(monkeypatch):
    """Check mode predicts change but never writes."""
    patch_ansible(monkeypatch)
    calls = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url(
        [(200, [])], calls=calls,      # GET: absent; NO write response queued
    ))
    set_module_args({
        "name": "test", "state": "present", "api_token": "token",
        "_ansible_check_mode": True,
    })

    with pytest.raises(AnsibleExitJson) as exc:
        my_module.main()

    assert exc.value.result["changed"] is True      # would change
    assert [c["method"] for c in calls] == ["GET"]  # but no POST/PATCH/DELETE
```

#### 4. Safety Guards Tests
Test fail-fast conditions. The captured exception carries the result dict — read
`msg` from `exc.value.result["msg"]` (the helper does **not** set `exc.value.msg`):

```python
def test_fails_without_token(monkeypatch):
    """Module fails fast when no token is available."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)      # no ambient token
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)
    set_module_args({"name": "test"})                      # no api_token param

    with pytest.raises(AnsibleFailJson) as exc:
        my_module.main()

    assert "token" in exc.value.result["msg"].lower()
```

#### 5. API Contract Tests
Test parameter encoding and response parsing via the recorded `calls`:

```python
def test_encodes_query_parameters(monkeypatch):
    """Query params are correctly URL-encoded by the shared client."""
    patch_ansible(monkeypatch)
    calls = []
    monkeypatch.setattr(ai, "fetch_url", fake_fetch_url(status=200, body=[], calls=calls))
    set_module_args({"owner": "user@example.com", "api_token": "token"})

    with pytest.raises(AnsibleExitJson):
        my_module.main()

    assert "owner=user%40example.com" in calls[0]["url"]  # @ encoded as %40
```

### Recording and asserting calls

Both `fake_fetch_url` and `queue_fetch_url` accept a `calls` list. Each HTTP call
appends a dict with `url`, `method`, `data`, `headers`, and `timeout`, so you can
assert which endpoint and verb fired:

```python
def test_makes_correct_api_call(monkeypatch):
    """Verify the module calls the right endpoint."""
    patch_ansible(monkeypatch)
    calls = []
    monkeypatch.setattr(ai, "fetch_url", fake_fetch_url(status=200, body={}, calls=calls))

    set_module_args({"cluster_id": "abc", "api_token": "token"})
    with pytest.raises(AnsibleExitJson):
        my_module.main()

    assert calls[0]["method"] == "GET"
    assert "/v2/clusters/abc" in calls[0]["url"]
```

> The helpers live in `tests/unit/plugins/modules/ansible_helpers.py`. Do not
> hand-roll a `mock_api_response` — the shared helpers already model the real
> `(resp, info)` contract (including `info["body"]` on errors), and reusing them
> keeps every test consistent with the actual client.

### Running Unit Tests

```bash
# With coverage (≥90% required)
./run.sh --check  # Includes coverage report

# Directly with ansible-test
ansible-test units --docker --coverage

# View coverage report
ansible-test coverage report --show-missing
```

### Coverage Requirements

**This project enforces ≥90% coverage:**
- Total coverage across all lines
- Branch coverage (tracks conditional paths)
- Report shows missing lines and partial branches

**Coverage failures mean untested code paths exist.**

---

## Integration Tests

### When Needed

**Required for:**
- State modules (create/update/delete lifecycle)
- Action modules (multi-step workflows)

**Not required for:**
- Info modules (unit tests sufficient)
- Simple query modules

### Structure

```
tests/integration/targets/
└── my_module/
    ├── tasks/
    │   └── main.yml
    ├── defaults/
    │   └── main.yml
    └── meta/
        └── main.yml
```

### Integration Test Patterns

#### State Module Integration Test

```yaml
# tests/integration/targets/infra_env/tasks/main.yml
---
- name: Create infra-env (first run)
  openshift_lab.assisted_installer.infra_env:
    name: test-infra
    pull_secret: "{{ test_pull_secret }}"
    state: present
    base_url: "{{ mock_server_url }}"  # Override to hit mock, not prod
  register: result

- name: Verify creation
  assert:
    that:
      - result is changed
      - result.infra_env.name == "test-infra"

- name: Create infra-env (second run, idempotent)
  openshift_lab.assisted_installer.infra_env:
    name: test-infra
    pull_secret: "{{ test_pull_secret }}"
    state: present
    base_url: "{{ mock_server_url }}"
  register: result

- name: Verify idempotency
  assert:
    that:
      - result is not changed

- name: Delete infra-env
  openshift_lab.assisted_installer.infra_env:
    name: test-infra
    state: absent
    base_url: "{{ mock_server_url }}"
  register: result

- name: Verify deletion
  assert:
    that:
      - result is changed

- name: Delete infra-env (already gone)
  openshift_lab.assisted_installer.infra_env:
    name: test-infra
    state: absent
    base_url: "{{ mock_server_url }}"
  register: result

- name: Verify delete is idempotent
  assert:
    that:
      - result is not changed
```

### Local Mock Server

**NEVER hit production API in tests.**

Use `base_url` parameter to redirect to mock:

```python
# In module argument_spec
base_url=dict(type="str", default="https://api.openshift.com")

# In module code - use shared request() method
from ..module_utils import assisted_installer as ai
data, info = ai.request(module, "GET", "/clusters", token)
```

**Integration test override:**
```yaml
base_url: "http://localhost:8080"  # Local mock server
```

### Running Integration Tests

```bash
# Run all integration tests
ansible-test integration --docker

# Run specific target
ansible-test integration my_module --docker

# With verbose output
ansible-test integration my_module --docker -vvv
```

---

## CI Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
jobs:
  sanity:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run sanity tests
        run: ./run.sh --check  # Runs sanity + units + coverage

  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run integration tests
        run: ansible-test integration --docker
```

### Coverage Reporting

```bash
# Generate coverage report
ansible-test coverage report

# Show missing lines
ansible-test coverage report --show-missing

# Enforce minimum (project uses 90%)
./run.sh --check
```

---

## Debugging Test Failures

### Sanity Failures

```bash
# Run sanity with verbose output
ansible-test sanity --docker -vvv

# Test specific file
ansible-test sanity plugins/modules/my_module.py --docker
```

**Common fixes:**
- Check GPLv3 header
- Verify author format
- Match DOCUMENTATION to argument_spec
- Remove forbidden imports

### Unit Test Failures

```bash
# Run with pytest verbose
ansible-test units --docker -vvv

# Run specific test
ansible-test units test_my_module --docker

# Use pdb for debugging
pytest tests/unit/plugins/modules/test_my_module.py::test_name --pdb
```

**Common issues:**
- Mock not applied (check patch target)
- set_module_args missing required params
- Assert on wrong field

### Coverage Failures

```bash
# See what's missing
ansible-test coverage report --show-missing
```

**Address:**
- Add tests for untested lines
- Test both branches of conditionals
- Test error paths (fail_json cases)

---

## Test Quality Checklist

Before submitting:

- [ ] All 5 test categories covered (lifecycle, idempotency, check-mode, safety, API contract)
- [ ] Sanity tests pass (`ansible-test sanity`)
- [ ] Unit tests pass (`ansible-test units`)
- [ ] Coverage ≥90% (`ansible-test coverage report`)
- [ ] No calls to production API (all mocked)
- [ ] Integration tests for state/action modules
- [ ] Tests use `base_url` override for integration

---

## Reference

- [Ansible Testing Guide](https://docs.ansible.com/projects/ansible/latest/dev_guide/testing.html)
- [Unit Testing Modules](https://docs.ansible.com/projects/ansible/latest/dev_guide/testing_units_modules.html)
- [Integration Testing](https://docs.ansible.com/projects/ansible/latest/dev_guide/testing_integration.html)
- This project: `DESIGN.md` §7, `docs/testing-cheat-sheet.md`

---

## Quick Commands

```bash
# Everything (sanity + units + coverage)
./run.sh --check

# Just sanity
ansible-test sanity --docker

# Just units with coverage
ansible-test units --docker --coverage
ansible-test coverage report --show-missing

# Integration tests
ansible-test integration --docker

# Specific test
ansible-test units tests/unit/plugins/modules/test_my_module.py::test_creates_resource --docker -vvv
```
