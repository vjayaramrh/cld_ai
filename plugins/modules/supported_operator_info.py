#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vishwanath Jayaraman (@vjayaramrh)
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
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

- name: Show the operator names
  ansible.builtin.debug:
    var: operators.operator_names

- name: Get properties for a specific operator
  openshift_lab.assisted_installer.supported_operator_info:
    name: lvm
    api_token: "{{ assisted_installer_token }}"
  register: lvm_props

- name: Show the queried operator's properties
  ansible.builtin.debug:
    var: lvm_props.operator_properties

- name: Query CNV operator properties (token from AI_API_TOKEN env)
  openshift_lab.assisted_installer.supported_operator_info:
    name: cnv
"""

RETURN = r"""
operator_names:
  description:
    - List of supported operator name strings.
    - Returned only when O(name) is B(not) provided (the list query).
  returned: when O(name) is not provided
  type: list
  elements: str
  sample:
    - "lso"
    - "cnv"
    - "odf"
    - "lvm"
operator_properties:
  description:
    - List of property objects for the operator named in O(name).
    - Returned only when O(name) is provided (the detail query).
  returned: when O(name) is provided
  type: list
  elements: dict
  contains:
    name:
      description: Property name.
      type: str
      sample: "SNO_SUPPORT"
    description:
      description: Human-readable description of the property.
      type: str
      sample: "Whether the operator supports Single Node OpenShift"
    data_type:
      description: The property's data type.
      type: str
      sample: "boolean"
    mandatory:
      description: Whether the property is required.
      type: bool
      sample: false
    default_value:
      description: Default value for the property, when defined.
      type: str
      sample: "false"
    options:
      description: Allowed values to select from, when the property is an enum.
      type: list
      elements: str
name:
  description: The operator name that was queried (only returned when O(name) was provided).
  returned: when O(name) is provided
  type: str
  sample: "lvm"
count:
  description:
    - When O(name) is not provided, the number of operators in RV(operator_names).
    - When O(name) is provided, the number of properties in RV(operator_properties).
  returned: success
  type: int
  sample: 28
changed:
  description: Always C(false); this is a read-only info module.
  returned: always
  type: bool
  sample: false
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

    # Split the return by shape so each field has one predictable type:
    #   - detail query (name given): a list of property dicts -> operator_properties
    #   - list query   (no name):    a list of name strings   -> operator_names
    result = {
        "changed": False,
        "count": len(operators),
    }
    if operator_name:
        result["name"] = operator_name
        result["operator_properties"] = operators
    else:
        result["operator_names"] = operators

    module.exit_json(**result)


if __name__ == "__main__":
    main()
