# Lessons Learned

A chronological journal of issues discovered, resolutions implemented, and lessons learned during development of the `openshift_lab.assisted_installer` collection.

**Format:** Each entry documents what went wrong, how we fixed it, and what to do differently going forward.

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
