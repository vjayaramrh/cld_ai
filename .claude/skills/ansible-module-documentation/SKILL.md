---
name: ansible-module-documentation
description: Comprehensive guide to Ansible module documentation standards - DOCUMENTATION, EXAMPLES, and RETURN blocks. Covers required fields, markup syntax (C(), O(), V(), etc.), elements attribute for lists, return type consistency, and module-type-specific example requirements. Use before writing module docs or when fixing documentation issues.
---

# Ansible Module Documentation Standards

Complete reference for documenting Ansible modules correctly, based on the [official Ansible documentation guide](https://docs.ansible.com/projects/ansible/latest/dev_guide/developing_modules_documenting.html).

## Overview

Every Ansible module MUST have three documentation blocks:
1. **DOCUMENTATION** - Module metadata, parameters, requirements
2. **EXAMPLES** - Real-world usage examples
3. **RETURN** - Return value schemas

---

## DOCUMENTATION Block

### Required Fields

```yaml
DOCUMENTATION = r"""
---
module: module_name
short_description: Brief overview without trailing period
version_added: "1.0.0"  # For collections, or "2.18" for ansible-core
description:
  - Detailed explanation in full sentences with periods.
  - Can be multiple paragraphs.
author:
  - Full Name (@githubhandle)
options:
  param_name:
    description: Param explanation with period.
    type: str
    required: false
    default: null
"""
```

### Optional But Important Fields

```yaml
requirements:
  - "python >= 3.9"
  - "requests library"
notes:
  - Important caveats or warnings.
  - Unexpected behavior to document.
seealso:
  - module: ansible.builtin.debug
    description: Related module.
  - name: External API
    description: API documentation.
    link: https://api.example.com/docs
```

### Short Description Rules

**CRITICAL:**
- ❌ **NO trailing period**
- ✅ Capitalized first word
- ✅ Under 80 characters
- ✅ Present tense, active voice

```yaml
# ✅ CORRECT
short_description: List OpenShift clusters from the Assisted Installer

# ❌ WRONG
short_description: list openshift clusters.
```

---

## Options Documentation

### Basic Option Structure

```yaml
options:
  api_token:
    description:
      - A short-lived API access token.
      - Second paragraph if needed.
    type: str
    required: false
    default: null
```

### Type Declarations

**For list-type options, ALWAYS specify `elements`:**

```yaml
cluster_ids:
  description: List of cluster identifiers.
  type: list
  elements: str     # ← REQUIRED for lists
  required: false
```

**Valid element types:** `str`, `dict`, `int`, `float`, `bool`, `path`, `raw`

### Environment Variable Fallbacks

**For modules (NOT plugins), document in description:**

```yaml
api_token:
  description:
    - Short-lived API token.
    - If not set, the value of environment variable E(AI_API_TOKEN) is used.
  type: str
```

**In code (argument_spec):**
```python
api_token=dict(
    type="str",
    no_log=True,
    fallback=(env_fallback, ["AI_API_TOKEN"])
)
```

**Note:** The `env:` keyword is for **plugins only**, not modules.

### Boolean Options

```yaml
enable_feature:
  description: Whether to enable the feature.
  type: bool
  default: false
  # ❌ Do NOT add choices: [true, false] for bool types
```

### Secret Parameters

```yaml
password:
  description: Database password.
  type: str
  required: true
  no_log: true    # ← Prevents logging
```

---

## EXAMPLES Block

### Thoroughness By Module Type

#### Info Modules
**MUST include:**
1. Basic query (no filters)
2. Filtered query (if module has filter params)
3. Registering and using the result

```yaml
EXAMPLES = r"""
- name: List all clusters
  openshift_lab.assisted_installer.cluster_info:
    api_token: "{{ token }}"
  register: all_clusters

- name: Filter clusters by owner
  openshift_lab.assisted_installer.cluster_info:
    owner: "user@example.com"
    api_token: "{{ token }}"
  register: filtered

- name: Use the result
  ansible.builtin.debug:
    msg: "Found {{ all_clusters.clusters | length }} clusters"
"""
```

#### State Modules
**MUST include:**
1. Create (state: present, resource doesn't exist)
2. Update (state: present, resource exists, field changes)
3. Delete (state: absent)
4. Check mode example
5. Comment noting second run is `changed=false`

```yaml
EXAMPLES = r"""
- name: Create infra-env (changed=true first time)
  openshift_lab.assisted_installer.infra_env:
    name: lab-infra
    pull_secret: "{{ secret }}"
    state: present

# Running identical task again: changed=false (idempotent)

- name: Update image type (changed=true only if drifted)
  openshift_lab.assisted_installer.infra_env:
    name: lab-infra
    pull_secret: "{{ secret }}"
    image_type: full-iso
    state: present

- name: Preview change without applying (check mode)
  openshift_lab.assisted_installer.infra_env:
    name: lab-infra
    pull_secret: "{{ secret }}"
    image_type: disconnected-iso
    state: present
  check_mode: true

- name: Delete infra-env (changed=false if already gone)
  openshift_lab.assisted_installer.infra_env:
    name: lab-infra
    state: absent
"""
```

#### Action Modules
**MUST include:**
1. Each action verb
2. Status precondition for each action
3. Check mode example

```yaml
EXAMPLES = r"""
- name: Bind host to cluster (requires discovered/known status)
  openshift_lab.assisted_installer.host_action:
    action: bind
    infra_env_id: "{{ env_id }}"
    host_id: "{{ host_id }}"
    cluster_id: "{{ cluster_id }}"

- name: Unbind host from cluster
  openshift_lab.assisted_installer.host_action:
    action: unbind
    infra_env_id: "{{ env_id }}"
    host_id: "{{ host_id }}"

- name: Check if action would change anything
  openshift_lab.assisted_installer.host_action:
    action: bind
    infra_env_id: "{{ env_id }}"
    host_id: "{{ host_id }}"
    cluster_id: "{{ cluster_id }}"
  check_mode: true
  register: bind_check
"""
```

### Example Quality Standards

**Every example task MUST have:**
- ✅ Meaningful `name:` field (capitalized, no period)
- ✅ Fully qualified collection name (FQCN)
- ✅ Secrets from variables, **never** literal tokens
- ✅ Copy-paste ready (valid YAML)

---

## RETURN Block

### Basic Structure

```yaml
RETURN = r"""
resource:
  description:
    - The resource object after the operation.
    - Empty dict if resource doesn't exist.
  returned: success
  type: dict
  sample:
    id: "uuid"
    name: "example"
    status: "ready"
"""
```

### Critical Rules

#### 1. Lists MUST Have `elements`

```yaml
# ✅ CORRECT
clusters:
  description: List of cluster resources.
  returned: success
  type: list
  elements: dict    # ← REQUIRED
  sample:
    - id: "uuid-1"
      name: "cluster-1"
    - id: "uuid-2"
      name: "cluster-2"

# ❌ WRONG - Missing elements
clusters:
  type: list
  sample: [...]
```

#### 2. Return Structure Must Be Static

**Never return different types from the same key:**

```yaml
# ❌ WRONG - Polymorphic return type
supported_operators:
  description: List of operators OR properties depending on parameters.
  type: raw    # Forced to use raw because type changes

# ✅ CORRECT - Separate keys
operator_names:
  description: List of operator names.
  returned: when name parameter is omitted
  type: list
  elements: str
operator_properties:
  description: Property definitions for an operator.
  returned: when name parameter is provided
  type: list
  elements: dict
```

#### 3. Info Modules Return Lists

Even for single-item lookups:

```yaml
# ✅ CORRECT
clusters:
  description: List of clusters (even if only one matches).
  type: list
  elements: dict

# Users access with: result.clusters[0] or result.clusters | first
```

### Nested Structures

Use `contains` for nested dicts:

```yaml
cluster:
  description: Cluster resource.
  type: dict
  returned: success
  contains:
    id:
      description: Cluster identifier.
      type: str
    status:
      description: Current cluster status.
      type: str
      sample: "ready"
```

### State Module Returns

```yaml
# State modules return single resource
infra_env:
  description:
    - The infra-env after create/update.
    - Empty dict after delete or in check mode.
  returned: success
  type: dict
id:
  description: Resource ID, or null if doesn't exist.
  returned: success
  type: str
```

---

## Ansible Markup

Use these macros in descriptions, notes, and seealso:

| Macro | Purpose | Example |
|-------|---------|---------|
| `C()` | Code/literal | `C(changed=false)` |
| `O()` | Option reference | `O(state=present)` |
| `V()` | Value | `V(present)` |
| `E()` | Environment var | `E(AI_API_TOKEN)` |
| `U()` | URL | `U(https://api.example.com)` |
| `B()` | Bold | `B(important)` |

```yaml
description:
  - The module ensures O(state=present) by calling C(POST /api/resource).
  - Set O(timeout) to V(60) for slow networks.
  - Reads token from E(API_TOKEN) if not provided.
```

---

## Common Pitfalls

### ❌ Don't Do This

1. **Trailing period in short_description**
   ```yaml
   short_description: List clusters.  # ← WRONG
   ```

2. **Missing elements for lists**
   ```yaml
   clusters:
     type: list
     # Missing: elements: dict
   ```

3. **Polymorphic return types**
   ```yaml
   results:
     type: raw  # Returns str OR dict
   ```

4. **Bare author names**
   ```yaml
   author: John Smith  # ← WRONG (needs @handle)
   ```

5. **Secrets in examples**
   ```yaml
   api_token: "abc123"  # ← WRONG (use variable)
   ```

6. **Single stub example**
   ```yaml
   EXAMPLES = r"""
   - name: Do something
     my.module:
       arg: value
   """
   # ← WRONG (not thorough for module type)
   ```

### ✅ Do This Instead

1. **No trailing period**
   ```yaml
   short_description: List clusters
   ```

2. **Always specify elements**
   ```yaml
   clusters:
     type: list
     elements: dict
   ```

3. **Separate keys for different types**
   ```yaml
   resource_names:
     type: list
     elements: str
   resource_details:
     type: list
     elements: dict
   ```

4. **Author with GitHub handle**
   ```yaml
   author:
     - John Smith (@jsmith)
   ```

5. **Secrets from variables**
   ```yaml
   api_token: "{{ assisted_installer_token }}"
   ```

6. **Thorough examples**
   - See module-type sections above

---

## Testing Documentation

Before committing, test with:

```bash
# View rendered docs
ansible-doc -t module namespace.collection.module_name

# Test in collection build
ansible-galaxy collection build
```

---

## Reference

- [Ansible Module Documentation Guide](https://docs.ansible.com/projects/ansible/latest/dev_guide/developing_modules_documenting.html)
- [Ansible Documentation Markup](https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_documenting.html#module-format-and-documentation)
- This project: `docs/skill-development-roadmap.md`

---

## Quick Checklist

Before submitting module documentation:

- [ ] DOCUMENTATION block has all required fields
- [ ] short_description has NO trailing period
- [ ] author field includes GitHub handle
- [ ] List-type options have `elements` attribute
- [ ] List-type returns have `elements` attribute
- [ ] EXAMPLES are thorough for module type
- [ ] Secrets use variables, not literals
- [ ] Every task has meaningful `name:`
- [ ] RETURN structure is static (no polymorphic types)
- [ ] Tested with `ansible-doc`
