#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vishwanath Jayaraman (@vjayaramrh)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: infra_env
short_description: Manage an Assisted Installer infrastructure environment (infra-env)
version_added: "0.1.0"
description:
  - Create, update, or delete an Assisted Installer B(infra-env) declaratively.
  - This is the reference B(state-based) module for the collection. It follows the
    observe-compare-reconcile model - GET the infra-envs, match by O(name),
    and only POST/PATCH/DELETE when the live state differs from the requested
    state - so re-running a play is safe and reports C(changed=false) on a no-op.
author:
  - Vishwanath Jayaraman (@vjayaramrh)
options:
  state:
    description:
      - V(present) creates the infra-env if missing and updates it if it has
        drifted; V(absent) deletes it if present.
    type: str
    choices: [present, absent]
    default: present
  name:
    description:
      - Name of the infra-env. This is the natural key used to find an existing
        infra-env, and it cannot be changed after creation (renaming produces a
        new infra-env).
    type: str
    required: true
  cluster_id:
    description:
      - Bind the infra-env to this cluster, and scope the lookup to it. Set at
        creation only; it cannot be changed on an existing infra-env.
    type: str
  pull_secret:
    description:
      - Red Hat pull secret used to create the infra-env. Required when
        O(state=present).
      - Write-only - the API never returns it, so it cannot be compared and never
        by itself triggers an update.
    type: str
  openshift_version:
    description:
      - OpenShift version for the discovery image.
    type: str
  cpu_architecture:
    description:
      - CPU architecture of the discovery image. Set at creation only; it cannot
        be changed on an existing infra-env. Defaults to V(x86_64) server-side.
    type: str
    choices: [x86_64, aarch64, arm64, ppc64le, s390x]
  image_type:
    description:
      - Discovery image format.
    type: str
    choices: [full-iso, minimal-iso, disconnected-iso]
  ssh_authorized_key:
    description:
      - SSH public key authorized for the discovery hosts.
    type: str
  proxy:
    description:
      - Proxy settings for hosts booting the discovery image.
    type: dict
    suboptions:
      http_proxy:
        description: Proxy URL for HTTP requests.
        type: str
      https_proxy:
        description: Proxy URL for HTTPS requests.
        type: str
      no_proxy:
        description: Comma-separated list of hosts/domains that bypass the proxy.
        type: str
  additional_ntp_sources:
    description:
      - Comma-separated list of additional NTP sources.
    type: str
  additional_trust_bundle:
    description:
      - PEM-encoded X.509 certificate bundle to trust.
    type: str
  api_token:
    description:
      - A short-lived Assisted Installer API access token (a bearer token).
      - If not set, the value of environment variable E(AI_API_TOKEN) is used.
    type: str
  offline_token:
    description:
      - A long-lived offline token used to obtain an access token via Red Hat SSO.
      - If not set, the value of environment variable E(AI_OFFLINE_TOKEN) is used.
    type: str
  timeout:
    description:
      - Timeout in seconds for each API request.
    type: int
    default: 30
  base_url:
    description:
      - Override the API base URL. Intended for integration tests against a local
        mock server; leave unset to use the production Assisted Installer API.
    type: str
