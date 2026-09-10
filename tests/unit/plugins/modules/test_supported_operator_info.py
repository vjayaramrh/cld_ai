# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vishwanath Jayaraman (@vjayaramrh)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Unit tests for the supported_operator_info module.

The API is mocked at the fetch_url layer (per CLAUDE.md): we patch
``...module_utils.assisted_installer.fetch_url`` so the REAL shared client runs
(URL building, query encoding, JSON parsing, status handling) while no live
call is ever made.
"""
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.openshift_lab.assisted_installer.plugins.modules import (
    supported_operator_info,
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

# Sample response for GET /supported-operators (list of operator names)
SAMPLE_OPERATOR_LIST = ["lso", "cnv", "odf", "lvm"]

# Sample response for GET /supported-operators/{name} (list of property objects)
SAMPLE_OPERATOR_PROPS = [
    {
        "name": "SNO_SUPPORT",
        "description": "Whether the operator supports Single Node OpenShift",
        "data_type": "boolean",
        "mandatory": False,
        "default_value": "false",
    },
    {
        "name": "VERSION",
        "description": "Operator version",
        "data_type": "string",
        "mandatory": True,
    },
]


def _run(monkeypatch, status=200, body=None, args=None, calls=None):
    """Drive the module once and return the raised Exit/Fail exception."""
    patch_ansible(monkeypatch)
    monkeypatch.setattr(ai, "fetch_url", fake_fetch_url(status=status, body=body, calls=calls))
    set_module_args(args or {})
    try:
        supported_operator_info.main()
    except (AnsibleExitJson, AnsibleFailJson) as exc:
        return exc
    raise AssertionError("module did not call exit_json or fail_json")


def test_list_all_operators_returns_list_and_is_never_changed(monkeypatch):
    # Run twice: a read-only info module is idempotent, so a second identical
    # run must also report changed=False (per CLAUDE.md testing posture).
    def _once():
        exc = _run(monkeypatch, body=SAMPLE_OPERATOR_LIST, args={"api_token": "t"})
        assert isinstance(exc, AnsibleExitJson)
        assert exc.result["changed"] is False
        assert exc.result["supported_operators"] == SAMPLE_OPERATOR_LIST
        assert exc.result["count"] == 4
        assert "name" not in exc.result  # name only returned when queried

    _once()  # first run
    _once()  # second (idempotent) run — still changed=False


def test_query_specific_operator_uses_name_in_path(monkeypatch):
    calls = []
    exc = _run(
        monkeypatch,
        body=SAMPLE_OPERATOR_PROPS,
        args={"api_token": "t", "name": "lvm"},
        calls=calls,
    )
    assert len(calls) == 1
    url = calls[0]["url"]
    assert "/supported-operators/lvm" in url
    # Verify the result includes the name
    assert exc.result["name"] == "lvm"
    assert exc.result["supported_operators"] == SAMPLE_OPERATOR_PROPS
    assert exc.result["count"] == 2


def test_uses_get_and_authorizes(monkeypatch):
    calls = []
    _run(
        monkeypatch,
        body=SAMPLE_OPERATOR_LIST,
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
        body=SAMPLE_OPERATOR_LIST,
        args={"api_token": "t", "_ansible_check_mode": True},
        calls=calls,
    )
    assert isinstance(exc, AnsibleExitJson)
    assert exc.result["changed"] is False
    assert all(c["method"] == "GET" for c in calls)


def test_auth_fail_fast_when_no_token(monkeypatch):
    calls = []
    exc = _run(monkeypatch, body=SAMPLE_OPERATOR_LIST, args={}, calls=calls)
    assert isinstance(exc, AnsibleFailJson)
    assert "token" in exc.result["msg"].lower()
    # Fail-fast: bail before any HTTP request is attempted.
    assert calls == []


def test_non_200_fails_with_status(monkeypatch):
    exc = _run(
        monkeypatch,
        status=401,
        body={"reason": "Unauthorized"},
        args={"api_token": "bad"},
    )
    assert isinstance(exc, AnsibleFailJson)
    assert exc.result["status"] == 401


def test_invalid_response_shape_fails(monkeypatch):
    # API returns dict instead of list (contract violation)
    exc = _run(
        monkeypatch,
        status=200,
        body={"error": "something went wrong"},
        args={"api_token": "t"},
    )
    assert isinstance(exc, AnsibleFailJson)
    assert "invalid response body" in exc.result["msg"].lower()
