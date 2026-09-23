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
├── ansible_helpers.py      # Mock helpers (AnsibleExitJson, set_module_args)
├── conftest.py             # pytest configuration
└── test_my_module.py       # Test cases
```

### Required Test Categories

Every module must test these scenarios:

#### 1. Lifecycle Tests
Test the main workflow:

```python
def test_creates_resource(monkeypatch):
    """Test creating a resource returns changed=True."""
    mock_api_response(monkeypatch, status=201, body={"id": "uuid", "name": "test"})
    
    set_module_args({
        "name": "test",
        "state": "present",
        "api_token": "fake-token"
    })
    
    with pytest.raises(AnsibleExitJson) as exc:
        my_module.run_module()
    
    assert exc.value.result["changed"] is True
    assert exc.value.result["resource"]["id"] == "uuid"
```

#### 2. Idempotency Tests
Test no-op when already in desired state:

```python
def test_idempotent_when_exists(monkeypatch):
    """Test second run with same state returns changed=False."""
    # First run: resource doesn't exist
    mock_api_response(monkeypatch, status=200, body=[])  # GET returns empty
    mock_api_response(monkeypatch, status=201, body={"id": "uuid"})  # POST creates
    
    set_module_args({"name": "test", "state": "present", "api_token": "token"})
    with pytest.raises(AnsibleExitJson) as exc:
        my_module.run_module()
    assert exc.value.result["changed"] is True
    
    # Second run: resource exists
    mock_api_response(monkeypatch, status=200, body=[{"id": "uuid", "name": "test"}])
    
    set_module_args({"name": "test", "state": "present", "api_token": "token"})
    with pytest.raises(AnsibleExitJson) as exc:
        my_module.run_module()
    assert exc.value.result["changed"] is False  # ← Idempotent
```

#### 3. Check Mode Tests
Ensure no mutations when `check_mode=True`:

```python
def test_check_mode_no_side_effect(monkeypatch):
    """Test check mode predicts change but doesn't execute."""
    mock_api_response(monkeypatch, status=200, body=[])  # Resource doesn't exist
    
    set_module_args({
        "name": "test",
        "state": "present",
        "api_token": "token",
        "_ansible_check_mode": True
    })
    
    with pytest.raises(AnsibleExitJson) as exc:
        my_module.run_module()
    
    assert exc.value.result["changed"] is True  # Would change
    # Verify NO POST/PATCH/DELETE was called (check mock call count)
```

#### 4. Safety Guards Tests
Test fail-fast conditions:

```python
def test_fails_without_token(monkeypatch):
    """Test module fails fast when no token is available."""
    set_module_args({"name": "test"})  # No api_token, no env var
    
    with pytest.raises(AnsibleFailJson) as exc:
        my_module.run_module()
    
    assert "authentication" in exc.value.msg.lower()
```

#### 5. API Contract Tests
Test parameter encoding and response parsing:

```python
def test_encodes_query_parameters(monkeypatch):
    """Test query params are correctly URL-encoded."""
    calls = []
    
    def fake_fetch_url(module, url, **kwargs):
        calls.append(url)
        return (None, {"status": 200, "body": b"[]"})
    
    monkeypatch.setattr("my_module.fetch_url", fake_fetch_url)
    
    set_module_args({
        "owner": "user@example.com",
        "api_token": "token"
    })
    
    with pytest.raises(AnsibleExitJson):
        my_module.run_module()
    
    assert "owner=user%40example.com" in calls[0]  # @ encoded as %40
```

### Mocking Patterns

#### Mock fetch_url

```python
def mock_api_response(monkeypatch, status=200, body=None, responses=None):
    """Mock fetch_url to return canned responses.
    
    Args:
        monkeypatch: pytest monkeypatch fixture
        status: HTTP status code for single response
        body: Response body for single response
        responses: List of (status, body) tuples for queued responses
    """
    class Response:
        def __init__(self, data):
            self.data = data

        def read(self):
            return self.data

    if responses is None:
        responses = [(status, body)]
    
    response_queue = list(responses)
    
    def fake_fetch_url(module, url, **kwargs):
        if not response_queue:
            raise RuntimeError("mock_api_response: response queue exhausted")
        
        status_code, response_body = response_queue.pop(0)
        encoded_body = json.dumps(response_body).encode() if response_body is not None else b""
        info = {"status": status_code}
        
        if status_code >= 400:
            info["body"] = encoded_body
            return (None, info)
        return (Response(encoded_body), info)
    
    monkeypatch.setattr("my_module.fetch_url", fake_fetch_url)
```

#### Record Calls

```python
def test_makes_correct_api_call(monkeypatch):
    """Verify the module calls the right endpoint."""
    calls = []
    
    def fake_fetch_url(module, url, method=None, **kwargs):
        calls.append({"url": url, "method": method})
        return (None, {"status": 200, "body": b"{}"})
    
    monkeypatch.setattr("my_module.fetch_url", fake_fetch_url)
    
    set_module_args({"name": "test", "api_token": "token"})
    with pytest.raises(AnsibleExitJson):
        my_module.run_module()
    
    assert calls[0]["method"] == "GET"
    assert "/v2/resources" in calls[0]["url"]
```

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
      - result.changed is true
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
      - result.changed is false

- name: Delete infra-env
  openshift_lab.assisted_installer.infra_env:
    name: test-infra
    state: absent
    base_url: "{{ mock_server_url }}"
  register: result

- name: Verify deletion
  assert:
    that:
      - result.changed is true

- name: Delete infra-env (already gone)
  openshift_lab.assisted_installer.infra_env:
    name: test-infra
    state: absent
    base_url: "{{ mock_server_url }}"
  register: result

- name: Verify delete is idempotent
  assert:
    that:
      - result.changed is false
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
