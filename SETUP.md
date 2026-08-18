# SETUP — running everything in a container

The only host dependency is **Docker or Podman**. All development, testing, and
building happen inside a container, so there is nothing else to install.

## Quick start

```bash
./run.sh            # build the image, open an interactive shell
./run.sh --check    # build + fast verification (collection build + sanity + units)
./run.sh --full     # build + deep verification (adds the install round-trip)
```

`run.sh` auto-detects Podman or Docker (and starts the Podman machine on macOS if
needed), builds the image, bind-mounts this repo into the required
`ansible_collections/openshift_lab/assisted_installer/` path, and runs from there.

## What `--check` verifies

- `ansible-galaxy collection build` — this is a valid, buildable collection
- `ansible-test sanity`
- `ansible-test units` — skipped until unit tests exist, then run automatically

Expect `passed: N failed: 0`. `--full` also installs the built tarball to confirm
the round-trip.

## Inside the shell

```bash
ansible-test sanity          # docs/spec/style checks
ansible-test units           # unit tests (once they exist)
ansible-galaxy collection build --force --output-path /tmp
```

`ansible-test` runs without `--docker` because you are already in the container.
(CI on GitHub uses `--docker` for isolation — same tests, right context.)

## Notes

- Podman rootless is handled with `--userns=keep-id`, SELinux `:Z`, and a writable
  `HOME=/tmp`.
- Never put real tokens or pull secrets in the repo; pass them via environment
  (`AI_OFFLINE_TOKEN` / `AI_API_TOKEN`).
