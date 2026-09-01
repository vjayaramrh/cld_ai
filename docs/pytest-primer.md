# pytest Primer for Ansible Module Testing

**Goal:** Learn the pytest concepts actually used in this collection's tests.

This is NOT a complete pytest tutorial. It covers only what you'll encounter in
`test_host_action.py`, `test_infra_env.py`, and `test_openshift_version_info.py`.

**New to pytest?** That's fine! This primer assumes you've never used it before.  
**Know pytest?** Use this as a quick refresher for our specific patterns.

---

## Self-Assessment

Before starting, check your testing knowledge:

- [ ] I know what a unit test is (tests one function in isolation)
- [ ] I understand the purpose of mocking (fake dependencies)
- [ ] I know what an assertion is (`assert x == y`)
- [ ] I'm comfortable reading Python exceptions

**All checked?** You're ready to write tests!  
**Some unchecked?** Read the sections below for those topics.

---

## 1. What is pytest?

**pytest** is a Python testing framework. It:
- Finds test files (anything matching `test_*.py` or `*_test.py`)
- Runs test functions (anything starting with `test_`)
- Reports which tests passed or failed

### Running tests

```bash
# Run all tests (build + sanity + units + coverage)
./run.sh --check

# Run tests for one module (inside container)
./run.sh
# Inside the container shell:
ansible-test units tests/unit/plugins/modules/test_host_action.py

# Run one specific test (inside container)
./run.sh
# Inside the container shell:
ansible-test units tests/unit/plugins/modules/test_host_action.py::test_bind_posts_when_unbound
```

**Where we use it:** Every time you verify your code works!

---

## 2. Test Structure (Arrange-Act-Assert)

Every test follows the same pattern:

```python
def test_bind_posts_when_unbound(monkeypatch):
    """Bind action: host is known and unbound → POSTs bind, changed=True."""
    
    # ARRANGE: Set up the test environment
    patch_ansible(monkeypatch)  # Patch Ansible internals
    calls = []                  # Track what HTTP calls were made
    monkeypatch.setattr(        # Mock the HTTP client
        ai,
        "fetch_url",
        queue_fetch_url([...], calls=calls),
    )
    set_module_args({...})      # Set module parameters
    
    # ACT: Run the code being tested
    with pytest.raises(AnsibleExitJson) as exc:
        host_action.main()
    
    # ASSERT: Verify the results
    assert exc.value.result["changed"] is True
    assert exc.value.result["action"] == "bind"
    assert len(calls) == 3
    assert calls[1]["method"] == "POST"
```

**Key sections:**
1. **Arrange** - Set up mocks, test data, module args
2. **Act** - Call the function being tested
3. **Assert** - Verify it did what we expected

---

## 3. pytest.raises (Catching Exceptions)

Ansible modules exit by **raising exceptions**: `AnsibleExitJson` (success) or `AnsibleFailJson` (failure).

### Basic usage

```python
import pytest
from ansible_helpers import AnsibleExitJson, patch_ansible, set_module_args

def test_successful_action(monkeypatch):
    # Setup (abbreviated - see full examples later)
    patch_ansible(monkeypatch)  # Required! Patches exit_json/fail_json
    set_module_args({...})       # Module parameters
    
    # This catches the exception raised by exit_json
    with pytest.raises(AnsibleExitJson) as exc:
        host_action.main()
    
    # After the with block, exc.value is the exception that was raised
    result = exc.value.result
    assert result["changed"] is True
```

**How it works:**
1. `pytest.raises(AnsibleExitJson)` expects an exception to be raised
2. If no exception → test fails ("Expected exception not raised")
3. If exception raised → caught in `exc.value`
4. Access the result dict: `exc.value.result`

### Testing failures

```python
from ansible_helpers import AnsibleFailJson, patch_ansible, set_module_args

def test_fail_when_no_token(monkeypatch):
    # Setup without a token
    patch_ansible(monkeypatch)  # Required!
    set_module_args({"action": "bind", ...})  # No api_token provided
    
    with pytest.raises(AnsibleFailJson) as exc:
        host_action.main()
    
    # Verify the error message
    assert "token" in str(exc.value.result["msg"]).lower()
```

