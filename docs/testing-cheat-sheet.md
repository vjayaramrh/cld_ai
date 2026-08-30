# Testing Cheat Sheet

**Quick reference for writing unit tests** — see [testing-guide.md](testing-guide.md) for detailed explanations.

---

## The 5 Required Test Categories

Every module needs tests in these 5 categories (see DESIGN.md §7):

### 1. ✅ Lifecycle (Happy Path)

Tests that the module does what it's supposed to do.

**Info module:**
```python
def test_query_returns_results(monkeypatch):
    """GET request returns data, changed=False."""
    calls = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([
        (200, {"4.16": {"display_name": "4.16.3"}}),
    ], calls=calls))
    set_module_args({'api_token': 'test-token'})
    
    with pytest.raises(AnsibleExitJson) as exc:
        my_module.main()
    
    assert exc.value.args[0]['changed'] is False
    assert len(exc.value.args[0]['results']) > 0
```

**State module (create):**
```python
def test_present_creates_when_absent(monkeypatch):
    """Creates resource when it doesn't exist, changed=True."""
    calls = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([
        (404, "Not found"),              # GET: resource doesn't exist
        (201, {"id": "123", "name": "test"}),  # POST: created
    ], calls=calls))
    set_module_args({'name': 'test', 'state': 'present', 'api_token': 'test-token'})
    
    with pytest.raises(AnsibleExitJson) as exc:
        my_module.main()
    
    assert exc.value.args[0]['changed'] is True
    assert calls[1]["method"] == "POST"
```

**State module (update):**
```python
def test_present_updates_when_drift(monkeypatch):
    """Updates resource when it exists but differs, changed=True."""
    calls = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([
        (200, {"id": "123", "name": "test", "version": "old"}),  # GET: exists but wrong
        (200, {"id": "123", "name": "test", "version": "new"}),  # PATCH: updated
    ], calls=calls))
    set_module_args({'name': 'test', 'version': 'new', 'state': 'present', 'api_token': 'test-token'})
    
    with pytest.raises(AnsibleExitJson) as exc:
        my_module.main()
    
    assert exc.value.args[0]['changed'] is True
    assert calls[1]["method"] == "PATCH"
```

**State module (delete):**
```python
def test_absent_deletes_when_exists(monkeypatch):
    """Deletes resource when it exists, changed=True."""
    calls = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([
        (200, {"id": "123", "name": "test"}),  # GET: exists
        (204, ""),                              # DELETE: deleted
    ], calls=calls))
    set_module_args({'name': 'test', 'state': 'absent', 'api_token': 'test-token'})
    
    with pytest.raises(AnsibleExitJson) as exc:
        my_module.main()
    
    assert exc.value.args[0]['changed'] is True
    assert calls[1]["method"] == "DELETE"
```

---

### 2. ✅ Idempotency

Tests that running the module twice with the same inputs doesn't change anything the second time.

**⚠️ IMPORTANT: Run the action TWICE in the SAME test**

The strongest idempotency test pattern is:
1. Start in state A (e.g., host unbound)
2. Run action → verify changed=True, state becomes B (host bound)
3. **Run SAME action again** → verify changed=False, still B (no second POST)

This proves: action → same action = no-op. See `test_bind_twice_second_is_noop`
in `test_host_action.py` for the reference pattern.

The simpler "start already in target state" pattern (below) is valid but weaker —
it proves "already done = no-op" but not "action → action = no-op."

---

**State module (no-op when already correct):**
```python
def test_present_no_drift_is_unchanged(monkeypatch):
    """Resource exists and matches desired state → changed=False, no PATCH."""
    calls = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([
        (200, {"id": "123", "name": "test", "version": "new"}),  # GET: already correct
    ], calls=calls))
    set_module_args({'name': 'test', 'version': 'new', 'state': 'present', 'api_token': 'test-token'})
    
    with pytest.raises(AnsibleExitJson) as exc:
        my_module.main()
    
    assert exc.value.args[0]['changed'] is False
    assert len(calls) == 1  # Only GET, no PATCH
```

**State module (absent when already absent):**
```python
def test_absent_when_missing_is_unchanged(monkeypatch):
    """Resource doesn't exist → changed=False, no DELETE."""
    calls = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([
        (404, "Not found"),  # GET: doesn't exist
    ], calls=calls))
    set_module_args({'name': 'test', 'state': 'absent', 'api_token': 'test-token'})
    
    with pytest.raises(AnsibleExitJson) as exc:
        my_module.main()
    
    assert exc.value.args[0]['changed'] is False
    assert len(calls) == 1  # Only GET, no DELETE
```

