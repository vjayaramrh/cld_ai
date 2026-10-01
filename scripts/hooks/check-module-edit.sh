#!/usr/bin/env bash
# PostToolUse(Edit|Write) hook: quick checks on edited module source.
# PostToolUse cannot block (the edit already applied) -- this surfaces a fast
# notice so a syntax error or missing license header is caught before you spend
# time on ./run.sh --check.
set -euo pipefail

input="$(cat)"
file_path="$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')"

case "$file_path" in
  */plugins/modules/*.py) ;;
  *) exit 0 ;;
esac
[ -f "$file_path" ] || exit 0

problems=""

if ! out="$(python3 -m py_compile "$file_path" 2>&1)"; then
  problems="${problems}py_compile failed:\n${out}\n"
fi

# GPLv3 header must appear in the first 20 lines (CLAUDE.md module rule).
if ! head -n 20 "$file_path" | grep -q "GNU General Public License"; then
  problems="${problems}missing GPLv3 header in first 20 lines\n"
fi

if [ -n "$problems" ]; then
  printf "Module check for %s:\n%b" "$(basename "$file_path")" "$problems" >&2
  exit 2   # non-blocking notice for PostToolUse
fi
exit 0
