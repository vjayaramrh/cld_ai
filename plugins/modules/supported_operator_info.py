#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vishwanath Jayaraman (@vjayaramrh)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: supported_operator_info
short_description: List supported OLM operators and their properties
version_added: "0.1.0"
description:
  - Retrieve the list of OpenShift Lifecycle Manager (OLM) operators supported
    by the Assisted Installer, optionally retrieving detailed properties for a
    specific operator.
  - This is a read-only C(_info) module. It never changes remote state and always
    reports C(changed=false).
author:
  - Vishwanath Jayaraman (@vjayaramrh)
options:
  name:
    description:
      - Name of a specific operator to query.
      - When provided, returns detailed properties for that operator.
      - When omitted, returns the list of all supported operator names.
    type: str
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
- name: List all supported operators
  openshift_lab.assisted_installer.supported_operator_info:
    api_token: "{{ assisted_installer_token }}"
  register: operators

- name: Show the operator list
  ansible.builtin.debug:
    var: operators.supported_operators

- name: Get properties for a specific operator
  openshift_lab.assisted_installer.supported_operator_info:
    name: lvm
    api_token: "{{ assisted_installer_token }}"
  register: lvm_props

- name: Query CNV operator properties (token from AI_API_TOKEN env)
  openshift_lab.assisted_installer.supported_operator_info:
    name: cnv
"""

RETURN = r"""
supported_operators:
  description:
    - When O(name) is not provided, this is a list of supported operator name strings.
    - When O(name) is provided, this is a list of property objects for that operator.
  returned: success
  type: raw
  sample:
    # Without name parameter - list of operator names
    - "lso"
    - "cnv"
    - "odf"
    - "lvm"
    # With name parameter - list of property objects
    - name: "SNO_SUPPORT"
      description: "Whether the operator supports Single Node OpenShift"
      data_type: "boolean"
      mandatory: false
      default_value: "false"
name:
  description: The operator name that was queried (only returned when O(name) was provided).
  returned: when name parameter is provided
  type: str
  sample: "lvm"
count:
  description:
    - When O(name) is not provided, the number of operators in the list.
    - When O(name) is provided, the number of properties returned.
  returned: success
  type: int
  sample: 28
"""

from ansible.module_utils.basic import AnsibleModule, env_fallback

from ..module_utils import assisted_installer as ai


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type="str"),
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

    # Build path based on whether name is provided
    operator_name = module.params.get("name")
    if operator_name:
        path = f"/supported-operators/{operator_name}"
    else:
        path = "/supported-operators"

    data, info = ai.request(
        module,
        "GET",
        path,
        token,
        timeout=module.params["timeout"],
    )

    status = info.get("status")
    if status != 200:
        module.fail_json(
            msg=f"Failed to retrieve supported operators (HTTP {status})",
            status=status,
            body=data,
        )

    # API returns data directly (list of strings or list of objects)
    if not isinstance(data, list):
        module.fail_json(
            msg="Supported operators API returned an invalid response body",
            body=data,
        )
    operators = data

    result = {
        "changed": False,
        "supported_operators": operators,
        "count": len(operators),
    }

    # Include the name in result if it was queried
    if operator_name:
        result["name"] = operator_name

    module.exit_json(**result)


if __name__ == "__main__":
    main()
