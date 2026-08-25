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
from ansible.module_utils.six.moves.urllib.parse import urlencode, urlparse

API_VERSION = "v2"
API_BASE = "https://api.openshift.com/api/assisted-install/%s" % API_VERSION
SSO_TOKEN_URL = (
    "https://sso.redhat.com/auth/realms/redhat-external"
    "/protocol/openid-connect/token"
)
DEFAULT_TIMEOUT = 30


def _validate_base_url(url):
    """Reject HTTP base_url unless it targets loopback (integration mock only).

    HTTPS is always allowed. HTTP is allowed only for verified loopback hosts
    (127.0.0.1, localhost, ::1) used by local integration test mocks.
    Remote HTTP endpoints would transmit bearer tokens and pull_secret in plaintext.
    """
    parsed = urlparse(url)

    # Require a hostname for any scheme
    if not parsed.hostname:
        raise ValueError(
            "base_url must include a hostname, got: %s" % url
        )
    if parsed.query or parsed.fragment:
        raise ValueError(
            "base_url must not include query or fragment, got: %s" % url
        )

    if parsed.scheme == "https":
        return  # always OK
    if parsed.scheme == "http":
        # Allow only loopback addresses for local test mocks
        if parsed.hostname in ("127.0.0.1", "localhost", "::1"):
            return
        raise ValueError(
            "base_url uses insecure HTTP for a non-loopback host (%s). "
            "Use HTTPS for remote endpoints, or 127.0.0.1/localhost for local mocks."
            % parsed.hostname
        )
    raise ValueError(
        "base_url must use http or https scheme, got: %s" % parsed.scheme
    )


def build_url(path, query=None, base_url=None):
    """Join a path onto the API base and append an optional query dict.

    ``base_url`` overrides the default production base (used by integration tests
    to point at a local mock); it must never default to anything but prod.
    """
    if not path.startswith("/"):
        path = "/" + path
    url = (base_url or API_BASE).rstrip("/") + path
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
        method="POST", timeout=DEFAULT_TIMEOUT, validate_certs=True,
    )
    if info.get("status") != 200:
        module.fail_json(msg="Failed to refresh API token (HTTP %s)" % info.get("status"))
    body = json.loads(resp.read())
    token = body.get("access_token")
    if not token:
        module.fail_json(msg="Token refresh response did not contain an access_token")
    return token


def request(module, method, path, token, body=None, query=None, timeout=None,
            base_url=None):
    """Make an authenticated JSON API call.

    Returns (data, info): `data` is the parsed JSON (or None), `info` is the
    fetch_url info dict (includes 'status'). Callers decide what counts as an
    error and call module.fail_json themselves so messages stay resource-specific.

    ``base_url`` overrides the production API base (integration mock only).
    """
    if base_url:
        try:
            _validate_base_url(base_url)
        except ValueError as exc:
            module.fail_json(msg=str(exc))
    url = build_url(path, query, base_url=base_url)

    # Disable proxy for HTTP loopback to prevent credential leakage to proxy logs.
    # HTTPS and production (no base_url) use default proxy behavior.
    use_proxy = True
    if base_url:
        parsed = urlparse(base_url)
        if parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost", "::1"):
            use_proxy = False

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
        timeout=timeout or DEFAULT_TIMEOUT, validate_certs=True,
        use_proxy=use_proxy,
    )

    # Parse body from either resp.read() (success) or info["body"] (error).
    # When fetch_url returns an error, resp=None and the body is in info["body"].
    data = None
    raw = resp.read() if resp is not None else info.get("body")
    if raw:
        try:
            data = json.loads(raw)
        except ValueError:
            data = raw
    return data, info
