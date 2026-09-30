# Running Infra-Env Tests

Complete guide to testing the `infra_env` module against the live API.

---

## Prerequisites

### 1. API Token (Auto-Loaded)
The `offline.token` file is automatically exchanged for a fresh API token when you run `./run.sh shell`.

**Already set up:** ✅ You have `offline.token` in the repo root.

### 2. Pull Secret
Required for state modules (create/modify operations).

**Already set up:** ✅ You have `pull_secret.json` in the repo root.

---

## Available Test Playbooks

### **Test 1: List All Infra-Envs** (Read-Only, Safe)

**File:** `list-infra-envs.yml`

Shows all infrastructure environments in your account.

```bash
./run.sh shell
# Inside container:
ansible-playbook tests/playbooks/list-infra-envs.yml
```

**Output:**
- Count of infra-envs
- Name, ID, cluster binding, CPU arch, OpenShift version for each

**Safe:** Read-only, no mutations.

---

### **Test 2: Query by Name**

**File:** `test-infra-env-query.yml`

Tests the module's lookup functionality.

```bash
./run.sh shell
# Inside container:
ansible-galaxy collection build --force
ansible-galaxy collection install openshift_lab-assisted_installer-*.tar.gz --force
ansible-playbook tests/playbooks/test-infra-env-query.yml
```

**What it tests:**
1. Create infra-env with name "ansible-query-test"
2. Query by same name → finds it (changed=false)
3. Query by different name → creates new (changed=true)
4. Verify both exist with different IDs
5. Cleanup both

**Duration:** ~30 seconds  
**Resources:** Creates 2 infra-envs, deletes both (clean slate at end)

---

### **Test 3: Full Lifecycle**

**File:** `test-infra-env-lifecycle.yml`

Comprehensive create → update → delete test.

```bash
./run.sh shell
# Inside container:
ansible-galaxy collection build --force
ansible-galaxy collection install openshift_lab-assisted_installer-*.tar.gz --force
ansible-playbook tests/playbooks/test-infra-env-lifecycle.yml
```

**What it tests:**
1. Create infra-env "ansible-test-infra-env" (changed=true)
2. Verify it appears in API list
3. Run create again → no-op (changed=false, idempotency)
4. Delete it (changed=true)
5. Verify deletion
6. Delete again → no-op (changed=false, idempotency)

**Duration:** ~30 seconds  
**Resources:** Creates 1 infra-env, deletes it (clean slate at end)

---

### **Test 4: Query by ID** (Raw API)

**File:** `query-infra-env-by-id.yml`

Direct API query by UUID (not using the state module).

```bash
# Step 1: Get an ID
./run.sh shell
ansible-playbook tests/playbooks/list-infra-envs.yml
# Copy an ID from the output

# Step 2: Query that ID
INFRA_ENV_ID="8437d6bf-4ee4-4eba-ad1f-69fcbc927f70" \
  ansible-playbook tests/playbooks/query-infra-env-by-id.yml
```

**What it shows:**
- Full details of a specific infra-env by UUID
- Download URL, expiry, timestamps

**Safe:** Read-only via API.

---

## Quick Test All

Run all tests in sequence:

```bash
./run.sh shell

# Inside container:
# Build and install collection once
ansible-galaxy collection build --force
ansible-galaxy collection install openshift_lab-assisted_installer-*.tar.gz --force

# Test 1: List (baseline)
echo "=== Test 1: List All ==="
ansible-playbook tests/playbooks/list-infra-envs.yml

# Test 2: Query by name
echo "=== Test 2: Query by Name ==="
ansible-playbook tests/playbooks/test-infra-env-query.yml

# Test 3: Full lifecycle
echo "=== Test 3: Full Lifecycle ==="
ansible-playbook tests/playbooks/test-infra-env-lifecycle.yml

# Test 4: List again (verify cleanup)
echo "=== Test 4: Verify Cleanup ==="
ansible-playbook tests/playbooks/list-infra-envs.yml

exit
```

**Total Duration:** ~2 minutes  
**Final State:** Clean (all test resources deleted)

---

## Troubleshooting

### Error: "Pull secret is required"

**Cause:** `pull_secret.json` file not found or empty.

**Fix:**
```bash
# Exit container, verify file exists on host
exit
ls -la pull_secret.json

# Should show ~2700 bytes
# If missing, see PULL_SECRET_SETUP.md
```

### Error: "AI_API_TOKEN environment variable is required"

**Cause:** Token not loaded or expired.

**Fix:**
```bash
# Exit and re-enter shell to get fresh token
exit
./run.sh shell
```

Tokens expire after 15 minutes. Re-entering the shell auto-exchanges your offline token for a fresh one.

### Error: "Module not found"

**Cause:** Collection not installed.

**Fix:**
```bash
# Inside container:
ansible-galaxy collection build --force
ansible-galaxy collection install openshift_lab-assisted_installer-*.tar.gz --force
```

---

## Test Output Interpretation

### Success Indicators
- ✅ Green `ok` or `changed` status
- ✅ All assertions pass
- ✅ Final summary shows "ALL TESTS PASSED"
- ✅ `failed=0` in PLAY RECAP

### What `changed=true` vs `changed=false` Means

**State Modules (infra_env):**
- `changed=true` = Resource was created, modified, or deleted
- `changed=false` = Resource already in desired state (idempotency working)

**Read-Only Operations:**
- Always `changed=false` (queries never mutate)

---

## What Each Test Proves

| Test | Proves |
|------|--------|
| **list-infra-envs** | API connectivity, read access |
| **test-infra-env-query** | Lookup by name, multiple resources, idempotency |
| **test-infra-env-lifecycle** | Create, delete, double-idempotency (create/delete) |
| **query-infra-env-by-id** | Direct API access by UUID |

All together: **The infra_env module correctly implements the state-based pattern against the live API.**

---

## Module Testing Status

| Module | Unit Tests | Live API Tests | Status |
|--------|------------|----------------|--------|
| `openshift_version_info` | ✅ 98% | ✅ Tested (736 versions) | **Production Ready** |
| `supported_operator_info` | ✅ 95% | ✅ Tested (28 operators) | **Production Ready** |
| `infra_env` | ✅ 88% | ✅ Tested (full lifecycle) | **Production Ready** |
| `host_action` | ✅ 94% | ⚠️ Manual only* | Code Complete |

\* `host_action` requires real hardware/VMs to discover hosts. Unit tests verify all logic (bind, unbind, install, reset, idempotency, guards). See `MANUAL_HOST_TESTING.md` for manual testing procedures if you have a test lab.
