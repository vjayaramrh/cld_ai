# Python Primer for Ansible Module Authors

**Goal:** Learn the Python constructs actually used in this collection's modules.

This is NOT a complete Python tutorial. It covers only what you'll encounter in
`host_action.py`, `infra_env.py`, and `openshift_version_info.py`.

**New to Python?** Complete a basic Python tutorial first (variables, functions, if/else).
**Know Python but rusty?** Use this as a quick refresher for Ansible-specific patterns.

---

## Self-Assessment

Before starting, check your Python knowledge:

- [ ] I can create and access dictionaries
- [ ] I know the difference between `is` and `==`
- [ ] I understand truthiness (when `if x:` evaluates to True/False)
- [ ] I can use f-strings for formatting
- [ ] I know what a function is and how to call one

**All checked?** You're ready to contribute!  
**Some unchecked?** Read the sections below for those topics.

---

## 1. Dictionaries (Most Important!)

Ansible modules are **dictionary-heavy**. Everything is a dict: `argument_spec`, `params`, API responses.

### Creating dictionaries

```python
# Two equivalent ways
params = {"name": "test", "state": "present"}
params = dict(name="test", state="present")

# Nested (used in argument_spec)
argument_spec = dict(
    name=dict(type="str", required=True),
    state=dict(type="str", choices=["present", "absent"], default="present"),
)
```

**Where we use it:** `argument_spec` in every module (see `run_module()` in host_action.py)

### Accessing values

```python
# Unsafe: KeyError if missing
name = params["name"]

# Safe: returns None if missing
name = params.get("name")

# Safe with default
timeout = params.get("timeout", 30)
```

**Where we use it:** Everywhere! Safe access with `.get()` for optional params, direct access with `["key"]` for params with defaults in argument_spec.

### Checking membership

```python
if "name" in params:
    print(f"Name is {params['name']}")

# Common pattern: check if optional param was provided
if "cluster_id" in params and params["cluster_id"]:
    bind_to_cluster(params["cluster_id"])
```

**Where we use it:** Checking optional parameters before using them.

### Iterating

```python
# Just keys
for key in params:
    print(key)

# Keys and values together
for key, value in params.items():
    print(f"{key} = {value}")
```

**Where we use it:** Building request bodies, comparing dicts for drift detection.

---

## 2. String Formatting

### f-strings (Modern, Preferred)

```python
name = "test-cluster"
version = "4.16"
msg = f"Creating cluster {name} with version {version}"
# Result: "Creating cluster test-cluster with version 4.16"

# Building URLs
path = f"/infra-envs/{infra_env_id}/hosts/{host_id}"

# In error messages
module.fail_json(msg=f"Host is bound to cluster {cluster_id}. Unbind it first.")
```

**Where we use it:** Error messages, URLs, logging throughout all modules.

### String methods

```python
status = "INSTALLING"
status.lower()              # "installing"
status.upper()              # "INSTALLING"

"bind" in "/actions/bind"   # True (substring check)

sources = "source1,source2,source3"
sources.split(",")          # ["source1", "source2", "source3"]

# Joining list elements into a string
statuses = ["known", "discovering"]
", ".join(statuses)         # "known, discovering"

# Direct interpolation (what Python does with f-strings)
f"Valid statuses: {statuses}"  # "Valid statuses: ['known', 'discovering']"
```

**Where we use it:**
- `status.lower()` in `needs_action()` function (host_action.py)
- Building error messages with `", ".join(valid_statuses)`

---

## 3. Conditionals and Boolean Logic

### Basic if/elif/else

```python
if status == "known":
    proceed_with_install()
elif status in ["installing", "installed"]:
    module.exit_json(changed=False, msg="Already installing/installed")
else:
    module.fail_json(msg=f"Cannot install from status {status}")
```

**Where we use it:** Everywhere! Especially in `needs_action()` functions.

### Guard clauses (early return pattern)

```python
# Common Ansible pattern: fail early if conditions not met
def needs_action(module, host, action, params):
    # Extract values first
    cluster_id = params.get("cluster_id")
    status = host.get("status", "").lower()
    valid_statuses = ["known", "discovering", "disconnected"]
    
    # Then validate (fail early if conditions not met)
    if not cluster_id:
        module.fail_json(msg="cluster_id required for bind action")
        # Never reaches here - fail_json exits
    
    if status not in valid_statuses:
        module.fail_json(msg=f"Cannot bind host in status '{status}'")
        # Never reaches here
    
    # If we get here, all validations passed
    return True, "Ready to proceed"
```

**Where we use it:** `needs_action()` function in host_action.py (validates action preconditions).

### Truthiness (Important!)

In Python, these are "falsy" (evaluate to False):
- `None`
- `False`
- `0` (the number zero)
- `""` (empty string)
- `[]` (empty list)
- `{}` (empty dict)

Everything else is "truthy" (evaluates to True).

```python
# Common pattern: check if value was provided
if cluster_id:  # True if cluster_id is not None and not ""
    bind_to_cluster(cluster_id)

# DANGER: This fails when count is 0 (which might be valid!)
if count:
    return count * 2
# Better:
if count is not None:
    return count * 2
```

**Where we use it:**
- Checking optional parameters: `if cluster_id:` throughout modules
- **Watch out for:** Don't use truthiness when 0 is a valid value!

---

## 4. None and Comparisons

### is vs ==

```python
# Use 'is' for None checks
if cluster_id is None:
    print("Not bound to any cluster")

if cluster_id is not None:
    print(f"Bound to {cluster_id}")

# Use '==' for value comparison
if status == "known":
    print("Host is ready")
```

**Why?** `None` is a singleton object. `is` checks identity (same object), `==` checks value equality.

