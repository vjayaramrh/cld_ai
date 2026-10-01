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
- **Don't echo secret-bearing *inputs* either.** A value like `base_url` can embed
  credentials (`https://user:pass@host`). A validation or error message must omit
  the raw value, and checks must be ordered so any message that *does* include it
  runs only after credentials are ruled out — otherwise the guard meant to reject a
  secret ends up leaking it (see `_validate_base_url`, and lessons-learned.md
  2026-09-30 "A Validation Error Message Leaked the Secret It Was Guarding").
- **Never commit secrets.** `.gitignore` blocks the common shapes (`*.token`,
  `*token*.txt`, `pull_secret*`, `pull-secret*.json`, `.env`), and a
  secret-scanning gate (below) runs in CI — but the first line of defense is not
  writing them to disk in the repo at all.

## 2. Fail fast on authentication

If no token resolves, the module must **`fail_json` with a clear message** — never
send `Authorization: Bearer None`. The shared client's `resolve_token()` already
does this; use it instead of reading the token yourself. Its precedence is:
`api_token` param → `AI_API_TOKEN` env → `AI_OFFLINE_TOKEN` env (refreshed via
Red Hat SSO into a short-lived access token). As defense in depth, `request()`
also fails fast if it is ever handed a falsy token, so a `Bearer None` header can't
slip through. Token refresh validates the SSO response body (a non-JSON or
non-object body fails cleanly rather than raising).

## 3. TLS is verified — keep it that way

All API calls go over HTTPS with **certificate verification on**. `fetch_url`
verifies certificates by default: it reads `validate_certs` from `module.params`
and falls back to `True` when the module does not expose that option — which ours
do not. The shared client therefore relies on that secure default rather than
passing `validate_certs` to `fetch_url` itself (`fetch_url` does **not** accept
`validate_certs` as a keyword argument — passing it raises `TypeError`; see
lessons-learned "Right Fix, Wrong Explanation").

- Do **not** disable certificate verification to work around a self-signed test
  endpoint. Use the integration mock server's documented setup instead.
- If a `validate_certs` option is ever exposed to users, it must **default to
  `True`**; turning it off is opt-in and clearly a footgun. (Because `fetch_url`
  reads `validate_certs` from `module.params`, merely adding such an option with a
  `True` default would wire it through — no change to the shared client needed.)

## 4. Every call has a timeout

Each request sets a timeout (a module param, default 30s) so a hung server can't
stall a playbook indefinitely. Use the shared client, which always applies one.

## 5. Use the shared client — don't hand-roll HTTP

Auth headers, base-URL building, query encoding, and TLS live in
`plugins/module_utils/assisted_installer.py`. Building these by hand in each
module is how inconsistencies (and security gaps) creep in. Never import
`requests`.

The `base_url` override (integration-mock only) is validated to prevent credential
leakage: HTTPS is always allowed; HTTP is allowed only for loopback
(`127.0.0.1`/`localhost`/`::1`); and an embedded-credentials URL
(`https://user:pass@host`) is rejected outright so the bearer token can't be sent
to a userinfo host. The rejection message deliberately omits the URL so an embedded
password can't leak into logs.

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
