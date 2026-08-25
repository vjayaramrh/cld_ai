# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vishwanath Jayaraman (@vjayaramrh)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Unit tests for the infra_env (state-based) module.

The API is mocked at the fetch_url layer (per CLAUDE.md), so the REAL shared
client runs (URL building, query encoding, JSON parsing, status handling). State
modules make several calls per run, so we drive them with ``queue_fetch_url`` and
assert on the recorded ``calls`` which HTTP verbs fired - that recording is what
gives idempotency and check-mode tests their teeth.
"""
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import json

from ansible_collections.openshift_lab.assisted_installer.plugins.modules import (
    infra_env,
)
from ansible_collections.openshift_lab.assisted_installer.plugins.module_utils import (
    assisted_installer as ai,
)

from ansible_helpers import (
    AnsibleExitJson,
    AnsibleFailJson,
    patch_ansible,
    queue_fetch_url,
    set_module_args,
)

# A representative infra-env as returned by GET /v2/infra-envs. Note the
# discovery-image format comes back as ``type`` (the create/update field is
# ``image_type``), and the pull_secret is never returned (only pull_secret_set).
EXISTING = {
    "id": "abc-123",
    "name": "lab-infra",
    "type": "minimal-iso",
    "cpu_architecture": "x86_64",
    "openshift_version": "4.16",
    "ssh_authorized_key": "ssh-ed25519 AAAAKEY",
    "proxy": {"http_proxy": "http://proxy:3128"},
    "pull_secret_set": True,
    "download_url": "https://example.test/discovery.iso",
}

BASE_ARGS = {"name": "lab-infra", "pull_secret": "ps", "api_token": "t"}


def _run(monkeypatch, responses, args, calls=None):
    """Drive the module once against a scripted list of (status, body) responses."""
    patch_ansible(monkeypatch)
    # Never let an ambient token leak into a test that means to have none.
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url(responses, calls=calls))
    set_module_args(args)
    try:
        infra_env.main()
    except (AnsibleExitJson, AnsibleFailJson) as exc:
        return exc
    raise AssertionError("module did not call exit_json or fail_json")


def _methods(calls):
    return [c["method"] for c in calls]


def test_create_when_absent_posts_and_is_changed(monkeypatch):
    """Create path: when no infra-env matches, observe (GET) then create (POST),
    reporting changed=True and returning the new id. Also pins the create body."""
    calls = []
    exc = _run(
        monkeypatch,
        responses=[(200, []), (201, dict(EXISTING))],
        args=dict(BASE_ARGS, openshift_version="4.16", image_type="minimal-iso"),
        calls=calls,
    )
    assert isinstance(exc, AnsibleExitJson)
    assert exc.result["changed"] is True
    assert exc.result["id"] == "abc-123"
    # Observed (GET) then reconciled (POST).
    assert _methods(calls) == ["GET", "POST"]
    sent = json.loads(calls[1]["data"])
    assert sent["name"] == "lab-infra"
    assert sent["pull_secret"] == "ps"
    assert sent["image_type"] == "minimal-iso"


def test_present_no_drift_is_unchanged_and_makes_no_write(monkeypatch):
    """Idempotency: a 2nd identical run must GET only and report changed=False.
    This is THE core state-module guarantee; the ``calls == ["GET"]`` assert is its teeth."""
    calls = []
    exc = _run(
        monkeypatch,
        responses=[(200, [dict(EXISTING)])],
        args=dict(BASE_ARGS, image_type="minimal-iso", openshift_version="4.16"),
        calls=calls,
    )
    assert isinstance(exc, AnsibleExitJson)
    assert exc.result["changed"] is False
    assert _methods(calls) == ["GET"]


def test_drift_triggers_patch_of_only_changed_fields(monkeypatch):
    """Drift reconciles with a PARTIAL patch - only the changed field is sent,
    never a full-object replace (which could clobber server-managed fields)."""
    calls = []
    exc = _run(
        monkeypatch,
        responses=[(200, [dict(EXISTING)]), (201, dict(EXISTING, type="full-iso"))],
        args=dict(BASE_ARGS, image_type="full-iso"),
        calls=calls,
    )
    assert isinstance(exc, AnsibleExitJson)
    assert exc.result["changed"] is True
    assert _methods(calls) == ["GET", "PATCH"]
    assert "/infra-envs/abc-123" in calls[1]["url"]
    patch = json.loads(calls[1]["data"])
    # Only the drifted field is sent; unchanged/undiffable fields are omitted.
    assert patch == {"image_type": "full-iso"}


def test_changing_an_immutable_field_fails(monkeypatch):
    """Immutable fields (e.g. cpu_architecture) fail loudly BEFORE any write,
    rather than silently no-op'ing or corrupting the resource."""
    calls = []
    exc = _run(
        monkeypatch,
        responses=[(200, [dict(EXISTING)])],
        args=dict(BASE_ARGS, cpu_architecture="aarch64"),
        calls=calls,
    )
    assert isinstance(exc, AnsibleFailJson)
    assert "immutable" in exc.result["msg"].lower()
    # Failed before any write.
    assert _methods(calls) == ["GET"]


