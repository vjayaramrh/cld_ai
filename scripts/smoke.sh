#!/usr/bin/env bash
#
# Verification suite — runs INSIDE the container (see run.sh).
# Fast by default; `--full` adds the collection install round-trip.
# We are already in a container, so ansible-test runs WITHOUT --docker.
#
set -uo pipefail

FULL=0
[ "${1:-}" = "--full" ] && FULL=1

pass=0
fail=0
section() { printf '\n=== %s ===\n' "$1"; }
ok()   { printf '  ok:   %s\n' "$1"; pass=$((pass + 1)); }
no()   { printf '  FAIL: %s\n' "$1"; fail=$((fail + 1)); }
skip() { printf '  skip: %s\n' "$1"; }

# --- collection builds --------------------------------------------------------
section "collection builds"
if ansible-galaxy collection build --force --output-path /tmp >/tmp/build.log 2>&1; then
    ok "ansible-galaxy collection build"
else
    no "ansible-galaxy collection build"
    tail -30 /tmp/build.log
fi

# --- sanity -------------------------------------------------------------------
section "ansible-test sanity"
if ansible-test sanity --color >/tmp/sanity.log 2>&1; then
    ok "ansible-test sanity"
else
    no "ansible-test sanity"
    tail -40 /tmp/sanity.log
fi

# --- units (only if tests exist) ---------------------------------------------
section "ansible-test units"
if ls tests/unit/plugins/modules/test_*.py >/dev/null 2>&1; then
    if ansible-test units --color >/tmp/units.log 2>&1; then
        ok "ansible-test units"
    else
        no "ansible-test units"
        tail -40 /tmp/units.log
    fi
else
    skip "no unit tests yet (add tests/unit/plugins/modules/test_*.py)"
fi

# --- full: collection install round-trip -------------------------------------
if [ "${FULL}" -eq 1 ]; then
    section "collection install round-trip"
    tarball="$(ls -t /tmp/${USER:-}*assisted_installer-*.tar.gz /tmp/*assisted_installer-*.tar.gz 2>/dev/null | head -1)"
    if [ -n "${tarball}" ] && \
       ansible-galaxy collection install "${tarball}" -p /tmp/collections --force >/tmp/install.log 2>&1; then
        ok "ansible-galaxy collection install"
    else
        no "ansible-galaxy collection install"
        tail -30 /tmp/install.log 2>/dev/null || true
    fi
fi

printf '\npassed: %s failed: %s\n' "${pass}" "${fail}"
[ "${fail}" -eq 0 ]