notes:
  - Authenticates with the C(Authorization) bearer header against
    U(https://api.openshift.com/api/assisted-install/v2).
  - O(name) is not enforced unique by the API; if more than one infra-env
    matches O(name) (within O(cluster_id) when given), the module fails
    rather than guessing.
seealso:
  - name: Assisted Installer REST API
    description: Upstream OpenAPI specification for the Assisted Installer service.
    link: https://api.openshift.com/api/assisted-install/v2/openapi
"""

EXAMPLES = r"""
- name: Create an infra-env (changed=true the first time)
  openshift_lab.assisted_installer.infra_env:
    name: lab-infra
    pull_secret: "{{ assisted_installer_pull_secret }}"
    openshift_version: "4.16"
    image_type: minimal-iso
    ssh_authorized_key: "{{ lab_ssh_public_key }}"
    api_token: "{{ assisted_installer_token }}"
  register: result

# Running the identical task again is a no-op: result.changed == false.

- name: Update the image type (changed=true only because it drifted)
  openshift_lab.assisted_installer.infra_env:
    name: lab-infra
    pull_secret: "{{ assisted_installer_pull_secret }}"
    image_type: full-iso
    api_token: "{{ assisted_installer_token }}"

- name: Preview a change without applying it (check mode)
  openshift_lab.assisted_installer.infra_env:
    name: lab-infra
    pull_secret: "{{ assisted_installer_pull_secret }}"
    image_type: disconnected-iso
    api_token: "{{ assisted_installer_token }}"
  check_mode: true

- name: Delete the infra-env (changed=false if it is already gone)
  openshift_lab.assisted_installer.infra_env:
    name: lab-infra
    state: absent
    # token taken from the AI_API_TOKEN environment variable
"""

RETURN = r"""
infra_env:
  description:
    - The infra-env resource as returned by the API after create/update, or the
      observed resource on a no-op. Empty dict after a delete or a create in
      check mode.
  returned: success
  type: dict
  sample:
    id: "0e1a...c9"
    name: "lab-infra"
    type: "minimal-iso"
    cpu_architecture: "x86_64"
    openshift_version: "4.16"
    download_url: "https://.../discovery.iso"
id:
  description: The infra-env identifier, or null when none exists.
  returned: success
  type: str
  sample: "0e1a2b3c-4d5e-6f70-8a9b-0c1d2e3f4a5b"
"""

from ansible.module_utils.basic import AnsibleModule, env_fallback

from ..module_utils import assisted_installer as ai

# Set at creation, absent from the update API -> cannot be PATCHed. Changing one
# on an existing infra-env is an error (delete + recreate instead).
IMMUTABLE_FIELDS = ("cluster_id", "cpu_architecture")

# Fields sent verbatim on create (request field name == module option name).
CREATE_FIELDS = (
    "name", "cluster_id", "pull_secret", "openshift_version", "cpu_architecture",
    "image_type", "ssh_authorized_key", "additional_ntp_sources",
    "additional_trust_bundle",
)

# Updatable option -> the field to compare it against in the GET response. The
# option name is also the PATCH body key. Note the discovery-image format is
# sent as ``image_type`` but returned as ``type``. ``pull_secret`` is absent on
# purpose: the API never returns it, so it is not drift-comparable.
UPDATABLE_TO_RESPONSE = {
    "openshift_version": "openshift_version",
    "image_type": "type",
    "ssh_authorized_key": "ssh_authorized_key",
    "additional_ntp_sources": "additional_ntp_sources",
    "additional_trust_bundle": "additional_trust_bundle",
    "proxy": "proxy",
}


def _clean(mapping):
    """Drop keys whose value is None so comparisons don't see phantom drift."""
    return {k: v for k, v in (mapping or {}).items() if v is not None}


def _error_detail(data):
    """Pull a safe, human-readable reason from an API error body (never a secret)."""
    if isinstance(data, dict):
        return data.get("reason") or data.get("message")
    return None


def _find_infra_env(module, token, params):
    """GET the infra-envs and return the single one matching name (else None)."""
    query = {}
    if params.get("cluster_id"):
        query["cluster_id"] = params["cluster_id"]
    data, info = ai.request(
        module, "GET", "/infra-envs", token,
        query=query, timeout=params["timeout"], base_url=params["base_url"],
    )
    if info.get("status") != 200:
        module.fail_json(
            msg="Failed to list infra-envs (HTTP %s)" % info.get("status"),
            status=info.get("status"),
        )
    items = data if isinstance(data, list) else []
    matches = [e for e in items if e.get("name") == params["name"]]
    if len(matches) > 1:
        module.fail_json(
            msg=("Found %d infra-envs named '%s'; refusing to guess. Scope with "
                 "cluster_id or ensure unique names." % (len(matches), params["name"])),
        )
    return matches[0] if matches else None


def _build_create_body(params):
    body = {}
    for field in CREATE_FIELDS:
        value = params.get(field)
        if value is not None:
            body[field] = value
    proxy = _clean(params.get("proxy"))
    if proxy:
        body["proxy"] = proxy
    return body


def _immutable_conflicts(params, current):
    """Return [(field, current, requested)] for immutable fields the user changed."""
    conflicts = []
    for field in IMMUTABLE_FIELDS:
        requested = params.get(field)
        if requested is not None and requested != current.get(field):
            conflicts.append((field, current.get(field), requested))
    return conflicts


def _compute_patch(params, current):
    """Build the PATCH body of only the updatable fields that actually differ."""
    patch = {}
    for option, response_field in UPDATABLE_TO_RESPONSE.items():
        desired = params.get(option)
        if desired is None:
            continue
        if option == "proxy":
            desired = _clean(desired)
            if desired != _clean(current.get("proxy")):
                patch["proxy"] = desired
        elif desired != current.get(response_field):
            patch[option] = desired
    return patch


def _present(module, token, params):
    current = _find_infra_env(module, token, params)

    if current is None:
        if module.check_mode:
            module.exit_json(changed=True, infra_env={}, id=None)
        body = _build_create_body(params)
        data, info = ai.request(
            module, "POST", "/infra-envs", token,
            body=body, timeout=params["timeout"], base_url=params["base_url"],
        )
        if info.get("status") != 201:
            module.fail_json(
                msg="Failed to create infra-env (HTTP %s)" % info.get("status"),
                status=info.get("status"), reason=_error_detail(data),
            )
        module.exit_json(changed=True, infra_env=data, id=data.get("id"))

    conflicts = _immutable_conflicts(params, current)
    if conflicts:
        module.fail_json(
            msg=("Cannot change immutable field(s) on an existing infra-env: %s. "
                 "Delete and recreate to change these."
                 % ", ".join(field for field, _current, _requested in conflicts)),
            immutable=[
                {"field": field, "current": cur, "requested": req}
                for field, cur, req in conflicts
            ],
        )

    patch = _compute_patch(params, current)
    if not patch:
        module.exit_json(changed=False, infra_env=current, id=current.get("id"))
    if module.check_mode:
        module.exit_json(changed=True, infra_env=current, id=current.get("id"))
    data, info = ai.request(
        module, "PATCH", "/infra-envs/%s" % current["id"], token,
        body=patch, timeout=params["timeout"], base_url=params["base_url"],
    )
    if info.get("status") != 201:
        module.fail_json(
            msg="Failed to update infra-env (HTTP %s)" % info.get("status"),
            status=info.get("status"), reason=_error_detail(data),
        )
    module.exit_json(changed=True, infra_env=data, id=data.get("id"))


def _absent(module, token, params):
    current = _find_infra_env(module, token, params)
    if current is None:
        module.exit_json(changed=False, infra_env={}, id=None)
    if module.check_mode:
        module.exit_json(changed=True, infra_env=current, id=current.get("id"))
    _data, info = ai.request(
        module, "DELETE", "/infra-envs/%s" % current["id"], token,
        timeout=params["timeout"], base_url=params["base_url"],
    )
    if info.get("status") not in (200, 204):
        module.fail_json(
            msg="Failed to delete infra-env (HTTP %s)" % info.get("status"),
            status=info.get("status"),
        )
    module.exit_json(changed=True, infra_env={}, id=current.get("id"))


def main():
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(type="str", default="present", choices=["present", "absent"]),
            name=dict(type="str", required=True),
            cluster_id=dict(type="str"),
            pull_secret=dict(type="str", no_log=True),
            openshift_version=dict(type="str"),
            cpu_architecture=dict(
                type="str",
                choices=["x86_64", "aarch64", "arm64", "ppc64le", "s390x"],
            ),
            image_type=dict(
                type="str",
                choices=["full-iso", "minimal-iso", "disconnected-iso"],
            ),
            ssh_authorized_key=dict(type="str", no_log=True),
            proxy=dict(
                type="dict",
                options=dict(
                    http_proxy=dict(type="str"),
                    https_proxy=dict(type="str"),
                    no_proxy=dict(type="str"),
                ),
            ),
            additional_ntp_sources=dict(type="str"),
            additional_trust_bundle=dict(type="str"),
            api_token=dict(
                type="str", no_log=True, fallback=(env_fallback, ["AI_API_TOKEN"])
            ),
            offline_token=dict(
                type="str", no_log=True, fallback=(env_fallback, ["AI_OFFLINE_TOKEN"])
            ),
            timeout=dict(type="int", default=30),
            base_url=dict(type="str"),
        ),
        supports_check_mode=True,
        required_if=[["state", "present", ["pull_secret"]]],
    )

    token = ai.resolve_token(module)
    params = module.params

    if params["state"] == "present":
        _present(module, token, params)
    else:
        _absent(module, token, params)


if __name__ == "__main__":
    main()
