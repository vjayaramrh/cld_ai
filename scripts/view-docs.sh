#!/usr/bin/env bash
# Quick documentation viewer for development
#
# Usage:
#   ./scripts/view-docs.sh [module_name]
#   ./scripts/view-docs.sh infra_env
#   ./scripts/view-docs.sh  # defaults to openshift_version_info

set -euo pipefail

MODULE="${1:-openshift_version_info}"
FQCN="openshift_lab.assisted_installer.${MODULE}"

echo "Viewing documentation for: $FQCN"
echo "============================================"
echo ""

# Run ansible-doc inside container
# Must build collection first so ansible-doc can find it
IMAGE="cld_ai:dev"
NAMESPACE="openshift_lab"
COLLECTION="assisted_installer"
CONTAINER_COLLECTION_PATH="/home/dev/ansible_collections/${NAMESPACE}/${COLLECTION}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Pick runtime
if command -v podman >/dev/null 2>&1; then
    RUNTIME="podman"
elif command -v docker >/dev/null 2>&1; then
    RUNTIME="docker"
else
    echo "ERROR: neither podman nor docker found" >&2
    exit 1
fi

# Ensure image exists
if ! "${RUNTIME}" image inspect "${IMAGE}" >/dev/null 2>&1; then
    echo "ERROR: Image ${IMAGE} not found. Run './run.sh --check' first to build it." >&2
    exit 1
fi

# Build collection and view docs
exec "${RUNTIME}" run --rm \
    -v "${REPO_DIR}:${CONTAINER_COLLECTION_PATH}:Z" \
    -w "${CONTAINER_COLLECTION_PATH}" \
    "${IMAGE}" \
    bash -c "ansible-galaxy collection build --force >/dev/null && ansible-galaxy collection install *.tar.gz --force >/dev/null && ansible-doc ${FQCN}"
