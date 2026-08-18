# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vishwanath Jayaraman (@vjayaramrh)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Unit tests for the openshift_version_info module.

The API is mocked at the fetch_url layer (per CLAUDE.md): we patch
``...module_utils.assisted_installer.fetch_url`` so the REAL shared client runs
(URL building, query encoding, JSON parsing, status handling) while no live
call is ever made.
"""
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.openshift_lab.assisted_installer.plugins.modules import (
    openshift_version_info,
)
from ansible_collections.openshift_lab.assisted_installer.plugins.module_utils import (
    assisted_installer as ai,
)

from ansible_helpers import (
    AnsibleExitJson,
    AnsibleFailJson,
    fake_fetch_url,
    patch_ansible,
    set_module_args,
)

# A representative slice of the real GET /openshift-versions response shape.
SAMPLE_VERSIONS = {
    "4.15": {
        "display_name": "4.15.20",
        "support_level": "production",
        "cpu_architectures": ["x86_64", "arm64"],
    },
    "4.16": {
        "display_name": "4.16.3",
        "support_level": "production",
        "cpu_architectures": ["x86_64"],
        "default": True,
    },
}


def _run(monkeypatch, status=200, body=None, args=None, calls=None):
    """Drive the module once and return the raised Exit/Fail exception."""
    patch_ansible(monkeypatch)
    monkeypatch.setattr(ai, "fetch_url", fake_fetch_url(status=status, body=body, calls=calls))
    set_module_args(args or {})
    try:
        openshift_version_info.main()
    except (AnsibleExitJson, AnsibleFailJson) as exc:
        return exc
    raise AssertionError("module did not call exit_json or fail_json")


def test_happy_path_returns_versions_and_is_never_changed(monkeypatch):
    exc = _run(monkeypatch, body={"openshift-versions": SAMPLE_VERSIONS}, args={"api_token": "t"})
    assert isinstance(exc, AnsibleExitJson)
    result = exc.result
    assert result["changed"] is False
    assert result["openshift_versions"] == SAMPLE_VERSIONS
    assert result["count"] == 2


def test_query_params_reach_the_url(monkeypatch):
    calls = []
    _run(
        monkeypatch,
        body={"openshift-versions": SAMPLE_VERSIONS},
        args={"api_token": "t", "version": "4.16", "only_latest": True},
        calls=calls,
    )
    assert len(calls) == 1
    url = calls[0]["url"]
    assert "/openshift-versions?" in url
    assert "version=4.16" in url
    assert "only_latest=true" in url


def test_only_latest_false_is_omitted_from_query(monkeypatch):
    calls = []
    _run(
        monkeypatch,
        body={"openshift-versions": SAMPLE_VERSIONS},
        args={"api_token": "t", "only_latest": False},
        calls=calls,
    )
    assert "only_latest" not in calls[0]["url"]


def test_uses_get_and_authorizes(monkeypatch):
    calls = []
    _run(
        monkeypatch,
        body={"openshift-versions": SAMPLE_VERSIONS},
        args={"api_token": "sekret"},
        calls=calls,
    )
    assert calls[0]["method"] == "GET"
    assert calls[0]["headers"]["Authorization"] == "Bearer sekret"


def test_check_mode_still_reads_and_reports_unchanged(monkeypatch):
    # A read-only info module is safe in check mode: it may GET, must not mutate,
    # and always reports changed=False.
    calls = []
    exc = _run(
        monkeypatch,
        body={"openshift-versions": SAMPLE_VERSIONS},
        args={"api_token": "t", "_ansible_check_mode": True},
        calls=calls,
    )
    assert isinstance(exc, AnsibleExitJson)
    assert exc.result["changed"] is False
    assert all(c["method"] == "GET" for c in calls)


def test_auth_fail_fast_when_no_token(monkeypatch):
    exc = _run(monkeypatch, body={"openshift-versions": SAMPLE_VERSIONS}, args={})
    assert isinstance(exc, AnsibleFailJson)
    assert "token" in exc.result["msg"].lower()


def test_non_200_fails_with_status(monkeypatch):
    exc = _run(
        monkeypatch,
        status=401,
        body={"reason": "Unauthorized"},
        args={"api_token": "bad"},
    )
    assert isinstance(exc, AnsibleFailJson)
    assert exc.result["status"] == 401
