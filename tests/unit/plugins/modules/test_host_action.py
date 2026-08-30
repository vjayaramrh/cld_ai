"""
Unit tests for host_action module.

Tests the RPC-style action pattern: guard on host status before acting,
idempotent no-ops when already in target state.
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import pytest
from ansible_collections.openshift_lab.assisted_installer.plugins.modules import (
    host_action,
)
from ansible_collections.openshift_lab.assisted_installer.plugins.module_utils import (
    assisted_installer as ai,
)
from ansible_helpers import (
    AnsibleExitJson,
    AnsibleFailJson,
    patch_ansible,
    queue_fetch_url,
    set_module_args,
)


# Sample host objects for different states
HOST_KNOWN_UNBOUND = {
    "id": "host-123",
    "infra_env_id": "infra-456",
    "status": "known",
    "cluster_id": None,
}

HOST_BOUND = {
    "id": "host-123",
    "infra_env_id": "infra-456",
    "status": "known",
    "cluster_id": "cluster-789",
}

HOST_INSTALLING = {
    "id": "host-123",
    "infra_env_id": "infra-456",
    "status": "installing",
    "cluster_id": "cluster-789",
}

HOST_INSTALLED = {
    "id": "host-123",
    "infra_env_id": "infra-456",
    "status": "installed",
    "cluster_id": "cluster-789",
}

HOST_ERROR = {
    "id": "host-123",
    "infra_env_id": "infra-456",
    "status": "error",
    "cluster_id": "cluster-789",
}


# ============================================================================
# 1. LIFECYCLE TESTS - each action's happy path
# ============================================================================


def test_bind_posts_when_unbound(monkeypatch):
    """Bind action: host is known and unbound → POSTs bind, changed=True."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)
    calls = []
    monkeypatch.setattr(
        ai,
        "fetch_url",
        queue_fetch_url(
            [
                (200, HOST_KNOWN_UNBOUND),  # GET: host is unbound
                (202, {}),  # POST: bind action accepted
                (200, HOST_BOUND),  # GET: fetch updated host
            ],
            calls=calls,
        ),
    )
    set_module_args({
        "action": "bind",
        "infra_env_id": "infra-456",
        "host_id": "host-123",
        "cluster_id": "cluster-789",
        "api_token": "test-token",
    })

    with pytest.raises(AnsibleExitJson) as exc:
        host_action.main()

    assert exc.value.result["changed"] is True
    assert exc.value.result["action"] == "bind"
    assert exc.value.result["host"]["cluster_id"] == "cluster-789"
    assert len(calls) == 3
    assert calls[0]["method"] == "GET"
    assert calls[1]["method"] == "POST"
    assert "/actions/bind" in calls[1]["url"]


def test_unbind_posts_when_bound(monkeypatch):
    """Unbind action: host is bound → POSTs unbind, changed=True."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)
    calls = []
    monkeypatch.setattr(
        ai,
        "fetch_url",
        queue_fetch_url(
            [
                (200, HOST_BOUND),  # GET: host is bound
                (202, {}),  # POST: unbind action accepted
                (200, HOST_KNOWN_UNBOUND),  # GET: fetch updated host
            ],
            calls=calls,
        ),
    )
    set_module_args({
        "action": "unbind",
        "infra_env_id": "infra-456",
        "host_id": "host-123",
        "api_token": "test-token",
    })

    with pytest.raises(AnsibleExitJson) as exc:
        host_action.main()

    assert exc.value.result["changed"] is True
    assert exc.value.result["action"] == "unbind"
    assert len(calls) == 3
    assert calls[1]["method"] == "POST"
    assert "/actions/unbind" in calls[1]["url"]


def test_install_posts_when_ready(monkeypatch):
    """Install action: host is known and bound → POSTs install, changed=True."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)
    calls = []
    monkeypatch.setattr(
        ai,
        "fetch_url",
        queue_fetch_url(
            [
                (200, HOST_BOUND),  # GET: host is ready
                (202, {}),  # POST: install action accepted
                (200, HOST_INSTALLING),  # GET: fetch updated host
            ],
            calls=calls,
        ),
    )
    set_module_args({
        "action": "install",
        "infra_env_id": "infra-456",
        "host_id": "host-123",
        "api_token": "test-token",
    })

    with pytest.raises(AnsibleExitJson) as exc:
        host_action.main()

    assert exc.value.result["changed"] is True
    assert exc.value.result["action"] == "install"
    assert exc.value.result["host"]["status"] == "installing"
    assert calls[1]["method"] == "POST"
    assert "/actions/install" in calls[1]["url"]


