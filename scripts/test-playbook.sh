#!/usr/bin/env bash
#
# Test info modules with a real playbook against the live API
# Runs inside the container via ./run.sh
#
# Usage:
#   AI_API_TOKEN="your-token" ./run.sh test-playbook
#
set -euo pipefail

echo "========================================="
echo "Testing Info Modules with Playbook"
echo "========================================="

# Check token is set
if [ -z "${AI_API_TOKEN:-}" ]; then
    echo "ERROR: AI_API_TOKEN environment variable is required"
    echo ""
    echo "Usage:"
    echo "  AI_API_TOKEN='your-token-here' ./run.sh test-playbook"
    echo ""
    echo "Or set it first:"
    echo "  export AI_API_TOKEN='your-token-here'"
    echo "  ./run.sh test-playbook"
    exit 1
fi

echo "✓ API token found"
echo ""

# Step 1: Build the collection
echo "Step 1: Building collection..."
ansible-galaxy collection build --force
TARBALL=$(find . -maxdepth 1 -name "openshift_lab-assisted_installer-*.tar.gz" -type f -printf '%T@ %p\n' | sort -rn | head -1 | cut -d' ' -f2-)
echo "✓ Built: ${TARBALL}"
echo ""

# Step 2: Install the collection
echo "Step 2: Installing collection..."
ansible-galaxy collection install "${TARBALL}" --force
echo "✓ Installed to: ${HOME}/.ansible/collections"
echo ""

# Step 3: Verify installation
echo "Step 3: Verifying installation..."
INSTALLED_PATH="${HOME}/.ansible/collections/ansible_collections/openshift_lab/assisted_installer"
if [ -d "${INSTALLED_PATH}" ]; then
    echo "✓ Collection installed at: ${INSTALLED_PATH}"
    echo "  Modules found:"
    find "${INSTALLED_PATH}/plugins/modules/" -maxdepth 1 -name "*.py" -type f -exec basename {} \; | sed 's/\.py$//' | sed 's/^/    - /'
else
    echo "ERROR: Collection not found at expected path"
    exit 1
fi
echo ""

# Step 4: Run the test playbook
echo "Step 4: Running test playbook..."
echo "========================================="
ansible-playbook -v tests/playbooks/test-info-modules.yml

echo ""
echo "========================================="
echo "✓ Playbook Testing Complete"
echo "========================================="
