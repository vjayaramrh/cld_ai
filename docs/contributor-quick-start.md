# Contributor Quick Start

**Tutorial for new contributors - your first module in 4 weeks!**

> **Official process:** See [CONTRIBUTING.md](../CONTRIBUTING.md) for requirements, testing strategy, and PR workflow.  
> **Design rationale:** See [DESIGN.md](../DESIGN.md) for idempotency patterns and architecture decisions.

---

## 🎯 What We're Building

Ansible modules that automate OpenShift cluster deployment via the Red Hat Assisted Installer API.

**Result:** Infrastructure-as-code instead of clicking through UIs.

**Current status:** 2 modules done, 5 remaining in Phase 1.

---

## 🚀 Your First Module (4-week plan)

### Week 1: Get Familiar

**Goal:** Understand the codebase and tooling

```bash
# Clone and verify setup works
git clone https://github.com/vjayaramrh/cld_ai.git
cd cld_ai
./run.sh --check   # Expected: passed: 4 failed: 0
```

**Read in order:**
1. [CLAUDE.md](../CLAUDE.md) - conventions (15 min)
2. [DESIGN.md](../DESIGN.md) - patterns (15 min)
3. [CONTRIBUTING.md](../CONTRIBUTING.md) - workflow (10 min)
4. `plugins/modules/openshift_version_info.py` - simplest module (59 lines)
5. `tests/unit/plugins/modules/test_openshift_version_info.py` - simplest tests

**By end of week:**
- [ ] Can run `./run.sh --check` successfully
- [ ] Understand the 3 module types (info, state, action)
- [ ] Know where tests go and what the 5 categories are

---

### Week 2: Claim & Scaffold

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

**By end of week:**
- [ ] Issue claimed and assigned
- [ ] Skeleton code generated
- [ ] Know what API endpoint you're wrapping

---

### Week 3: Implement & Test

**Goal:** Write the module and get to 90% coverage

**For info modules (easiest):**
1. Update the GET endpoint URL
2. Add any filter parameters (if the API supports them)
3. Write the DOCUMENTATION block (parameters, return values)
4. Write EXAMPLES showing: basic query, filtered query, register + debug
5. Write tests for the 5 categories (see [CONTRIBUTING.md](../CONTRIBUTING.md))

**Run the checks:**
```bash
./run.sh --check   # Must pass before PR
```

**Get help:**
- Compare against `openshift_version_info.py` (reference implementation for info modules)
- Compare against `infra_env.py` (reference implementation for state modules)
- Check test examples in `tests/unit/plugins/modules/`

**By end of week:**
- [ ] Module code complete
- [ ] Tests written and passing
- [ ] Coverage ≥90%
- [ ] `./run.sh --check` passes

---

### Week 4: Submit & Iterate

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

**By end of week:**
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

For manual verification against the real API, see [CONTRIBUTING.md](../CONTRIBUTING.md#manual-verification-against-the-live-api).

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

1. Week 1: Read docs, run `./run.sh --check`
2. Week 2: Claim issue #9 or #10, scaffold the module
3. Week 3: Implement and test (≥90% coverage)
4. Week 4: Open PR, address reviews, merge!

**First module is the hardest - you've got this! 🎉**