**Action module (already in target state):**
```python
def test_action_when_already_done_is_unchanged(monkeypatch):
    """Host already bound → changed=False, no action POST."""
    calls = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([
        (200, {"id": "host-1", "status": "bound"}),  # GET: already bound
    ], calls=calls))
    set_module_args({
        'host_id': 'host-1', 
        'action': 'bind', 
        'api_token': 'test-token'
    })
    
    with pytest.raises(AnsibleExitJson) as exc:
        my_module.main()
    
    assert exc.value.args[0]['changed'] is False
    assert len(calls) == 1  # Only GET, no action POST
```

**STRONGER: Run action twice (recommended pattern):**
```python
def test_bind_twice_second_is_noop(monkeypatch):
    """Bind unbound host, then bind again → first changes, second doesn't."""
    calls = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([
        # First run: bind
        (200, {"id": "host-1", "status": "known", "cluster_id": None}),     # GET: unbound
        (202, {}),                                                           # POST: bind action
        (200, {"id": "host-1", "status": "known", "cluster_id": "c-1"}),    # GET: fetch updated
        # Second run: same action, already bound
        (200, {"id": "host-1", "status": "known", "cluster_id": "c-1"}),    # GET: already bound
    ], calls=calls))
    
    args = {
        'infra_env_id': 'infra-1',
        'host_id': 'host-1',
        'action': 'bind',
        'cluster_id': 'c-1',
        'api_token': 'test-token',
    }
    
    # First run: should bind (changed=True)
    set_module_args(args)
    with pytest.raises(AnsibleExitJson) as exc:
        my_module.main()
    assert exc.value.args[0]['changed'] is True
    
    # Second run: already bound (changed=False, no POST)
    set_module_args(args)
    with pytest.raises(AnsibleExitJson) as exc:
        my_module.main()
    assert exc.value.args[0]['changed'] is False
    assert len(calls) == 4  # GET, POST, GET, GET (no second POST!)
```

This pattern proves: action → same action = no-op. Stronger than just
"start already done."

---

### 3. ✅ Check Mode

Tests that `--check` mode (dry-run) doesn't actually make changes.

```python
def test_check_mode_does_not_write(monkeypatch):
    """Check mode predicts changes but doesn't POST/PATCH/DELETE."""
    calls = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([
        (404, "Not found"),  # GET: doesn't exist
    ], calls=calls))
    set_module_args({
        'name': 'test', 
        'state': 'present', 
        'api_token': 'test-token',
        '_ansible_check_mode': True,  # ← Check mode enabled
    })
    
    with pytest.raises(AnsibleExitJson) as exc:
        my_module.main()
    
    assert exc.value.args[0]['changed'] is True  # Would create
    assert len(calls) == 1  # Only GET, NO POST
    assert calls[0]["method"] == "GET"
```

---

### 4. ✅ Safety Guards

Tests that the module fails gracefully with helpful messages.

**Missing required parameter:**
```python
def test_fail_when_no_token(monkeypatch):
    """Missing api_token → fail before any HTTP call."""
    calls = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([], calls=calls))
    set_module_args({'name': 'test'})  # Missing api_token
    
    with pytest.raises(AnsibleFailJson) as exc:
        my_module.main()
    
    assert 'api_token' in str(exc.value.args[0]['msg']).lower()
    assert len(calls) == 0  # No HTTP calls attempted
```

**State module: immutable field conflict:**
```python
def test_fail_when_changing_immutable_field(monkeypatch):
    """Trying to change immutable field → fail with clear message."""
    calls = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([
        (200, {"id": "123", "cpu_architecture": "x86_64"}),
    ], calls=calls))
    set_module_args({
        'name': 'test',
        'cpu_architecture': 'arm64',  # Can't change this!
        'state': 'present',
        'api_token': 'test-token',
    })
    
    with pytest.raises(AnsibleFailJson) as exc:
        my_module.main()
    
    assert 'cpu_architecture' in str(exc.value.args[0]['msg'])
    assert 'immutable' in str(exc.value.args[0]['msg']).lower()
    assert len(calls) == 1  # Only GET, no PATCH
```