**Where we use it:**
- Checking if host is bound: `if cluster_id is not None` in `needs_action()` (host_action.py)
- Everywhere we check for optional parameters

---

## 5. Functions

### Defining functions

```python
def needs_action(module, host, action, params):
    """
    Determine if the requested action needs to be performed.
    
    Returns: (bool, str) - (needs_action, reason)
    """
    status = host.get("status", "").lower()
    cluster_id = host.get("cluster_id")
    
    if action == "bind":
        # ... logic ...
        return True, "Ready to bind"
    
    return False, "Already in target state"
```

**Key points:**
- Docstrings explain what the function does
- `return` statement exits the function
- Can return multiple values (tuple): `return True, "reason"`

**Where we use it:**
- `needs_action()` in host_action.py
- `run_module()` in all modules (the main logic)

### Calling functions

```python
# Positional arguments
action_needed, reason = needs_action(module, host, "bind", params)

# Keyword arguments (more readable)
data, info = ai.request(
    module,
    "GET",
    "/clusters",
    token,
    timeout=30,
    base_url=None,
)
```

**Where we use it:** Calling `ai.request()` throughout all modules.

---

## 6. List Operations

### Checking membership

```python
valid_statuses = ["discovering", "known", "disconnected"]

if status in valid_statuses:
    print("Status is valid")
else:
    module.fail_json(msg=f"Invalid status: {status}")
```

**Where we use it:** Valid status checking in `needs_action()` bind guard (host_action.py)

### List comprehensions

```python
# Transform a list
calls = [{"method": "GET"}, {"method": "POST"}, {"method": "GET"}]
methods = [c["method"] for c in calls]
# Result: ["GET", "POST", "GET"]

# Same as:
methods = []
for c in calls:
    methods.append(c["method"])
```

**Where we use it:**
- Extracting fields from lists
- Building request bodies
- Test assertions

---

## 7. Common Patterns in Our Modules

### Pattern: Ternary operator

```python
# Instead of:
if body:
    data = body
else:
    data = None

# Write:
data = body if body else None

# Or:
changed = True if action_needed else False
```

**Where we use it:** Optional request body in `ai.request()` call (host_action.py)

### Pattern: Unpacking

```python
# Functions can return multiple values
data, info = ai.request(module, "GET", path, token)
# data = first return value
# info = second return value

needs_bind, reason = needs_action(module, host, "bind", params)
```

**Where we use it:** Every `ai.request()` call returns `(data, info)`

### Pattern: Default arguments

```python
def request(module, method, path, token, body=None, query=None):
    # body and query are optional (default to None)
    if body:
        # Only runs if body was provided
        ...
```

**Where we use it:** `ai.request()` in module_utils/assisted_installer.py

---

## 8. What You DON'T Need

These Python features are **NOT used** in our modules:

- ❌ Classes (we use functions and dicts)
- ❌ Async/await
- ❌ Decorators (except `@pytest` in tests)
- ❌ Generators / `yield`
- ❌ Type hints (Ansible doesn't use them)
- ❌ Regular expressions (minimal use)
- ❌ File I/O (modules use `fetch_url`, not `open()`)

**Focus on:** dictionaries, strings, conditionals, functions. That's 90% of what you'll see.

---

## 9. Common Pitfalls

### Pitfall: Mutable default arguments

```python
# WRONG (default list is shared across all calls!)
def add_item(items=[]):
    items.append("x")
    return items

# First call: ["x"]
# Second call: ["x", "x"]  <-- UNEXPECTED!

# RIGHT
def add_item(items=None):
    if items is None:
        items = []
    items.append("x")
    return items
```

**Why it matters:** Default mutable arguments are shared across calls—avoid them!

### Pitfall: Truthiness with numbers

```python
count = 0

# WRONG: 0 is falsy, so this skips valid data!
if count:
    return count * 2

# RIGHT: explicit check
if count is not None:
    return count * 2
```

**Why it matters:** When 0 is a valid value, use explicit `is not None`.

### Pitfall: Dictionary access

```python
# WRONG: crashes if 'status' key doesn't exist
status = host["status"]

# RIGHT: returns None if missing
status = host.get("status")

# BETTER: provide a default
status = host.get("status", "unknown")
```

**Why it matters:** API responses might not always include every field.

---

## 10. Learning Resources

**For topics in this primer:**
- [Real Python: Dictionaries](https://realpython.com/python-dicts/) - Comprehensive guide
- [Python docs: String formatting](https://docs.python.org/3/tutorial/inputoutput.html#formatted-string-literals) - f-strings official docs
- [Real Python: None](https://realpython.com/null-in-python/) - Understanding None and is vs ==

**To see these concepts in action:**
- Read `plugins/modules/host_action.py` (simplest action module)
- Read `plugins/modules/openshift_version_info.py` (simplest info module)
- Read `plugins/modules/infra_env.py` (state module, more complex)

**Practice exercises:**

1. **Dictionary exercise:** Write an `argument_spec` for a module with 3 params (one required, one with choices, one with a default)
2. **Conditionals exercise:** Write a function that takes a status string and returns whether installation is allowed
3. **Truthiness exercise:** Find the bug in this code:
   ```python
   def get_count(params):
       count = params.get("count", 10)
       if count:
           return count
       return 10
   ```
   Hint: What happens when `count=0`?

---

## Ready to Contribute?

✅ **If you understand:** dictionaries, f-strings, if/else, `is` vs `==`, and functions  
✅ **Next step:** Read [pytest-primer.md](pytest-primer.md) to learn our testing patterns  
✅ **Then:** Read [DESIGN.md](../DESIGN.md) to understand the three idempotency patterns

**Still confused?** That's okay! Copy patterns from existing modules and ask questions in your PR.
