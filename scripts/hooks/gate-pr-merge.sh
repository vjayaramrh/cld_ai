#!/usr/bin/env bash
# PreToolUse(Bash) hook: gate `gh pr merge`. Blocks the merge unless BOTH hold
# (CLAUDE.md §6):
#   1. a cost-breakdown comment carrying the marker <!-- cost-breakdown --> was
#      posted on the PR within the last 15 min (cost is atomic with merge), and
#   2. the PR has no unresolved review threads.
# Fail-closed: any gh/network error denies rather than waving the merge through.
set -euo pipefail

input="$(cat)"
command="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"

# Match `gh pr merge` only when it begins a command segment (start of string, or
# after a ; && || | separator) -- so it does not trip on a quoted mention.
if ! printf '%s' "$command" \
  | grep -Eq '(^|[;&|])[[:space:]]*gh[[:space:]]+pr[[:space:]]+merge([[:space:]]|$)'; then
  exit 0
fi

deny() {
  jq -nc --arg reason "$1" '{hookSpecificOutput: {
    hookEventName: "PreToolUse", permissionDecision: "deny",
    permissionDecisionReason: $reason}}'
  exit 0   # JSON deny is parsed only on exit 0
}

# `|| true` so a no-match grep doesn't trip `set -e` and exit 1 (which Claude
# Code treats as a NON-blocking error -- the merge would slip through). We want
# the empty-pr case to fall through to deny() below, which exits 0 and blocks.
pr="$(printf '%s' "$command" | grep -oE 'gh pr merge[[:space:]]+#?[0-9]+' \
      | grep -oE '[0-9]+' | head -n1 || true)"
[ -n "$pr" ] || deny "Could not parse a PR number from the merge command; refusing so the gate can't be bypassed. Use 'gh pr merge <number>'."

# Resolve owner/name once (GraphQL needs real values, not gh's REST {owner} macro).
nwo="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")"
[ -n "$nwo" ] || deny "Could not resolve the repository (gh auth/network?). Refusing to merge fail-closed."
owner="${nwo%%/*}"; name="${nwo##*/}"

# --- 1. Fresh cost-breakdown comment (hidden marker, not prose) ---------------
cutoff="$(date -u -v-15M +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
         || date -u -d '15 minutes ago' +%Y-%m-%dT%H:%M:%SZ)"
cost="$(gh api "repos/${owner}/${name}/issues/${pr}/comments" \
  --jq "[.[] | select((.body | contains(\"<!-- cost-breakdown -->\")) and .created_at > \"${cutoff}\")] | length" \
  2>/dev/null || echo "ERR")"
[ "$cost" != "ERR" ] || deny "Could not query PR #${pr} comments (gh/network?). Refusing to merge fail-closed."
[ "${cost:-0}" -ge 1 ] || deny "No cost-breakdown comment with the '<!-- cost-breakdown -->' marker on PR #${pr} in the last 15 min. Per CLAUDE.md §6, post the cost breakdown (with the marker) in the SAME step as the merge, then merge."

# --- 2. No unresolved review threads -----------------------------------------
unresolved="$(gh api graphql -f query='
  query($owner:String!,$name:String!,$pr:Int!){
    repository(owner:$owner,name:$name){
      pullRequest(number:$pr){
        reviewThreads(first:100){ nodes{ isResolved } }
      }
    }
  }' -f owner="$owner" -f name="$name" -F pr="$pr" \
  --jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved==false)] | length' \
  2>/dev/null || echo "ERR")"
[ "$unresolved" != "ERR" ] || deny "Could not query review threads on PR #${pr}. Refusing to merge fail-closed."
[ "${unresolved:-0}" -eq 0 ] || deny "PR #${pr} has ${unresolved} unresolved review thread(s). Per CLAUDE.md §6, apply fixes and resolve every thread before merging."

exit 0
