# Secure coding & testing

The practices every module in this collection must follow to handle credentials
and API calls safely. These are enforced partly by review and partly by automated
gates (sanity, units, and secret scanning). To *report* a vulnerability, see
[SECURITY.md](../SECURITY.md).

The rules here consolidate what's stated across [CLAUDE.md](../CLAUDE.md) and
[DESIGN.md](../DESIGN.md) — this page is the single place to read them together.

## 1. Secrets: declare them, never leak them

Any token, `pull_secret`, or key is a **secret parameter**, not an incidental
string.

- **Mark every secret arg `no_log=True`** in `argument_spec`. This keeps its value
  out of Ansible's task logs and `--verbose` output.
- **Source secrets from a param and/or environment**, never a literal. Modules use
  `fallback=(env_fallback, ["AI_API_TOKEN"])` so a token can come from the env
  without appearing in the playbook. In `EXAMPLES`, always use
  `"{{ assisted_installer_token }}"` or an env var — never a real-looking token.
- **Never echo response bodies that may contain secrets.** A failed call may
  return a body with sensitive data; don't blindly put it in `fail_json`. Prefer
  the status code and a safe message. If a body is genuinely needed for
  debugging, be sure it cannot contain a token or `pull_secret`.
- **Never commit secrets.** `.gitignore` blocks the common shapes (`*.token`,
  `*token*.txt`, `pull_secret*`, `pull-secret*.json`, `.env`), and a
  secret-scanning gate (below) runs in CI — but the first line of defense is not
  writing them to disk in the repo at all.

## 2. Fail fast on authentication

If no token resolves, the module must **`fail_json` with a clear message** — never
send `Authorization: Bearer None`. The shared client's `resolve_token()` already
does this; use it instead of reading the token yourself. Its precedence is:
`api_token` param → `AI_API_TOKEN` env → `AI_OFFLINE_TOKEN` env (refreshed via
Red Hat SSO into a short-lived access token).

## 3. TLS is verified — keep it that way

All API calls go over HTTPS with **certificate verification on**. The shared
client passes `validate_certs=True` to `fetch_url` explicitly, so the protection
is visible in the code and can't be lost to a silent default change.

- Do **not** disable certificate verification to work around a self-signed test
  endpoint. Use the integration mock server's documented setup instead.
- If a `validate_certs` option is ever exposed to users, it must **default to
  `True`**; turning it off is opt-in and clearly a footgun.

## 4. Every call has a timeout

Each request sets a timeout (a module param, default 30s) so a hung server can't
stall a playbook indefinitely. Use the shared client, which always applies one.

## 5. Use the shared client — don't hand-roll HTTP

Auth headers, base-URL building, query encoding, and TLS live in
`plugins/module_utils/assisted_installer.py`. Building these by hand in each
module is how inconsistencies (and security gaps) creep in. Never import
`requests`.

## 6. Testing safely

- **Units mock the API at `fetch_url`** (or the shared client). They must **never
  make live calls and never use real credentials.** CI runs with no secrets.
- Required security-relevant unit cases: **fail-fast on a missing token asserts
  zero HTTP calls attempted**, and a non-2xx response maps to `fail_json` without
  leaking a secret-bearing body.
- **Integration tests never hit `api.openshift.com`** — they run against a local
  mock via a `base_url` override, gated so they cannot reach production.
- When verifying manually against the live API, use a **short-lived token from an
  env var**, keep the ad-hoc playbook out of the repo, and never paste raw
  response bodies into issues or PRs. See
  [CONTRIBUTING.md](../CONTRIBUTING.md#manual-verification-against-the-live-api).

## 7. Secret scanning (CI gate)

[gitleaks](https://github.com/gitleaks/gitleaks) runs on every push and pull
request (`.github/workflows/security.yml`) and scans the git history for
committed secrets. A hit **fails the build**. If it flags a false positive (e.g. a
sample value), refine the pattern or add a scoped allow rule rather than deleting
the check. This gate complements `.gitignore`; it does not replace careful
handling.
