# openshift_lab.assisted_installer

Ansible modules for the OpenShift **Assisted Installer** API
(`https://api.openshift.com/api/assisted-install/v2`).

> **Status:** scaffold. No modules implemented yet — see [DESIGN.md](DESIGN.md)
> for scope and phasing.

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

## Developing

Conventions are in [CLAUDE.md](CLAUDE.md); scope/idempotency in [DESIGN.md](DESIGN.md).
Fastest way to add a module (with Claude Code):

```
/new-ai-endpoint-module      # this API's base URL, auth, GET→PATCH idempotency
/new-ansible-module          # generic scaffold
```

Keep `main` green:

```bash
ansible-test sanity
ansible-test units
```

## License

GPL-3.0-or-later.
