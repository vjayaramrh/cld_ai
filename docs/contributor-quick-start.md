# Contributor Quick Start

**Step-by-step guide to your first module contribution.**

> **Time estimate:** Most people complete these steps in 1-4 weeks, depending on
> their background. Go at your own pace—some steps might take hours, others days.

> **Official process:** See [CONTRIBUTING.md](../CONTRIBUTING.md) for requirements, testing strategy, and PR workflow.  
> **Design rationale:** See [DESIGN.md](../DESIGN.md) for idempotency patterns and architecture decisions.

---

## 🎯 What We're Building

Ansible modules that automate OpenShift cluster deployment via the Red Hat Assisted Installer API.

**Result:** Infrastructure-as-code instead of clicking through UIs.

**Current status:** 3 modules done (info, state, action), 4 remaining in Phase 1.

---

## Prerequisites

Before you start, make sure you have:

- [ ] **Basic Python knowledge** - variables, functions, if/else statements
- [ ] **Git installed and configured**
- [ ] **Docker or Podman** installed

**New to Ansible module development?** Start with the 
[ansible-module-workshop](https://github.com/vjayaramrh/ansible-module-workshop) 
to learn module fundamentals (argument_spec, exit_json, idempotency). Then come 
back here to apply those concepts to this collection.

**Know Ansible modules but new to this codebase?** Jump straight to Step 1 below.

---

## 🚀 Your First Module (Step-by-Step)

### Step 1: Learn the Foundations

**Goal:** Understand the tools and patterns used in this codebase.

**First, clone and verify setup works:**

```bash
git clone https://github.com/vjayaramrh/cld_ai.git
cd cld_ai
./run.sh --check   # Expected: passed: 4 failed: 0
```

**Then, read these primers (in order):**

1. **[python-primer.md](python-primer.md)** - Python constructs we actually use (30 min)
   - Dictionaries, f-strings, truthiness, guard clauses
   - Self-assessment checklist to verify you're ready
   
2. **[pytest-primer.md](pytest-primer.md)** - How our tests work (30 min)
   - monkeypatch, pytest.raises, queue_fetch_url
   - Reading test failures, coverage interpretation

3. **[DESIGN.md](../DESIGN.md)** - Architecture and idempotency patterns (20 min)
   - Three patterns: info (read-only), state (declarative), action (RPC verbs)
   - Per-resource classification

4. **[CLAUDE.md](../CLAUDE.md)** - Coding conventions (20 min)
   - Module requirements, testing rules, verification checklist
   - What to check before committing

5. **[testing-cheat-sheet.md](testing-cheat-sheet.md)** - Quick reference (10 min)
   - The 5 test categories with code examples
   - Common patterns you'll copy-paste

**Then, read example code:**

6. `plugins/modules/openshift_version_info.py` - Simplest info module (59 lines)
7. `tests/unit/plugins/modules/test_openshift_version_info.py` - Simplest tests
8. `plugins/modules/host_action.py` - Reference action module (shows guard-on-status pattern)

**Verify you're ready:**

- [ ] Can run `./run.sh --check` successfully
- [ ] Can explain what `monkeypatch` does
- [ ] Can identify the 3 idempotency patterns (info, state, action)
- [ ] Know what the 5 test categories are
- [ ] Understand what `queue_fetch_url` is for

**Time estimate:** 2-4 hours for reading + running verification

---

### Step 2: Claim & Scaffold

**Goal:** Choose your module and generate the skeleton

**Pick an issue:** https://github.com/users/vjayaramrh/projects/2

| Module | Difficulty | Type | Issue |
|--------|-----------|------|-------|
| `support_level_info` | 🟢 Easiest | Info | #12 |
| `supported_operator_info` | 🟢 Easiest | Info | #13 |
| `cluster_info` | 🟡 Medium | Info | #10 |

**Recommendation:** Start with #12 or #13 (read-only, no state management)

**Claim it:**
1. Go to the issue
2. Comment "I'll work on this"
3. Assign to yourself

**Scaffold it:**

Option A - Claude Code (faster):
```
/new-ai-endpoint-module
```

Option B - Manual copy:
```bash
cp plugins/modules/openshift_version_info.py plugins/modules/YOUR_MODULE.py
cp tests/unit/plugins/modules/test_openshift_version_info.py \
   tests/unit/plugins/modules/test_YOUR_MODULE.py
```

**Read the API spec** for your endpoint (see `docs/api-endpoint-map.md`)

**Checkpoint - you're ready for the next step when:**
- [ ] Issue claimed and assigned
- [ ] Skeleton code generated
- [ ] Know what API endpoint you're wrapping

---

### Step 3: Implement & Test

**Goal:** Write the module and get to 90% coverage

**For info modules (easiest):**
1. Update the GET endpoint URL
2. Add any filter parameters (if the API supports them)
3. Write the DOCUMENTATION block (parameters, return values)
4. Write EXAMPLES showing: basic query, filtered query, register + debug
5. Write tests for the 5 categories (see [testing-cheat-sheet.md](testing-cheat-sheet.md) for patterns)

**Run the checks:**
```bash
./run.sh --check   # Must pass before PR
```

**Get help:**
- Compare against `openshift_version_info.py` (reference implementation for info modules)
- Compare against `infra_env.py` (reference implementation for state modules)
- Check test examples in `tests/unit/plugins/modules/`

**Checkpoint - you're ready for the next step when:**
- [ ] Module code complete
- [ ] Tests written and passing
- [ ] Coverage ≥90%
- [ ] `./run.sh --check` passes

---

### Step 4: Submit & Iterate

**Goal:** Open PR and address reviews

```bash
git checkout -b module/YOUR_MODULE
git add plugins/modules/YOUR_MODULE.py tests/unit/plugins/modules/test_YOUR_MODULE.py
git commit -m "Add YOUR_MODULE module"
git push origin module/YOUR_MODULE
```

**Open PR on GitHub:**
- Title: "Add YOUR_MODULE module"
- Body: Use the template, link to issue with "Closes #N"
- Wait for CI (all required checks must pass)
- Wait for CodeRabbit review
- Address any comments

**Review process:**
1. CodeRabbit reviews automatically (usually within minutes)
2. Address automated findings
3. Human reviews (requires 1 approval to merge)
4. Merge! The issue auto-closes

**Checkpoint - you're ready for the next step when:**
- [ ] PR opened and linked to issue
- [ ] All CI checks green
- [ ] Review comments addressed
- [ ] Merged! 🎉

---

## 🛠️ Command Cheat Sheet

```bash
# Setup
./run.sh --check              # Build + sanity + units + coverage

# Development
./run.sh                      # Interactive shell in container
ansible-test units --coverage tests/unit/plugins/modules/test_YOUR_MODULE.py

# Coverage
ansible-test units --coverage
ansible-test coverage report --show-missing

# Manual verification (optional but recommended)
ansible-galaxy collection build --force
ansible-galaxy collection install ./openshift_lab-assisted_installer-*.tar.gz --force
```

See [CONTRIBUTING.md](../CONTRIBUTING.md) for manual API verification workflow.

---

## ❓ Common Questions

### "Do I need to use Claude Code?"

**No!** It's completely optional. You can write modules manually by copying from existing examples.

**Claude Code helps because:**
- Knows the conventions (reads CLAUDE.md automatically)
- Generates boilerplate fast with `/new-ai-endpoint-module`
- Runs tests for you

**But:** You're still responsible for understanding and verifying the code!

---

### "How do I test without hitting the real API?"

We mock at the `fetch_url` layer - see examples in `tests/unit/plugins/modules/test_infra_env.py`:

```python
from ansible_helpers import queue_fetch_url

calls = []
monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([
    (200, [{"id": "123", "name": "test"}]),  # GET response
    (201, {"id": "123"}),                     # POST response
], calls=calls))
```

**No live credentials needed** - all unit tests run offline!

See [testing-cheat-sheet.md](testing-cheat-sheet.md) for complete test patterns and examples. For manual verification against the real API, see [CONTRIBUTING.md](../CONTRIBUTING.md#manual-verification-against-the-live-api).

---

### "What if I break something?"

**You can't!** Here's why:

1. ❌ Can't push directly to `main` (branch protection)
2. ✅ All PRs require passing CI checks (sanity, units, lint, security)
3. ✅ All PRs require human approval
4. ✅ Tests run in isolation (mocked API)
5. ✅ Squash-merge keeps history clean

**Worst case:** Your PR fails CI → you fix it → try again. The `main` branch stays green.

---

### "How long does it take to add a module?"

**Realistic estimates:**

| Type | First time | Second time |
|------|-----------|-------------|
| Info module | 4-6 hours | 2-3 hours |
| State module (simple) | 8-12 hours | 4-6 hours |
| State module (complex) | 16-20 hours | 8-12 hours |

**First module has a learning curve** - you're learning the patterns, tooling, and API. Second module is much faster!

---

### "Where do I get help?"

**Self-service:**
1. Read existing modules (`openshift_version_info.py` for info, `infra_env.py` for state)
2. Read the test files for examples
3. Check [CONTRIBUTING.md](../CONTRIBUTING.md) for official requirements

**Ask humans:**
1. Comment on your issue
2. Ask in PR review comments

**Pair up:**
- Two people working together on the first module = faster learning + more fun!

---

## 📋 Module Types Quick Reference

See [DESIGN.md](../DESIGN.md#4-idempotency-model-per-resource-kind) for full details.

**🟦 Info modules:** Read-only, always `changed=False`  
**🟩 State modules:** `state: present/absent`, observe → compare → reconcile  
**🟧 Action modules:** RPC verbs, guard on current status before acting

---

## 🎯 What Success Looks Like

After Phase 1 (7 modules), users can write playbooks like this:

```yaml
---
- name: Deploy OpenShift cluster
  hosts: localhost
  tasks:
    - name: Get available OpenShift versions
      openshift_lab.assisted_installer.openshift_version_info:
      register: versions

    - name: Create infrastructure environment
      openshift_lab.assisted_installer.infra_env:
        name: prod-infra
        openshift_version: "4.16"
        pull_secret: "{{ lookup('env', 'PULL_SECRET') }}"
        state: present
      register: infra

    - name: Create cluster
      openshift_lab.assisted_installer.cluster:
        name: prod-cluster
        openshift_version: "4.16"
        base_dns_domain: example.com
        state: present

    - name: Download discovery ISO
      get_url:
        url: "{{ infra.infra_env.download_url }}"
        dest: /tmp/discovery.iso
```

**Zero manual clicking!** Pure infrastructure-as-code.

---

## 🔗 Essential Links

- **Repo:** https://github.com/vjayaramrh/cld_ai
- **Project Board:** https://github.com/users/vjayaramrh/projects/2
- **API Spec:** https://api.openshift.com/api/assisted-install/v2/openapi
- **OpenAPI Endpoint Map:** [docs/api-endpoint-map.md](api-endpoint-map.md)

---

## 🚀 Ready to Start?

**Quick summary - the path ahead:**

1. **Step 1:** Learn foundations (2-4 hours) → Read primers, verify setup works
2. **Step 2:** Claim & scaffold (1-2 hours) → Pick an issue, generate skeleton
3. **Step 3:** Implement & test (4-12 hours) → Write code, reach 90% coverage
4. **Step 4:** Submit & iterate (2-6 hours) → Open PR, address reviews, merge!

**Total time:** 1-4 weeks depending on your pace and prior experience.

**First module is the hardest** - you're learning the patterns, tooling, and API.  
**Second module is much faster** - you already know the workflow!

**You've got this! 🎉**
