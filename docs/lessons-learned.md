# Lessons Learned

A chronological journal of issues discovered, resolutions implemented, and lessons learned during development of the `openshift_lab.assisted_installer` collection.

**Format:** Each entry documents what went wrong, how we fixed it, and what to do differently going forward.

---

## 2026-09-30: A Validation Error Message Leaked the Secret It Was Guarding

**Issue:** PR #54 added a check to `_validate_base_url` that rejects a `base_url`
carrying embedded credentials (`https://user:pass@host`) — the whole point being to
*prevent* credential leakage. CodeRabbit found the fix itself leaked: for
`https://user:pass@` (credentials, **no host**), `urlparse()` returns no hostname
but keeps the credentials, so the pre-existing hostname check ran first and raised
`"base_url must include a hostname, got: %s" % url` — echoing the full URL, password
and all, straight into `fail_json`.

**Root cause (three things lined up):**
1. A validation **error message echoed the raw, secret-bearing input** (the URL).
2. **Check ordering** — the URL-echoing hostname check ran *before* the credential
   check (whose message omits the URL).
3. The new **no-leak test only covered the with-host case**
   (`https://u:pass@evil.com`), where the hostname check passes and the credential
   check fires safely — so it went green while the no-host edge leaked.

**How we discovered it:** CodeRabbit flagged it as a Major security finding on the
PR; verified with `urlparse('https://alice:secret@')` → `hostname=None`,
`password='secret'`.

**Resolution implemented:** Reordered so the credential check (message omits the
URL) runs before the hostname check; added no-host regression cases to both the
userinfo-rejection and password-leak tests (commit 4530f41).

**Lesson learned:** When validating a value that can embed a secret (a URL with
userinfo, a DSN, a connection string), (a) never echo the raw value in an error
message, and (b) order the checks so any message that includes the raw value runs
only *after* the secret has been ruled out. And test the leak-prevention with the
edge case that breaks the ordering (empty/missing host), not just the happy path —
a "does not leak" test that only exercises the easy input passes while the real
gap ships. This generalizes the existing "never echo secret-bearing response
bodies" rule to *inputs* and *error messages*.

**What to do differently:**
- Treat error-message text as an output channel for secrets: audit every
  `fail_json`/`ValueError` message that interpolates a user-supplied value that
  could embed a credential.
- For any "does not leak X" test, include the boundary input that makes an
  earlier, value-echoing branch fire (here: no host).

---

## 2026-09-30: Shared Client Had No Direct Tests - Error Paths Hid in Indirect Coverage

**Issue:** A code audit found real defects in `plugins/module_utils/assisted_installer.py`
that had shipped undetected: `_validate_base_url` accepted a `base_url` carrying
embedded credentials (`https://user:pass@host`), and `_refresh_token` did an
unguarded `json.loads(resp.read())` that would escape as a raw
`ValueError`/`AttributeError` on a 200 with an empty or non-object body (violating
the "finish only via exit_json/fail_json" contract).

**What happened:** The shared client had no dedicated unit test file — it was only
exercised *indirectly* through the module tests. Those tests only drive the
`api_token` path, so the token-refresh branch was never executed. Coverage on the
file sat at 79% with lines 117–136 (the entire `_refresh_token` body) uncovered,
and the branch coverage gate didn't catch it because the module tests never enter
that code at all.

**Impact:** No module was broken in normal use (production always resolves an
`api_token`), but the offline-token refresh path and the integration `base_url`
override were both under-tested — one a robustness gap, one a credential-leak vector.

**How we discovered it:** Four parallel review agents audited the client and each
module against the OpenAPI spec; the client findings were then verified line-by-line
against the source before being treated as real.

