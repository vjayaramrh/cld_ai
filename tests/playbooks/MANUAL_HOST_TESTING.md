# Manual Testing Guide: host_action Module

**⚠️ WARNING:** This requires real hardware or VMs. Not automatable without infrastructure.

---

## Prerequisites

### 1. Create a Cluster
You need an existing cluster to bind hosts to.

```bash
# Use the OpenShift console or ocm CLI to create a cluster
# Get the cluster_id for use below
```

### 2. Create an Infra-Env
```bash
./run.sh shell
# Inside container:
ansible-galaxy collection build --force
ansible-galaxy collection install openshift_lab-assisted_installer-*.tar.gz --force

# Create infra-env bound to your cluster
cat > /tmp/create-infra-env.yml <<'EOF'
---
- hosts: localhost
  gather_facts: false
  vars:
    api_token: "{{ lookup('env', 'AI_API_TOKEN') }}"
    pull_secret: "{{ lookup('file', '../../pull_secret.json') }}"
    cluster_id: "YOUR-CLUSTER-ID-HERE"
  tasks:
    - name: Create infra-env for testing
      openshift_lab.assisted_installer.infra_env:
        state: present
        name: "test-host-actions"
        cluster_id: "{{ cluster_id }}"
        pull_secret: "{{ pull_secret }}"
        openshift_version: "4.16"
        cpu_architecture: "x86_64"
        image_type: "full-iso"
        api_token: "{{ api_token }}"
      register: result

    - debug:
        msg: |
          Download ISO:
          {{ result.infra_env.download_url }}

          Boot a VM with this ISO to discover a host.
EOF

ansible-playbook /tmp/create-infra-env.yml
```

### 3. Boot a VM with the Discovery ISO

1. Download the ISO from the URL shown above
2. Boot a VM (or bare metal) with it
3. Wait ~2-5 minutes for the host to discover itself
4. Get the host_id from the API

```bash
# List hosts in your infra-env
cat > /tmp/list-hosts.yml <<'EOF'
---
- hosts: localhost
  gather_facts: false
  vars:
    api_token: "{{ lookup('env', 'AI_API_TOKEN') }}"
    infra_env_id: "YOUR-INFRA-ENV-ID"
  tasks:
    - name: List hosts
      uri:
        url: "https://api.openshift.com/api/assisted-install/v2/infra-envs/{{ infra_env_id }}/hosts"
        method: GET
        headers:
          Authorization: "Bearer {{ api_token }}"
        return_content: true
      register: hosts

    - debug:
        msg: "{{ hosts.json }}"
EOF

ansible-playbook /tmp/list-hosts.yml
```

---

## Test host_action Module

Once you have a discovered host:

### Test 1: Bind Host to Cluster

```yaml
---
- hosts: localhost
  gather_facts: false
  vars:
    api_token: "{{ lookup('env', 'AI_API_TOKEN') }}"
  tasks:
    - name: Bind host to cluster
      openshift_lab.assisted_installer.host_action:
        action: bind
        infra_env_id: "YOUR-INFRA-ENV-ID"
        host_id: "YOUR-HOST-ID"
        cluster_id: "YOUR-CLUSTER-ID"
        api_token: "{{ api_token }}"
      register: result

    - debug:
        var: result
```

**Expected:**
- First run: `changed=true` (host bound)
- Second run: `changed=false` (already bound, idempotency)

---

### Test 2: Unbind Host

```yaml
- name: Unbind host from cluster
  openshift_lab.assisted_installer.host_action:
    action: unbind
    infra_env_id: "YOUR-INFRA-ENV-ID"
    host_id: "YOUR-HOST-ID"
    api_token: "{{ api_token }}"
  register: result
```

**Expected:**
- First run: `changed=true` (host unbound)
- Second run: `changed=false` (already unbound)

---

### Test 3: Install (Requires Validated Host)

**⚠️ WARNING:** This actually starts OpenShift installation on the host!

```yaml
- name: Install OpenShift on host
  openshift_lab.assisted_installer.host_action:
    action: install
    infra_env_id: "YOUR-INFRA-ENV-ID"
    host_id: "YOUR-HOST-ID"
    api_token: "{{ api_token }}"
  register: result
```

**Expected:**
- Host must be bound, validated, and cluster ready
- `changed=true` (install started)
- Monitor progress via OpenShift console

---

### Test 4: Reset

```yaml
- name: Reset host
  openshift_lab.assisted_installer.host_action:
    action: reset
    infra_env_id: "YOUR-INFRA-ENV-ID"
    host_id: "YOUR-HOST-ID"
    api_token: "{{ api_token }}"
  register: result
```

**Expected:**
- `changed=true` (host reset)
- Host returns to discovery state

---

## Why This is Manual

**Challenges:**
1. **Infrastructure Required:** Need VMs or bare metal
2. **Time:** Discovery takes 2-5 minutes
3. **Cost:** VMs cost money, bare metal requires hardware
4. **State Management:** Hosts go through complex state transitions
5. **Not Automatable:** Can't easily boot/destroy VMs in CI

**Recommendation:** Rely on unit tests (94% coverage) unless you have a dedicated test lab.

---

## Alternative: Integration Test Environment

If you have a lab environment with automated VM provisioning (libvirt, VMware, etc.), you could:

1. Script VM creation
2. Boot with discovery ISO
3. Wait for discovery
4. Run host_action tests
5. Clean up VMs

This is **out of scope** for basic module testing but could be added as an advanced integration test suite.
