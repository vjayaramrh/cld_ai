#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vishwanath Jayaraman (@vjayaramrh)
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: host_action
short_description: Perform actions on Assisted Installer hosts
version_added: "0.1.0"
description:
  - Execute RPC-style actions on hosts discovered by an infrastructure environment.
  - This is the reference B(action) module for the collection. It follows the
    guard-on-status pattern - GET the host to check its current status,
    and only POST the action if the host is in a valid state for that action.
    Re-running a play is safe and reports C(changed=false) if already in the
    target state.
  - Supported actions are V(bind) (attach host to a cluster), V(unbind)
    (detach from cluster), V(install) (begin installation), and V(reset)
    (reset to discovery).
author:
  - Vishwanath Jayaraman (@vjayaramrh)
options:
  action:
    description:
      - The action to perform on the host.
      - V(bind) attaches the host to a cluster (requires O(cluster_id)).
      - V(unbind) detaches the host from its cluster.
      - V(install) begins installation on the host.
      - V(reset) resets the host to discovery state.
    type: str
    choices: [bind, unbind, install, reset]
    required: true
  infra_env_id:
    description:
      - The infrastructure environment ID containing the host.
    type: str
    required: true
  host_id:
    description:
      - The host ID (UUID) to act upon.
    type: str
    required: true
  cluster_id:
    description:
      - Cluster ID to bind the host to. Required when O(action=bind).
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
      - HTTP request timeout in seconds.
    type: int
    default: 30
  base_url:
    description:
      - Override the API base URL (for testing with a mock server).
      - Only HTTPS URLs are allowed, except for loopback (127.0.0.1/localhost).
    type: str
requirements:
  - ansible-core >= 2.17
notes:
  - Authentication requires either O(api_token) or O(offline_token).
  - Actions are guarded by host status. V(bind) requires an unbound host (no
    C(cluster_id); the status is one of the API's C(-unbound) variants such as
    C(known-unbound)) - a host already bound to a different cluster must be
    V(unbind)ed first. V(install) requires the host to be bound and C(known);
    V(reset) applies to C(error), C(installed), or C(cancelled) hosts.
  - Each action is idempotent - if the host is already in the target state for
    that action, C(changed=false) is returned and no API call is made. This
    includes the in-flight installation states - re-running V(install) while the
    host is C(preparing-for-installation), C(installing), or already
    C(installed) is a no-op, not a failure.
  - V(unbind) refuses a host that is mid-installation
    (C(preparing-for-installation), C(installing), etc.) because the API rejects
    it; wait for installation to finish or V(reset) the host first.
"""

EXAMPLES = r"""
# bind: guarded on an unbound host (e.g. status "known-unbound", no cluster_id)
- name: Bind a discovered host to a cluster
  openshift_lab.assisted_installer.host_action:
    action: bind
    infra_env_id: "{{ infra_env_id }}"
    host_id: "{{ discovered_host_id }}"
    cluster_id: "{{ target_cluster_id }}"
    api_token: "{{ assisted_installer_token }}"

# unbind: guarded on a bound host that is NOT mid-installation
- name: Unbind a host from its cluster
  openshift_lab.assisted_installer.host_action:
    action: unbind
    infra_env_id: "{{ infra_env_id }}"
    host_id: "{{ host_id }}"
    api_token: "{{ assisted_installer_token }}"

# install: guarded on a bound host in status "known" (no-op if already installing/installed)
- name: Install a bound and ready host
  openshift_lab.assisted_installer.host_action:
    action: install
    infra_env_id: "{{ infra_env_id }}"
    host_id: "{{ host_id }}"
    api_token: "{{ assisted_installer_token }}"

# reset: guarded on a host in "error", "installed", or "cancelled"
- name: Reset a failed host back to discovery
  openshift_lab.assisted_installer.host_action:
    action: reset
    infra_env_id: "{{ infra_env_id }}"
    host_id: "{{ host_id }}"
    api_token: "{{ assisted_installer_token }}"