**Action module: wrong status for action:**
```python
def test_fail_when_wrong_status_for_action(monkeypatch):
    """Trying to bind an installing host → fail with helpful message."""
    calls = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([
        (200, {"id": "host-1", "status": "installing"}),
    ], calls=calls))
    set_module_args({
        'host_id': 'host-1',
        'action': 'bind',
        'api_token': 'test-token',
    })
    
    with pytest.raises(AnsibleFailJson) as exc:
        my_module.main()
    
    assert 'installing' in str(exc.value.args[0]['msg'])
    assert len(calls) == 1  # Only GET, no action POST
```

---

### 5. ✅ API Contract

Tests that the module handles API errors correctly.

**Non-2xx response:**
```python
def test_handles_500_error(monkeypatch):
    """API returns 500 → fail_json with status and details."""
    calls = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([
        (500, {"error": "Internal server error"}),
    ], calls=calls))
    set_module_args({'name': 'test', 'api_token': 'test-token'})
    
    with pytest.raises(AnsibleFailJson) as exc:
        my_module.main()
    
    assert '500' in str(exc.value.args[0]['msg'])
```

**Required fields validation:**
```python
def test_required_params(monkeypatch):
    """Missing required parameter → fail before HTTP."""
    set_module_args({})  # Missing everything
    
    with pytest.raises(AnsibleFailJson) as exc:
        my_module.main()
    
    assert 'required' in str(exc.value.args[0]['msg']).lower()
```

**Base URL validation:**
```python
def test_rejects_http_remote(monkeypatch):
    """HTTP to remote host → fail (security)."""
    set_module_args({
        'api_token': 'test-token',
        'base_url': 'http://evil.com',  # Not HTTPS!
    })
    
    with pytest.raises(AnsibleFailJson) as exc:
        my_module.main()
    
    assert 'https' in str(exc.value.args[0]['msg']).lower()
```

---

## Common Test Patterns

### Pattern: Mock Multiple API Calls

Use `queue_fetch_url` to return different responses in sequence:

```python
from ansible_helpers import queue_fetch_url

calls = []
monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([
    (200, {"id": "1"}),   # 1st call returns this
    (201, {"id": "2"}),   # 2nd call returns this
    (204, ""),            # 3rd call returns this
], calls=calls))

# After module runs, inspect what it called:
assert len(calls) == 3
assert calls[0]["method"] == "GET"
assert calls[1]["method"] == "POST"
assert calls[2]["method"] == "DELETE"
```

---

### Pattern: Verify Request Body

Check what the module sent in the request:

```python
calls = []
monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([
    (201, {"id": "123"}),
], calls=calls))

# ... run module ...

# Verify POST body
import json
sent_data = json.loads(calls[0]["data"])
assert sent_data['name'] == 'test'
assert sent_data['version'] == '4.16'
```

---

### Pattern: Verify Query Parameters

Check URL query string:

```python
calls = []
# ... run module ...

# Parse query params
from urllib.parse import urlparse, parse_qs
parsed = urlparse(calls[0]["url"])
params = parse_qs(parsed.query)
assert params['version_substring'] == ['4.16']
```

---

### Pattern: Test Field Filtering (Write-Only Fields)

State modules with write-only fields (like `pull_secret`) must exclude them from drift comparison:

```python
def test_ignores_write_only_fields_in_drift(monkeypatch):
    """pull_secret is write-only → not in drift comparison."""
    calls = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([
        (200, {"id": "123", "name": "test"}),  # GET doesn't return pull_secret
    ], calls=calls))
    set_module_args({
        'name': 'test',
        'pull_secret': 'secret-value',  # Sent on create, never returned
        'state': 'present',
        'api_token': 'test-token',
    })
    
    with pytest.raises(AnsibleExitJson) as exc:
        my_module.main()
    
    # Should NOT consider this drift (pull_secret can't be compared)
    assert exc.value.args[0]['changed'] is False
    assert len(calls) == 1  # Only GET, no PATCH
```

---

## Test Helper Reference

### Import These

```python
from ansible_collections.openshift_lab.assisted_installer.plugins.modules import (
    my_module,  # Your module
)
from ansible_collections.openshift_lab.assisted_installer.plugins.module_utils import (
    assisted_installer as ai,  # The shared client
)
from ansible_helpers import (
    AnsibleExitJson,    # Catch module.exit_json()
    AnsibleFailJson,    # Catch module.fail_json()
    queue_fetch_url,    # Mock HTTP responses (multiple calls)
    set_module_args,    # Pass parameters to module
)
```

---

### Helper Functions

**`set_module_args(args_dict)`**
Sets module parameters (what user passes in playbook).