def test_reset_posts_when_in_error(monkeypatch):
    """Reset action: host is in error state → POSTs reset, changed=True."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)
    calls = []
    monkeypatch.setattr(
        ai,
        "fetch_url",
        queue_fetch_url(
            [
                (200, HOST_ERROR),  # GET: host is in error
                (202, {}),  # POST: reset action accepted
                (200, HOST_KNOWN_UNBOUND),  # GET: fetch updated host
            ],
            calls=calls,
        ),
    )
    set_module_args({
        "action": "reset",
        "infra_env_id": "infra-456",
        "host_id": "host-123",
        "api_token": "test-token",
    })

    with pytest.raises(AnsibleExitJson) as exc:
        host_action.main()

    assert exc.value.result["changed"] is True
    assert exc.value.result["action"] == "reset"
    assert calls[1]["method"] == "POST"
    assert "/actions/reset" in calls[1]["url"]


# ============================================================================
# 2. IDEMPOTENCY TESTS - already in target state
# ============================================================================


def test_bind_when_already_bound_to_target_cluster(monkeypatch):
    """Bind when already bound to the same cluster → changed=False, no POST."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)
    calls = []
    monkeypatch.setattr(
        ai,
        "fetch_url",
        queue_fetch_url(
            [
                (200, HOST_BOUND),  # GET: already bound to target cluster
            ],
            calls=calls,
        ),
    )
    set_module_args({
        "action": "bind",
        "infra_env_id": "infra-456",
        "host_id": "host-123",
        "cluster_id": "cluster-789",  # Same as HOST_BOUND
        "api_token": "test-token",
    })

    with pytest.raises(AnsibleExitJson) as exc:
        host_action.main()

    assert exc.value.result["changed"] is False
    assert "already bound" in exc.value.result["msg"].lower()
    assert len(calls) == 1  # Only GET, no POST
    assert calls[0]["method"] == "GET"


def test_unbind_when_not_bound(monkeypatch):
    """Unbind when host is not bound → changed=False, no POST."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)
    calls = []
    monkeypatch.setattr(
        ai,
        "fetch_url",
        queue_fetch_url(
            [
                (200, HOST_KNOWN_UNBOUND),  # GET: not bound
            ],
            calls=calls,
        ),
    )
    set_module_args({
        "action": "unbind",
        "infra_env_id": "infra-456",
        "host_id": "host-123",
        "api_token": "test-token",
    })

    with pytest.raises(AnsibleExitJson) as exc:
        host_action.main()

    assert exc.value.result["changed"] is False
    assert "not bound" in exc.value.result["msg"].lower()
    assert len(calls) == 1


def test_install_when_already_installing(monkeypatch):
    """Install when host is already installing → changed=False, no POST."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)
    calls = []
    monkeypatch.setattr(
        ai,
        "fetch_url",
        queue_fetch_url(
            [
                (200, HOST_INSTALLING),  # GET: already installing
            ],
            calls=calls,
        ),
    )
    set_module_args({
        "action": "install",
        "infra_env_id": "infra-456",
        "host_id": "host-123",
        "api_token": "test-token",
    })

    with pytest.raises(AnsibleExitJson) as exc:
        host_action.main()

    assert exc.value.result["changed"] is False
    assert "already" in exc.value.result["msg"].lower()
    assert len(calls) == 1