def test_ambiguous_name_match_fails(monkeypatch):
    """When >1 infra-env shares the name, refuse to guess: fail before any write
    so we never mutate the wrong resource."""
    calls = []
    exc = _run(
        monkeypatch,
        responses=[(200, [dict(EXISTING), dict(EXISTING, id="dup-456")])],
        args=BASE_ARGS,
        calls=calls,
    )
    assert isinstance(exc, AnsibleFailJson)
    assert "refusing to guess" in exc.result["msg"].lower()
    assert _methods(calls) == ["GET"]


def test_absent_deletes_when_present(monkeypatch):
    """state=absent on an existing infra-env: observe (GET) then delete (DELETE),
    reporting changed=True."""
    calls = []
    exc = _run(
        monkeypatch,
        responses=[(200, [dict(EXISTING)]), (204, None)],
        args={"name": "lab-infra", "state": "absent", "api_token": "t"},
        calls=calls,
    )
    assert isinstance(exc, AnsibleExitJson)
    assert exc.result["changed"] is True
    assert exc.result["id"] == "abc-123"
    assert _methods(calls) == ["GET", "DELETE"]


def test_absent_when_already_gone_is_unchanged(monkeypatch):
    """Deleting an already-absent resource is a no-op, not an error: GET only,
    changed=False (the absent-side idempotency guarantee)."""
    calls = []
    exc = _run(
        monkeypatch,
        responses=[(200, [])],
        args={"name": "lab-infra", "state": "absent", "api_token": "t"},
        calls=calls,
    )
    assert isinstance(exc, AnsibleExitJson)
    assert exc.result["changed"] is False
    assert _methods(calls) == ["GET"]


def test_check_mode_create_does_not_write(monkeypatch):
    """Check mode predicts a create (changed=True) but must not POST - only the
    read (GET) is allowed; a write would raise on the empty queue."""
    calls = []
    exc = _run(
        monkeypatch,
        responses=[(200, [])],  # queue only the GET; a POST would raise (unexpected call)
        args=dict(BASE_ARGS, _ansible_check_mode=True),
        calls=calls,
    )
    assert isinstance(exc, AnsibleExitJson)
    assert exc.result["changed"] is True
    assert _methods(calls) == ["GET"]


def test_check_mode_update_does_not_write(monkeypatch):
    """Check mode predicts a drift update (changed=True) but must not PATCH -
    only the read (GET) fires."""
    calls = []
    exc = _run(
        monkeypatch,
        responses=[(200, [dict(EXISTING)])],  # GET only; a PATCH would raise
        args=dict(BASE_ARGS, image_type="full-iso", _ansible_check_mode=True),
        calls=calls,
    )
    assert isinstance(exc, AnsibleExitJson)
    assert exc.result["changed"] is True
    assert _methods(calls) == ["GET"]


def test_check_mode_delete_does_not_write(monkeypatch):
    """Check mode predicts a delete (changed=True) but must not DELETE -
    only the read (GET) fires (protects the destructive branch)."""
    calls = []
    exc = _run(
        monkeypatch,
        responses=[(200, [dict(EXISTING)])],  # GET only; a DELETE would raise
        args={"name": "lab-infra", "state": "absent", "api_token": "t",
              "_ansible_check_mode": True},
        calls=calls,
    )
    assert isinstance(exc, AnsibleExitJson)
    assert exc.result["changed"] is True
    assert _methods(calls) == ["GET"]


def test_fail_fast_when_no_token(monkeypatch):
    """No token (param or env) fails fast with a clear message and zero HTTP calls -
    we never send ``Bearer None``."""
    calls = []
    exc = _run(
        monkeypatch,
        responses=[],
        args={"name": "lab-infra", "pull_secret": "ps"},  # no token, env cleared
        calls=calls,
    )
    assert isinstance(exc, AnsibleFailJson)
    assert "token" in exc.result["msg"].lower()
    assert calls == []  # bailed before any HTTP request


def test_present_requires_pull_secret(monkeypatch):
    """required_if: state=present without pull_secret is rejected by argument
    parsing (before any logic runs)."""
    exc = _run(
        monkeypatch,
        responses=[],
        args={"name": "lab-infra", "api_token": "t"},  # missing pull_secret
    )
    assert isinstance(exc, AnsibleFailJson)
    assert "pull_secret" in exc.result["msg"]


def test_non_2xx_on_list_fails_with_status(monkeypatch):
    """A non-2xx from the API is mapped to fail_json and surfaces the status code
    (here 401), so failures are actionable rather than silent."""
    exc = _run(
        monkeypatch,
        responses=[(401, {"reason": "Unauthorized"})],
        args=BASE_ARGS,
    )
    assert isinstance(exc, AnsibleFailJson)
    assert exc.result["status"] == 401


