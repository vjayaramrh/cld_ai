# Manual Smoke Tests (Live API)

**⚠️ WARNING:** These playbooks create/delete **real resources** on the live OpenShift Assisted Installer API (`api.openshift.com`). They require real credentials and **should never be automated in CI**.

---

## Purpose

These are **manual smoke tests** for validating modules against the live API during development. They are **not** the primary test suite (unit tests and mock-server integration tests are).

## Why Separate from tests/?

Per DESIGN.md §8 and CLAUDE.md:
- **Integration tests** run against a **local mock HTTP server** (no credentials, no network egress)
- **These playbooks** hit the **live production API** (real credentials, real resources)

The module is designed with a `base_url` override specifically to support mock-server integration. These live API tests do **not** use that pattern and therefore:
- Cannot run in CI (no credentials in CI, ever)
- Cannot be automated without risk
- Are purely for manual validation/debugging

## Available Playbooks

### Read-Only (Safe)
- `list-infra-envs.yml` - List all infrastructure environments in your account

### State-Mutating (Creates/Deletes Real Resources)
- `test-infra-env-lifecycle.yml` - Full create → delete lifecycle test
- `test-infra-env-query.yml` - Query by name test (creates 2, deletes 2)
- `query-infra-env-by-id.yml` - Query specific infra-env by UUID
- `debug-create-infra-env.yml` - Debug helper for testing creation

---

## Prerequisites

1. **API Token:** Automatic via `offline.token` file (see `../../PULL_SECRET_SETUP.md`)
2. **Pull Secret:** Required for state-mutating tests (see `../../PULL_SECRET_SETUP.md`)

---

## Usage

```bash
# Enter container
../../run.sh shell

# Inside container, build and install collection
ansible-galaxy collection build --force
ansible-galaxy collection install openshift_lab-assisted_installer-*.tar.gz --force

# Run a manual smoke test
ansible-playbook scripts/manual-smoke/list-infra-envs.yml
```

---

## Important Notes

### These Are NOT the Test Suite

The **actual test suite** lives in `tests/`:
- **Unit tests:** `tests/unit/` - 94% coverage, all modules
- **Integration tests:** `tests/integration/` - Mock server (to be built per DESIGN.md §8)

### Cleanup Responsibility

**You are responsible for cleanup.** If a playbook fails mid-run, it may leave orphaned resources in your account. Always verify cleanup:

```bash
ansible-playbook scripts/manual-smoke/list-infra-envs.yml
# Should show 0 infra-envs after tests complete
```

### Cost Warning

These tests create real infrastructure environments. While infra-envs themselves are free, they generate ISO download URLs and consume API quota. Be mindful of:
- Running tests repeatedly
- Leaving resources uncleaned
- Running tests in production accounts

---

## When to Use These

✅ **Use when:**
- Manually validating a module change before PR
- Debugging unexpected live API behavior
- Verifying credentials/auth setup

❌ **Don't use when:**
- Running automated tests (use unit tests + mock integration)
- Testing in CI (forbidden - no credentials in CI)
- Testing core logic (use unit tests - 94% coverage)

---

## Relation to DESIGN.md §8

DESIGN.md §8 specifies that integration tests:
- Run against a **local mock HTTP server**
- Use the `base_url` override to redirect API calls to localhost
- Never contact `api.openshift.com`
- Never require credentials

These manual smoke tests are **supplemental** - they verify behavior against the real API but are **not a substitute** for the DESIGN §8 integration tests.

The planned integration test structure:
```
tests/integration/
  targets/
    infra_env/
      tasks/
        main.yml  # Tests against mock server (base_url: http://127.0.0.1:8080)
```

---

## See Also

- `tests/playbooks/RUN_TESTS.md` - Info module testing (read-only, safe)
- `tests/playbooks/MANUAL_HOST_TESTING.md` - host_action manual testing (requires VMs)
- `../../PULL_SECRET_SETUP.md` - Credential setup guide
