# Note on validate_certs Parameter Removal

## What Changed

Removed explicit `validate_certs=True` argument from two `fetch_url()` calls in
`plugins/module_utils/assisted_installer.py` (`_refresh_token()` and `request()`).

## Why This Was a Real Fix (Not a No-Op)

`ansible.module_utils.urls.fetch_url()` **does not accept `validate_certs` as a
keyword argument** in ansible-core 2.17–2.19. Its signature is:

```python
def fetch_url(module, url, data=None, headers=None, method=None,
              use_proxy=None, force=False, last_mod_time=None, timeout=10,
              use_gssapi=False, unix_socket=None, ca_path=None, cookies=None,
              unredirected_headers=None, decompress=True, ciphers=None,
              use_netrc=True):
```

Instead, `fetch_url()` reads certificate validation from `module.params`,
defaulting to `True` when `validate_certs` is absent, and passes it to
`open_url()`. (Verified against the ansible-core `stable-2.17`, `stable-2.18`,
and `stable-2.19` sources.)

Passing `validate_certs=True` as a keyword therefore raised:

```
fetch_url() got an unexpected keyword argument 'validate_certs'
```

Removing the unsupported keyword **resolves the TypeError** while **retaining
default TLS validation** (`True`), because that is the default `fetch_url()`
applies when the parameter is absent.

## Root Cause (Identified)

The `TypeError` is exactly consistent with passing an unsupported keyword to
`fetch_url()`. There is no mystery: the argument was never part of the
`fetch_url()` signature. The correct way to control TLS validation is via the
module's `argument_spec`/`module.params`, not a `fetch_url()` keyword.

## Current Status

**Change kept** because it is the correct fix:
- Removes the unsupported keyword that caused the `TypeError`
- Retains default TLS certificate validation (`True`)

## How Certificate Validation Works Now

TLS validation defaults to `True` via `fetch_url()`'s read of `module.params`.
If a future requirement needs to expose `validate_certs` to users, add it to the
module `argument_spec` (default `True`); do **not** pass it directly to
`fetch_url()`.

## Lesson Learned

See `docs/lessons-learned.md` entry "Bug Fix Verification Gap" (2026-09-29).

**Verify the actual API contract before shipping a fix or documenting it:**
1. Check the function signature in the target library/version
2. Reproduce the original error
3. Confirm the fix resolves it
4. Document the real root cause, not a guess