def test_post_error_preserves_api_error_details(monkeypatch):
    """POST/PATCH errors parse the API error body so _error_detail can extract
    the reason/message. fetch_url returns resp=None with body in info["body"]."""
    exc = _run(
        monkeypatch,
        responses=[
            (200, []),  # GET returns empty (not found)
            (400, {"reason": "Invalid pull_secret format"}),  # POST fails with API error
        ],
        args=dict(BASE_ARGS, openshift_version="4.16"),
    )
    assert isinstance(exc, AnsibleFailJson)
    assert exc.result["status"] == 400
    assert "reason" in exc.result  # API error detail preserved
    assert exc.result["reason"] == "Invalid pull_secret format"


def test_base_url_override_is_honored(monkeypatch):
    """base_url override retargets requests at a local mock (for integration) while
    still sending the auth header - the request never leaks to production.
    HTTP loopback disables proxy to prevent credential leakage to proxy logs."""
    calls = []
    _run(
        monkeypatch,
        responses=[(200, [])],
        args=dict({"name": "x", "state": "absent", "api_token": "t"},
                  base_url="http://localhost:8080/api/assisted-install/v2"),
        calls=calls,
    )
    assert calls[0]["url"].startswith("http://localhost:8080/api/assisted-install/v2/infra-envs")
    assert calls[0]["headers"]["Authorization"] == "Bearer t"
    assert calls[0]["use_proxy"] is False  # HTTP loopback bypasses proxy


def test_remote_http_base_url_is_rejected(monkeypatch):
    """Remote HTTP base_url is rejected before any request - prevents credential
    leakage over plaintext. HTTPS and loopback HTTP are allowed."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)

    # Install a fail-on-call stub so a validation regression can't make a live request
    fetch_called = []

    def _fail_on_fetch(*args, **kwargs):
        fetch_called.append(True)
        raise AssertionError("fetch_url was called - validation did not reject the URL")
    monkeypatch.setattr(ai, "fetch_url", _fail_on_fetch)

    set_module_args({
        "name": "x",
        "state": "absent",
        "api_token": "t",
        "base_url": "http://evil.example.com/api",
    })
    try:
        infra_env.main()
    except AnsibleFailJson as exc:
        assert "insecure HTTP" in exc.result["msg"]
        assert "non-loopback" in exc.result["msg"]
        assert not fetch_called, "validation rejected but fetch_url was still called"
        return
    raise AssertionError("remote HTTP base_url was not rejected")


def test_hostless_base_url_is_rejected(monkeypatch):
    """base_url without a hostname (e.g. "https://") is rejected before any request
    to prevent malformed URLs like "https:/infra-envs"."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)

    fetch_called = []

    def _fail_on_fetch(*args, **kwargs):
        fetch_called.append(True)
        raise AssertionError("fetch_url was called - validation did not reject the URL")
    monkeypatch.setattr(ai, "fetch_url", _fail_on_fetch)

    for hostless_url in ["https://", "http://"]:
        set_module_args({
            "name": "x",
            "state": "absent",
            "api_token": "t",
            "base_url": hostless_url,
        })
        try:
            infra_env.main()
        except AnsibleFailJson as exc:
            assert "hostname" in exc.result["msg"]
            assert not fetch_called, "validation rejected but fetch_url was still called"
            fetch_called.clear()
            continue
        raise AssertionError("hostless base_url %s was not rejected" % hostless_url)


def test_base_url_with_query_or_fragment_is_rejected(monkeypatch):
    """base_url with query or fragment (e.g. "https://host?x=1" or "https://host#frag")
    is rejected to prevent malformed URLs like "https://host?x=1/infra-envs"."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)

    fetch_called = []

    def _fail_on_fetch(*args, **kwargs):
        fetch_called.append(True)
        raise AssertionError("fetch_url was called - validation did not reject the URL")
    monkeypatch.setattr(ai, "fetch_url", _fail_on_fetch)

    for bad_url in ["https://example.com?query=1", "http://127.0.0.1#fragment"]:
        set_module_args({
            "name": "x",
            "state": "absent",
            "api_token": "t",
            "base_url": bad_url,
        })
        try:
            infra_env.main()
        except AnsibleFailJson as exc:
            assert "query or fragment" in exc.result["msg"]
            assert not fetch_called, "validation rejected but fetch_url was still called"
            fetch_called.clear()
            continue
        raise AssertionError("base_url with query/fragment was not rejected: %s" % bad_url)


def test_https_base_url_uses_proxy(monkeypatch):
    """HTTPS base_url retains default proxy behavior (use_proxy=True) to allow
    corporate proxies to work. Only HTTP loopback disables proxy."""
    calls = []
    _run(
        monkeypatch,
        responses=[(200, [])],
        args=dict({"name": "x", "state": "absent", "api_token": "t"},
                  base_url="https://mock.example.com/api/v2"),
        calls=calls,
    )
    assert calls[0]["url"].startswith("https://mock.example.com/api/v2/infra-envs")
    assert calls[0]["use_proxy"] is True  # HTTPS uses default proxy behavior
