# Security Policy

## Reporting a vulnerability

**Do not open a public issue or pull request for a security vulnerability.**
Public reports can expose users before a fix is available.

Instead, report privately via GitHub Security Advisories:

1. Go to the repository's **Security** tab → **Report a vulnerability**
   (this opens a private advisory only the maintainers can see).
2. Describe the issue, the impact, and steps to reproduce.

If you cannot use GitHub Security Advisories, open a minimal issue titled
"Security contact request" (no details) and a maintainer will arrange a private
channel.

### What to include

- The affected module(s) or file(s).
- What an attacker could do (e.g. leaked token, request to an unintended host).
- A minimal reproduction — **redact any real tokens, `pull_secret`s, or response
  bodies** before sharing (see [docs/security.md](docs/security.md)).

### What to expect

- We aim to acknowledge a report within a few business days.
- We'll work with you on a fix and a coordinated disclosure, and credit you in
  the release notes unless you prefer to stay anonymous.

## Scope

This collection wraps the OpenShift Assisted Installer API. Security-relevant
areas include credential handling (`api_token` / `offline_token` / `pull_secret`),
TLS verification of API calls, and never leaking secrets into logs, return
values, or test fixtures. Secure-coding and testing practices for contributors
live in [docs/security.md](docs/security.md).

## Supported versions

This project is pre-`1.0.0` and under active development. Security fixes land on
`main` and in the latest release; older pre-release tags are not maintained.
