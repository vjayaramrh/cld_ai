#!/usr/bin/env bash
# PreToolUse(Bash) hook: refuse `git commit` while on the main branch.
# Complements the git pre-commit hook (scripts/install-hooks.sh) and remote
# branch protection; this one fires before the tool call executes.
set -euo pipefail

input="$(cat)"
command="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"

# Match `git commit` only when it begins a command segment (start of string, or
# after a ; && || | separator) -- so it does not trip on `echo "git commit"` or
# a commit message that merely mentions the phrase.
if ! printf '%s' "$command" \
  | grep -Eq '(^|[;&|])[[:space:]]*git[[:space:]]+commit([[:space:]]|$)'; then
  exit 0
fi

branch="$(git -C "${CLAUDE_PROJECT_DIR:-.}" symbolic-ref --short HEAD 2>/dev/null || echo "")"
if [ "$branch" = "main" ]; then
  echo "Refusing to commit on 'main'. Create a feature branch first:
  git checkout -b <type>/<description>
(see CLAUDE.md -> Git workflow)." >&2
  exit 2   # exit 2 blocks the tool; stderr is returned to Claude as the reason
fi
exit 0
