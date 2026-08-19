# API endpoint map — `openshift_lab.assisted_installer`

Maps every operation in the Assisted Installer **v2** OpenAPI spec to its
idempotency pattern, target module, and release phase. This is the authoring
backlog and the reviewer lookup: given an endpoint, find the module; given a
module, find the endpoints it must cover.

- **Model (do not restate here):** the three idempotency patterns are defined in
  [DESIGN.md §4](../DESIGN.md); naming rules in [DESIGN.md §5](../DESIGN.md).
- **Spec source:** `https://api.openshift.com/api/assisted-install/v2/openapi`
  (Swagger 2.0, `basePath: /api/assisted-install`).
- **Snapshot:** enumerated **2026-08-19**, **81 operations**. The spec is *not*
  vendored/pinned — this map is a snapshot. If endpoints look stale, re-run the
  enumeration (see [How this was generated](#how-this-was-generated)) and diff.

## Legend — pattern column

| Pattern | Meaning | `changed` |
|---------|---------|-----------|
| **info** | Read-only GET (catalog or resource); `*_info` module | always `False` |
| **download** | Read-only GET returning an artifact/URL (ISO, kubeconfig, logs, files) — a read-only variant of *info* | always `False` |
| **state** | Declarative CRUD (`state: present/absent`), GET→POST/PATCH/DELETE | real change |
| **action** | RPC verb (`/actions/*`), guarded on current status; `*_action` module | real change |
| **agent-internal** | Called by the assisted-installer agent/host, not an operator — **out of scope**, no module | — |

Everything not `agent-internal` is a candidate module. Phase per DESIGN.md §3;
"backlog" = beyond the currently-planned Phase 1/2.

---

## Catalog / read-only (no resource state)

| Method | Path | operationId | Pattern | Module | Phase |
|--------|------|-------------|---------|--------|-------|
| GET | /v2/openshift-versions | v2ListSupportedOpenshiftVersions | info | `openshift_version_info` | 1 ✅ |
| GET | /v2/component-versions | v2ListComponentVersions | info | `component_version_info` | backlog |
| GET | /v2/release-sources | v2ListReleaseSources | info | `release_source_info` | backlog |
| GET | /v2/support-levels/architectures | GetSupportedArchitectures | info | `support_level_info` (`kind: architectures`) | 1 |
| GET | /v2/support-levels/features | GetSupportedFeatures | info | `support_level_info` (`kind: features`) | 1 |
| GET | /v2/support-levels/features/detailed | GetDetailedSupportedFeatures | info | `support_level_info` (`kind: features_detailed`) | 1 |
| GET | /v2/supported-operators | V2ListSupportedOperators | info | `supported_operator_info` | 1 |
| GET | /v2/supported-operators/{operator_name} | V2ListOperatorProperties | info | `supported_operator_info` (`name:`) | 1 |
| GET | /v2/operators/bundles | V2ListBundles | info | `operator_bundle_info` | backlog |
| GET | /v2/operators/bundles/{id} | V2GetBundle | info | `operator_bundle_info` (`id:`) | backlog |
| GET | /v2/domains | V2ListManagedDomains | info | `managed_domain_info` | backlog |
| GET | /v2/events | v2ListEvents | info | `event_info` | backlog |

## Cluster — state-based CRUD + reads

| Method | Path | operationId | Pattern | Module | Phase |
|--------|------|-------------|---------|--------|-------|
| GET | /v2/clusters | v2ListClusters | info | `cluster_info` | 1 |
| GET | /v2/clusters/{cluster_id} | v2GetCluster | info | `cluster_info` | 1 |
| POST | /v2/clusters | v2RegisterCluster | state | `cluster` (`state: present`) | 1 |
| PATCH | /v2/clusters/{cluster_id} | V2UpdateCluster | state | `cluster` (drift → PATCH) | 1 |
| DELETE | /v2/clusters/{cluster_id} | v2DeregisterCluster | state | `cluster` (`state: absent`) | 1 |
| POST | /v2/clusters/import | v2ImportCluster | state | `cluster` (import variant — open Q) | backlog |
| POST | /v2/clusters/disconnected | v2RegisterDisconnectedCluster | state | `cluster` (disconnected variant — open Q) | backlog |
| GET | /v2/clusters/default-config | V2GetClusterDefaultConfig | info | `cluster_info` / `cluster_default_config_info` | backlog |
| GET | /v2/clusters/{cluster_id}/supported-platforms | GetClusterSupportedPlatforms | info | `cluster_info` sub-read | backlog |
| GET | /v2/clusters/{cluster_id}/preflight-requirements | v2GetPreflightRequirements | info | `cluster_info` sub-read | backlog |

## Cluster — RPC actions

| Method | Path | operationId | Pattern | Module | Phase |
|--------|------|-------------|---------|--------|-------|
| POST | /v2/clusters/{cluster_id}/actions/install | v2InstallCluster | action | `cluster_action` (`action: install`) | 2 |
| POST | /v2/clusters/{cluster_id}/actions/reset | v2ResetCluster | action | `cluster_action` (`reset`) | 2 |
| POST | /v2/clusters/{cluster_id}/actions/cancel | V2CancelInstallation | action | `cluster_action` (`cancel`) | 2 |
| POST | /v2/clusters/{cluster_id}/actions/complete-installation | v2CompleteInstallation | action | `cluster_action` (`complete-installation`) | 2 |
| POST | /v2/clusters/{cluster_id}/actions/allow-add-hosts | TransformClusterToAddingHosts | action | `cluster_action` (`allow-add-hosts`) | 2 |
| POST | /v2/clusters/{cluster_id}/actions/allow-add-workers | TransformClusterToDay2 | action | `cluster_action` (`allow-add-workers`) | 2 |

## Cluster — config sub-resources (state-based)

| Method | Path | operationId | Pattern | Module | Phase |
|--------|------|-------------|---------|--------|-------|
| GET | /v2/clusters/{cluster_id}/install-config | v2GetClusterInstallConfig | info | `cluster_install_config_info` (or fold into `cluster_info`) | backlog |
| PATCH | /v2/clusters/{cluster_id}/install-config | v2UpdateClusterInstallConfig | state | fold into `cluster`, or `cluster_install_config` (open Q) | backlog |
| GET | /v2/clusters/{cluster_id}/ignored-validations | v2GetIgnoredValidations | info | `cluster_info` sub-read | backlog |
| PUT | /v2/clusters/{cluster_id}/ignored-validations | v2SetIgnoredValidations | state | fold into `cluster` (open Q) | backlog |
| GET | /v2/clusters/{cluster_id}/ui-settings | V2GetClusterUISettings | info | UI concern — likely out of scope | — |
| PUT | /v2/clusters/{cluster_id}/ui-settings | V2UpdateClusterUISettings | state | UI concern — likely out of scope | — |

## Cluster — manifests (state-based CRUD, `manifests` tag)

| Method | Path | operationId | Pattern | Module | Phase |
|--------|------|-------------|---------|--------|-------|
| GET | /v2/clusters/{cluster_id}/manifests | V2ListClusterManifests | info | `cluster_manifest_info` | backlog |
| POST | /v2/clusters/{cluster_id}/manifests | V2CreateClusterManifest | state | `cluster_manifest` (`state: present`) | backlog |
| PATCH | /v2/clusters/{cluster_id}/manifests | V2UpdateClusterManifest | state | `cluster_manifest` | backlog |
| DELETE | /v2/clusters/{cluster_id}/manifests | V2DeleteClusterManifest | state | `cluster_manifest` (`state: absent`) | backlog |
| GET | /v2/clusters/{cluster_id}/manifests/files | v2DownloadClusterManifest | download | `cluster_manifest_info` (content) | backlog |

## Cluster — downloads / credentials

| Method | Path | operationId | Pattern | Module | Phase |
|--------|------|-------------|---------|--------|-------|
| GET | /v2/clusters/{cluster_id}/credentials | V2GetCredentials | info | `cluster_credentials_info` | 2 |
| GET | /v2/clusters/{cluster_id}/downloads/credentials | V2DownloadClusterCredentials | download | `cluster_credentials_info` (kubeconfig etc.) | 2 |
| GET | /v2/clusters/{cluster_id}/downloads/credentials-presigned | V2GetPresignedForClusterCredentials | download | `cluster_credentials_info` (presigned) | 2 |
| GET | /v2/clusters/{cluster_id}/downloads/files | V2DownloadClusterFiles | download | `cluster_file_info` | backlog |
| GET | /v2/clusters/{cluster_id}/downloads/files-presigned | V2GetPresignedForClusterFiles | download | `cluster_file_info` (presigned) | backlog |
| GET | /v2/clusters/{cluster_id}/logs | V2DownloadClusterLogs | download | `cluster_logs_info` | backlog |
| GET | /v2/clusters/{cluster_id}/hosts | ListClusterHosts | info | `host_info` (by cluster) | 2 |
| GET | /v2/clusters/{cluster_id}/monitored-operators | V2ListOfClusterOperators | info | `cluster_operator_info` (or `cluster_info` sub) | backlog |

## Infra-env — state-based CRUD + reads/actions

| Method | Path | operationId | Pattern | Module | Phase |
|--------|------|-------------|---------|--------|-------|
| GET | /v2/infra-envs | ListInfraEnvs | info | `infra_env_info` | 1 |
| GET | /v2/infra-envs/{infra_env_id} | GetInfraEnv | info | `infra_env_info` | 1 |
| POST | /v2/infra-envs | RegisterInfraEnv | state | `infra_env` (`state: present`) | 1 |
| PATCH | /v2/infra-envs/{infra_env_id} | UpdateInfraEnv | state | `infra_env` | 1 |
| DELETE | /v2/infra-envs/{infra_env_id} | DeregisterInfraEnv | state | `infra_env` (`state: absent`) | 1 |
| POST | /v2/infra-envs/{infra_env_id}/regenerate-signing-key | RegenerateInfraEnvSigningKey | action | `infra_env_action` (`regenerate-signing-key`) | backlog |
| GET | /v2/infra-envs/{infra_env_id}/downloads/image-url | GetInfraEnvDownloadURL | download | `infra_env_info` / `infra_env_image_info` (ISO URL) | 2 |
| GET | /v2/infra-envs/{infra_env_id}/downloads/files | v2DownloadInfraEnvFiles | download | `infra_env_file_info` | backlog |
| GET | /v2/infra-envs/{infra_env_id}/downloads/files-presigned | GetInfraEnvPresignedFileURL | download | `infra_env_file_info` (presigned) | backlog |
| GET | /v2/infra-envs/{infra_env_id}/downloads/minimal-initrd | DownloadMinimalInitrd | download | `infra_env_file_info` (initrd) | backlog |

## Host — state-based CRUD + reads

| Method | Path | operationId | Pattern | Module | Phase |
|--------|------|-------------|---------|--------|-------|
| GET | /v2/infra-envs/{infra_env_id}/hosts | v2ListHosts | info | `host_info` | 2 |
| GET | /v2/infra-envs/{infra_env_id}/hosts/{host_id} | v2GetHost | info | `host_info` | 2 |
| POST | /v2/infra-envs/{infra_env_id}/hosts | v2RegisterHost | state | `host` (`state: present`) | 2 |
| PATCH | /v2/infra-envs/{infra_env_id}/hosts/{host_id} | v2UpdateHost | state | `host` | 2 |
| DELETE | /v2/infra-envs/{infra_env_id}/hosts/{host_id} | v2DeregisterHost | state | `host` (`state: absent`) | 2 |
| PATCH | /v2/infra-envs/{infra_env_id}/hosts/{host_id}/installer-args | v2UpdateHostInstallerArgs | state | fold into `host` (open Q) | backlog |
| GET | /v2/infra-envs/{infra_env_id}/hosts/{host_id}/ignition | v2GetHostIgnition | info | `host_info` sub-read | backlog |
| PATCH | /v2/infra-envs/{infra_env_id}/hosts/{host_id}/ignition | v2UpdateHostIgnition | state | fold into `host` / `host_ignition` (open Q) | backlog |
| GET | /v2/infra-env/{infra_env_id}/hosts/{host_id}/downloads/ignition | v2DownloadHostIgnition | download | `host_info` (ignition content) | backlog |

## Host — RPC actions

| Method | Path | operationId | Pattern | Module | Phase |
|--------|------|-------------|---------|--------|-------|
| POST | /v2/infra-envs/{infra_env_id}/hosts/{host_id}/actions/bind | BindHost | action | `host_action` (`bind`) | 2 |
| POST | /v2/infra-envs/{infra_env_id}/hosts/{host_id}/actions/unbind | UnbindHost | action | `host_action` (`unbind`) | 2 |
| POST | /v2/infra-envs/{infra_env_id}/hosts/{host_id}/actions/install | v2InstallHost | action | `host_action` (`install`) | 2 |
| POST | /v2/infra-envs/{infra_env_id}/hosts/{host_id}/actions/reset | v2ResetHost | action | `host_action` (`reset`) | 2 |
| PATCH | /v2/infra-envs/{infra_env_id}/hosts/{host_id}/actions/reset-validation/{validation_id} | v2ResetHostValidation | action | `host_action` (`reset-validation`) | backlog |

## Agent-internal — **out of scope** (no module)

These are invoked by the assisted-installer agent running on the host, or push
telemetry back to the service. An Ansible operator never drives them, so they are
deliberately excluded from the collection.

| Method | Path | operationId | Why excluded |
|--------|------|-------------|--------------|
| POST | /v2/events | v2TriggerEvent | agent emits events |
| PUT | /v2/clusters/{cluster_id}/monitored-operators | v2ReportMonitoredOperatorStatus | agent reports operator status |
| POST | /v2/clusters/{cluster_id}/logs | V2UploadLogs | agent uploads logs |
| PUT | /v2/clusters/{cluster_id}/logs-progress | v2UpdateClusterLogsProgress | agent progress telemetry |
| PUT | /v2/clusters/{cluster_id}/progress | v2UpdateClusterFinalizingProgress | agent progress telemetry |
| POST | /v2/clusters/{cluster_id}/uploads/ingress-cert | v2UploadClusterIngressCert | agent uploads cert |
| GET | /v2/infra-envs/{infra_env_id}/hosts/{host_id}/instructions | v2GetNextSteps | agent polls next steps |
| POST | /v2/infra-envs/{infra_env_id}/hosts/{host_id}/instructions | v2PostStepReply | agent replies with step results |
| PUT | /v2/infra-envs/{infra_env_id}/hosts/{host_id}/logs-progress | v2UpdateHostLogsProgress | agent progress telemetry |
| PUT | /v2/infra-envs/{infra_env_id}/hosts/{host_id}/progress | v2UpdateHostInstallProgress | agent progress telemetry |

---

## Coverage summary

| Pattern | Ops | Notes |
|---------|----:|-------|
| info | 29 | catalog + resource GETs + sub-reads |
| download | 11 | artifact/URL GETs (read-only) |
| state | 19 | CRUD across cluster / infra_env / host / manifest + config sub-resources |
| action | 12 | 6 cluster + 5 host + 1 infra_env |
| agent-internal | 10 | excluded |
| **Total** | **81** | matches spec op count |

### Phase rollup (modules to author)

- **Phase 1:** `openshift_version_info` ✅, `support_level_info`,
  `supported_operator_info`, `cluster` + `cluster_info`, `infra_env` + `infra_env_info`.
- **Phase 2:** `cluster_action`, `host` + `host_info` + `host_action`,
  `cluster_credentials_info`, `infra_env` ISO-URL download helper.
- **Backlog:** manifests, install-config/ignored-validations sub-resources,
  events/domains/bundles/component-versions/release-sources info modules,
  import/disconnected cluster variants, `infra_env_action`, host ignition/installer-args.

## Open questions (feed [[module-naming-decisions]])

1. **`support_level_info` shape** — one module with a `kind:` param
   (`architectures` / `features` / `features_detailed`) vs. three modules?
2. **Config sub-resources** — fold `install-config`, `ignored-validations`,
   `installer-args`, `ignition` into the parent `cluster`/`host` module as options,
   or ship dedicated modules? (Affects how many Phase-backlog modules exist.)
3. **Cluster register variants** — are `import` and `disconnected` a mode of
   `cluster`, or separate modules?
4. **`reset-validation`** — action verb (`host_action`) or state-based sub-resource?
   It is a PATCH, unlike the other POST `/actions/*`.
5. **UI settings** — confirm out of scope (no operator use case).

## How this was generated

```bash
curl -sS https://api.openshift.com/api/assisted-install/v2/openapi \
| jq -r '.paths | to_entries[] as $p | $p.value | to_entries[]
    | select(.key|test("^(get|post|patch|put|delete)$"))
    | [(.key|ascii_upcase), $p.key, (.value.operationId // "-"),
       ((.value.tags // ["-"])|join(","))] | @tsv' \
| sort -t$'\t' -k4,4 -k2,2
```

Pattern/module/phase columns are hand-classified per DESIGN.md §4–§5. Re-run the
command and diff against this file's tables to detect spec drift.
