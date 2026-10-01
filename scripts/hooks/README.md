# Claude Code hooks

Workflow guards that run as [Claude Code hooks](https://code.claude.com/docs/en/hooks).
They are wired up in `.claude/settings.json` (committed, so every contributor using
Claude Code in this repo gets them) and complement — do not replace — the git
pre-commit hook (`scripts/install-hooks.sh`) and GitHub branch protection.

All three are plain `bash` + `jq`; the merge gate also needs an authenticated
`gh`. The `.claude/` and `scripts/` directories are `build_ignore`d in `galaxy.yml`,
so none of this ships in the collection tarball.

## The hooks

| Script | Event | What it does |
|---|---|---|
| `guard-commit-on-main.sh` | `PreToolUse(Bash)` | Blocks `git commit` while on `main` (exit 2). Enforces the branch-only workflow earlier than the git hook. |
| `check-module-edit.sh` | `PostToolUse(Edit\|Write)` | On edits to `plugins/modules/*.py`, runs `py_compile` and checks for the GPLv3 header. Cannot block (edit already applied) — surfaces a fast notice so a broken module is caught before `./run.sh --check`. |
| `gate-pr-merge.sh` | `PreToolUse(Bash)` | Blocks `gh pr merge` unless (1) a cost-breakdown comment carrying `<!-- cost-breakdown -->` was posted on the PR in the last 15 min (CLAUDE.md §6 atomic-cost rule) **and** (2) the PR has no unresolved review threads. |

## Design notes (read before editing these)

- **Command matching is a heuristic, not a parser.** The `git commit` / `gh pr merge`
  guards match the command only when the phrase begins a command segment (start of
  line or after `;`/`&&`/`||`/`|`). A `grep` on the raw command string *cannot*
  distinguish a quoted mention from real shell syntax, so a literal `&& git commit`
  inside a string will still match. For a fail-*safe* guard (errs toward blocking)
  that is acceptable; do not assume it is airtight.
- **The merge gate is fail-closed.** Any `gh`/network error, or an unparseable PR
  number, routes through `deny()` (exit 0 + a `permissionDecision: "deny"` JSON).
  This matters: Claude Code only *blocks* on exit 2 or an explicit deny decision —
  a bare non-zero exit (e.g. `set -e` aborting mid-script) is treated as a
  **non-blocking** error and the tool would proceed. Keep every rejection path
  going through `deny()`; never let `set -e` kill the script before it.

## Testing a change

These guards block Bash calls that contain the trigger phrases, so to test them
put the JSON payload in a file and feed it on stdin (keeps the phrase out of your
own command line):

```bash
printf '{"tool_input":{"command":"gh pr merge 70"}}' > /tmp/p.json
scripts/hooks/gate-pr-merge.sh < /tmp/p.json; echo "exit=$?"
```