def test_reset_when_status_does_not_require_reset(monkeypatch):
    """Reset when host is in known state (not error/installed) → changed=False."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)
    calls = []
    monkeypatch.setattr(
        ai,
        "fetch_url",
        queue_fetch_url(
            [
                (200, HOST_KNOWN_UNBOUND),  # GET: status is "known", doesn't need reset
            ],
            calls=calls,
        ),
    )
    set_module_args({
        "action": "reset",
        "infra_env_id": "infra-456",
        "host_id": "host-123",
        "api_token": "test-token",
    })

    with pytest.raises(AnsibleExitJson) as exc:
        host_action.main()

    assert exc.value.result["changed"] is False
    assert "does not require reset" in exc.value.result["msg"]
    assert len(calls) == 1


def test_bind_twice_second_is_noop(monkeypatch):
    """Bind unbound host, then bind again → first changes, second doesn't."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)
    calls = []
    monkeypatch.setattr(
        ai,
        "fetch_url",
        queue_fetch_url(
            [
                # First run: bind
                (200, HOST_KNOWN_UNBOUND),  # GET: unbound
                (202, {}),  # POST: bind action
                (200, HOST_BOUND),  # GET: fetch updated host
                # Second run: already bound
                (200, HOST_BOUND),  # GET: already bound to target
            ],
            calls=calls,
        ),
    )
    args = {
        "action": "bind",
        "infra_env_id": "infra-456",
        "host_id": "host-123",
        "cluster_id": "cluster-789",
        "api_token": "test-token",
    }

    # First run: should bind
    set_module_args(args)
    with pytest.raises(AnsibleExitJson) as exc:
        host_action.main()
    assert exc.value.result["changed"] is True

    # Second run: should be no-op
    set_module_args(args)
    with pytest.raises(AnsibleExitJson) as exc:
        host_action.main()
    assert exc.value.result["changed"] is False
    assert len(calls) == 4  # GET, POST, GET, GET (no second POST)


def test_unbind_twice_second_is_noop(monkeypatch):
    """Unbind bound host, then unbind again → first changes, second doesn't."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)
    calls = []
    monkeypatch.setattr(
        ai,
        "fetch_url",
        queue_fetch_url(
            [
                # First run: unbind
                (200, HOST_BOUND),  # GET: bound
                (202, {}),  # POST: unbind action
                (200, HOST_KNOWN_UNBOUND),  # GET: fetch updated host
                # Second run: already unbound
                (200, HOST_KNOWN_UNBOUND),  # GET: already unbound
            ],
            calls=calls,
        ),
    )
    args = {
        "action": "unbind",
        "infra_env_id": "infra-456",
        "host_id": "host-123",
        "api_token": "test-token",
    }

    # First run: should unbind
    set_module_args(args)
    with pytest.raises(AnsibleExitJson) as exc:
        host_action.main()
    assert exc.value.result["changed"] is True

    # Second run: should be no-op
    set_module_args(args)
    with pytest.raises(AnsibleExitJson) as exc:
        host_action.main()
    assert exc.value.result["changed"] is False
    assert len(calls) == 4


# ============================================================================
# 3. CHECK MODE TESTS - predict changes without acting
# ============================================================================


def test_check_mode_bind_predicts_change(monkeypatch):
    """Check mode: bind action needed → changed=True, no POST."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)
    calls = []
    monkeypatch.setattr(
        ai,
        "fetch_url",
        queue_fetch_url(
            [
                (200, HOST_KNOWN_UNBOUND),  # GET: unbound, would bind
            ],
            calls=calls,
        ),
    )
    set_module_args({
        "action": "bind",
        "infra_env_id": "infra-456",
        "host_id": "host-123",
        "cluster_id": "cluster-789",
        "api_token": "test-token",
        "_ansible_check_mode": True,
    })

    with pytest.raises(AnsibleExitJson) as exc:
        host_action.main()

    assert exc.value.result["changed"] is True
    assert "would perform" in exc.value.result["msg"].lower()
    assert len(calls) == 1  # Only GET, no POST
    assert calls[0]["method"] == "GET"