**Where we use it:** Every single test! All module runs end with `exit_json` or `fail_json`.

---

## 4. monkeypatch (The Magic Ingredient)

**monkeypatch** is how we **fake dependencies** so tests don't make real HTTP calls.

### What is it?

`monkeypatch` is a pytest **fixture** (a function that provides test utilities). It replaces real functions with fake ones during tests.

### Why we need it

```python
# Without mocking: this makes a REAL HTTP call to api.openshift.com!
data, info = ai.request(module, "GET", "/clusters", token)

# With mocking: this returns fake data we control
monkeypatch.setattr(ai, "fetch_url", fake_fetch_url)
data, info = ai.request(module, "GET", "/clusters", token)  # Uses fake!
```

**Goal:** Test our module logic without hitting the real API.

### How to use it

```python
def test_something(monkeypatch):  # ← monkeypatch passed as argument
    # Replace ai.fetch_url with our fake
    monkeypatch.setattr(
        ai,           # The module containing the function
        "fetch_url",  # The function name to replace
        fake_function,  # What to replace it with
    )
```

**Pattern in our tests:**

```python
def test_bind_posts_when_unbound(monkeypatch):
    patch_ansible(monkeypatch)  # Patches Ansible internals (always needed)
    
    # Patch environment variables
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    
    # Patch the HTTP client
    calls = []
    monkeypatch.setattr(
        ai,
        "fetch_url",
        queue_fetch_url([
            (200, {"id": "host-1", "status": "known"}),  # Fake response
        ], calls=calls),
    )
```

**Where we use it:** Every test that calls a module function!

---

## 5. Test Fixtures (Helper Functions)

Our tests use several helper functions (from `ansible_helpers.py`):

### patch_ansible(monkeypatch)

```python
patch_ansible(monkeypatch)
```

**What it does:** Patches Ansible's internal argument parsing machinery.  
**When to use:** First line of every test (before anything else).

### set_module_args(args)

```python
set_module_args({
    "action": "bind",
    "infra_env_id": "infra-456",
    "host_id": "host-123",
    "cluster_id": "cluster-789",
    "api_token": "test-token",
})
```

**What it does:** Sets the parameters the module will receive (like playbook vars).  
**When to use:** Before calling `module.main()`.

### queue_fetch_url(responses, calls=None)

```python
calls = []
fake_fetch = queue_fetch_url([
    (200, {"id": "123", "name": "test"}),  # First call returns this
    (201, {"id": "456", "name": "new"}),   # Second call returns this
], calls=calls)

monkeypatch.setattr(ai, "fetch_url", fake_fetch)
```

**What it does:** Creates a fake HTTP client that returns canned responses in sequence.  
**Parameters:**
- `responses`: List of `(status_code, response_body)` tuples
- `calls`: Optional list to record what HTTP calls were made

**When to use:** Every test that makes HTTP calls.

**After the test runs:**

```python
assert len(calls) == 2
assert calls[0]["method"] == "GET"
assert calls[0]["url"] == "https://api.openshift.com/api/assisted-install/v2/hosts/123"
assert calls[1]["method"] == "POST"
```

---

## 6. Assertions

Assertions are how you verify results.

### Basic assertions

```python
# Equality
assert result["changed"] is True
assert result["action"] == "bind"

# Membership
assert "token" in str(error_message).lower()

# Comparisons
assert len(calls) == 3
assert len(calls) > 0

# Truthiness
assert result["host"]  # Fails if host is None or empty dict
```

**Common pattern in our tests:**

```python
with pytest.raises(AnsibleExitJson) as exc:
    host_action.main()

# Access the result
result = exc.value.result

# Make assertions
assert result["changed"] is True
assert result["host"]["id"] == "host-123"
assert result["action"] == "bind"
```

### Assertion failure messages

When an assertion fails, pytest shows:

```
>       assert exc.value.result["changed"] is True
E       AssertionError: assert False is True
E        +  where False = {'changed': False, ...}['changed']
```

**How to read this:**
1. Line that failed: `assert exc.value.result["changed"] is True`
2. What was actually there: `False`
3. Full context: `{'changed': False, ...}`

---

## 7. Our Test Patterns

### Pattern: Idempotency test (run twice)

