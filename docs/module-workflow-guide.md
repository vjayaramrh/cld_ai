# Module Workflow Guide

**Status:** 🏗️ PROVISIONAL - All model recommendations unvalidated until cluster_info (#10) completes.

See [api-endpoint-map.md](api-endpoint-map.md) for module→pattern→phase mapping.

## Purpose

Track model usage, costs, time, and task breakdown for each module implementation. This guide helps answer:
- Which AI model to use for each phase of module development?
- What are the actual costs and time investments?
- Which patterns are proven vs. theoretical?

## Completed Modules

| Module | Pattern | Model(s) | Cost | Time | Date | Notes |
|--------|---------|----------|------|------|------|-------|
| openshift_version_info | info | Sonnet | ~$0.28 | ~45m | 2026-08-18 | First module, pre-TDD |
| supported_operator_info | info | Sonnet | ~$0.31 | ~50m | 2026-09-09 | 404 handling, pre-TDD |
| infra_env | state | Sonnet | ~$0.65 | ~90m | 2026-08-26 | Reference state module |
| host_action | action | Sonnet | ~$0.42 | ~60m | 2026-08-29 | Reference action module |

**Notes on completed modules:**
- All costs are estimates reconstructed from session context
- Pre-TDD workflow (module + tests generated together)
- Times include human review and iteration

## In Progress

| Module | Pattern | Planned Approach | Status | Started |
|--------|---------|------------------|--------|---------|
| cluster_info | info | TDD (Sonnet) | Pending start | 2026-09-15 |

## Task Breakdown by Pattern

### Info Modules (TDD Workflow)

⚠️ **PROVISIONAL** - Validating with cluster_info (#10)

| Phase | Task | Model | Est. Time | Validation |
|-------|------|-------|-----------|------------|
| 1 | API spec verification | Sonnet | 10-15m | ⚠️ TBD |
| 2 | Test generation | Sonnet | 15-20m | ⚠️ TBD |
| 3 | Test review (human) | N/A | 10-15m | N/A |
| 4 | Module generation | Sonnet/Haiku | 15-20m | ⚠️ TBD |
| 5 | Gate verification (`./run.sh --check`) | Automated | 5-10m | N/A |
| 6 | PR creation | N/A | 5m | N/A |
| **Total** | | | **60-90m** | ⚠️ TBD |

**Key questions to validate:**
- Can Haiku generate module after tests approved? (Phase 4)
- Are time estimates accurate?
- Does TDD actually improve quality?

### State Modules

⚠️ **TBD** - Will validate with cluster (#11) after cluster_info

Expected phases:
1. API spec verification (Sonnet)
2. Test generation (Sonnet) - lifecycle, idempotency, check-mode, safety guards, API contract
3. Test review (Human)
4. Module generation (Sonnet recommended - lifecycle complexity)
5. Gate verification
6. PR creation

Estimated: 90-120m (more complex than info modules)

### Action Modules

✅ Pattern proven with host_action, but pre-TDD workflow

Expected TDD workflow:
1. API spec verification (Sonnet)
2. Test generation (Sonnet) - action verbs, status guards
3. Test review (Human)
4. Module generation (Sonnet/Haiku)
5. Gate verification
6. PR creation

Estimated: 60-90m

## Model Selection Decision Tree

⚠️ **PROVISIONAL** - Guidelines to validate with cluster_info

### When to use Sonnet

**Always use Sonnet for:**
- ✅ API spec verification (every module - easy to miss params)
- ✅ Test generation for complex/novel endpoints
- ✅ First module of a new pattern
- ✅ State modules (lifecycle complexity)

**Reason:** Higher quality, better edge case reasoning, accurate spec interpretation.

### When to consider Haiku

**Candidates for Haiku:**
- ⚡ Module generation AFTER tests approved (lowest risk - tests define contract)
- ⚡ Nth simple info module (pattern established, straightforward)
- ⚡ Non-critical iterations/fixes

**Reason:** Faster, cheaper, sufficient when pattern is clear.

### Hybrid Approach (Recommended for Validation)

**Phase breakdown:**
1. **Sonnet:** Spec verification + test generation (~60% of cognitive work)
2. **Haiku:** Module generation to satisfy approved tests (~40% of code generation)

**Benefits:**
- Quality where it matters (tests define the contract)
- Speed where it's safe (code satisfies known tests)
- Estimated savings: 30-40% on total cost

**Validation needed:**
- Does Haiku produce quality code from approved tests?
- How often do we need iterations?
- Is the cost savings worth the potential rework?

## Cost Tracking Template

Use this template when implementing a module. Track tokens at each phase boundary.

```markdown
### Module: [module_name]

**Model:** [Sonnet / Haiku / Hybrid: Sonnet tests + Haiku module]
**Pattern:** [info / state / action]
**Date:** YYYY-MM-DD

**Sonnet 4.5 pricing:**
- Input: $3.00 per million tokens
- Output: $15.00 per million tokens

| Phase | Input Tokens | Output Tokens | Input Cost | Output Cost | Phase Total |
|-------|--------------|---------------|------------|-------------|-------------|
| 1. Spec verification | | | | | |
| 2. Test generation | | | | | |
| 3. Module generation | | | | | |
| 4. Verification & PR | | | | | |
| **Total** | | | | | **$X.XX** |

**Time breakdown:**
- Spec verification: Xm
- Test generation: Xm
- Test review (human): Xm
- Module generation: Xm
- Gate verification: Xm
- PR creation: Xm
**Total:** Xm

**Notes:**
- [Any learnings, issues encountered, quality observations]
- [Model performance observations]
- [Whether estimates were accurate]
```

## Validation Criteria

**cluster_info (#10) will validate:**
- [ ] TDD workflow time estimates accurate?
- [ ] Can Haiku handle module generation from approved tests?
- [ ] Actual costs vs. estimates
- [ ] Quality differences (Sonnet vs. Haiku for module generation)
- [ ] Template completeness (missing phases/data?)
- [ ] Does TDD prevent "gray errors"?

**After cluster_info completes:**
1. Update this document with actual data
2. Mark validated phases with ✅
3. Update time estimates with actuals
4. Promote model recommendations from ⚠️ to ✅ where proven
5. Add lessons learned to process

**Future validations:**
- support_level_info (#12) - Complex query params with TDD
- cluster (#11) - State module with TDD (most complex)

## Pricing Reference

**Claude Sonnet 4.5:**
- Input: $3.00 per million tokens
- Output: $15.00 per million tokens

**Claude Haiku 4.5:**
- Input: $0.25 per million tokens
- Output: $1.25 per million tokens

**Cost comparison (typical module):**
- Full Sonnet: ~$0.30-0.40
- Full Haiku: ~$0.03-0.05 (90% savings, ⚠️ quality risk)
- Hybrid: ~$0.20-0.25 (30-40% savings)

## Related Documentation

- [api-endpoint-map.md](api-endpoint-map.md) - Module→pattern→phase mapping (what to build)
- [DESIGN.md](../DESIGN.md) - Idempotency patterns and testing strategy
- [CLAUDE.md](../CLAUDE.md) - Module authoring workflow and conventions
- [contributor-quick-start.md](contributor-quick-start.md) - Step-by-step onboarding
- [testing-cheat-sheet.md](testing-cheat-sheet.md) - Test patterns and examples

## Update Log

| Date | Change | Reason |
|------|--------|--------|
| 2026-09-15 | Initial creation | Track costs and validate model selection for cluster_info |

---

**Next:** Validate with cluster_info (#10), then update with real data.
