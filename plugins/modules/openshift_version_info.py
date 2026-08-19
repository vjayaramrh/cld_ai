#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vishwanath Jayaraman (@vjayaramrh)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: openshift_version_info
short_description: List OpenShift release versions available to the Assisted Installer
version_added: "0.1.0"
description:
  - Retrieve the OpenShift release versions the Assisted Installer can install,
    optionally filtered by version substring or restricted to the latest release
    per minor stream.
  - This is a read-only C(_info) module. It never changes remote state and always
    reports C(changed=false).
author:
  - Vishwanath Jayaraman (@vjayaramrh)
options:
  version:
    description:
      - Filter results to versions whose identifier contains this substring
        (for example V(4.16)).
    type: str
  only_latest:
    description:
      - When V(true), return only the latest release for each minor version
        stream.
    type: bool
    default: false
  api_token:
    description:
      - A short-lived Assisted Installer API access token (a bearer token).
      - If not set, the value of environment variable E(AI_API_TOKEN) is used.
      - Mutually complementary with O(offline_token); at least one source of
        credentials must resolve or the module fails fast.
    type: str
  offline_token:
    description:
      - A long-lived offline token used to obtain an access token via Red Hat SSO.
      - If not set, the value of environment variable E(AI_OFFLINE_TOKEN) is used.
    type: str
  timeout:
    description:
      - Timeout in seconds for the API request.
    type: int
    default: 30
notes:
  - Authenticates with the C(Authorization) bearer header against
    U(https://api.openshift.com/api/assisted-install/v2).
seealso:
  - name: Assisted Installer REST API
    description: Upstream OpenAPI specification for the Assisted Installer service.
    link: https://api.openshift.com/api/assisted-install/v2/openapi
"""

EXAMPLES = r"""
- name: List all available OpenShift versions
  openshift_lab.assisted_installer.openshift_version_info:
    api_token: "{{ assisted_installer_token }}"
  register: versions

- name: List only the latest release in each minor stream
  openshift_lab.assisted_installer.openshift_version_info:
    api_token: "{{ assisted_installer_token }}"
    only_latest: true

- name: Filter to 4.16 releases (token taken from AI_API_TOKEN env)
  openshift_lab.assisted_installer.openshift_version_info:
    version: "4.16"
"""

RETURN = r"""
openshift_versions:
  description:
    - Mapping of OpenShift version identifier to its metadata, as returned by the
      Assisted Installer API. Empty dict when nothing matches the filter.
  returned: success
  type: dict
  sample:
    "4.16":
      display_name: "4.16.3"
      support_level: "production"
      cpu_architectures:
        - "x86_64"
      default: true
count:
  description: Number of versions returned.
  returned: success
  type: int
  sample: 2
"""

from ansible.module_utils.basic import AnsibleModule, env_fallback

from ..module_utils import assisted_installer as ai


def main():
    module = AnsibleModule(
        argument_spec=dict(
            version=dict(type="str"),
            only_latest=dict(type="bool", default=False),
            api_token=dict(
                type="str", no_log=True, fallback=(env_fallback, ["AI_API_TOKEN"])
            ),
            offline_token=dict(
                type="str", no_log=True, fallback=(env_fallback, ["AI_OFFLINE_TOKEN"])
            ),
            timeout=dict(type="int", default=30),
        ),
        supports_check_mode=True,
    )

    token = ai.resolve_token(module)

    query = {}
    if module.params.get("version"):
        query["version"] = module.params["version"]
    if module.params.get("only_latest"):
        query["only_latest"] = "true"

    data, info = ai.request(
        module,
        "GET",
        "/openshift-versions",
        token,
        query=query,
        timeout=module.params["timeout"],
    )

    status = info.get("status")
    if status != 200:
        module.fail_json(
            msg="Failed to list OpenShift versions (HTTP %s)" % status,
            status=status,
            body=data,
        )

    versions = data if isinstance(data, dict) else {}
    # The API wraps the map under "openshift-versions"; unwrap defensively.
    if "openshift-versions" in versions:
        versions = versions["openshift-versions"]

    module.exit_json(
        changed=False,
        openshift_versions=versions,
        count=len(versions),
    )


if __name__ == "__main__":
    main()
