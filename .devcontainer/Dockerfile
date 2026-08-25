# Dev/CI image for the openshift_lab.assisted_installer collection.
# Everything (sanity, units, build) runs inside here — no host deps but Docker/Podman.
FROM python:3.12-slim

ARG ANSIBLE_CORE="ansible-core>=2.17,<2.20"

RUN apt-get update && apt-get install -y --no-install-recommends \
        git make vim less ca-certificates openssh-client rsync shellcheck \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
        "${ANSIBLE_CORE}" \
        "pytest>=8.0" \
        "pytest-mock>=3.12" \
        "pytest-xdist>=3.5" \
        "pyyaml>=6.0" \
        "coverage==7.6.1"

# Bind-mounted repo is owned by the host user; avoid git "dubious ownership".
RUN git config --system --add safe.directory '*'

# Non-root dev user (UID 1000 pairs with rootless podman --userns=keep-id).
RUN useradd -m -u 1000 dev
USER dev

# ansible-test must run from inside ansible_collections/<ns>/<name>/.
# run.sh bind-mounts the repo here.
WORKDIR /home/dev/ansible_collections/openshift_lab/assisted_installer