**Resolution implemented:** Added `tests/unit/plugins/module_utils/test_assisted_installer.py`
(with its own conftest reusing the shared `ansible_helpers`), written TDD-first
(red → green). Fixed `_validate_base_url` to reject userinfo (message omits the URL
so the password can't leak), guarded the refresh parse to require a dict, dropped
empty-list query values in `build_url`, added a defensive no-token guard in
`request()`, and made `timeout=0` pass through instead of silently becoming 30.
Client coverage rose 79% → 95% (total 94% → 96%). PR on branch
`fix/shared-client-hardening`.

**Lesson learned:** Cross-cutting code in `module_utils/` needs its OWN unit tests,
not just incidental coverage from the modules that call it. "Overall coverage ≥90%"
can hide a shared file whose error branches are entirely unexecuted — check
per-file coverage on `module_utils/`, and add a direct test whenever a branch there
isn't reachable from any module's happy path.

**What to do differently:**
- Give every `module_utils/` file a dedicated test target; don't rely on module
  tests to cover its error/refresh/validation branches.
- When adding a shared-client capability (a new auth path, a new validation rule),
  add its unit test in the same PR, including the falsy/empty/non-object inputs.

---

## 2026-09-30: Skills Drifted From Real Code - Teaching Materials Need Executable Verification

**Issue:** An audit of the five `.claude/skills/*/SKILL.md` files found nine defects
— several of them "gray errors" (examples that look right but do not run) — even
though the actual `plugins/` modules and `tests/` were correct.

**What happened:** The skills had accumulated drift from the codebase they teach:
- `ansible-module-testing` mocked `monkeypatch.setattr("my_module.fetch_url", ...)`,
  but modules here never import `fetch_url` — they call the shared client, and real
  tests patch `ai.fetch_url`. The taught mock would silently no-op (hit the network).
- The same skill used `exc.value.msg` (the helper only sets `exc.value.result`),
  re-patched `monkeypatch` twice instead of queuing responses, and used invalid
  Jinja `result.changed is true`/`is false` in integration asserts.
- `ansible-collection-structure` claimed support for ansible-core **2.20**, which
  exists nowhere in `meta/runtime.yml`, CI, or the sanity ignore files (2.17–2.19).
- `new-ansible-module` documented only `no_log=False` (the false-positive case),
  never the primary `no_log=True` rule for real secrets.

**Impact:** The existing modules were unaffected (written correctly), but a new
contributor following the skills verbatim would have produced a module whose tests
don't actually mock, assert on a nonexistent attribute, and fail to parse — the
exact "one broken skill → many broken implementations" risk CLAUDE.md §0 warns about.

**How we discovered it:** User asked for a review of CLAUDE.md and the skills; each
suspected defect was then verified against the real `ansible_helpers.py`,
`test_infra_env.py`, `meta/runtime.yml`, and the modules' `argument_spec` before
being confirmed as a finding.

**Resolution implemented:** Rewrote the testing skill to teach the real
`ansible_helpers` API (`fake_fetch_url`/`queue_fetch_url` patched onto
`ai.fetch_url`, `exc.value.result["msg"]`, `is changed`/`is not changed`);
corrected the support matrix; added the `no_log=True` rule; and added
canonical-source pointers so the doc-standards stop being triplicated (PR on
branch `docs/fix-skill-gray-errors`). Every corrected test example was copied into
a scratch test and run green via `ansible-test units` before commit.

**Lesson learned:** Skills are code, not prose — verify their examples execute
against the real helpers/modules, and treat drift from the repo (mock targets,
helper APIs, support matrices) as a defect class of its own.

**Artifacts:** PR on `docs/fix-skill-gray-errors`; five SKILL.md files + CLAUDE.md.

**What to do differently:**
- When code that a skill teaches changes (helper API, support matrix, module
  patterns), update the skill in the same PR — add it to the conflict-check sweep.
- Keep one canonical source per topic and have the others point to it, so there is
  one place to update.
- Run skill code examples through `ansible-test units` (not plain `pytest`, which
  lacks the collection path) as part of skill authoring.

---

## 2026-09-29: Opus Review - Four Critical Process Gaps

**Context:** Requested Opus review of testing infrastructure before committing. Opus identified four critical process gaps that would have leaked credentials and violated design commitments.

---

### 1. Build Ignore Gap - Credentials in Collection Tarball

**Issue:** Added secrets to `.gitignore` but forgot `build_ignore` in `galaxy.yml` → real credentials bundled into collection tarball.

**What happened:**
- Created `pull_secret.json`, `offline.token`, `api.token` files
- Added `*.token` and `pull_secret*` to `.gitignore` (protects git)
- Ran `ansible-galaxy collection build --force` per documentation
- **Tarball contained all three secret files** (Opus verified by inspecting tarball)
- Documentation told contributors to run `collection build` → every contributor would package their own credentials

**Root cause:**
- Only checked **git protection** (`.gitignore`)
- Forgot **build protection** (`galaxy.yml` `build_ignore`)
- Ansible Galaxy uses **separate ignore mechanism** for tarballs

**How we discovered it:**
- Opus review explicitly checked tarball contents: `tar tzf openshift_lab-assisted_installer-*.tar.gz | grep -iE 'token|secret'`
- Found `offline.token`, `api.token`, `pull_secret.json` all present
- `.gitignore` worked (files not in git), but `build_ignore` was incomplete

**Impact:**
- **CRITICAL:** If tarball uploaded to Galaxy or attached to issue, credentials leak
- Every developer following the documented workflow would bundle their secrets
- Multiple copies of real credentials would exist in shareable artifacts

**Resolution implemented:**

1. **Updated `galaxy.yml` `build_ignore`:**
   - Added: `*.token`, `pull_secret*`, `.env`
   - Comment: "Secrets - never bundle credentials into collection tarball"

2. **Deleted existing tarball:**
   - Removed `openshift_lab-assisted_installer-*.tar.gz` (contained real secrets)

3. **Updated comment in `galaxy.yml`:**
   - `scripts` comment now mentions "Includes manual-smoke (live API tests requiring real credentials)"

**What to do differently:**

**When protecting secrets in Ansible collections, check TWO ignore mechanisms:**
1. `.gitignore` - protects git commits
2. `galaxy.yml` `build_ignore` - protects collection tarballs

**Verification pattern:**
```bash
# After adding secrets to ignore files:
ansible-galaxy collection build
tar tzf *.tar.gz | grep -iE 'token|secret|\.env'
# Should return NOTHING

# Then delete the tarball:
rm *.tar.gz
```

**Files changed:**
- `galaxy.yml` - Added `*.token`, `pull_secret*`, `.env` to `build_ignore`

**References:**
- Opus review finding #1 (CRITICAL severity)
- Galaxy packaging docs: https://docs.ansible.com/ansible/latest/dev_guide/collections_galaxy_meta.html#build-ignore

---

### 2. Design Document Verification Gap - Wrong Testing Approach

**Issue:** Built entire live API testing infrastructure without re-reading DESIGN.md §8, which explicitly requires **mock server integration**, not live API tests with real credentials.

**What happened:**
- DESIGN.md §8 states: "Integration NEVER targets `api.openshift.com`. No credentials, no network egress."
- DESIGN.md §8 says: "together with the first state-based module (`cluster`/`infra_env`)" is the trigger
- `infra_env` module landed (trigger fired)
- Built comprehensive test suite in `tests/playbooks/` that:
  - Creates/deletes **real** resources on `api.openshift.com`
  - Requires **real** credentials (`pull_secret.json`, `offline.token`)
  - Cannot run in CI (violates "no credentials in CI" rule)
- Module already has `base_url` parameter and `_validate_base_url()` for mock server support
- **Never used the mock server pattern we designed for**

**Root cause:**
- Started implementation without re-reading design section that covers it
- Focused on "testing against live API" without checking if that's what was designed
- Design documents contain **commitments** ("integration NEVER targets prod"), not suggestions

**How we discovered it:**
- Opus review explicitly cross-referenced DESIGN.md §8
- Quoted the design commitments back to us
- Pointed out the contradiction: design says "mock server", we built "live API"

**Impact:**
- Tests violate project's documented testing posture
- Tests live in `tests/` but can never run in CI
- Missing the actual deliverable (mock server integration)
- Future contributors will wire live API tests into CI (disaster)

**Resolution implemented:**

1. **Moved live API tests to `scripts/manual-smoke/`:**
   - Created `scripts/manual-smoke/` directory (build-ignored)
   - Moved: `list-infra-envs.yml`, `test-infra-env-lifecycle.yml`, `test-infra-env-query.yml`, `query-infra-env-by-id.yml`, `debug-create-infra-env.yml`
   - These are now **manual smoke tests**, not the test suite

2. **Created `scripts/manual-smoke/README.md`:**
   - Clearly labels these as "manual smoke tests (live API)"
   - Warning: "should never be automated in CI"
   - Explains difference from DESIGN §8 integration tests

3. **Updated `galaxy.yml`:**
   - `scripts` directory build-ignored (includes manual-smoke)
   - Comment clarifies why

4. **Documented what's still needed:**
   - `tests/integration/targets/infra_env/` against local mock server
   - CI integration job (the DESIGN §8 deliverable)

**What to do differently:**

**Before significant implementation work:**
1. **Re-read the design document** section that covers it
2. **Quote the relevant design commitments** in your planning
3. **Verify approach matches design** before writing code
4. **Check for design keywords:** "MUST", "NEVER", "always", "forbidden"

**Design documents aren't suggestions:**
- "Integration NEVER targets prod" means **never**, not "usually not"
- Violations need explicit design change discussion, not silent implementation

**Pattern:**
```markdown
## Before implementing [feature]

**Design reference:** DESIGN.md §N says:
> [quote the relevant section]

**My approach:** [describe]

**Verification:** Does my approach match the design? YES/NO
- If NO: why is the design wrong? Propose design change first.
```

**Files changed:**
- Moved 5 playbooks from `tests/playbooks/` to `scripts/manual-smoke/`
- `scripts/manual-smoke/README.md` - Created with warnings
- `galaxy.yml` - Updated comment for `scripts` ignore

**What's still needed:**
- Build `tests/integration/targets/infra_env/` (DESIGN §8 deliverable)
- Local mock HTTP server setup
- CI integration job

**References:**
- Opus review finding #2 (CRITICAL severity)
- DESIGN.md §8 "When to build the integration layer"

---

### 3. Bug Fix Verification Gap - Right Fix, Wrong Explanation (Twice)

**Issue:** Removed `validate_certs=True` from two `fetch_url()` calls as a "bug
fix" without verifying *why* it worked. Two successive reviews then documented the
root cause wrongly before CodeRabbit checked the actual source and settled it.

**What happened (three stages of getting it wrong, then right):**

1. **Original change (unverified fix):** Encountered
   `fetch_url() got an unexpected keyword argument 'validate_certs'`, removed the
   parameter, and shipped it as a "bug fix" — without documenting the error,
   reproducing it, or explaining the mechanism.

2. **Opus review (over-corrected):** Concluded `validate_certs` "**is** a valid
   parameter (default `True`)" and that removal was a **no-op**. We documented
   that in `VALIDATE_CERTS_NOTE.md` and here, calling the root cause "unknown."
   This was *also* unverified — it reasoned from the general Ansible convention
   (modules expose `validate_certs`) without checking the `fetch_url()` signature.

3. **CodeRabbit review (verified against source):** Checked the ansible-core
   `stable-2.17`, `stable-2.18`, and `stable-2.19` sources and found:
   `fetch_url()` **does not accept `validate_certs` as a keyword argument.** It
   reads it from `module.params` (default `True`) and passes it to `open_url()`.

**Actual root cause (settled):**
- `validate_certs` is a valid *module parameter*, but NOT a `fetch_url()` keyword.
- Passing it as a keyword raised the `TypeError`.
- Removing it **resolved the error** AND **retained default TLS validation**
  (`True`), because that is the default `fetch_url()` applies when it is absent.
- So the original change was a **real fix** — we just never explained it, then
  mis-explained it as a no-op.

**The deeper lesson — verification gaps compound:**
- The original author didn't verify the fix mechanism.
- The Opus review "correcting" it *also* didn't verify — it substituted a
  plausible-sounding convention ("modules take `validate_certs`") for checking
  the specific function's signature in the specific versions.
- Only checking the **authoritative source for the exact API and versions**
  settled it. A confident second opinion is not verification.

**Resolution implemented:**
1. **Kept the change** — it is the correct fix.
2. **Rewrote `VALIDATE_CERTS_NOTE.md`** to state the real root cause, cite the
   `fetch_url()` signature, and explain TLS validation still defaults to `True`.
3. **Classification:** this IS a bug fix (resolves a `TypeError`), not a no-op
   and not mere cleanup.

**What to do differently:**

Before claiming to fix — OR to *un*-fix — a bug:
1. **Document the exact error** (message, version, environment).
2. **Check the authoritative source for the exact API and version**, not the
   general convention. Signatures differ between "module argument_spec" and the
   helper functions modules call (`fetch_url` vs `open_url` vs a module param).
3. **Reproduce** the failure and confirm the change flips it.
4. Treat a reviewer's confident claim as a hypothesis to verify, not a fact.

**Pattern for actual bug fixes:**
```markdown
## Bug: [Short description]

**Original error:** [exact message + stack trace + version]
**Root cause:** [checked against source: file/version/line]
**Fix:** [what changed]
**Verification:** reproduced before ✓ / gone after ✓ / no recurrence ✓
```

**Files changed:**
- `VALIDATE_CERTS_NOTE.md` - Rewritten with the verified root cause
- `plugins/module_utils/assisted_installer.py` - Change kept (it is the fix)

**References:**
- Opus review finding #3 (initial, partially wrong conclusion)
- CodeRabbit PR #52 (verified `fetch_url()` signature across 2.17–2.19)

---

### 4. Test Cleanup Pattern Missing - Resource Leak on Failure

**Issue:** Live API tests create resources without guaranteed cleanup. If assertions fail mid-run, resources leak.

**What happened:**
- `test-infra-env-lifecycle.yml` creates test infra-env
- Runs assertions
- Deletes infra-env at end
- **If any assertion fails:** playbook stops, delete never runs
- Result: orphaned infra-env accumulates on live account on every failure

**Root cause:**
- Linear task flow (create → assert → delete)
- No failure handling
- Cleanup depends on reaching the delete step
- Didn't use Ansible's `block/rescue/always` pattern

**How we discovered it:**
- Opus review asked: "What happens if STEP 3 assertion fails?"
- Answer: STEP 4 (delete) never runs
- No `block/always` pattern for guaranteed cleanup

**Impact:**
- Failed test runs leak real infrastructure
- Costs accumulate (infra-envs are free but generate ISOs, consume quota)
- Manual cleanup required after every failure
- Same issue in `test-infra-env-query.yml` (creates 2, may leak both)

**Resolution implemented:**

1. **Rewrote `test-infra-env-lifecycle.yml` with `block/rescue/always`:**
   ```yaml
   - block:
       # All test steps including delete
     rescue:
       - debug: msg="Test failed, attempting cleanup..."
       - name: Guaranteed cleanup on failure
         infra_env:
           state: absent
           name: "{{ test_name }}"
         ignore_errors: true
       # Re-fail so successful cleanup does not mask the original failure.
       # A rescue that completes clears the error and the play reports success.
       - name: Re-fail the test after cleanup
         ansible.builtin.fail:
           msg: "Test failed; cleanup was attempted."
     always:
       - debug: msg="Cleanup attempted via block/always (cleanup errors ignored)"
   ```

2. **Added real update step (bonus fix):**
   - Opus also noted: lifecycle test claims to test "update" but only tests no-op
   - Added STEP 4: Update (change `image_type` from `full-iso` to `minimal-iso`)
   - Verifies `changed=true` for real drift reconciliation

3. **Updated test steps:**
   - Now 7 steps instead of 6
   - Create → Verify → Create idempotency → **Update** → Delete → Verify deletion → Delete idempotency

**What to do differently:**

**Tests that mutate external state MUST use `block/rescue/always` for guaranteed cleanup:**

```yaml
- block:
    - name: Create resource
      module:
        state: present
      register: created

    - name: Run assertions
      assert:
        that: [conditions]

    - name: Normal cleanup
      module:
        state: absent
      register: deleted

  rescue:
    - name: Log failure
      debug:
        msg: "Test failed, attempting cleanup"

    - name: Guaranteed cleanup on failure
      module:
        state: absent
      ignore_errors: true

    # A completed rescue clears the original error, so the play would report
    # success. Re-fail to keep a failed test failed after cleanup runs.
    - name: Re-fail the test after cleanup
      ansible.builtin.fail:
        msg: "Test failed; cleanup was attempted."

  always:
    - name: Report cleanup status
      debug:
        msg: "Cleanup attempted via always block (cleanup errors ignored)"
```

**Pattern applies to:**
- Live API tests
- Database tests
- VM provisioning tests
- Any test that creates external resources

**Don't rely on:**
- Linear task flow reaching cleanup steps
- Playbook completing successfully
- Manual cleanup after failures

**Files changed:**
- `scripts/manual-smoke/test-infra-env-lifecycle.yml` - Rewritten with block/rescue/always + update step

**References:**
- Opus review finding #4 (HIGH severity)
- Ansible docs: https://docs.ansible.com/ansible/latest/user_guide/playbooks_blocks.html

---

## 2026-09-22: Cost Tracking Scope Clarification - Not Just Module PRs

**Issue:** Cost tracking scope was assumed to be module implementation PRs only, but user expects it for ALL PRs where Claude is used.

**What happened:**
- PR #45 (docs/parameter-naming-convention) merged successfully
- Documentation-only PR (DESIGN.md +39, CLAUDE.md +4)
- No cost breakdown posted (I assumed cost tracking was module PRs only)
- User asked: "did the PR 45 have the cost and token updated as part of merge?"
- I explained: "PR #45 was doc-only, not a module implementation - I interpreted cost tracking as out-of-scope"
- User clarified: "I want it posted for all PRs in the repo"
- User noted caveat: "of course there will be some PRs that will not use Claude and could use other AI tools and some could be manually authored"

**Impact of unclear scope:**
- Incomplete cost tracking record (PR #45 had no breakdown)
- Violated atomic posting rule (already merged when user asked)
- Unclear guideline for contributors using other AI tools
- No documented threshold for "when to track costs"

**How we discovered it:**
- User proactively checked PR #45 for cost breakdown
- Asked directly about the missing breakdown
- Revealed assumption gap: I thought "module PRs only", user meant "all Claude PRs"

**Resolution implemented:**

1. **Posted retroactive cost for PR #45:**
   - Estimated: ~20-25 min, ~$0.15-0.20 (Sonnet 4.5)
   - Posted as PR comment (after merge, with note about process gap)
   - Comment link: https://github.com/vjayaramrh/cld_ai/pull/45#issuecomment-5771222313

2. **Updated CLAUDE.md §6 - Cost tracking scope:**
   - Clarified: "ALL PRs using Claude require cost breakdown (module, docs, fixes, all types)"
   - Added caveat: "PRs using other AI tools or manually authored: note in PR or skip"
   - Threshold: If Claude Code/API was used for any part of the PR, cost breakdown required
   - Reinforced atomic rule: Cost + merge in same response (applies to ALL Claude PRs now)

3. **This lesson-learned entry:**
   - Documents the scope clarification
   - Provides retroactive cost posting as Option C resolution
   - Establishes clear threshold for future PRs

**Lesson learned:**

> **Cost tracking applies to ALL PRs where Claude is used, not just module implementations.**  
> Explicit scope documentation prevents assumptions about "what counts."  
> For non-Claude PRs (other AI or manual): note in PR description, cost breakdown optional.

**What to do differently:**
- When establishing tracking/reporting requirements, document explicit scope
- Don't assume "obvious" boundaries (module vs. docs vs. fixes)
- Caveat: Some PRs may use other tools → note in PR, don't guess at costs
- Threshold test: "Was Claude Code/API used?" → YES = cost breakdown required
- For mixed authorship (Claude + other AI): estimate Claude portion, note in breakdown

**Artifacts:**
- PR #45 retroactive cost comment (posted after merge)
- CLAUDE.md §6 update (cost tracking scope clarification) - this PR
- This lessons-learned entry

**Cost tracking scope decision matrix:**

| PR Type | Claude Used? | Cost Breakdown Required? |
|---------|--------------|--------------------------|
| Module implementation | Yes | ✅ Required (atomic with merge) |
| Documentation | Yes | ✅ Required (atomic with merge) |
| Fixes, refactors | Yes | ✅ Required (atomic with merge) |
| Manual authoring | No | ❌ Note "manual" in PR description |
| Other AI tool (GPT, etc.) | No | ❌ Note tool used, cost optional |
| Mixed (Claude + manual) | Partial | ✅ Estimate Claude portion |

**Why this matters:**
- Tracks actual Claude usage across ALL work types (not just modules)
- Provides complete cost visibility for the project
- Enables future analysis: "What does doc work cost vs. module work?"
- Transparent record for contributors using different tools

**Validation questions for any PR:**
1. Was Claude Code or Claude API used? → YES = cost breakdown required
2. If other AI tool: Is it noted in PR description? → Must clarify
3. If manual: Is it noted in PR description? → Must clarify
4. If mixed: Is Claude's portion estimated? → Must separate

---

## 2026-09-22: Specification Verification Pattern - Third Occurrence

**Issue:** Assumed namespace/name validation pattern without checking Ansible Galaxy requirements (third time making specification assumptions).

**What happened:**
- While creating `ansible-collection-structure` skill for PR #50
- Documented namespace/name rules as: `Pattern: ^[a-z0-9_]+$`
- CodeRabbit review caught this accepts invalid names:
  - Starting with digit: `9foo` (❌ Galaxy rejects)
  - Starting with underscore: `_bar` (❌ Galaxy rejects)
  - Consecutive underscores: `foo__bar` (❌ Galaxy rejects)
- Didn't verify against authoritative source (Ansible Galaxy metadata requirements)
- This is the **THIRD occurrence** of this pattern:
  1. **PR #28 (2026-09-08):** Assumed `env:` keyword was for modules (it's plugin-specific)
  2. **PR #31 (2026-09-15):** Assumed "support level" definition without verifying
  3. **PR #50 (now):** Assumed namespace pattern without checking Galaxy spec

**Impact:**
- Skill would teach contributors to create invalid galaxy.yml
- `ansible-galaxy collection build` would accept it locally
- Upload to Galaxy would fail with validation error
- Wasted time fixing invalid collection metadata

**How we discovered it:**
- CodeRabbit static analysis caught the pattern accepts invalid forms
- Linked to official docs: https://docs.ansible.com/projects/ansible/latest/dev_guide/collections_galaxy_meta.html
- Recommended explicit rules instead of regex

**Resolution implemented:**
1. **Fixed the skill:**
   - Replaced regex pattern with explicit rules
   - "Start with lowercase letter; use only lowercase letters, digits, underscores; no consecutive underscores"
   - Matches Galaxy requirements exactly

2. **Pattern recognition:**
   - This is the third specification assumption in 14 days
   - Each time: assumed pattern → didn't verify → caught in review
   - Common thread: documentation/skill creation without checking authoritative source

**Lesson learned:**

> **Before documenting ANY specification (API, Galaxy, ansible-test, etc.), verify against the authoritative source.**  
> This is now a PATTERN - three occurrences means it's systemic, not isolated.

**What to do differently:**
- **New rule:** When writing skills/docs that reference external specs, cite the source
- **Verification checklist for skills:**
  1. Does this skill reference an external spec/API/tool?
  2. If YES: Have I checked the authoritative docs/spec?
  3. If NO: Am I making an assumption that could be wrong?
  4. Can I link to the source in the skill?
- **Pattern examples:**
  - API parameters → Check OpenAPI spec
  - Galaxy metadata → Check Galaxy meta docs  
  - ansible-test syntax → Check ansible-test --help or official docs
  - Module doc format → Check developing_modules_documenting.html

**Artifacts:**
- PR #50: fix (CodeRabbit review comment, commit a3aa218)
- Related lessons: "API Spec Verification Gap" (2026-09-08), "Terminology Precision" (2026-09-15)

**Why this matters:**
- Third occurrence elevates this from "mistake" to "systemic pattern"
- Pattern cuts across different spec types (API, plugin system, Galaxy)
- Always caught in review, never prevented upfront
- Time cost: review cycle + fix commit for every occurrence

**Prevention going forward:**
- Treat all external references as "verify before documenting"
- Link to authoritative source in the skill/doc
- When in doubt, grep the official docs or run the tool with --help

---

## 2026-09-22: Mock Pattern Correctness - Gray Error in Test Helper

**Issue:** Test helper mock_api_response looked correct but had fatal flaws that would break actual use.

**What happened:**
- While creating `ansible-module-testing` skill for PR #50
- Wrote a mock_api_response() helper for unit tests
- Original implementation had three flaws:
  1. **Response queuing broken:** Each call to mock_api_response() replaced the mock, so multi-step tests (GET → POST) wouldn't work
  2. **Wrong response shape:** Returned `(None, info)` for ALL statuses, but successful responses should return `(Response, info)`
  3. **Falsy body handling:** `if body` converted empty list `[]` to empty bytes, breaking idempotency tests
- CodeRabbit caught all three issues:
  - "Queue mock responses instead of replacing the mock"
  - "Return a response object for successful API mocks"
  - "Preserve falsy JSON response bodies"
- This is a **gray error:** code looks plausible, would pass casual review, fails in practice

**Impact:**
- Skill taught a broken pattern that LOOKS correct
- Idempotency test examples in the skill wouldn't actually work:
  ```python
  # This example wouldn't run correctly:
  mock_api_response(monkeypatch, 200, {"id": "123"})  # GET
  mock_api_response(monkeypatch, 201, {})  # POST - replaces first mock!
  ```
- Contributors copying the pattern would hit failures
- Tests would fail with confusing errors (AttributeError on resp.read())

**How we discovered it:**
- CodeRabbit static analysis identified the pattern flaws
- Each finding included a specific failure scenario
- Confirmed the examples in the skill wouldn't execute correctly

**Resolution implemented:**
1. **Fixed the mock pattern:**
   - Added `responses` parameter for queueing: `[(status1, body1), (status2, body2)]`
   - Created Response class with read() method for successful calls
   - Changed `if body` to `if body is not None` for falsy value handling
   - Pattern now supports the idempotency examples shown

2. **Why this matters - gray errors:**
   - Pattern LOOKED correct (had the right structure)
   - Would pass a surface review (uses monkeypatch, returns tuples)
   - FAILS in actual use (doesn't match fetch_url contract)
   - This is exactly what research calls a "gray error" (appears correct, implements wrong behavior)

**Lesson learned:**

> **Test helper patterns must be EXECUTABLE, not just plausible.**  
> If the skill shows example usage, verify the helper actually supports that usage.

**What to do differently:**
- **For test helpers in skills:** Actually run the examples shown
- **Pattern validation:**
  1. Does the skill show usage examples?
  2. If YES: Can I copy the helper + example and run it?
  3. If NO: The helper is incomplete or wrong
- **Gray error detection:**
  - Looks right ≠ works right
  - Multi-step examples catch broken state management
  - Edge cases (falsy values) catch lazy conditionals

**Artifacts:**
- PR #50: fix (CodeRabbit review comments, commit a3aa218)
- Fixed pattern in `.claude/skills/ansible-module-testing/SKILL.md`

**Why this matters:**
- Skills are teaching tools - broken patterns multiply
- Gray errors are WORSE than obvious bugs (they propagate)
- Static analysis caught what human review might miss
- Research-backed concept: 75% of AI-generated code passes tests but has wrong logic

**Prevention going forward:**
- Test helper code in skills must be runnable as-is
- If showing multi-step examples, verify the helper supports them
- Don't skip edge cases (empty lists, None, zero) in examples

---

## 2026-09-22: Status Tracking Maintenance - Roadmap Not Updated

**Issue:** Created roadmap to track skill development but didn't update it when skills were completed.

**What happened:**
- PR #50 created three skills: `ansible-module-documentation`, `ansible-module-testing`, `ansible-collection-structure`
- Also created `docs/skill-development-roadmap.md` to track the work
- Roadmap included a Phase 1 checklist and status markers
- Completed all three skills but left roadmap showing:
  - Status: "📝 Planned" (should be "✅ Created")
  - Phase 1 checklist: unchecked boxes (should be all checked)
  - Current Skills table: missing the three new skills
- CodeRabbit caught this: "Synchronize the roadmap with the skills added in this PR"

**Impact:**
- Roadmap claims work is planned but it's actually done
- Contributors checking status see incorrect state
- Defeats the purpose of having a roadmap
- "Planned" vs "Created" matters for deciding what to work on next

**How we discovered it:**
- CodeRabbit review: "The roadmap still marks ... as planned"
- Pointed out three places needing updates (status, checklist, current skills table)

**Resolution implemented:**
1. **Updated roadmap (commit a3aa218):**
   - Changed status from "📝 Planned" to "✅ Created" for all three skills
   - Marked Phase 1 checklist items as complete
   - Added three skills to "Current Skills" table
   - Changed Phase 1 header from "Current" to "Complete"

2. **Why this happened:**
   - Created roadmap at START of work (planning phase)
   - Completed work but didn't revisit roadmap
   - Missing step: "update status tracking when work completes"

**Lesson learned:**

> **Status tracking documents must be updated when state changes, not just created.**  
> Creating a roadmap/checklist without maintaining it is worse than not having one.

**What to do differently:**
- **Workflow addition:** When completing tracked work, update the tracking doc IN THE SAME PR
- **Pattern:**
  1. Work starts → roadmap shows "in progress"
  2. Work completes → roadmap shows "completed"
  3. PR includes BOTH the work AND the status update
- **Verification:** Before marking PR ready, check all status docs for stale state
- **Examples of status docs:** roadmap, project board, DONE.md, phase tracking

**Artifacts:**
- PR #50: fix (CodeRabbit review comment, commit a3aa218)
- Updated `docs/skill-development-roadmap.md`

**Why this matters:**
- Status docs are for OTHERS (contributors, future work planning)
- Stale status wastes time ("Is this done?" → check code, not doc)
- Creating tracking then not maintaining it erodes trust in docs
- Pattern applies to all status docs (boards, checklists, roadmaps)

**Prevention going forward:**
- Status updates are part of completing work, not optional
- Check status docs before marking PR ready
- If work creates a tracking doc, work completion must update it

---

## 2026-09-20: Process Compliance Gap - Documented Workflow Violated

**Issue:** Documented workflow for atomic cost-breakdown-then-merge was violated even though it was clearly documented in CLAUDE.md §6 and feedback memory.

**What happened:**
- PR #41 (module granularity principle)
- Workflow clearly documented: "When user approves merge, BOTH post comment and merge happen atomically"
- During PR #41: I posted cost breakdown early (while CI was running), before user approval to merge
- When user said "merge", I just merged (didn't do both atomically)
- User noticed: "I am surprised that the cost breakdown and PR merging were not carried out as an atomic operation"
- I acknowledged: the documentation was clear, I simply didn't follow it
- User asked: "what guarantees that this will not happen again?"

**Impact:**
- Broke atomic pattern (even though end result was correct: cost before merge)
- Created discretion where none should exist
- Showed that documentation alone doesn't prevent violations
- User lost confidence in process adherence

**How we discovered it:**
- User observed the non-atomic behavior after PR #41 merged
- Asked "Was it not already clearly understood prior to this?"
- Answer: Yes, it was clearly documented. I violated it anyway.
- Deeper question: "what guarantees that this will not happen again?"

**Root cause analysis:**

**Why documentation wasn't followed:**
- I had discretion to post cost breakdown early ("to be helpful")
- No explicit prohibition against posting before merge approval
- Rule said "post before merge" but didn't say "ONLY when user approves merge"
- Anticipation seemed harmless (cost still ended up before merge)

**Why this is a problem:**
- Documentation exists but doesn't prevent violations
- Discretion creates opportunities for "helpful" deviations
- Atomic behavior breaks even if end result looks correct
- Pattern: documented → violated → "won't happen again" → happens again

**Resolution implemented:**

1. **Updated CLAUDE.md §6 - Added strict rule section:**
   - "NEVER post cost breakdown separately from merge"
   - Explicit ❌ prohibited patterns (posting early, posting in anticipation)
   - Explicit ✅ required pattern (ONLY when user approves, atomic execution)
   - Pre-merge checklist (forces evaluation at trigger point)
   - "Why strict rule" explanation (removes discretion)

2. **Updated feedback memory (cost-breakdown-before-merge.md):**
   - Changed from permissive ("post before merge") to strict ("atomic only")
   - Documented prohibited anti-patterns
   - Explicit trigger: user approval to merge
   - No discretion to post early

3. **This lesson-learned entry:**
   - Documents the compliance gap
   - Shows that documentation alone is insufficient
   - Enforcement requires removing discretion, not adding more docs

**Lesson learned:**

> **When documented workflows keep getting violated, remove discretion rather than add more documentation.**  
> Documentation that says "do X before Y" can be violated by doing X too early.  
> Documentation that says "ONLY do X when triggered by Z" removes the discretion to violate.

**What to do differently:**
- When creating process documentation, ask: "What discretion does this leave?"
- If there's a way to follow the rule incorrectly, remove that path
- Explicit prohibitions ("NEVER do X") stronger than implicit ones ("do X before Y")
- Pre-action checklists force evaluation at the right moment
- Strict rules ("ONLY when") remove discretion that permissive rules ("before") leave

**Meta-lesson (5th process gap entry):**

This is the 5th lessons-learned entry about process issues:
1. API Spec Verification Gap (2026-09-08) - verify before assuming
2. Terminology Precision (2026-09-09/10) - verify industry definitions
3. Process Documentation Gap (2026-09-15) - document workflow steps
4. Architectural Decision Gap (2026-09-20) - research precedents, document rationale
5. **Process Compliance Gap (2026-09-20) - remove discretion, not just document**

**The escalating pattern:**
- Entry 1-2: Missing information (verify first)
- Entry 3-4: Missing documentation (document it)
- Entry 5: **Documentation exists but insufficient (enforce it)**

**The next level:** Documentation + enforcement mechanisms (strict rules, removed discretion, forced evaluation).

**Artifacts:**
- CLAUDE.md §6 updated with strict rule (PR #42)
- Feedback memory cost-breakdown-before-merge.md updated (PR #42)
- This lessons-learned entry

**Validation after this PR:**
- Does CLAUDE.md §6 leave any discretion to post cost early? NO
- Can cost breakdown be posted before user approves merge? NO (explicitly prohibited)
- Is the trigger clear? YES (user approval to merge)
- Is the action clear? YES (both tool calls, one response)

---

## 2026-09-20: Architectural Decision Gap - Module Granularity Without Precedent

**Issue:** The api-endpoint-map.md splits cluster-related info modules into multiple specialized modules (`cluster_info`, `cluster_manifest_info`, `cluster_credentials_info`, `cluster_file_info`, `cluster_logs_info`, `cluster_operator_info`) without documented rationale or industry precedent.

**What happened:**
- User asked (issue #10 comment): "Do you mind listing exhaustively all the GET APIs related to clusters and which would be implemented?"
- I found 18 cluster-related GET endpoints in the OpenAPI spec
- I referenced api-endpoint-map.md and saw it splits them across 6+ separate `*_info` modules
- User asked deeper question: "Why do we need cluster_info, cluster_manifest_info, cluster_credentials_info, cluster_file_info and such? What is the reference and precedent for this?"
- **I could not find any documented rationale or precedent research**
- DESIGN.md §5 explains `_info` suffix convention but NOT when to split into multiple modules
- Memory (module-naming-decisions.md) says "RESOLVED" but only covers naming, not granularity
- The map shows line 106: `cluster_operator_info` **(or `cluster_info` sub)** - revealing uncertainty!

**Impact of the gap:**
- Architectural decisions made without documented reasoning
- Cannot explain to contributors WHY this granularity was chosen
- Risk of inconsistent patterns (some resources split, others consolidated)
- May be over-engineering (6+ modules) when 1 flexible module could work
- Starting implementation before resolving this would bake in an unvalidated pattern

**Industry precedent research (what major collections ACTUALLY do):**

1. **kubernetes.core:**
   - `k8s_info` - ONE module gets ANY Kubernetes resource via parameters
   - NOT separate `k8s_pod_info`, `k8s_service_info`, `k8s_deployment_info`
   - Pattern: Flexible, parameter-driven

2. **amazon.aws:**
   - `ec2_instance_info` - ONE module for EC2 instances
   - NOT separate `ec2_instance_network_info`, `ec2_instance_storage_info`
   - Pattern: Consolidated per resource

3. **Industry pattern:** Fewer, more flexible info modules with parameters to vary behavior

**The unanswered question:**
Why does our map choose multiple specialized modules (Option B) when major collections use consolidated flexible modules (Option A)?

**How we discovered it:**
- User's probing question about references consulted
- Could not cite any precedent or documented decision rationale
- Realized the api-endpoint-map.md granularity was assumed, not researched

**Resolution implemented:**

1. **Paused cluster_info implementation** - Don't bake in unvalidated pattern
2. **Researched actual precedents** - kubernetes.core, amazon.aws use consolidated pattern
3. **Documented the gap** - This lessons-learned entry
4. **Established design principle decision process:**
   - Present both options with precedent research
   - User decides architectural principle
   - Document rationale in DESIGN.md
   - Update api-endpoint-map.md accordingly
   - THEN implement cluster_info following validated principle

**Lesson learned:**

> **Architectural decisions affecting module granularity MUST cite precedent and document rationale.**  
> Don't assume a structure because it "seems right" - research what major Ansible collections actually do.  
> If diverging from industry patterns, document WHY and the tradeoffs explicitly.

**What to do differently:**
- Before creating api-endpoint-map.md, research precedents from 3+ major Ansible collections
- Document design principle for module granularity in DESIGN.md (when to split, when to consolidate)
- Cite specific examples from kubernetes.core, amazon.aws, azure.azcollection, etc.
- Any architectural decision that affects multiple modules needs documented rationale
- Pattern: Research → Document principle → Apply consistently
- Add to DESIGN.md: "When to split info modules" section with examples

**Resolution steps:**
1. ✅ Document this gap (this entry)
2. ✅ Present granularity options with precedent analysis
3. ✅ User decides design principle
4. ✅ Update DESIGN.md with principle + rationale
5. ✅ Revise api-endpoint-map.md to match principle
6. ⏳ Then implement cluster_info following validated pattern (next)

**Artifacts:**
- This lessons-learned entry
- DESIGN.md §6 "Module granularity principle" (PR #41)
- api-endpoint-map.md revision (PR #41)

**Why this matters:**
This is the 4th lessons-learned entry about **undocumented decisions**:
1. API Spec Verification Gap (2026-09-08) - verify before assuming
2. Terminology Precision (2026-09-09/10) - verify industry definitions
3. Process Documentation Gap (2026-09-15) - document workflow steps
4. **Architectural Decision Gap (2026-09-20) - research precedents, document rationale**

The meta-lesson: **Assumptions fail. Research, document, cite sources.**

---

## 2026-09-15: Process Documentation Gap - CodeRabbit Comment Resolution

**Issue:** Inconsistent handling of CodeRabbit review thread resolution after addressing findings.

**What happened:**
- PR #33 (TDD documentation): User explicitly asked to resolve CodeRabbit comments → resolved all 3 threads via GraphQL API ✅
- PR #34 (module-workflow-guide): User didn't explicitly ask → forgot to resolve 2 threads after applying fixes ❌
- PR merged with unresolved threads (addressed retroactively when user noticed)
- User asked: "do you resolve the code review comments always?"
- I admitted: "No, I didn't resolve them for PR #34 - I forgot that step"
- User pushed deeper: "what ensures that this step will always be followed?"
- Answer: **Nothing** - no documented process, only ad-hoc memory when explicitly reminded

**Impact:**
- Unresolved threads on merged PRs look incomplete (even when fixes were applied)
- Inconsistent workflow quality across PRs
- No feedback loop to reviewers that findings were addressed
- Relies on user asking each time, not systematic process
- Professional appearance suffers (looks like we didn't finish the review)

**How we discovered it:**
- User noticed threads weren't marked as resolved on PR #34
- Asked if this is always done
- I revealed it was inconsistent (only when explicitly asked)
- User identified the gap: no enforcement mechanism

**Resolution implemented:**

1. **Updated CLAUDE.md verification checklist** (PR #35):
   - Added section 6: "PR hygiene and review workflow"
   - Checklist item: "Mark each review thread as resolved after fixing"
   - Included GraphQL commands for resolution
   - Linked to this lesson-learned entry

2. **Saved as feedback memory:**
   - When CodeRabbit reviews, always resolve threads after applying fixes
   - Never leave threads unresolved on merge
   - Part of standard PR workflow, not optional

3. **Documented pattern:**
   - Apply fix → commit → push → **resolve thread** → merge
   - Thread resolution is part of "address the finding", not separate

4. **Made lessons-learned evaluation mandatory** (PR #35):
   - Changed section 5 from "Consider documenting" to "Evaluate (mandatory)"
   - Required checkbox: "Evaluated: Is there a lesson worth documenting? [Yes/No + reason]"
   - Forces explicit evaluation for every PR (even if answer is "no")
   - Prevents the meta-gap: forgetting to evaluate if we should record a lesson

**Lesson learned:**

> **Critical workflow steps must be documented in CLAUDE.md, not assumed.**  
> "I'll remember" is hope, not process. Memory degrades across sessions.  
> If a step matters for quality, it belongs in the verification checklist.

**What to do differently:**
- When establishing new workflow patterns, document them immediately in CLAUDE.md
- Verification checklist is the enforcement mechanism (auto-loaded every session)
- Don't rely on "I learned this" - codify it in documented process
- Test: If the step could be forgotten when user doesn't explicitly ask, it needs documentation
- Quality steps that depend on human memory will fail eventually
- **Enforcement pattern:** "Evaluate X: [Yes/No + reason]" forces evaluation (vs. soft "Consider X")

**Artifacts:**
- PR #35: Add CodeRabbit resolution step to CLAUDE.md verification checklist
- Feedback memory: coderabbit-resolution-required.md
- This lessons-learned entry

**Why this pattern matters:**
This is the third lessons-learned entry about **process gaps**:
1. API Spec Verification Gap (2026-09-08) - assumed params without checking
2. Terminology Precision (2026-09-09/10) - used terms without verifying industry definition
3. **Process Documentation Gap (2026-09-15) - relied on memory instead of documented steps**

The meta-lesson: **Undocumented processes fail. CLAUDE.md is the source of truth.**

**The meta-meta-lesson (from user follow-up question):**
User asked: "What ensures we always evaluate if a lesson needs to be recorded?"
Answer: Nothing, until we made it a mandatory checklist item (section 5).

**Process enforcement pattern identified:**
- ❌ "Consider X" → skippable
- ❌ "X is important" → stated but not enforced  
- ✅ **"Evaluate X: [Yes/No + reason]"** → forces evaluation

This same pattern now applies to:
- CodeRabbit thread resolution (section 6) - mandatory checklist item
- Lessons-learned evaluation (section 5) - mandatory evaluation, recording only if yes
- API spec verification (already mandatory) - documented in module authoring rules

---

## 2026-09-09/10: Terminology Precision - "Agentic SDLC" vs AI-Assisted Development

**Issue:** Using industry terminology imprecisely can mislead contributors about capabilities and autonomy levels.

**What happened:**
- In `docs/agentic-sdlc.md`, we described the repo's workflow as "Agentic SDLC"
- During discussion about applying this to remaining modules, user asked me to verify industry backing
- Research confirmed "Agentic SDLC" is a well-established 2026 industry term (Forrester, Gartner, academic)
- **BUT** the industry definition means: autonomous agents with retry loops, multi-agent collaboration (Product Agent ↔ Coding Agent ↔ Review Agent), agent-to-agent communication, autonomous planning/execution/testing/refinement (Devin, SWE-agent)
- User provided the precise definition: "autonomous AI agents actively participate in, and eventually orchestrate, the software engineering process"
- What we actually implement: **human-supervised AI-assisted development** - agents generate code, gates verify, humans approve at each phase
- We were using "agentic" to mean "agent-assisted" when industry uses it to mean "autonomous multi-agent"

**Impact:**
- Documentation claimed a level of autonomy we don't actually have
- Could mislead contributors about what to expect
- Risks damaging credibility if contributors discover the mismatch
- Creates confusion about the intentional design choice (quality over speed)

**How we discovered it:**
- User asked for industry backing research
- I searched and found extensive coverage (Forrester, Gartner, PwC, arXiv)
- User then provided the precise industry definition
- Revealed the terminology mismatch

**Resolution implemented:**

1. **Updated `docs/agentic-sdlc.md` (PR #31):**
   - Added section: "Where this repo sits on the autonomy spectrum"
   - Clarified industry definition vs our implementation
   - Explained why we chose human-supervised (quality control, +41% complexity with full autonomy)
   - Noted future evolution path (Workflow tool enables retry loops)
   - Added terminology note: "agentic-lite" or "supervised agentic"

2. **Accurate positioning:**
   - Industry definition: Fully autonomous multi-agent orchestration
   - This repo: Human-supervised AI-assisted development
   - Terminology: Using "agentic SDLC" as shorthand, with explicit clarification

**Lesson learned:**

> **Be precise with industry terminology, especially when it's rapidly evolving.**  
> If borrowing an industry term but implementing differently, explicitly clarify the distinction.  
> Better to be honest about "supervised agentic" than claim "full agentic" and disappoint.

**What the research actually showed:**
- **Adoption:** 70% of software teams use GenAI across SDLC (PwC, 2026)
- **Performance:** SWE-bench Verified: 1.96% → 78.4% (Oct 2023 → Apr 2026)
- **Productivity:** 13.6%-55.8% time savings
- **Quality risks:** +30% code warnings, +41% complexity (CMU study, 807 projects)
- **Silent errors:** 75.17% of multi-agent failures are "gray errors" (pass tests, wrong logic)

**Why our approach is intentional:**
- Research validates human gates as quality control
- +15.6% improvement with builder-validator chains (tests approved first)
- Quality over speed is a legitimate design choice

**Artifacts:**
- PR #31: Terminology clarification in docs/agentic-sdlc.md
- Industry research sources documented in that PR

**What to do differently:**
- When using industry terms, verify precise definitions
- If implementing a variant, explicitly state how it differs
- Cite research to support design choices
- Be honest about current state vs future evolution
- "Supervised agentic" > claiming "full agentic" without autonomy

---

## 2026-09-08: API Spec Verification Gap

**Issue:** No mandatory step to verify API endpoint contract before coding modules.

**What happened:**
- While designing `support_level_info` (#12), we assumed the three endpoints (`/v2/support-levels/architectures`, `/features`, `/features/detailed`) were simple GETs with only a `kind` parameter to differentiate them
- Started writing a walkthrough for manual implementation without checking the actual API spec
- User asked: "is timeout defined in the swagger spec?" (excellent question!)
- This prompted checking the actual spec, which revealed ALL three endpoints require:
  - `openshift_version` (required query parameter)
  - `cpu_architecture` (optional, with enum choices)
  - `platform_type` (optional, with enum choices)
  - `external_platform_name` (optional)
- We had completely missed these required parameters by assuming instead of verifying

**Impact:**
- If we'd continued without checking, the module would have been implemented with the wrong `argument_spec`
- Tests would have mocked incorrect API calls
- Module would fail when used against the real API
- Would require rework and potentially a breaking change to fix

**How we discovered it:**
- User asked a probing question about timeout
- This triggered verification of the actual API spec using curl/jq
- Revealed the parameter mismatch

**Resolution implemented:**

1. **Created mandatory verification workflow:**
   - New file: `docs/api-verification-template.md` - Step-by-step checklist
   - Updated: `CLAUDE.md` - Added spec verification requirement with curl/jq example
   - Updated: `.claude/skills/new-ai-endpoint-module/SKILL.md` - "FIRST, query the spec" section
   - Updated: `CONTRIBUTING.md` - References verification template
   - Updated: `docs/contributor-quick-start.md` - Added verification step in Step 2

2. **Process change:**
   - Before coding ANY module, query the OpenAPI spec
   - Document findings using the verification template
   - Never assume parameter names, types, or requirements
   - Post findings in issue comments or commit message

3. **Corrected module difficulty ratings:**
   - `supported_operator_info` (#13) → Easiest (no query params)
   - `support_level_info` (#12) → Medium (complex query params)

4. **Validated existing modules:**
   - Audited `openshift_version_info`, `infra_env`, `host_action` against spec
   - All three were correct (we got lucky on those three!)

**Lesson learned:**

> **Always query the OpenAPI spec BEFORE designing the module interface.**  
> The spec is the source of truth - assumptions lead to bugs.

**Command to verify any endpoint:**
```bash
# For GET endpoints with query params
curl -s "https://api.openshift.com/api/assisted-install/v2/openapi" | \
  jq '.paths."/v2/your-endpoint".get.parameters'

# For POST endpoints with body schema
curl -s "https://api.openshift.com/api/assisted-install/v2/openapi" | \
  jq '.definitions."your-create-params" | {required, properties: .properties | keys}'
```

**Artifacts:**
- PR #28: Add API spec verification workflow
- Template: `docs/api-verification-template.md`

**What to do differently:**
- Never skip spec verification, even for "simple-looking" endpoints
- Use the verification template checklist
- Document findings before coding
- If uncertain about parameters, query the spec - don't guess

---

## 2026-09-09: HTTP Status Code Handling Strategy Gap

**Issue:** No documented strategy for handling different HTTP status codes across module types.

**What happened:**
- While implementing `supported_operator_info` (#13), user asked: "what return codes are specified in the openapi spec?"
- Queried the spec and found:
  - `GET /supported-operators`: returns 200, 401, 403, 500
  - `GET /supported-operators/{name}`: returns 200, 401, 403, **404**, 500
- Current implementation treats all non-200 as generic failure: `if status != 200: module.fail_json(...)`
- This raised the question: **Should we handle specific status codes differently?**

**Impact of current generic approach:**
- ❌ User gets `"Failed to retrieve supported operators (HTTP 404)"` instead of `"Operator 'nonexistent' not found"`
- ❌ No distinction between "typo in operator name" (404) vs "auth failure" (401) vs "server error" (500)
- ✅ Simple, consistent code across all modules
- ✅ HTTP status is still visible in error message for debugging

**The deeper question - what about different module types?**

User observed: "We would have to take into account all the REST API calls"

**404 means different things:**
1. **Info module** querying specific resource: `name: nonexistent` → probably user error (typo)
2. **State module DELETE**: resource not found → **idempotent success** (`changed=False`, not an error!)
3. **State module PATCH**: resource not found → error (can't update what doesn't exist)
4. **Action module**: POST action to non-existent resource → error

**401/403 are consistent across all types:**
- Authentication/authorization failure → always `fail_json`

**What's missing:**
- No documented strategy in DESIGN.md for error handling
- No decision on: generic vs specific error messages
- No guidance on: which status codes warrant special handling per module type
- No consistency check across existing modules

**What we need to decide:**

1. **Error message specificity:**
   - Option A (current): Generic message + status code → simpler, consistent
   - Option B: Status-specific messages → better UX, more code, potential inconsistency

2. **404 handling per module type:**
   - Info modules: error with helpful message?
   - State DELETE: `changed=False` (idempotent)
   - State GET (drift check): treat as "absent"
   - State PATCH: error
   - Action modules: error

3. **Documentation location:**
   - Add "Error Handling Strategy" section to DESIGN.md
   - Include decision rationale and per-type rules
   - Update module authoring checklist

**Resolution: DEFERRED**

This requires:
1. Audit all existing modules (`openshift_version_info`, `infra_env`, `host_action`)
2. Check how each handles non-200 status codes
3. Identify inconsistencies
4. Design comprehensive strategy covering all module types × all status codes
5. Document in DESIGN.md
6. Update existing modules if needed

**Tracking:** Issue #30 - Design comprehensive error-handling strategy for HTTP status codes

**Lesson learned:**

> **Error handling is a cross-cutting concern that needs a documented strategy.**  
> Status code semantics vary by module type (404 for DELETE is success, for PATCH is error).  
> Don't design error handling per-module; design it once for the entire collection.

**What to do differently:**
- Before implementing more modules, decide the error-handling strategy
- Document it in DESIGN.md alongside the idempotency patterns
- Apply it consistently across all new modules
- Audit and update existing modules to match

**Current state:**
- `supported_operator_info` uses generic approach (matches `openshift_version_info`)
- Decision deferred until we can design holistically
- All tests pass with current approach

---

## Template for Future Entries

**Date:** YYYY-MM-DD: Title

**Issue:** What went wrong or what we discovered

**What happened:** Detailed narrative

**Impact:** What could have happened / what did happen

**How we discovered it:** How the issue surfaced

**Resolution implemented:** What we did to fix it (with PR numbers, file references)

**Lesson learned:** Key takeaway in one sentence

**Artifacts:** PRs, commits, new files created

**What to do differently:** Actionable guidance for future work

---

## Contributing to This Journal

**When to add an entry:**
- Discovered a gap in our process or documentation
- Found a bug that points to a systemic issue
- Made a design decision that future contributors should know about
- Encountered an API behavior that wasn't obvious from the spec
- Implemented a workaround that needs explaining

**What NOT to log here:**
- Simple bugs fixed in normal development
- Expected test failures
- Individual module implementation details (those go in commit messages)

**Format:**
- Chronological (newest at top after this entry)
- Focus on lessons that apply to future work
- Include enough context that someone reading 6 months later understands
- Link to PRs, issues, commits for details