def test_check_mode_unbind_predicts_no_change(monkeypatch):
    """Check mode: unbind when already unbound → changed=False, no POST."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)
    calls = []
    monkeypatch.setattr(
        ai,
        "fetch_url",
        queue_fetch_url(
            [
                (200, HOST_KNOWN_UNBOUND),  # GET: already unbound
            ],
            calls=calls,
        ),
    )
    set_module_args({
        "action": "unbind",
        "infra_env_id": "infra-456",
        "host_id": "host-123",
        "api_token": "test-token",
        "_ansible_check_mode": True,
    })

    with pytest.raises(AnsibleExitJson) as exc:
        host_action.main()

    assert exc.value.result["changed"] is False
    assert len(calls) == 1


# ============================================================================
# 4. SAFETY GUARDS - fail gracefully with helpful errors
# ============================================================================


def test_fail_when_no_token(monkeypatch):
    """Missing api_token/offline_token → fail before any HTTP call."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)
    calls = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([], calls=calls))
    set_module_args({
        "action": "bind",
        "infra_env_id": "infra-456",
        "host_id": "host-123",
        "cluster_id": "cluster-789",
    })

    with pytest.raises(AnsibleFailJson) as exc:
        host_action.main()

    assert "token" in str(exc.value.result["msg"]).lower()
    assert len(calls) == 0  # No HTTP calls attempted


def test_fail_when_bind_missing_cluster_id(monkeypatch):
    """Bind action without cluster_id → fail before any HTTP call."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)
    calls = []
    monkeypatch.setattr(ai, "fetch_url", queue_fetch_url([], calls=calls))
    set_module_args({
        "action": "bind",
        "infra_env_id": "infra-456",
        "host_id": "host-123",
        "api_token": "test-token",
        # Missing cluster_id
    })

    with pytest.raises(AnsibleFailJson) as exc:
        host_action.main()

    assert "cluster_id" in str(exc.value.result["msg"]).lower()
    assert len(calls) == 0


def test_fail_when_bind_invalid_status(monkeypatch):
    """Bind when host is installing (unbound) → fail with helpful message."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)
    calls = []
    # Host is installing but NOT bound (cluster_id = None)
    host_installing_unbound = {
        "id": "host-123",
        "infra_env_id": "infra-456",
        "status": "installing",
        "cluster_id": None,
    }
    monkeypatch.setattr(
        ai,
        "fetch_url",
        queue_fetch_url(
            [
                (200, host_installing_unbound),  # GET: status is "installing", unbound
            ],
            calls=calls,
        ),
    )
    set_module_args({
        "action": "bind",
        "infra_env_id": "infra-456",
        "host_id": "host-123",
        "cluster_id": "cluster-new",
        "api_token": "test-token",
    })

    with pytest.raises(AnsibleFailJson) as exc:
        host_action.main()

    assert "cannot bind" in str(exc.value.result["msg"]).lower()
    assert "installing" in str(exc.value.result["msg"])
    assert len(calls) == 1  # Only GET, no POST


def test_fail_when_bind_to_different_cluster(monkeypatch):
    """Bind when already bound to a different cluster → fail, require unbind first."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)
    calls = []
    monkeypatch.setattr(
        ai,
        "fetch_url",
        queue_fetch_url(
            [
                (200, HOST_BOUND),  # GET: bound to cluster-789
            ],
            calls=calls,
        ),
    )
    set_module_args({
        "action": "bind",
        "infra_env_id": "infra-456",
        "host_id": "host-123",
        "cluster_id": "cluster-different",  # Trying to bind to a DIFFERENT cluster
        "api_token": "test-token",
    })

    with pytest.raises(AnsibleFailJson) as exc:
        host_action.main()

    assert "unbind" in str(exc.value.result["msg"]).lower()
    assert "cluster-789" in str(exc.value.result["msg"])  # Current cluster
    assert len(calls) == 1  # Only GET, no POST


def test_fail_when_install_not_bound(monkeypatch):
    """Install when host is not bound to a cluster → fail with helpful message."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)
    calls = []
    monkeypatch.setattr(
        ai,
        "fetch_url",
        queue_fetch_url(
            [
                (200, HOST_KNOWN_UNBOUND),  # GET: not bound
            ],
            calls=calls,
        ),
    )
    set_module_args({
        "action": "install",
        "infra_env_id": "infra-456",
        "host_id": "host-123",
        "api_token": "test-token",
    })

    with pytest.raises(AnsibleFailJson) as exc:
        host_action.main()

    assert "not bound" in str(exc.value.result["msg"]).lower()
    assert len(calls) == 1