- name: Bind with offline token from environment
  openshift_lab.assisted_installer.host_action:
    action: bind
    infra_env_id: "{{ infra_env_id }}"
    host_id: "{{ host_id }}"
    cluster_id: "{{ cluster_id }}"
  environment:
    AI_OFFLINE_TOKEN: "{{ lookup('env', 'REDHAT_OFFLINE_TOKEN') }}"

- name: Check if bind would change anything (check mode)
  openshift_lab.assisted_installer.host_action:
    action: bind
    infra_env_id: "{{ infra_env_id }}"
    host_id: "{{ host_id }}"
    cluster_id: "{{ cluster_id }}"
    api_token: "{{ assisted_installer_token }}"
  check_mode: true
  register: bind_check

- name: Proceed with bind only if it would change
  openshift_lab.assisted_installer.host_action:
    action: bind
    infra_env_id: "{{ infra_env_id }}"
    host_id: "{{ host_id }}"
    cluster_id: "{{ cluster_id }}"
    api_token: "{{ assisted_installer_token }}"
  when: bind_check.changed
"""

RETURN = r"""
changed:
  description: Whether the action changed the host state.
  returned: always
  type: bool
  sample: true
msg:
  description: Human-readable message describing what happened.
  returned: always
  type: str
  sample: "Successfully performed bind"
host:
  description: The host object after the action (or current state in check mode).
  returned: success
  type: dict
  sample:
    id: "550e8400-e29b-41d4-a716-446655440000"
    infra_env_id: "7c9e6679-7425-40de-944b-e07fc1f90ae7"
    cluster_id: "8b3c1cf0-4824-4f67-9a6e-9e9e0b74e0c8"
    status: "known"
    requested_hostname: "worker-1"
action:
  description: The action that was performed (or would be performed in check mode).
  returned: success
  type: str
  sample: "bind"
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.openshift_lab.assisted_installer.plugins.module_utils import (
    assisted_installer as ai,
)

# Host status groups, taken from the Assisted Installer OpenAPI host.status enum.
# Installation is in flight for these: a re-run of "install" must treat them as
# "already underway" (idempotent no-op, not a failure), and "unbind" must refuse
# them because the API rejects unbinding a host mid-installation.
INSTALLING_STATUSES = frozenset([
    "preparing-for-installation",
    "preparing-successful",
    "installing",
    "installing-in-progress",
    "installing-pending-user-action",
])
# Installation has completed for these: "install" is likewise a no-op.
INSTALLED_STATUSES = frozenset([
    "installed",
    "added-to-existing-cluster",
])
# An unbind is already underway for these: "unbind" is a no-op.
UNBINDING_STATUSES = frozenset([
    "unbinding",
    "unbinding-pending-user-action",
])


