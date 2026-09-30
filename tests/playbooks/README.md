# Playbook Testing for Info Modules

This directory contains playbooks for testing Ansible modules against the live OpenShift Assisted Installer API.

## Prerequisites

### 1. Get an API Token

You need an API token from Red Hat to test against the live API.

**Option A: Offline Token (Recommended - Auto-Refresh)**
Get your offline token once, never worry about expiry:

1. Get offline token: https://console.redhat.com/openshift/token
2. Put it in `offline.token` file:
   ```bash
   echo "your-offline-token-here" > offline.token
   ```
3. Run tests - fresh token auto-generated every time:
   ```bash
   ./run.sh test-playbook
   ```

**Offline tokens are long-lived (30 days)** and automatically exchanged for fresh 15-minute access tokens on every run.

**Option B: Direct Access Token**
If you have a short-lived access token:
```bash
echo "your-access-token-here" > api.token
./run.sh test-playbook
```

**Note:** You'll need to update `api.token` every 15 minutes as tokens expire.

**Option C: Environment Variable**
```bash
export AI_API_TOKEN="your-access-token-here"
./run.sh test-playbook
```

**Token Priority:**
1. `AI_API_TOKEN` environment variable (if set)
2. `offline.token` file → auto-exchange for fresh access token
3. `api.token` file (may be expired)

**Security Note:** Never commit tokens to git. Both `*.token` files are in `.gitignore`.

---

### 2. Get a Pull Secret (for State/Action Module Tests Only)

**Info modules** (read-only) don't need a pull secret. **State/action modules** (create/modify resources) require one.

**Option A: Pull Secret File (Recommended)**

1. Get your pull secret: https://console.redhat.com/openshift/install/pull-secret
2. Save it to `pull_secret.json` in the repo root:
   ```bash
   # From Red Hat console, copy the JSON and save it
   cat > pull_secret.json
   # Paste the JSON: {"auths":{"cloud.openshift.com":{...}}}
   # Press Ctrl+D to save
   ```
3. Run tests - the playbook will automatically load it

**Option B: Environment Variable**
```bash
export PULL_SECRET='{"auths":{"cloud.openshift.com":{...}}}'
./run.sh shell
```

**Pull Secret Priority:**
1. `pull_secret.json` file (recommended - survives shell restarts)
2. `PULL_SECRET` environment variable

**Security Note:** The `pull_secret.json` file is git-ignored (pattern: `pull_secret*` in `.gitignore`).

---

## Running Tests

### Quick Test (Info Modules Only)

Tests read-only info modules against the live API:

```bash
AI_API_TOKEN="your-token" ./run.sh test-playbook
```

**What this tests:**
- ✅ `openshift_version_info` - List versions, query specific version
- ✅ `supported_operator_info` - List operators, query by name
- ✅ Idempotency (changed=false for reads)
- ✅ Response shape validation

**Safe:** Only reads data, no mutations.

---

## Test Playbook Details

### File: `test-info-modules.yml`

**Tests performed:**
1. List all OpenShift versions
2. Query specific version (4.16)
3. List all supported operators
4. Query specific operator (lvm)
5. Idempotency verification (run twice, compare results)

**Assertions:**
- Returns expected fields (`versions`, `operators`)
- `changed=false` for all reads
- Same results on repeated runs
- Proper error handling

---

## Manual Testing in Shell

If you prefer manual testing:

```bash
# 1. Enter container shell
AI_API_TOKEN="your-token" ./run.sh shell

# 2. Inside container, build and install collection
ansible-galaxy collection build --force
ansible-galaxy collection install openshift_lab-assisted_installer-*.tar.gz --force

# 3. Create a quick test playbook
cat > /tmp/test.yml <<'EOF'
---
- hosts: localhost
  gather_facts: false
  tasks:
    - openshift_lab.assisted_installer.openshift_version_info:
        api_token: "{{ lookup('env', 'AI_API_TOKEN') }}"
      register: result
    - debug: var=result
EOF

# 4. Run it
ansible-playbook /tmp/test.yml
```

**Token Expiry in Shell Sessions:**

Access tokens expire after **15 minutes**. If you get HTTP 401 errors during a long
shell session, the token has expired. Tokens are only resolved when the shell starts,
not refreshed during the session.

**Fix:** Exit and re-enter the shell to get a fresh token:
```bash
# In container, exit:
exit

# Re-enter (fresh token auto-exchanged from offline.token):
./run.sh shell
```

For long debug sessions, prefer `./run.sh test-playbook` (fresh container each run)
or periodically restart your shell.

---

## Troubleshooting

### Error: "AI_API_TOKEN environment variable is required"

**Cause:** Token not set or not passed to container.

**Fix:**
```bash
# Set token first
export AI_API_TOKEN="your-token-here"

# Then run
./run.sh test-playbook
```

### Error: "Failed to authenticate"

**Cause:** Token expired or invalid.

**Fix:** Get a fresh token from Red Hat SSO (see Prerequisites above).

### Error: "Module not found"

**Cause:** Collection not installed correctly.

**Fix:** The `test-playbook.sh` script handles this automatically. If running manually, ensure you ran `ansible-galaxy collection install`.

---

## Next Steps

Once info modules pass:
1. **State modules testing** - Requires mock server (no live mutations)
2. **Action modules testing** - Requires mock server (no live mutations)
3. **Integration tests** - Full lifecycle testing with mock API

See `CLAUDE.md` testing section for details on mock server setup.
