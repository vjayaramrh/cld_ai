---
name: ansible-collection-structure
description: Complete guide to Ansible collection directory structure, galaxy.yml configuration, meta/runtime.yml, and file placement conventions. Covers namespace/name rules, where to put modules/plugins/tests/docs, and collection metadata. Use when setting up a new collection or onboarding contributors.
---

# Ansible Collection Structure Guide

Complete reference for organizing Ansible collections, based on the [official collection development guide](https://docs.ansible.com/projects/ansible/latest/dev_guide/developing_collections.html).

## Overview

Ansible collections use a standardized directory structure. The namespace and collection name MUST match the directory path.

**Example:** Collection `openshift_lab.assisted_installer` must live at:
```
ansible_collections/openshift_lab/assisted_installer/
```

---

## Complete Directory Tree

```
ansible_collections/<namespace>/<name>/
├── galaxy.yml                      # Collection metadata (REQUIRED)
├── README.md                       # Collection overview
├── LICENSE                         # License file (GPL-3.0-or-later)
├── CHANGELOG.md                    # Change history
├── CLAUDE.md                       # Project-specific guidance
├── DESIGN.md                       # Architecture decisions
├── CONTRIBUTING.md                 # Contributor guide
├── SECURITY.md                     # Security policy
│
├── changelogs/                     # Changelog fragments
│   ├── config.yaml                 # Changelog config
│   └── fragments/                  # Individual change files
│
├── docs/                           # Additional documentation
│   ├── api-endpoint-map.md
│   ├── testing-cheat-sheet.md
│   └── ...
│
├── meta/                           # Collection metadata
│   └── runtime.yml                 # ansible-core support matrix (REQUIRED)
│
├── plugins/                        # All plugin types
│   ├── modules/                    # Modules (REQUIRED for this project)
│   │   ├── cluster_info.py
│   │   ├── infra_env.py
│   │   └── ...
│   ├── module_utils/               # Shared utilities
│   │   └── assisted_installer.py  # Shared API client
│   ├── inventory/                  # Inventory plugins
│   ├── filter/                     # Filter plugins
│   └── ...                         # Other plugin types
│
├── roles/                          # Ansible roles (if any)
│   └── example_role/
│
├── tests/                          # All tests
│   ├── sanity/                     # Sanity test config
│   │   ├── ignore-2.17.txt         # Sanity ignores per ansible-core version
│   │   ├── ignore-2.18.txt
│   │   └── ...
│   ├── unit/                       # Unit tests
│   │   └── plugins/
│   │       └── modules/
│   │           ├── ansible_helpers.py
│   │           ├── conftest.py
│   │           └── test_*.py
│   └── integration/                # Integration tests
│       └── targets/
│           └── module_name/
│               ├── tasks/
│               │   └── main.yml
│               ├── defaults/
│               │   └── main.yml
│               └── meta/
│                   └── main.yml
│
├── scripts/                        # Helper scripts
│   └── install-hooks.sh
│
└── .github/                        # GitHub-specific
    ├── workflows/
    │   └── ci.yml                  # CI pipeline
    ├── CODEOWNERS                  # Code review owners
    └── pull_request_template.md   # PR template
```

---

## galaxy.yml (REQUIRED)

**Location:** Root of collection directory

**Purpose:** Collection metadata for Ansible Galaxy

```yaml
namespace: openshift_lab
name: assisted_installer
version: 0.1.0

readme: README.md
authors:
  - Vishwanath Jayaraman (@vjayaramrh)

description: >-
  Ansible collection wrapping the OpenShift Assisted Installer API.
  Provides modules for managing clusters, infrastructure environments,
  and hosts.

license:
  - GPL-3.0-or-later

tags:
  - openshift
  - redhat
  - kubernetes
  - infrastructure

repository: https://github.com/vjayaramrh/cld_ai
documentation: https://github.com/vjayaramrh/cld_ai/blob/main/README.md
homepage: https://github.com/vjayaramrh/cld_ai
issues: https://github.com/vjayaramrh/cld_ai/issues

dependencies: {}

build_ignore:
  - '*.tar.gz'
  - '.git'
  - '.github'
  - '.gitignore'
  - '.vscode'
  - '__pycache__'
  - '*.pyc'
```

### Critical Fields

**namespace + name:**
- MUST match directory path
- Rules: start with a lowercase letter; use only lowercase letters, digits, and underscores; do not use consecutive underscores.

**version:**
- Semantic versioning: `MAJOR.MINOR.PATCH`
- Updated for each release

**license:**
- List of SPDX identifiers
- Must match LICENSE file

---

## meta/runtime.yml (REQUIRED)

**Location:** `meta/runtime.yml`

**Purpose:** Declares which ansible-core versions this collection supports

```yaml
---
requires_ansible: ">=2.17.0"
```

### ansible-core Support Matrix

**This project supports:** ansible-core 2.17, 2.18, 2.19, 2.20

**CRITICAL:** Maintain consistency across three places:
1. `meta/runtime.yml` - `requires_ansible`
2. `.github/workflows/ci.yml` - test matrix
3. `tests/sanity/ignore-*.txt` - one file per supported version

**Example CI matrix:**
```yaml
strategy:
  matrix:
    ansible-core:
      - stable-2.17
      - stable-2.18
      - stable-2.19
      - stable-2.20
```

**Sanity ignore files:**
```
tests/sanity/ignore-2.17.txt
tests/sanity/ignore-2.18.txt
tests/sanity/ignore-2.19.txt
tests/sanity/ignore-2.20.txt
```

---

## Module Placement

### Main Modules

**Location:** `plugins/modules/`

**Naming:**
- snake_case
- No `ansible_` or collection name prefix
- Suffix: `_info` for read-only, `_action` for RPC verbs

**Examples:**
```
plugins/modules/
├── cluster_info.py          # Read-only (info)
├── cluster.py               # State-based (CRUD)
├── cluster_action.py        # RPC verbs
├── infra_env_info.py
├── infra_env.py
└── ...
```

### Module Utilities

**Location:** `plugins/module_utils/`

**Purpose:** Shared code used by multiple modules

**Example:**
```python
# plugins/module_utils/assisted_installer.py
def request(module, method, path, token, **kwargs):
    """Shared HTTP request wrapper."""
    ...
```

**Import in modules:**
```python
from ansible_collections.openshift_lab.assisted_installer.plugins.module_utils import (
    assisted_installer as ai,
)
```

---

## Test Placement

### Unit Tests

**Location:** `tests/unit/plugins/modules/`

**Structure:**
```
tests/unit/plugins/modules/
├── ansible_helpers.py      # Shared test utilities
├── conftest.py             # pytest configuration
├── test_cluster_info.py
├── test_infra_env.py
└── ...
```

**Naming:** `test_<module_name>.py`

### Integration Tests

**Location:** `tests/integration/targets/<module_name>/`

**Structure:**
```
tests/integration/targets/cluster_info/
├── tasks/
│   └── main.yml           # Test playbook
├── defaults/
│   └── main.yml           # Test variables
└── meta/
    └── main.yml           # Dependencies
```

### Sanity Configuration

**Location:** `tests/sanity/ignore-<version>.txt`

**One file per ansible-core version:**
```
tests/sanity/
├── ignore-2.17.txt
├── ignore-2.18.txt
├── ignore-2.19.txt
└── ignore-2.20.txt
```

**Format:** `path/to/file.py error-code`

**Example:**
```
plugins/modules/legacy_module.py use-argspec-type-path
```

---

## Documentation Placement

### Collection-Level Docs

**README.md:** Collection overview, installation, basic usage

**CONTRIBUTING.md:** How to contribute (setup, workflow, standards)

**SECURITY.md:** Security policy, vulnerability reporting

**DESIGN.md:** Architecture decisions, patterns, rationale

**CLAUDE.md:** Claude Code project guidance

### Additional Documentation

**Location:** `docs/`

**Examples:**
```
docs/
├── api-endpoint-map.md          # API → module mapping
├── testing-cheat-sheet.md       # Quick testing reference
├── module-workflow-guide.md     # Module development workflow
├── lessons-learned.md           # Process improvements
└── skill-development-roadmap.md # Skill tracking
```

---

## Changelog Management

### Changelog Fragments

**Location:** `changelogs/fragments/`

**Naming:** `<pr-number>-<type>.yml`

**Example:** `changelogs/fragments/10-feat.yml`
```yaml
---
minor_changes:
  - "cluster_info - new info module for querying clusters"
```

### Changelog Config

**Location:** `changelogs/config.yaml`

```yaml
---
changelog_filename_template: CHANGELOG-%s.md
changelog_filename_version_depth: 0
changes_file: changelog.yaml
changes_format: combined
keep_fragments: false
mention_ancestor: true
new_plugins_after_name: removed_features
notesdir: fragments
prelude_section_name: release_summary
prelude_section_title: Release Summary
sanitize_changelog: true
sections:
  - - major_changes
    - Major Changes
  - - minor_changes
    - Minor Changes
  - - breaking_changes
    - Breaking Changes / Porting Guide
  - - deprecated_features
    - Deprecated Features
  - - removed_features
    - Removed Features (previously deprecated)
  - - security_fixes
    - Security Fixes
  - - bugfixes
    - Bugfixes
  - - known_issues
    - Known Issues
title: openshift_lab.assisted_installer
trivial_section_name: trivial
use_fqcn: true
```

---

## Git Configuration

### .gitignore

**Collection-specific ignores:**
```
*.tar.gz
.cache/
tests/output/
__pycache__/
*.pyc
.pytest_cache/
.coverage
htmlcov/
*.retry
```

### .githooks/

**Pre-commit hooks:**
```
.githooks/
└── pre-commit    # Block commits to main
```

**Install:** `./scripts/install-hooks.sh`

---

## Where Things Go: Quick Reference

| Item | Location |
|------|----------|
| Modules | `plugins/modules/` |
| Shared utilities | `plugins/module_utils/` |
| Unit tests | `tests/unit/plugins/modules/` |
| Integration tests | `tests/integration/targets/<name>/` |
| Collection metadata | `galaxy.yml` |
| ansible-core support | `meta/runtime.yml` |
| Collection README | `README.md` (root) |
| Design decisions | `DESIGN.md` |
| API documentation | `docs/` |
| Changelog fragments | `changelogs/fragments/` |
| CI workflows | `.github/workflows/` |
| License | `LICENSE` |
| Security policy | `SECURITY.md` |

---

## Building and Installing

### Build Collection

```bash
# From collection root
ansible-galaxy collection build

# Output: namespace-name-version.tar.gz
```

### Install Locally

```bash
# Install from tarball
ansible-galaxy collection install openshift_lab-assisted_installer-0.1.0.tar.gz

# Install from directory (development)
ansible-galaxy collection install .
```

### Verify Installation

```bash
# List installed collections
ansible-galaxy collection list

# View module docs
ansible-doc openshift_lab.assisted_installer.cluster_info
```

---

## Common Mistakes

### ❌ Wrong namespace/name path

```
# ❌ WRONG
ansible_collections/my_namespace/my_collection/
# galaxy.yml: namespace: other_namespace

# ✅ CORRECT
ansible_collections/my_namespace/my_collection/
# galaxy.yml: namespace: my_namespace, name: my_collection
```

### ❌ Missing meta/runtime.yml

```
ERROR: Collection must have meta/runtime.yml
```

**Fix:** Create `meta/runtime.yml` with `requires_ansible`

### ❌ Sanity ignore files out of sync

```
# ❌ CI tests ansible-core 2.20, but no ignore-2.20.txt exists
```

**Fix:** Add `tests/sanity/ignore-2.20.txt` (even if empty)

### ❌ Module in wrong directory

```
# ❌ WRONG
modules/my_module.py

# ✅ CORRECT
plugins/modules/my_module.py
```

---

## Validation Checklist

Before publishing:

- [ ] `galaxy.yml` exists with correct namespace/name
- [ ] `meta/runtime.yml` exists with `requires_ansible`
- [ ] Namespace/name match directory path
- [ ] LICENSE file matches `galaxy.yml` license field
- [ ] README.md exists
- [ ] Modules in `plugins/modules/`
- [ ] Tests in `tests/unit/` and `tests/integration/`
- [ ] Sanity ignore files for each supported ansible-core version
- [ ] CI tests all supported ansible-core versions
- [ ] Collection builds: `ansible-galaxy collection build`
- [ ] Collection installs: `ansible-galaxy collection install *.tar.gz`

---

## Reference

- [Developing Collections](https://docs.ansible.com/projects/ansible/latest/dev_guide/developing_collections.html)
- [Collection Structure](https://docs.ansible.com/projects/ansible/latest/dev_guide/developing_collections_structure.html)
- [galaxy.yml Reference](https://docs.ansible.com/projects/ansible/latest/dev_guide/collections_galaxy_meta.html)
- This project: `galaxy.yml`, `meta/runtime.yml`, `DESIGN.md`
