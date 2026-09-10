# Lessons Learned

A chronological journal of issues discovered, resolutions implemented, and lessons learned during development of the `openshift_lab.assisted_installer` collection.

**Format:** Each entry documents what went wrong, how we fixed it, and what to do differently going forward.

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