```python
set_module_args({
    'name': 'test-cluster',
    'state': 'present',
    'api_token': 'fake-token',
    '_ansible_check_mode': True,  # For check mode tests
})
```

**`queue_fetch_url(responses, calls=None)`**
Mocks HTTP responses in sequence. Returns a function you patch onto `ai.fetch_url`.

```python
calls = []  # List to record what HTTP calls were made
monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([
    (200, {"id": "123"}),  # (status_code, response_body)
    (201, {"id": "456"}),
], calls=calls))

# After module runs:
assert len(calls) == 2
assert calls[0]["method"] == "GET"
assert calls[0]["url"] == "https://..."
assert calls[0]["data"] == '{"name": "test"}'  # Request body
```

**`AnsibleExitJson` and `AnsibleFailJson`**
Exceptions raised by `module.exit_json()` and `module.fail_json()`.

```python
# Successful module run
with pytest.raises(AnsibleExitJson) as exc:
    my_module.main()

result = exc.value.args[0]
assert result['changed'] is True
assert result['resource']['id'] == '123'

# Failed module run
with pytest.raises(AnsibleFailJson) as exc:
    my_module.main()

error = exc.value.args[0]
assert 'required' in error['msg']
```

---

## Running Tests

### Run All Tests
```bash
./run.sh --check   # Runs: build + sanity + units + coverage
```

### Run One Test File
```bash
ansible-test units --coverage tests/unit/plugins/modules/test_my_module.py
```

### Run One Test Function
```bash
ansible-test units --coverage tests/unit/plugins/modules/test_my_module.py::test_present_creates
```

### Check Coverage
```bash
ansible-test units --coverage
ansible-test coverage report --show-missing
```

---

## Coverage Tips

**Goal:** ≥90% coverage (enforced)

**If coverage is low:**

1. **Find missing lines:**
   ```bash
   ansible-test coverage report --show-missing
   ```
   Output shows uncovered lines:
   ```text
   plugins/modules/my_module.py: 45-47, 89
   ```

2. **Find untested branches:**
   ```bash
   ansible-test coverage report --show-missing
   ```
   Output shows partially-covered branches:
   ```text
   plugins/modules/my_module.py: 52->54 (branch not taken)
   ```
   This means line 52 has an `if` that never evaluated to True/False in tests.

3. **Add tests for those paths:**
   - Missing line? Add a test that executes it
   - Missing branch? Add tests for both True and False cases

---

## Common Pitfalls

### ❌ Forgetting to Record Calls
```python
# WRONG: Can't verify what was called
monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([(200, {})]))

# RIGHT: Pass `calls=calls` to record
calls = []
monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([(200, {})], calls=calls))
assert len(calls) == 1
```

### ❌ Not Testing Idempotency
Every state/action module MUST have a test proving `changed=False` when already in desired state.

### ❌ Testing Too Much in One Test
Each test should verify ONE behavior. Split complex scenarios into multiple tests.

```python
# WRONG: Tests create AND update AND delete
def test_everything(monkeypatch):
    # 100 lines testing all scenarios

# RIGHT: One test per scenario
def test_creates_when_absent(monkeypatch): ...
def test_updates_when_drift(monkeypatch): ...
def test_deletes_when_exists(monkeypatch): ...
```

### ❌ Hard-Coding Expected Values
```python
# WRONG: Magic numbers
assert result['count'] == 2

# RIGHT: Derive from test data
assert result['count'] == len(SAMPLE_DATA)
```

---

## Next Steps

- **New to testing?** Read [testing-guide.md](testing-guide.md) for detailed explanations
- **Ready to write tests?** Copy from `test_openshift_version_info.py` (info) or `test_infra_env.py` (state)
- **Stuck?** Check [CONTRIBUTING.md](../CONTRIBUTING.md) or ask in your PR

---

**Quick Template:**

```python
from ansible_collections.openshift_lab.assisted_installer.plugins.modules import my_module
from ansible_collections.openshift_lab.assisted_installer.plugins.module_utils import assisted_installer as ai
from ansible_helpers import AnsibleExitJson, AnsibleFailJson, queue_fetch_url, set_module_args
import pytest

def test_happy_path(monkeypatch):
    calls = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([
        (200, {"id": "123"}),
    ], calls=calls))
    set_module_args({'api_token': 'test'})
    
    with pytest.raises(AnsibleExitJson) as exc:
        my_module.main()
    
    assert exc.value.args[0]['changed'] is False
```
