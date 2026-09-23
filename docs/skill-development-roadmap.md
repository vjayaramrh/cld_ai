# Skill Development Roadmap

Tracking skill gaps identified from [Ansible Developer Guide](https://docs.ansible.com/projects/ansible/latest/dev_guide/index.html) analysis on 2026-09-22.

## Current Skills ✅

| Skill | Purpose | Status |
|-------|---------|--------|
| `new-ansible-module` | Generic module scaffolding (state/value-based patterns) | ✅ Updated |
| `new-ai-endpoint-module` | Assisted Installer API-specific module scaffolding | ✅ Exists |
| `ansible-module-documentation` | Comprehensive module documentation standards (DOCUMENTATION/EXAMPLES/RETURN) | ✅ Created |
| `ansible-module-testing` | Testing guide (sanity/unit/integration, mocking, coverage) | ✅ Created |
| `ansible-collection-structure` | Collection directory structure and metadata (galaxy.yml, runtime.yml) | ✅ Created |
| `k8s-ansible-skill` | Kubernetes cluster deployment with Ansible | ✅ Exists (different domain) |

---

## High Priority Skills (Create Before cluster_info Implementation)

### 1. ansible-module-documentation ⭐ MOST URGENT
**Status:** ✅ Created  
**Source:** [Module format and documentation](https://docs.ansible.com/projects/ansible/latest/dev_guide/developing_modules_documenting.html)

**Coverage:**
- DOCUMENTATION block structure and required fields
- EXAMPLES thoroughness by module type (info/state/action)
- RETURN block standards (`elements` attribute, no polymorphic types)
- Ansible markup (C(), O(), V(), E(), U(), B())
- Short description rules (no trailing period)
- Common pitfalls (avoid `type: raw`, static return structures)

**Triggers:**
- "How do I document my module?"
- "ansible module documentation standards"
- Before writing any new module

**Why urgent:** Addresses issue #49, prevents documentation mistakes

---

### 2. ansible-module-testing
**Status:** ✅ Created  
**Source:** [Testing Ansible and Collections](https://docs.ansible.com/projects/ansible/latest/dev_guide/testing.html)

**Coverage:**
- Sanity tests (`ansible-test sanity`) - what they check
- Unit tests (`ansible-test units`) - mocking patterns, conftest setup
- Integration tests (`ansible-test integration`) - when/how to write them
- Coverage requirements (≥90% for this project)
- Running tests locally vs. CI
- Debugging test failures

**Triggers:**
- "How do I test my module?"
- "ansible-test sanity failing"
- "write unit tests"
- "integration test setup"

**Why important:** Critical for quality, DESIGN.md §7 requires comprehensive testing

---

### 3. ansible-collection-structure
**Status:** ✅ Created  
**Source:** [Developing collections](https://docs.ansible.com/projects/ansible/latest/dev_guide/developing_collections.html)

**Coverage:**
- Collection directory tree (`plugins/`, `tests/`, `meta/`, etc.)
- `galaxy.yml` configuration (namespace, name, version, dependencies)
- `meta/runtime.yml` (ansible-core support matrix)
- Namespace/name conventions (must match directory path)
- Where to put modules, module_utils, tests
- README.md and CHANGELOG.md requirements

**Triggers:**
- "collection directory structure"
- "where do I put my module?"
- "galaxy.yml configuration"
- New contributor onboarding

**Why important:** Helps contributors navigate the codebase

---

## Medium Priority Skills (Create As Needed)

### 4. ansible-module-security
**Status:** 💭 Deferred  
**Source:** [Module security](https://docs.ansible.com/projects/ansible/latest/dev_guide/developing_modules_security.html)

**Coverage:**
- `no_log=True` for secrets
- Command injection prevention
- Input validation best practices
- Secure HTTP/API calls
- Write-only fields (pull_secret, tokens)

**Triggers:**
- "handle secrets securely"
- "module security best practices"
- Before handling new secret types

---

### 5. ansible-module-debugging
**Status:** 💭 Deferred  
**Source:** [Debugging modules](https://docs.ansible.com/projects/ansible/latest/dev_guide/debugging.html)

**Coverage:**
- Local testing with `ansible localhost -m`
- Using pdb/ipdb for debugging
- Common failure modes
- Log inspection (`ansible-test` output)
- Troubleshooting sanity/unit failures

**Triggers:**
- "my module fails"
- "how to debug ansible module"
- "pdb debugging ansible"

---

### 6. ansible-integration-tests
**Status:** 💭 Deferred  
**Source:** [Integration tests](https://docs.ansible.com/projects/ansible/latest/dev_guide/testing_integration.html)

**Coverage:**
- Integration test structure (`tests/integration/targets/`)
- Local mock server setup (avoid hitting prod API)
- `base_url` override pattern
- CI integration job configuration
- When to write integration tests (state/action modules)

**Triggers:**
- "integration test setup"
- "mock server for testing"
- Before implementing first state module

---

## Low Priority Skills (Future)

### 7. ansible-module-deprecation
**Status:** 💤 Not needed yet  
**Source:** [Ansible deprecation cycle](https://docs.ansible.com/projects/ansible/latest/dev_guide/module_lifecycle.html)

**When needed:** When deprecating parameters or modules

---

### 8. ansible-collection-distribution
**Status:** 💤 Not needed yet  
**Source:** [Publishing collections to Galaxy](https://docs.ansible.com/projects/ansible/latest/dev_guide/developing_collections_distributing.html)

**When needed:** When ready to publish to Ansible Galaxy (Phase 2+)

---

## Execution Plan

### Phase 1: Documentation Standards (Complete)
- [x] Analyze Ansible developer guide
- [x] Identify skill gaps
- [x] **Update `new-ansible-module` skill** (add `elements`, return consistency)
- [x] **Create `ansible-module-documentation` skill**
- [x] **Create `ansible-module-testing` skill**
- [x] **Create `ansible-collection-structure` skill**

### Phase 2: Implementation
- [ ] Implement `cluster_info` module (issue #10) using new standards
- [ ] Validate skills during implementation
- [ ] Document any additional gaps discovered

### Phase 3: As Needed
- Create medium/low priority skills when contributors encounter those topics

---

## Tracking

**Created:** 2026-09-22  
**Last updated:** 2026-09-22  
**Related issues:** #49 (elements attribute), #47 (env_fallback), #48 (polymorphic return)  
**Related files:** `.claude/skills/new-ansible-module/SKILL.md`

---

## Decision Log

**2026-09-22:** Chose Option B (create skills first, then implement cluster_info)
- **Rationale:** Having comprehensive guides before implementation prevents mistakes
- **Alternative considered:** Implement first, document learnings after (Option A)
