# Note on validate_certs Parameter Removal

## What Changed

Removed explicit `validate_certs=True` parameter from two `fetch_url()` calls in `plugins/module_utils/assisted_installer.py`:
- Line 128: `_refresh_token()` function
- Line 175: `request()` function

## Why This Change is a No-Op

Per Opus review and `ansible.module_utils.urls.fetch_url` documentation:
- `validate_certs` **is** a valid parameter
- Default value: `True`
- Removing explicit `validate_certs=True` changes nothing behaviorally

## Original Error (Unresolved)

The change was made in response to an error message:
```
fetch_url() got an unexpected keyword argument 'validate_certs'
```

**However:** This error is **inconsistent** with the parameter being valid and working in production Ansible versions. The **real root cause** was never identified.

## Possible Causes (Uninvestigated)

1. **Version mismatch:** Older Ansible version that doesn't support validate_certs?
2. **Misread error:** Error was actually about a different parameter?
3. **Module import issue:** fetch_url imported from wrong location?
4. **Testing artifact:** Error from test environment, not production code?

## Current Status

**Change kept** because:
- Removing explicit `validate_certs=True` is harmless (it's the default)
- Reduces parameter noise
- No behavioral impact

**Not marked as bug fix** because:
- Doesn't actually fix anything
- Real error cause unknown
- May resurface if root cause is environmental

## Action Required

If the original error reoccurs:
1. Document the **exact error message** and **full stack trace**
2. Note the **Ansible version** (`ansible --version`)
3. Verify `fetch_url` import: `from ansible.module_utils.urls import fetch_url`
4. Test with explicit `validate_certs=True` to confirm parameter validity
5. Check if it's an ansible-test vs. runtime difference

## Lesson Learned

See `docs/lessons-learned.md` entry "Bug Fix Verification Gap" (2026-09-29).

**Don't ship a fix without:**
1. Documenting the original error
2. Reproducing the failure
3. Verifying the fix resolves it
4. Testing that the error doesn't recur