```python
def test_bind_twice_second_is_noop(monkeypatch):
    """Bind unbound host, then bind again → first changes, second doesn't."""
    calls = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([
        # First run: bind
        (200, {"id": "host-1", "status": "known", "cluster_id": None}),
        (202, {}),
        (200, {"id": "host-1", "status": "known", "cluster_id": "c-1"}),
        # Second run: already bound
        (200, {"id": "host-1", "status": "known", "cluster_id": "c-1"}),
    ], calls=calls))
    
    args = {'infra_env_id': 'infra-1', 'host_id': 'host-1', 
            'action': 'bind', 'cluster_id': 'c-1', 'api_token': 'test-token'}
    
    # First run: should bind
    set_module_args(args)
    with pytest.raises(AnsibleExitJson) as exc:
        host_action.main()
    assert exc.value.result["changed"] is True
    
    # Second run: should be no-op
    set_module_args(args)
    with pytest.raises(AnsibleExitJson) as exc:
        host_action.main()
    assert exc.value.result["changed"] is False
    assert len(calls) == 4  # GET, POST, GET, GET (no second POST!)
```

**Key insight:** Run `set_module_args` and `main()` TWICE in the same test to prove idempotency.

### Pattern: Check mode test

```python
def test_check_mode_does_not_write(monkeypatch):
    """Check mode predicts changes but doesn't POST."""
    calls = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([
        (200, {"id": "host-1", "status": "known", "cluster_id": None}),
    ], calls=calls))
    
    set_module_args({
        'action': 'bind',
        'infra_env_id': 'infra-1',
        'host_id': 'host-1',
        'cluster_id': 'c-1',
        'api_token': 'test-token',
        '_ansible_check_mode': True,  # ← Special parameter
    })
    
    with pytest.raises(AnsibleExitJson) as exc:
        host_action.main()
    
    assert exc.value.result["changed"] is True  # Would change
    assert len(calls) == 1  # Only GET, NO POST
    assert calls[0]["method"] == "GET"
```

**Key insight:** `_ansible_check_mode: True` enables check mode. Verify NO write calls happen.

### Pattern: Verify request body

```python
def test_bind_sends_cluster_id(monkeypatch):
    """Bind action sends cluster_id in POST body."""
    calls = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([
        (200, {"id": "host-1", "status": "known", "cluster_id": None}),
        (202, {}),
        (200, {"id": "host-1", "status": "known", "cluster_id": "c-1"}),
    ], calls=calls))
    
    set_module_args({
        'action': 'bind',
        'infra_env_id': 'infra-1',
        'host_id': 'host-1',
        'cluster_id': 'cluster-789',
        'api_token': 'test-token',
    })
    
    with pytest.raises(AnsibleExitJson):
        host_action.main()
    
    # Verify POST body
    import json
    post_body = json.loads(calls[1]["data"])
    assert post_body["cluster_id"] == "cluster-789"
```

**Key insight:** `calls[N]["data"]` contains the request body as a JSON string.

---

## 8. Reading Test Failures

When a test fails, pytest shows:

```
FAILED tests/unit/plugins/modules/test_host_action.py::test_bind_posts_when_unbound

    def test_bind_posts_when_unbound(monkeypatch):
        # ... setup ...
        
        with pytest.raises(AnsibleExitJson) as exc:
>           host_action.main()

E       Failed: DID NOT RAISE <class 'ansible_helpers.AnsibleExitJson'>
```

**How to read this:**
1. **Test name:** `test_bind_posts_when_unbound`
2. **Line that failed:** `host_action.main()`
3. **Why it failed:** "DID NOT RAISE" - expected exception wasn't raised
4. **What to check:** Did the module fail instead? Check for `fail_json` calls.

Another common failure:

```
>       assert exc.value.result["changed"] is True
E       AssertionError: assert False is True
```

**How to debug:**
1. Print the full result: `print(exc.value.result)`
2. Check what `changed` actually is
3. Look at the module logic - why didn't it change?

---

## 9. Common Pitfalls

### Pitfall: Forgetting to record calls

```python
# WRONG: Can't verify what was called
monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([(200, {})]))

# RIGHT: Pass calls= to record
calls = []
monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([(200, {})], calls=calls))
assert len(calls) == 1  # Now this works!
```

