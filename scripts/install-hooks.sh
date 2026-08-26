#!/bin/bash
# Install git hooks for this repository using pre-commit framework
#
# Run this once after cloning to enable local commit guards.

set -e

# Verify we're in repo root
if [ ! -d ".git" ]; then
  echo "❌ Error: .git directory not found."
  echo "   Are you in the repository root?"
  exit 1
fi

# Verify the branch-guard hook script exists
if [ ! -f ".githooks/pre-commit" ]; then
  echo "❌ Error: .githooks/pre-commit not found."
  echo "   The branch-guard hook script is missing from the repository."
  exit 1
fi

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
  echo "❌ Error: pre-commit is not installed."
  echo ""
  echo "Install it with:"
  echo "  pipx install pre-commit"
  echo "  # or"
  echo "  pip install pre-commit"
  echo ""
  exit 1
fi

# Install all hooks (including our local branch-guard hook)
echo "Installing pre-commit hooks..."
pre-commit install

echo ""
echo "✅ Git hooks installed successfully!"
echo ""
echo "Installed hooks:"
echo "  - Trailing whitespace, end-of-file fixes"
echo "  - Merge conflict detection"
echo "  - YAML validation"
echo "  - yamllint"
echo "  - ansible-lint"
echo "  - Branch guard (prevents commits to main)"
echo ""
echo "All changes must go through feature branches and PRs."
