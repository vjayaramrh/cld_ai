# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vishwanath Jayaraman (@vjayaramrh)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

"""Shared helpers for openshift_lab.assisted_installer modules.

Cross-cutting concerns live here so modules don't duplicate them:
  * token resolution / refresh
  * base-URL building
  * a thin fetch_url wrapper (timeout + auth header + JSON + error shape)

HTTP is done with ansible.module_utils.urls.fetch_url — never `requests`.
This is a STUB: the request plumbing is real and usable, but endpoint-specific
logic belongs in the individual modules (see DESIGN.md for scope/phasing).
"""

import json

from ansible.module_utils.urls import fetch_url
from ansible.module_utils.six.moves.urllib.parse import urlencode

API_VERSION = "v2"
API_BASE = "https://api.openshift.com/api/assisted-install/%s" % API_VERSION
SSO_TOKEN_URL = (
    "https://sso.redhat.com/auth/realms/redhat-external"
    "/protocol/openid-connect/token"
)
DEFAULT_TIMEOUT = 30


def build_url(path, query=None):
    """Join a path onto the API base and append an optional query dict."""
    if not path.startswith("/"):
        path = "/" + path
    url = API_BASE + path
    if query:
        # drop None/empty values; join lists as comma-separated
        clean = {}
        for k, v in query.items():
            if v is None or v == "":
                continue
            clean[k] = ",".join(v) if isinstance(v, (list, tuple)) else v
        if clean:
            url = "%s?%s" % (url, urlencode(clean))
    return url


def resolve_token(module):
    """Return a bearer token, or fail_json with a clear message.

    Precedence:
      1. module param `api_token` (no_log) if provided
      2. env AI_API_TOKEN (short-lived access token)
      3. env AI_OFFLINE_TOKEN (offline token) -> refresh into an access token

    TODO(impl session): wire `api_token`/`offline_token` into each module's
    argument_spec with env_fallback so this reads from params or env uniformly.
    """
    import os

    token = module.params.get("api_token") or os.environ.get("AI_API_TOKEN")
    if token:
        return token

    offline = module.params.get("offline_token") or os.environ.get("AI_OFFLINE_TOKEN")
    if offline:
        return _refresh_token(module, offline)

    module.fail_json(
        msg="No API token found. Set AI_API_TOKEN, or set AI_OFFLINE_TOKEN "
            "(or pass api_token/offline_token) so a token can be obtained."
    )


def _refresh_token(module, offline_token):
    data = urlencode({
        "grant_type": "refresh_token",
        "client_id": "cloud-services",
        "refresh_token": offline_token,
    })
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    resp, info = fetch_url(
        module, SSO_TOKEN_URL, data=data, headers=headers,
        method="POST", timeout=DEFAULT_TIMEOUT,
    )
    if info.get("status") != 200:
        module.fail_json(msg="Failed to refresh API token (HTTP %s)" % info.get("status"))
    body = json.loads(resp.read())
    token = body.get("access_token")
    if not token:
        module.fail_json(msg="Token refresh response did not contain an access_token")
    return token


def request(module, method, path, token, body=None, query=None, timeout=None):
    """Make an authenticated JSON API call.

    Returns (data, info): `data` is the parsed JSON (or None), `info` is the
    fetch_url info dict (includes 'status'). Callers decide what counts as an
    error and call module.fail_json themselves so messages stay resource-specific.
    """
    url = build_url(path, query)
    headers = {
        "Authorization": "Bearer %s" % token,
        "Accept": "application/json",
    }
    payload = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        payload = json.dumps(body)

    resp, info = fetch_url(
        module, url, data=payload, headers=headers, method=method.upper(),
        timeout=timeout or DEFAULT_TIMEOUT,
    )

    data = None
    if resp is not None:
        raw = resp.read()
        if raw:
            try:
                data = json.loads(raw)
            except ValueError:
                data = raw
    return data, info