def test_fail_when_install_wrong_status(monkeypatch):
    """Install when host is in error state → fail with helpful message."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)
    calls = []
    monkeypatch.setattr(
        ai,
        "fetch_url",
        queue_fetch_url(
            [
                (200, HOST_ERROR),  # GET: status is "error"
            ],
            calls=calls,
        ),
    )
    set_module_args({
        "action": "install",
        "infra_env_id": "infra-456",
        "host_id": "host-123",
        "api_token": "test-token",
    })

    with pytest.raises(AnsibleFailJson) as exc:
        host_action.main()

    assert "cannot install" in str(exc.value.result["msg"]).lower()
    assert "error" in str(exc.value.result["msg"])
    assert len(calls) == 1


# ============================================================================
# 5. API CONTRACT TESTS - error handling, base_url override
# ============================================================================


def test_handles_404_on_get_host(monkeypatch):
    """GET host returns 404 → fail_json with status and details."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)
    calls = []
    monkeypatch.setattr(
        ai,
        "fetch_url",
        queue_fetch_url(
            [
                (404, {"error": "Host not found"}),
            ],
            calls=calls,
        ),
    )
    set_module_args({
        "action": "bind",
        "infra_env_id": "infra-456",
        "host_id": "nonexistent",
        "cluster_id": "cluster-789",
        "api_token": "test-token",
    })

    with pytest.raises(AnsibleFailJson) as exc:
        host_action.main()

    assert "404" in str(exc.value.result["msg"]) or exc.value.result["status"] == 404
    assert len(calls) == 1


def test_handles_500_on_action_post(monkeypatch):
    """POST action returns 500 → fail_json with status and details."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)
    calls = []
    monkeypatch.setattr(
        ai,
        "fetch_url",
        queue_fetch_url(
            [
                (200, HOST_KNOWN_UNBOUND),  # GET succeeds
                (500, {"error": "Internal server error"}),  # POST fails
            ],
            calls=calls,
        ),
    )
    set_module_args({
        "action": "bind",
        "infra_env_id": "infra-456",
        "host_id": "host-123",
        "cluster_id": "cluster-789",
        "api_token": "test-token",
    })

    with pytest.raises(AnsibleFailJson) as exc:
        host_action.main()

    assert "500" in str(exc.value.result["msg"]) or exc.value.result["status"] == 500
    assert len(calls) == 2


def test_base_url_override_for_testing(monkeypatch):
    """base_url param allows integration testing with mock server."""
    patch_ansible(monkeypatch)
    monkeypatch.delenv("AI_API_TOKEN", raising=False)
    monkeypatch.delenv("AI_OFFLINE_TOKEN", raising=False)
    calls = []
    monkeypatch.setattr(
        ai,
        "fetch_url",
        queue_fetch_url(
            [
                (200, HOST_BOUND),  # GET: already bound
            ],
            calls=calls,
        ),
    )
    set_module_args({
        "action": "bind",
        "infra_env_id": "infra-456",
        "host_id": "host-123",
        "cluster_id": "cluster-789",
        "api_token": "test-token",
        "base_url": "http://127.0.0.1:8080",  # Loopback allowed
    })

    with pytest.raises(AnsibleExitJson) as exc:
        host_action.main()

    # Should succeed (idempotent no-op)
    assert exc.value.result["changed"] is False
    assert len(calls) == 1
    # Verify the mock URL was used (checked by shared client validation)
