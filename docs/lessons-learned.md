# Lessons Learned

A chronological journal of issues discovered, resolutions implemented, and lessons learned during development of the `openshift_lab.assisted_installer` collection.

**Format:** Each entry documents what went wrong, how we fixed it, and what to do differently going forward.

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
