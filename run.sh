#!/usr/bin/env bash
#
# One entry point for the cld_ai collection — runs everything inside a container
# so the only host dependency is Docker or Podman.
#
#   ./run.sh                 build the image and open an interactive shell
#   ./run.sh --check         build + fast verification (collection build + sanity + units)
#   ./run.sh --full          build + deep verification (adds collection install round-trip)
#   ./run.sh test-playbook   test info modules with playbook against live API
#                            (auto-uses 'ocm token' if available, else AI_API_TOKEN env var or api.token file)
#
set -euo pipefail

IMAGE="cld_ai:dev"
NAMESPACE="openshift_lab"
COLLECTION="assisted_installer"
# ansible-test requires this exact path structure inside the container.
CONTAINER_COLLECTION_PATH="/home/dev/ansible_collections/${NAMESPACE}/${COLLECTION}"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- pick a container runtime -------------------------------------------------
if command -v podman >/dev/null 2>&1; then
    RUNTIME="podman"
elif command -v docker >/dev/null 2>&1; then
    RUNTIME="docker"
else
    echo "ERROR: neither podman nor docker found. Install one and retry." >&2
    exit 1
fi
echo ">> using ${RUNTIME}"

# Start the podman machine on macOS if it isn't running.
if [ "${RUNTIME}" = "podman" ]; then
    if ! podman info >/dev/null 2>&1; then
        echo ">> starting podman machine..."
        podman machine start || true
    fi
fi

# --- runtime-specific mount flags --------------------------------------------
MOUNT_OPTS=""
USERNS=()
if [ "${RUNTIME}" = "podman" ]; then
    MOUNT_OPTS=":Z"                 # SELinux relabel for the bind mount
    USERNS=(--userns=keep-id)       # map host UID -> dev inside (rootless)
fi

# --- build --------------------------------------------------------------------
echo ">> building ${IMAGE} ..."
"${RUNTIME}" build -t "${IMAGE}" -f "${REPO_DIR}/.devcontainer/Dockerfile" "${REPO_DIR}"

# --- token resolution (for playbook testing) ---------------------------------
# Priority: 1. AI_API_TOKEN env var, 2. Exchange offline.token, 3. Use api.token
# Note: 'ocm token' generates OCM API tokens, not Assisted Installer API tokens
# Timing: Tokens resolved at STARTUP, not refreshed during shell sessions (15-min expiry).
#         For long shell sessions, exit and re-enter to get a fresh token.

if [ -z "${AI_API_TOKEN:-}" ]; then
    # Try exchanging offline token for fresh access token
    if [ -f "${REPO_DIR}/offline.token" ]; then
        OFFLINE_TOKEN=$(grep -v '^#' "${REPO_DIR}/offline.token" | grep -v '^[[:space:]]*$' | head -1 | tr -d '[:space:]')
        if [ -n "${OFFLINE_TOKEN}" ] && command -v curl >/dev/null 2>&1; then
            AI_API_TOKEN=$(curl -s -X POST \
                "https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token" \
                -d "grant_type=refresh_token" \
                -d "client_id=cloud-services" \
                -d "refresh_token=${OFFLINE_TOKEN}" \
                | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
            if [ -n "${AI_API_TOKEN}" ]; then
                echo ">> exchanged offline token for fresh API token"
            fi
        fi
    fi

    # Fall back to api.token file
    if [ -z "${AI_API_TOKEN:-}" ] && [ -f "${REPO_DIR}/api.token" ]; then
        AI_API_TOKEN=$(grep -v '^#' "${REPO_DIR}/api.token" | grep -v '^[[:space:]]*$' | head -1 | tr -d '[:space:]')
        if [ -n "${AI_API_TOKEN}" ]; then
            echo ">> loaded API token from api.token file (may be expired)"
        fi
    fi
fi

# --- common run args ----------------------------------------------------------
RUN_ARGS=(
    --rm
    "${USERNS[@]}"
    -e HOME=/tmp
    -v "${REPO_DIR}:${CONTAINER_COLLECTION_PATH}${MOUNT_OPTS}"
    -w "${CONTAINER_COLLECTION_PATH}"
)

# Pass through AI_API_TOKEN if set (for playbook testing)
if [ -n "${AI_API_TOKEN:-}" ]; then
    RUN_ARGS+=(-e "AI_API_TOKEN=${AI_API_TOKEN}")
fi

RUN_ARGS+=("${IMAGE}")

MODE="${1:-shell}"
case "${MODE}" in
    --check)
        echo ">> running fast checks..."
        exec "${RUNTIME}" run "${RUN_ARGS[@]}" bash scripts/smoke.sh
        ;;
    --full)
        echo ">> running full checks..."
        exec "${RUNTIME}" run "${RUN_ARGS[@]}" bash scripts/smoke.sh --full
        ;;
    test-playbook)
        echo ">> testing info modules with playbook..."
        exec "${RUNTIME}" run "${RUN_ARGS[@]}" bash scripts/test-playbook.sh
        ;;
    shell)
        echo ">> opening a shell (exit to leave the container)"
        exec "${RUNTIME}" run -it "${RUN_ARGS[@]}" bash
        ;;
    *)
        echo "usage: ./run.sh [--check|--full|test-playbook]" >&2
        exit 2
        ;;
esac
