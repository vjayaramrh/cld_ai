# Lessons Learned

A chronological journal of issues discovered, resolutions implemented, and lessons learned during development of the `openshift_lab.assisted_installer` collection.

**Format:** Each entry documents what went wrong, how we fixed it, and what to do differently going forward.

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

**Next steps (before implementing cluster_info):**
1. ✅ Document this gap (this entry)
2. ⏳ Present granularity options with precedent analysis
3. ⏳ User decides design principle
4. ⏳ Update DESIGN.md with principle + rationale
5. ⏳ Revise api-endpoint-map.md to match principle
6. ⏳ Then implement cluster_info following validated pattern

**Artifacts:**
- This lessons-learned entry
- Pending: DESIGN.md update with granularity principle
- Pending: api-endpoint-map.md revision

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