### Pitfall: Wrong number of responses

```python
# WRONG: Only 1 response, but module makes 3 HTTP calls
monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([
    (200, {"id": "123"}),
]))

# This will raise: "queue_fetch_url: ran out of responses"

# RIGHT: Provide enough responses for all calls
monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([
    (200, {"id": "123"}),  # GET
    (202, {}),              # POST
    (200, {"id": "123"}),  # GET again
]))
```

### Pitfall: Not using patch_ansible

```python
# WRONG: Missing patch_ansible
def test_something(monkeypatch):
    monkeypatch.setattr(ai, "fetch_url", ...)
    set_module_args({...})
    host_action.main()  # CRASHES - Ansible internals not patched

# RIGHT: Always call patch_ansible first
def test_something(monkeypatch):
    patch_ansible(monkeypatch)  # ← First!
    monkeypatch.setattr(ai, "fetch_url", ...)
    set_module_args({...})
    host_action.main()  # Works!
```

---

## 10. Coverage (How Well Are We Testing?)

### What is coverage?

**Coverage** measures which lines of code ran during tests.

```bash
# Run tests with coverage
./run.sh --check

# See which lines are missing
ansible-test coverage report --show-missing
```

**Output:**

```
plugins/modules/host_action.py: 94% coverage
  Missing lines: 215, 329, 344
  Missing branches: 196->198 (else branch not taken)
```

**What this means:**
- Lines 215, 329, 344 never ran in any test
- Line 196 has an `if` statement - the `else` branch never ran

### How to improve coverage

1. **Find missing lines:**
   ```bash
   ansible-test coverage report --show-missing
   ```

2. **Write a test that runs those lines:**
   - Line 215 might be an error path - test that error!
   - Missing `else` branch - write a test where that condition is False

3. **Verify coverage improved:**
   ```bash
   ./run.sh --check
   ```

**Goal:** ≥90% coverage (enforced by CI)

---

## 11. Learning Resources

**pytest documentation:**
- [pytest getting started](https://docs.pytest.org/en/latest/getting-started.html)
- [pytest.raises](https://docs.pytest.org/en/latest/how-to/assert.html#assertions-about-expected-exceptions)
- [monkeypatch](https://docs.pytest.org/en/latest/how-to/monkeypatch.html)

**To see these concepts in action:**
- Read `tests/unit/plugins/modules/test_host_action.py` (most complete)
- Read `tests/unit/plugins/modules/test_openshift_version_info.py` (simplest)
- Read `tests/unit/plugins/modules/ansible_helpers.py` (see how fixtures work)

**Practice exercises:**

1. **Write a test** for a function that takes a status and returns whether install is allowed:
   ```python
   def can_install(status):
       return status == "known"
   
   def test_can_install_when_known():
       # Your test here
       ...
   ```

2. **Debug this test** - why does it fail?
   ```python
   def test_bind(monkeypatch):
       patch_ansible(monkeypatch)
       calls = []
       monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([
           (200, {"id": "host-1", "status": "known", "cluster_id": None}),
       ], calls=calls))
       set_module_args({
           "action": "bind",
           "infra_env_id": "infra-1",
           "host_id": "host-1", 
           "cluster_id": "c-1",
           "api_token": "t",
       })
       
       with pytest.raises(AnsibleExitJson):
           host_action.main()
       
       assert calls[1]["method"] == "POST"
   ```
   Hint: How many HTTP calls does bind make?

3. **Which assertion is more idiomatic for booleans?**
   ```python
   # Both work, but which is the Python convention?
   assert exc.value.result["changed"] == True  # works, but...
   assert exc.value.result["changed"] is True  # more idiomatic
   ```
   Hint: `is` checks identity, `==` checks equality. For booleans, `is` is preferred style.

---

## Ready to Write Tests?

✅ **If you understand:** monkeypatch, pytest.raises, queue_fetch_url, and assertions  
✅ **Next step:** Read [testing-cheat-sheet.md](testing-cheat-sheet.md) for the 5 test categories  
✅ **Then:** Copy patterns from `test_host_action.py` and adapt them to your module

**Still confused?** That's okay! Copy an existing test and modify it. Tests are just code!
