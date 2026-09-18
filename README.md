# openshift_lab.assisted_installer

Ansible modules for the OpenShift **Assisted Installer** API
(`https://api.openshift.com/api/assisted-install/v2`).

> **Status:** Active development. **4 of 7 Phase 1 modules complete.**  
> See [project board](https://github.com/users/vjayaramrh/projects/2) for progress and [DESIGN.md](DESIGN.md) for scope.

## Modules Implemented

**Phase 1 (in progress):**
- ✅ `openshift_version_info` - Query available OpenShift versions
- ✅ `supported_operator_info` - List supported operators  
- ✅ `infra_env` - Manage infrastructure environments (state-based, reference implementation)
- ✅ `host_action` - Host lifecycle actions (bind, unbind, install, reset)
- 🏗️ `cluster_info` - Query cluster information (next)
- ⏳ `support_level_info` - Architecture and feature support levels
- ⏳ `cluster` - Manage clusters (state-based)

See [docs/api-endpoint-map.md](docs/api-endpoint-map.md) for complete Phase 1 & 2 scope (81 API operations mapped).

## Quick start

Everything runs in a container — the only host dependency is **Docker or Podman**.

```bash
./run.sh            # build the image and open a shell
./run.sh --check    # build + sanity + units (fast verification)
```

See [SETUP.md](SETUP.md) for details.

## Requirements

- Docker or Podman (for the containerized workflow above)
- A Red Hat account on https://console.redhat.com
- An offline token from https://console.redhat.com/openshift/token
- `ansible-core` >= 2.17 (provided inside the container)

## Authentication

Provide a token via environment (or, later, module params):

```bash
export AI_OFFLINE_TOKEN=...   # offline token; refreshed to an access token, or
export AI_API_TOKEN=...       # a short-lived access token
```

Never commit tokens or pull secrets.

## Layout

```
cld_ai/
├── run.sh                     # one entry point (Docker/Podman)
├── SETUP.md                   # containerized workflow
├── galaxy.yml                 # collection metadata (openshift_lab.assisted_installer)
├── meta/runtime.yml           # requires_ansible
├── CLAUDE.md                  # design + implementation conventions
├── DESIGN.md                  # scope, phasing, per-resource idempotency
├── .devcontainer/             # Dockerfile + devcontainer.json
├── scripts/smoke.sh           # verification suite (run.sh --check/--full)
├── plugins/
│   ├── module_utils/          # shared auth / url / fetch_url client
│   └── modules/               # (modules land here)
├── tests/
│   ├── sanity/                # per-version ignore files
│   └── unit/                  # mocked unit tests
└── .github/workflows/ci.yml   # sanity + units matrix
```

## Contributing

**New contributors:** Start with [docs/contributor-quick-start.md](docs/contributor-quick-start.md) - step-by-step tutorial from zero to first PR.

**Project board:** https://github.com/users/vjayaramrh/projects/2 - claim an issue before starting.

**Workflow:**
- Test-Driven Development (TDD) recommended: tests first, then module
- See [CONTRIBUTING.md](CONTRIBUTING.md) for complete process

## Developing

**Conventions:** [CLAUDE.md](CLAUDE.md) (workflow, verification checklist)  
**Architecture:** [DESIGN.md](DESIGN.md) (idempotency patterns, scope, phasing)

**Recommended workflow (Test-Driven Development):**
1. Document assumptions in issue (get user confirmation)
2. Generate tests first (based on OpenAPI spec verification)
3. Get tests approved
4. Generate module to satisfy approved tests

**Scaffold modules (with Claude Code):**
```
/new-ai-endpoint-module      # this API's base URL, auth, idempotency patterns
/new-ansible-module          # generic scaffold
```

**Keep `main` green:**
```bash
./run.sh --check    # build + sanity + units + coverage (≥90%)
```

## License

GPL-3.0-or-later.
