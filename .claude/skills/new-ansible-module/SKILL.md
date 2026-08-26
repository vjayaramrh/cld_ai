---
name: new-ansible-module
description: Scaffold a new custom Ansible module in Python that passes `ansible-test sanity` on the first try. Generates the module file (GPL header, DOCUMENTATION/EXAMPLES/RETURN doc blocks, argument_spec, an idempotent + check-mode-aware run_module) plus a pytest unit test (create / idempotency / check-mode cases, fetch_url mocked) and the conftest/helpers, inside a collection. Use whenever someone wants to write, create, generate, or start a custom Ansible module / plugin — keywords: AnsibleModule, argument_spec, module_utils, ansible-test units/sanity, idempotency, check_mode, fetch_url, collection, galaxy.
---

# Scaffold a new custom Ansible module

Portable skill: works in any repo, not just the workshop it shipped with. Produces a
module that is idempotent, check-mode-aware, documented, and passes `ansible-test
sanity` + `ansible-test units`. All templates are inline — nothing to copy from
elsewhere.

## Conventions (non-negotiable — these prevent real sanity failures)

1. **Standard header** with the GPLv3 line in the first 20 lines (sanity requires it).
2. **All three doc blocks** — `DOCUMENTATION`, `EXAMPLES`, `RETURN`; `options:` must
   match `argument_spec` **exactly**. `EXAMPLES` must be **thorough for the module
   kind**, not a single stub (see the template below).
3. **Valid author**: `author:\n  - Name (@githubhandle)` (bare names fail sanity).
4. **`no_log=False`** on any arg *named* like a secret (`key`/`password`/`token`/…)
   that isn't actually secret.
5. **Idempotent**: observe → compare → act; `changed=True` only on real change.
6. **Check mode**: `supports_check_mode=True`, and never mutate when `module.check_mode`.
7. **Finish only** via `module.exit_json(...)` / `module.fail_json(msg=...)`.
8. **HTTP** via `ansible.module_utils.urls.fetch_url` — never `requests`.

## 1. Gather what you can't guess

- **Module name** (snake_case).
- **Collection** as `namespace.name` (reuse one that exists, or create a new tree).
- **Arguments**: name, type (`str`/`bool`/`int`/`list`/`dict`), required?, default, choices.
- **Shape**: **state-based** (`state: present/absent`) or **value-based** (ensure a
  setting equals a desired value)? This picks the idempotency skeleton.

If the collection doesn't exist, also create `galaxy.yml` (namespace/name MUST match
the directory path) and a `README.md`.

## 2. Files to create

```
ansible_collections/<namespace>/<name>/
├── galaxy.yml                       # if new collection
├── plugins/modules/<module>.py
└── tests/unit/plugins/modules/
    ├── ansible_helpers.py           # from template in §5
    ├── conftest.py                  # from template in §5
    └── test_<module>.py             # from template in §4
```

> In the workshop repo you can instead copy `ansible_helpers.py`/`conftest.py` from
> `solutions/session-3/.../tests/unit/plugins/modules/` — they're identical to §5.

## 3. Module template

```python
#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, <Author>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: <module>
short_description: <one line, no trailing period>
description:
  - <what it does>
options:
  <arg>:
    description: <...>
    required: <true|false>
    type: <str|bool|int|list|dict>
    # choices: [a, b]
    # default: <...>
author:
  - <Name> (@<githubhandle>)
'''

EXAMPLES = r'''
# Thorough for the module's kind — do NOT ship a single stub.
# Every task has a meaningful name:; secrets come from a var/env, never a literal.
#
# info kind: basic query + filtered query (if any filters) + use the result:
- name: <query the resource>
  <namespace>.<name>.<module>:
    <filter_arg>: <value>
  register: result
- name: <use the registered result>
  ansible.builtin.debug:
    var: result.<key>
#
# state kind: create + update + delete + check-mode; note 2nd run is changed=false:
- name: <ensure present (create)>
  <namespace>.<name>.<module>:
    name: <name>
    state: present
- name: <update a field (re-running unchanged reports changed=false)>
  <namespace>.<name>.<module>:
    name: <name>
    <field>: <new value>
    state: present
- name: <ensure absent (delete)>
  <namespace>.<name>.<module>:
    name: <name>
    state: absent
#
# action kind: each representative verb, showing the status it guards on:
- name: <perform the action when in the expected state>
  <namespace>.<name>.<module>:
    name: <name>
    action: <verb>
'''

RETURN = r'''
<key>:
  description: <...>
  returned: always
  type: <str|bool|...>
'''

from ansible.module_utils.basic import AnsibleModule
# from ansible.module_utils.urls import fetch_url   # if the module talks HTTP


def run_module():
    module = AnsibleModule(
        argument_spec=dict(
            # arg=dict(type="str", required=True),
            # keyish=dict(type="str", required=True, no_log=False),
        ),
        supports_check_mode=True,
    )

    # 1. OBSERVE current state
    # 2. COMPARE to desired; honest no-op if already correct:
    #    module.exit_json(changed=False, ...)
    # 3. CHECK MODE: change needed but don't act:
    #    if module.check_mode: module.exit_json(changed=True, ...)
    # 4. ACT (wrap side effects; module.fail_json(msg=...) on error)

    module.exit_json(changed=True)


if __name__ == "__main__":
    run_module()
```