def needs_action(module, host, action, params):
    """
    Determine if the requested action needs to be performed based on current host status.

    Returns: (bool, str) - (needs_action, reason)
    """
    status = host.get("status", "").lower()
    cluster_id = host.get("cluster_id")

    if action == "bind":
        # Can bind if host is discovered/known and not already bound to the target cluster
        if cluster_id == params["cluster_id"]:
            return False, f"Host already bound to cluster {cluster_id}"
        # Cannot rebind to a different cluster without unbinding first.
        # Use truthiness so an empty cluster_id ("" or None) both read as unbound.
        if cluster_id:
            module.fail_json(
                msg=f"Host is bound to cluster {cluster_id}. Unbind it first before binding to {params['cluster_id']}",
                host=host,
            )
        # Reaching here, cluster_id is falsy => the host is unbound (one of the
        # API's "*-unbound" statuses, e.g. "known-unbound"). Binding is valid
        # from any unbound state, so we do NOT mirror the status enum with an
        # allowlist: that mirror drifts as the API evolves and shipped exactly
        # this bug (it listed the bound-family names, so every real unbound host
        # was wrongly refused). The API is the final authority on rarer edge
        # cases and a non-2xx maps to fail_json. See DESIGN.md §4 (coarse
        # guards) and issue #59.
        return True, f"Host is unbound (status '{status}'); ready to bind"

    elif action == "unbind":
        # Already unbound -> nothing to do.
        if not cluster_id:
            return False, "Host is not bound to any cluster"
        # An unbind is already in progress -> idempotent no-op.
        if status in UNBINDING_STATUSES:
            return False, f"Host is already unbinding (status '{status}')"
        # The API rejects unbinding a host mid-installation; guard before POSTing.
        if status in INSTALLING_STATUSES:
            module.fail_json(
                msg=f"Cannot unbind host in status '{status}' (installation in "
                    f"progress). Wait for it to finish or reset the host first.",
                host=host,
            )
        return True, f"Host is bound to cluster {cluster_id}"

    elif action == "install":
        # Already installing (incl. the preparing phases) or installed -> no-op,
        # so re-running the play is safe rather than failing mid-installation.
        if status in INSTALLING_STATUSES or status in INSTALLED_STATUSES:
            return False, f"Host is already {status}"
        if not cluster_id:
            module.fail_json(
                msg="Cannot install host that is not bound to a cluster",
                host=host,
            )
        if status != "known":
            module.fail_json(
                msg=f"Cannot install host in status '{status}'. Expected 'known'",
                host=host,
            )
        return True, f"Host status '{status}' and bound, ready to install"

    elif action == "reset":
        # Can reset if host is in a terminal or error state
        resettable_statuses = ["error", "installed", "cancelled"]
        if status not in resettable_statuses:
            return False, f"Host status '{status}' does not require reset"
        return True, f"Host status '{status}' can be reset"

    return False, "Unknown action"


def run_module():
    module_args = dict(
        action=dict(type="str", required=True, choices=["bind", "unbind", "install", "reset"]),
        infra_env_id=dict(type="str", required=True),
        host_id=dict(type="str", required=True),
        cluster_id=dict(type="str"),
        api_token=dict(type="str", no_log=True),
        offline_token=dict(type="str", no_log=True),
        timeout=dict(type="int", default=30),
        base_url=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        required_if=[
            ("action", "bind", ("cluster_id",)),
        ],
    )

    params = module.params
    action = params["action"]
    infra_env_id = params["infra_env_id"]
    host_id = params["host_id"]
    timeout = params["timeout"]
    base_url = params.get("base_url")

    # Resolve authentication token
    token = ai.resolve_token(module)

    # GET current host state
    host_path = f"/infra-envs/{infra_env_id}/hosts/{host_id}"
    host, info = ai.request(
        module, "GET", host_path, token,
        timeout=timeout, base_url=base_url,
    )

    if info["status"] != 200:
        module.fail_json(
            msg=f"Failed to retrieve host {host_id}",
            status=info["status"],
            response=host,
        )

    # Check if action is needed
    action_needed, reason = needs_action(module, host, action, params)

    if not action_needed:
        # Already in target state - idempotent no-op
        module.exit_json(
            changed=False,
            host=host,
            action=action,
            msg=reason,
        )

    # Action is needed
    if module.check_mode:
        # In check mode, predict the change but don't execute
        module.exit_json(
            changed=True,
            host=host,
            action=action,
            msg=f"Would perform {action}: {reason}",
        )

    # Execute the action
    action_path = f"/infra-envs/{infra_env_id}/hosts/{host_id}/actions/{action}"

    # Build request body based on action
    body = {}
    if action == "bind":
        body["cluster_id"] = params["cluster_id"]

    result, info = ai.request(
        module, "POST", action_path, token,
        body=body if body else None,
        timeout=timeout, base_url=base_url,
    )

    if info["status"] not in [200, 201, 202, 204]:
        module.fail_json(
            msg=f"Failed to {action} host",
            status=info["status"],
            response=result,
        )

    # Fetch updated host state
    updated_host, info = ai.request(
        module, "GET", host_path, token,
        timeout=timeout, base_url=base_url,
    )

    if info["status"] != 200:
        # Action succeeded but couldn't fetch updated state - return action result
        updated_host = result if result else host

    module.exit_json(
        changed=True,
        host=updated_host,
        action=action,
        msg=f"Successfully performed {action}",
    )


def main():
    run_module()


if __name__ == "__main__":
    main()
