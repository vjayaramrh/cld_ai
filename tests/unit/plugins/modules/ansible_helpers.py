# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vishwanath Jayaraman (@vjayaramrh)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Unit-test helpers for openshift_lab.assisted_installer modules.

Provides:
  * AnsibleExitJson / AnsibleFailJson  — capture a module's exit/fail result
  * set_module_args                    — feed input into argument_spec parsing
  * patch_ansible                      — patch AnsibleModule.exit_json/fail_json
  * fake_fetch_url                     — a fetch_url stand-in returning
                                         (resp, info) and recording each call

We mock at the ``fetch_url`` layer (per CLAUDE.md), so tests exercise the REAL
shared client in ``plugins/module_utils`` — URL building, query encoding, JSON
parsing and status handling — not just the module under test.
"""
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import json

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes


class AnsibleExitJson(Exception):
    """Raised by the patched exit_json so tests can inspect the result."""

    def __init__(self, result):
        self.result = result
        super(AnsibleExitJson, self).__init__(result.get("msg", "exit_json"))


class AnsibleFailJson(Exception):
    """Raised by the patched fail_json so tests can inspect the result."""

    def __init__(self, result):
        self.result = result
        super(AnsibleFailJson, self).__init__(result.get("msg", "fail_json"))


def set_module_args(args):
    """Set the args a module will parse. Add ``_ansible_check_mode: True`` for check mode."""
    basic._ANSIBLE_ARGS = to_bytes(json.dumps({"ANSIBLE_MODULE_ARGS": args}))
    # ansible-core 2.19+ requires a serialization profile alongside the args
    # buffer; older versions ignore this attribute.
    if hasattr(basic, "_ANSIBLE_PROFILE"):
        basic._ANSIBLE_PROFILE = "legacy"


def exit_json(self, **kwargs):
    kwargs.setdefault("changed", False)
    raise AnsibleExitJson(kwargs)


def fail_json(self, **kwargs):
    kwargs["failed"] = True
    raise AnsibleFailJson(kwargs)


def patch_ansible(monkeypatch):
    """Redirect AnsibleModule.exit_json/fail_json to raise capturable exceptions."""
    monkeypatch.setattr(basic.AnsibleModule, "exit_json", exit_json)
    monkeypatch.setattr(basic.AnsibleModule, "fail_json", fail_json)


class _FakeResponse(object):
    """Minimal file-like object mimicking what fetch_url returns on success."""

    def __init__(self, raw):
        self._raw = raw

    def read(self):
        return self._raw


def fake_fetch_url(status=200, body=None, calls=None):
    """Build a ``fetch_url`` replacement producing ``(resp, info)``.

    :param status: HTTP status to report in ``info``.
    :param body:   JSON-serializable response body (or None for empty).
    :param calls:  optional list; each invocation appends a dict recording the
                   url/method/data/headers/timeout so tests can assert which
                   HTTP verb fired (the teeth of idempotency / check-mode tests).

    On success (< 400) ``resp`` carries the JSON body; on error ``resp`` is None
    and the body is surfaced via ``info['body']`` — mirroring real fetch_url.
    """
    def _fetch(module, url, data=None, headers=None, method="GET", timeout=None, **kwargs):
        if calls is not None:
            calls.append({
                "url": url,
                "method": method,
                "data": data,
                "headers": headers,
                "timeout": timeout,
            })
        info = {"status": status, "url": url}
        if status >= 400:
            info["body"] = to_bytes(json.dumps(body)) if body is not None else b""
            return None, info
        raw = to_bytes(json.dumps(body)) if body is not None else b""
        return _FakeResponse(raw), info

    return _fetch