**State-based** (`present`/`absent`): observe existence → `need_change = (not exists)
if state == "present" else exists` → no-op if not needed → check mode → create/delete.
**Value-based**: read current value → no-op if it already equals desired → check mode
→ write.

## 4. Unit test template

Always include **create/act**, **idempotency**, and **check-mode** cases. Mock network
with `monkeypatch.setattr(<module>, "fetch_url", fake)` (patch the name where it's
*used* — inside your module).

```python
import pytest
from ansible_helpers import (
    AnsibleExitJson, AnsibleFailJson, set_module_args, patch_ansible,
)
from ansible_collections.<namespace>.<name>.plugins.modules import <module>


@pytest.fixture(autouse=True)
def _patch(monkeypatch):
    patch_ansible(monkeypatch)


def test_makes_change(...):
    set_module_args({...})
    with pytest.raises(AnsibleExitJson) as exc:
        <module>.run_module()
    assert exc.value.result["changed"] is True


def test_idempotent_second_run(...):
    # run twice with same args; assert first changed True, second False
    ...


def test_check_mode_no_side_effect(...):
    set_module_args({..., "_ansible_check_mode": True})
    with pytest.raises(AnsibleExitJson) as exc:
        <module>.run_module()
    assert exc.value.result["changed"] is True
    # assert the side effect did NOT happen
```

## 5. Test harness templates (inline — copy verbatim)

`tests/unit/plugins/modules/ansible_helpers.py`:

```python
"""Unit-test helpers (args + exit/fail capture)."""
import json

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes


class AnsibleExitJson(Exception):
    def __init__(self, result):
        self.result = result
        super().__init__(result.get("msg", "exit_json"))


class AnsibleFailJson(Exception):
    def __init__(self, result):
        self.result = result
        super().__init__(result.get("msg", "fail_json"))


def set_module_args(args):
    basic._ANSIBLE_ARGS = to_bytes(json.dumps({"ANSIBLE_MODULE_ARGS": args}))
    # ansible-core 2.19+ requires a serialization profile alongside the args buffer
    if hasattr(basic, "_ANSIBLE_PROFILE"):
        basic._ANSIBLE_PROFILE = "legacy"


def exit_json(self, **kwargs):
    kwargs.setdefault("changed", False)
    raise AnsibleExitJson(kwargs)


def fail_json(self, **kwargs):
    kwargs["failed"] = True
    raise AnsibleFailJson(kwargs)


def patch_ansible(monkeypatch):
    monkeypatch.setattr(basic.AnsibleModule, "exit_json", exit_json)
    monkeypatch.setattr(basic.AnsibleModule, "fail_json", fail_json)
```

`tests/unit/plugins/modules/conftest.py` (makes plain `pytest` resolve imports; walks
up to `ansible_collections/` so tree depth doesn't matter):

```python
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_d = HERE
while _d != os.path.dirname(_d):
    if os.path.basename(_d) == "ansible_collections":
        sys.path.insert(0, os.path.dirname(_d))
        break
    _d = os.path.dirname(_d)
```

## 6. Verify (do not stop until green)

From the collection directory:

```bash
python -m pytest tests/unit/plugins/modules/test_<module>.py -v
ansible-test sanity --test validate-modules plugins/modules/<module>.py
ansible-test units  --python 3.12 tests/unit/plugins/modules/test_<module>.py
```

`ansible-test units` needs `pytest-xdist` installed (it runs `-n auto`). Fix every
sanity finding (the usual ones: GPL header, `author` format, `no_log`, docs↔spec
mismatch). In the workshop repo you can run `./run.sh --check` / `--full`, and add the
module to `scripts/smoke.sh` so CI covers it.
