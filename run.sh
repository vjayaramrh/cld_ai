#!/usr/bin/env bash
#
# One entry point for the cld_ai collection — runs everything inside a container
# so the only host dependency is Docker or Podman.
#
#   ./run.sh            build the image and open an interactive shell
#   ./run.sh --check    build + fast verification (collection build + sanity + units)
#   ./run.sh --full     build + deep verification (adds collection install round-trip)
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

# --- common run args ----------------------------------------------------------
RUN_ARGS=(
    --rm
    "${USERNS[@]}"
    -e HOME=/tmp
    -v "${REPO_DIR}:${CONTAINER_COLLECTION_PATH}${MOUNT_OPTS}"
    -w "${CONTAINER_COLLECTION_PATH}"
    "${IMAGE}"
)

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
    shell)
        echo ">> opening a shell (exit to leave the container)"
        exec "${RUNTIME}" run -it "${RUN_ARGS[@]}" bash
        ;;
    *)
        echo "usage: ./run.sh [--check|--full]" >&2
        exit 2
        ;;
esac
