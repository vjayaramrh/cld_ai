# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vishwanath Jayaraman (@vjayaramrh)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Unit tests for the shared client ``plugins/module_utils/assisted_installer``.

The client is exercised indirectly by the module tests, but these cases pin the
cross-cutting behavior directly: base_url validation (including embedded
credentials), token refresh error handling, query building, and the auth guard.
"""
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import pytest

from ansible.module_utils import basic
from ansible_helpers import (
    AnsibleFailJson, fake_fetch_url, patch_ansible, set_module_args,
)
from ansible_collections.openshift_lab.assisted_installer.plugins.module_utils import (
    assisted_installer as ai,
)


def make_module():
    """Construct a real AnsibleModule for request()/refresh tests."""
    set_module_args({})
    return basic.AnsibleModule(
        argument_spec=dict(
            api_token=dict(type="str", no_log=True),
            offline_token=dict(type="str", no_log=True),
            timeout=dict(type="int", default=30),
            base_url=dict(type="str"),
        ),
        supports_check_mode=True,
    )


# --------------------------------------------------------------------------- #
# _validate_base_url — reject embedded credentials (#6)                        #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("url", [
    "https://alice:secret@evil.com",
    "https://alice@evil.com",
    "https://alice:secret@api.openshift.com/api/assisted-install/v2",
    "https://alice:secret@",   # credentials but no host: must not leak via hostname check
])
def test_validate_base_url_rejects_userinfo(url):
    """A base_url carrying username/password must be rejected (would leak the
    bearer token / credentials to the embedded host)."""
    with pytest.raises(ValueError) as exc:
        ai._validate_base_url(url)
    # The message must not echo the password.
    assert "secret" not in str(exc.value)


@pytest.mark.parametrize("url", [
    "https://u:sup3rsecret@evil.com",
    "https://u:sup3rsecret@",   # no host: hostname check must not fire first and echo the URL
])
def test_validate_base_url_error_does_not_leak_password(url):
    """The rejection message never contains the embedded password, even when the
    URL has no hostname (the credential check must run before the hostname check)."""
    with pytest.raises(ValueError) as exc:
        ai._validate_base_url(url)
    assert "sup3rsecret" not in str(exc.value)


@pytest.mark.parametrize("url", [
    "https://api.openshift.com/api/assisted-install/v2",
    "http://127.0.0.1:8080",
    "http://localhost:8080",
])
def test_validate_base_url_accepts_valid(url):
    """Regression: plain HTTPS and HTTP loopback remain valid."""
    ai._validate_base_url(url)  # must not raise


def test_request_fails_on_userinfo_base_url(monkeypatch):
    """request() surfaces the userinfo rejection as fail_json, not a raw raise,
    and never contacts the network."""
    patch_ansible(monkeypatch)
    module = make_module()
    calls = []
    monkeypatch.setattr(ai, "fetch_url", fake_fetch_url(status=200, body={}, calls=calls))

    with pytest.raises(AnsibleFailJson) as exc:
        ai.request(module, "GET", "/clusters", "token",
                   base_url="https://u:p@evil.com")

    assert calls == []  # no HTTP call fired
    assert "p" not in exc.value.result["msg"] or "password" in exc.value.result["msg"].lower()


# --------------------------------------------------------------------------- #
# _refresh_token — guard the JSON parse (#7)                                   #
# --------------------------------------------------------------------------- #

def test_refresh_token_happy_path(monkeypatch):
    """A well-formed refresh response returns the access token."""
    patch_ansible(monkeypatch)
    module = make_module()
    monkeypatch.setattr(ai, "fetch_url",
                        fake_fetch_url(status=200, body={"access_token": "fresh-tok"}))
    assert ai._refresh_token(module, "offline-abc") == "fresh-tok"


def test_refresh_token_empty_body_fails_cleanly(monkeypatch):
    """A 200 with an empty (non-JSON) body must fail_json, not raise ValueError."""
    patch_ansible(monkeypatch)
    module = make_module()
    monkeypatch.setattr(ai, "fetch_url", fake_fetch_url(status=200, body=None))
    with pytest.raises(AnsibleFailJson):
        ai._refresh_token(module, "offline-abc")


def test_refresh_token_non_dict_body_fails_cleanly(monkeypatch):
    """A 200 whose JSON body is not an object must fail_json, not AttributeError."""
    patch_ansible(monkeypatch)
    module = make_module()
    monkeypatch.setattr(ai, "fetch_url", fake_fetch_url(status=200, body=["not", "a", "dict"]))
    with pytest.raises(AnsibleFailJson):
        ai._refresh_token(module, "offline-abc")


def test_refresh_token_missing_access_token_fails(monkeypatch):
    """A 200 dict without access_token fails with a clear message."""
    patch_ansible(monkeypatch)
    module = make_module()
    monkeypatch.setattr(ai, "fetch_url", fake_fetch_url(status=200, body={"foo": "bar"}))
    with pytest.raises(AnsibleFailJson) as exc:
        ai._refresh_token(module, "offline-abc")
    assert "access_token" in exc.value.result["msg"]


def test_refresh_token_non_200_fails(monkeypatch):
    """A non-200 refresh response fails with the status."""
    patch_ansible(monkeypatch)
    module = make_module()
    monkeypatch.setattr(ai, "fetch_url", fake_fetch_url(status=401, body={"error": "bad"}))
    with pytest.raises(AnsibleFailJson) as exc:
        ai._refresh_token(module, "offline-abc")
    assert "401" in exc.value.result["msg"]


# --------------------------------------------------------------------------- #
# build_url — empty collection query values (LOW)                             #
# --------------------------------------------------------------------------- #

def test_build_url_drops_empty_list_query():
    """An empty list value must not produce a dangling '?k=' parameter."""
    url = ai.build_url("/clusters", query={"ids": []})
    assert url.endswith("/clusters")
    assert "ids=" not in url


def test_build_url_joins_non_empty_list_query():
    """Regression: a non-empty list is comma-joined."""
    url = ai.build_url("/clusters", query={"ids": ["a", "b"]})
    assert "ids=a%2Cb" in url or "ids=a,b" in url


def test_build_url_drops_none_and_empty_string():
    """Regression: None and '' values are dropped."""
    url = ai.build_url("/clusters", query={"a": None, "b": "", "c": "x"})
    assert "a=" not in url and "b=" not in url and "c=x" in url


# --------------------------------------------------------------------------- #
# request — defensive auth + explicit timeout (LOW)                           #
# --------------------------------------------------------------------------- #

def test_request_fails_fast_without_token(monkeypatch):
    """request() must not send 'Bearer None'; it fails fast and makes no call."""
    patch_ansible(monkeypatch)
    module = make_module()
    calls = []
    monkeypatch.setattr(ai, "fetch_url", fake_fetch_url(status=200, body={}, calls=calls))

    with pytest.raises(AnsibleFailJson):
        ai.request(module, "GET", "/clusters", None)

    assert calls == []  # never contacted the network with a None token


def test_request_honors_explicit_zero_timeout(monkeypatch):
    """An explicit timeout=0 is passed through, not silently replaced by 30."""
    patch_ansible(monkeypatch)
    module = make_module()
    calls = []
    monkeypatch.setattr(ai, "fetch_url", fake_fetch_url(status=200, body={}, calls=calls))

    ai.request(module, "GET", "/clusters", "token", timeout=0)

    assert calls[0]["timeout"] == 0
