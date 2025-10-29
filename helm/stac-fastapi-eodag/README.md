# EODAG Server

This chart bootstraps a [stac-fastapi-eodag](https://github.com/CS-SI/stac-fastapi-eodag) deployment on a [Kubernetes](http://kubernetes.io) cluster using the [Helm](https://helm.sh) package manager.

## TL;DR

```console
helm repo add stac-fastapi-eodag https://cs-si.github.io/stac-fastapi-eodag
helm repo update
helm install my-release stac-fastapi-eodag/stac-fastapi-eodag
```

## Prerequisites

- Kubernetes 1.23+
- Helm 3.8.0+

## Installing the Chart

### Add the Helm Repository

First, add the stac-fastapi-eodag Helm repository:

```console
helm repo add stac-fastapi-eodag https://cs-si.github.io/stac-fastapi-eodag
helm repo update
```

### Install the Chart

To install the chart with the release name `my-release`:

```console
helm install my-release stac-fastapi-eodag/stac-fastapi-eodag
```

These commands deploy stac-fastapi-eodag on the Kubernetes cluster in the default configuration.

> **Tip**: List all releases using `helm list`

## Uninstalling the Chart

To uninstall the `my-release` deployment:

```bash
helm uninstall my-release
```

The command removes all the Kubernetes components associated with the chart and deletes the release.

## Parameters

### Global parameters

| Name                      | Description                                     | Value |
| ------------------------- | ----------------------------------------------- | ----- |
| `global.imageRegistry`    | Global Docker image registry                    | `""`  |
| `global.imagePullSecrets` | Global Docker registry secret names as an array | `[]`  |
| `global.storageClass`     | Global StorageClass for Persistent Volume(s)    | `""`  |

### Common parameters

| Name                | Description                                                          | Value           |
| ------------------- | -------------------------------------------------------------------- | --------------- |
| `kubeVersion`       | Force target Kubernetes version (using Helm capabilities if not set) | `""`            |
| `nameOverride`      | String to partially override common.names.fullname                   | `""`            |
| `fullnameOverride`  | String to fully override common.names.fullname                       | `""`            |
| `namespaceOverride` | String to fully override common.names.namespaceapi                   | `""`            |
| `commonLabels`      | Labels to add to all deployed objects                                | `{}`            |
| `commonAnnotations` | Annotations to add to all deployed objects                           | `{}`            |
| `clusterDomain`     | Kubernetes cluster domain name                                       | `cluster.local` |
| `extraDeploy`       | Array of extra objects to deploy with the release                    | `[]`            |

### EODAG configuration

| Name                        | Description                                                                         | Value |
| --------------------------- | ----------------------------------------------------------------------------------- | ----- |
| `collections`               | Optional overwrite of collections default configuration                             | `""`  |
| `providers`                 | Optional overwrite of providers default configuration                               | `""`  |
| `config`                    | EODAG configuration                                                                 | `{}`  |
| `configExistingSecret.name` | Existing secret name for EODAG config. If this is set, value config will be ignored | `""`  |
| `configExistingSecret.key`  | Existing secret key for EODAG config. If this is set, value config will be ignored  | `""`  |

### stac-fastapi-eodag configuration

| Name              | Description                                                                                                 | Value                                        |
| ----------------- | ----------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| `api.title`       | API title                                                                                                   | `EODAG STAC FastAPI`                         |
| `api.description` | API description                                                                                             | `STAC API powered by EODAG and STAC FastAPI` |
| `api.landingId`   | ID of the landing page                                                                                      | `eodag-stac-fastapi`                         |
| `rootPath`        | Application root path                                                                                       | `""`                                         |
| `debug`           | When set to true, set the EODAG logging level to 3 (DEBUG). Otherwise, set EODAG logging level to 2 (INFO). | `false`                                      |
| `keepOriginUrl`   | Keep the original URL in the response headers                                                               | `false`                                      |

### stac-fastapi-eodag common parameters

| Name                                                | Description                                                                                                                     | Value                    |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| `image.registry`                                    | stac-fastapi-eodag image registry                                                                                               | `docker.io`              |
| `image.repository`                                  | stac-fastapi-eodag image repository                                                                                             | `csspace/eodag-server`   |
| `image.tag`                                         | Overrides the stac-fastapi-eodag image tag whose default is the chart appVersion (immutable tags are recommended)               | `""`                     |
| `image.digest`                                      | stac-fastapi-eodag image digest in the way sha256:aa.... Please note this parameter, if set, will override the tag              | `""`                     |
| `image.pullPolicy`                                  | stac-fastapi-eodag image pull policy                                                                                            | `IfNotPresent`           |
| `image.pullSecrets`                                 | Specify docker-registry secret names as an array                                                                                | `[]`                     |
| `replicaCount`                                      | Number of stac-fastapi-eodag replicas                                                                                           | `1`                      |
| `startupProbe.enabled`                              | Enable startupProbe on stac-fastapi-eodag containers                                                                            | `false`                  |
| `startupProbe.initialDelaySeconds`                  | Initial delay seconds for startupProbe                                                                                          | `10`                     |
| `startupProbe.periodSeconds`                        | Period seconds for startupProbe                                                                                                 | `10`                     |
| `startupProbe.timeoutSeconds`                       | Timeout seconds for startupProbe                                                                                                | `1`                      |
| `startupProbe.failureThreshold`                     | Failure threshold for startupProbe                                                                                              | `3`                      |
| `startupProbe.successThreshold`                     | Success threshold for startupProbe                                                                                              | `1`                      |
| `livenessProbe.enabled`                             | Enable livenessProbe on stac-fastapi-eodag containers                                                                           | `false`                  |
| `livenessProbe.initialDelaySeconds`                 | Initial delay seconds for livenessProbe                                                                                         | `3`                      |
| `livenessProbe.periodSeconds`                       | Period seconds for livenessProbe                                                                                                | `10`                     |
| `livenessProbe.timeoutSeconds`                      | Timeout seconds for livenessProbe                                                                                               | `1`                      |
| `livenessProbe.failureThreshold`                    | Failure threshold for livenessProbe                                                                                             | `3`                      |
| `livenessProbe.successThreshold`                    | Success threshold for livenessProbe                                                                                             | `1`                      |
| `readinessProbe.enabled`                            | Enable readinessProbe on stac-fastapi-eodag containers                                                                          | `false`                  |
| `readinessProbe.initialDelaySeconds`                | Initial delay seconds for readinessProbe                                                                                        | `3`                      |
| `readinessProbe.periodSeconds`                      | Period seconds for readinessProbe                                                                                               | `10`                     |
| `readinessProbe.timeoutSeconds`                     | Timeout seconds for readinessProbe                                                                                              | `1`                      |
| `readinessProbe.failureThreshold`                   | Failure threshold for readinessProbe                                                                                            | `3`                      |
| `readinessProbe.successThreshold`                   | Success threshold for readinessProbe                                                                                            | `1`                      |
| `customLivenessProbe`                               | Custom livenessProbe that overrides the default one                                                                             | `{}`                     |
| `customReadinessProbe`                              | Custom readinessProbe that overrides the default one                                                                            | `{}`                     |
| `resources.limits`                                  | The resources limits for the stac-fastapi-eodag containers                                                                      | `{}`                     |
| `resources.requests`                                | The requested resources for the stac-fastapi-eodag containers                                                                   | `{}`                     |
| `podSecurityContext.enabled`                        | Enabled stac-fastapi-eodag pods' Security Context                                                                               | `false`                  |
| `podSecurityContext.fsGroup`                        | Set stac-fastapi-eodag pod's Security Context fsGroup                                                                           | `1001`                   |
| `containerSecurityContext.enabled`                  | Enabled stac-fastapi-eodag containers' Security Context                                                                         | `false`                  |
| `containerSecurityContext.runAsUser`                | Set stac-fastapi-eodag containers' Security Context runAsUser                                                                   | `1001`                   |
| `containerSecurityContext.allowPrivilegeEscalation` | Set stac-fastapi-eodag containers' Security Context allowPrivilegeEscalation                                                    | `false`                  |
| `containerSecurityContext.capabilities.drop`        | Set stac-fastapi-eodag containers' Security Context capabilities to be dropped                                                  | `["all"]`                |
| `containerSecurityContext.readOnlyRootFilesystem`   | Set stac-fastapi-eodag containers' Security Context readOnlyRootFilesystem                                                      | `false`                  |
| `containerSecurityContext.runAsNonRoot`             | Set stac-fastapi-eodag container's Security Context runAsNonRoot                                                                | `true`                   |
| `command`                                           | Override default container command (useful when using custom images)                                                            | `[]`                     |
| `args`                                              | Override default container args (useful when using custom images). Overrides the defaultArgs.                                   | `[]`                     |
| `containerPorts.http`                               | stac-fastapi-eodag application HTTP port number                                                                                 | `8080`                   |
| `hostAliases`                                       | stac-fastapi-eodag pods host aliases                                                                                            | `[]`                     |
| `podLabels`                                         | Extra labels for stac-fastapi-eodag pods                                                                                        | `{}`                     |
| `podAnnotations`                                    | Annotations for stac-fastapi-eodag pods                                                                                         | `{}`                     |
| `podAffinityPreset`                                 | Pod affinity preset. Ignored if `affinity` is set. Allowed values: `soft` or `hard`                                             | `""`                     |
| `podAntiAffinityPreset`                             | Pod anti-affinity preset. Ignored if `affinity` is set. Allowed values: `soft` or `hard`                                        | `soft`                   |
| `nodeAffinityPreset.type`                           | Node affinity preset type. Ignored if `affinity` is set. Allowed values: `soft` or `hard`                                       | `""`                     |
| `nodeAffinityPreset.key`                            | Node label key to match. Ignored if `affinity` is set                                                                           | `""`                     |
| `nodeAffinityPreset.values`                         | Node label values to match. Ignored if `affinity` is set                                                                        | `[]`                     |
| `affinity`                                          | Affinity for stac-fastapi-eodag pods assignment                                                                                 | `{}`                     |
| `nodeSelector`                                      | Node labels for stac-fastapi-eodag pods assignment                                                                              | `{}`                     |
| `tolerations`                                       | Tolerations for stac-fastapi-eodag pods assignment                                                                              | `[]`                     |
| `schedulerName`                                     | Name of the k8s scheduler (other than default)                                                                                  | `""`                     |
| `shareProcessNamespace`                             | Enable shared process namespace in a pod.                                                                                       | `false`                  |
| `topologySpreadConstraints`                         | Topology Spread Constraints for pod assignment                                                                                  | `[]`                     |
| `updateStrategy.type`                               | stac-fastapi-eodag statefulset strategy type                                                                                    | `RollingUpdate`          |
| `priorityClassName`                                 | stac-fastapi-eodag pods' priorityClassName                                                                                      | `""`                     |
| `runtimeClassName`                                  | Name of the runtime class to be used by pod(s)                                                                                  | `""`                     |
| `lifecycleHooks`                                    | for the stac-fastapi-eodag container(s) to automate configuration before or after startup                                       | `{}`                     |
| `extraEnvVars`                                      | Array with extra environment variables to add to stac-fastapi-eodag nodes                                                       | `[]`                     |
| `extraEnvVarsCM`                                    | Name of existing ConfigMap containing extra env vars for stac-fastapi-eodag nodes                                               | `""`                     |
| `extraEnvVarsSecret`                                | Name of existing Secret containing extra env vars for stac-fastapi-eodag nodes                                                  | `""`                     |
| `extraVolumes`                                      | Optionally specify extra list of additional volumes for the stac-fastapi-eodag pod(s)                                           | `[]`                     |
| `extraVolumeMounts`                                 | Optionally specify extra list of additional volumeMounts for the stac-fastapi-eodag container(s)                                | `[]`                     |
| `sidecars`                                          | Add additional sidecar containers to the stac-fastapi-eodag pod(s)                                                              | `[]`                     |
| `initContainers`                                    | Add additional init containers to the stac-fastapi-eodag pod(s)                                                                 | `[]`                     |
| `service.type`                                      | Kubernetes service type                                                                                                         | `ClusterIP`              |
| `service.http.enabled`                              | Enable http port on service                                                                                                     | `true`                   |
| `service.ports.http`                                | stac-fastapi-eodag service HTTP port                                                                                            | `8080`                   |
| `service.nodePorts`                                 | Specify the nodePort values for the LoadBalancer and NodePort service types.                                                    | `{}`                     |
| `service.sessionAffinity`                           | Control where client requests go, to the same pod or round-robin                                                                | `None`                   |
| `service.sessionAffinityConfig`                     | Additional settings for the sessionAffinity                                                                                     | `{}`                     |
| `service.clusterIP`                                 | stac-fastapi-eodag service clusterIP IP                                                                                         | `""`                     |
| `service.loadBalancerIP`                            | loadBalancerIP for the SuiteCRM Service (optional, cloud specific)                                                              | `""`                     |
| `service.loadBalancerSourceRanges`                  | Address that are allowed when service is LoadBalancer                                                                           | `[]`                     |
| `service.externalTrafficPolicy`                     | Enable client source IP preservation                                                                                            | `Cluster`                |
| `service.annotations`                               | Additional custom annotations for stac-fastapi-eodag service                                                                    | `{}`                     |
| `service.extraPorts`                                | Extra port to expose on stac-fastapi-eodag service                                                                              | `[]`                     |
| `ingress.enabled`                                   | Enable the creation of an ingress for the stac-fastapi-eodag                                                                    | `false`                  |
| `ingress.pathType`                                  | Path type for the stac-fastapi-eodag ingress                                                                                    | `ImplementationSpecific` |
| `ingress.apiVersion`                                | Ingress API version for the stac-fastapi-eodag ingress                                                                          | `""`                     |
| `ingress.hostname`                                  | Ingress hostname for the stac-fastapi-eodag ingress                                                                             | `eodag.local`            |
| `ingress.annotations`                               | Annotations for the stac-fastapi-eodag ingress. To enable certificate autogeneration, place here your cert-manager annotations. | `{}`                     |
| `ingress.tls`                                       | Enable TLS for the stac-fastapi-eodag ingress                                                                                   | `false`                  |
| `ingress.extraHosts`                                | Extra hosts array for the stac-fastapi-eodag ingress                                                                            | `[]`                     |
| `ingress.path`                                      | Path array for the stac-fastapi-eodag ingress                                                                                   | `/`                      |
| `ingress.extraPaths`                                | Extra paths for the stac-fastapi-eodag ingress                                                                                  | `[]`                     |
| `ingress.extraTls`                                  | Extra TLS configuration for the stac-fastapi-eodag ingress                                                                      | `[]`                     |
| `ingress.secrets`                                   | Secrets array to mount into the Ingress                                                                                         | `[]`                     |
| `ingress.ingressClassName`                          | IngressClass that will be be used to implement the Ingress (Kubernetes 1.18+)                                                   | `""`                     |
| `ingress.selfSigned`                                | Create a TLS secret for this ingress record using self-signed certificates generated by Helm                                    | `false`                  |
| `ingress.servicePort`                               | Backend service port to use                                                                                                     | `http`                   |
| `ingress.extraRules`                                | Additional rules to be covered with this ingress record                                                                         | `[]`                     |
| `serviceAccount.create`                             | Specifies whether a ServiceAccount should be created                                                                            | `true`                   |
| `serviceAccount.name`                               | The name of the ServiceAccount to use.                                                                                          | `""`                     |
| `serviceAccount.annotations`                        | Additional custom annotations for the ServiceAccount                                                                            | `{}`                     |
| `serviceAccount.automountServiceAccountToken`       | Automount service account token for the server service account                                                                  | `false`                  |

### Telemetry parameters

| Name                                      | Description                                                               | Value                                  |
| ----------------------------------------- | ------------------------------------------------------------------------- | -------------------------------------- |
| `otel.enabled`                            | Enable otel export                                                        | `false`                                |
| `otel.endpoint`                           | The hostname and port for an otel compatible backend                      | `http://localhost:4318`                |
| `otel.interval`                           | The                                                                       | `60000`                                |
| `otel.timeout`                            | The timeout for data transfer                                             | `10`                                   |
| `otel.collector.enabled`                  | Deploy an otel collector backend as sidecar                               | `false`                                |
| `otel.collector.image.registry`           | OpenTelemetry Collector image registry                                    | `docker.io`                            |
| `otel.collector.image.repository`         | OpenTelemetry Collector image repository                                  | `otel/opentelemetry-collector-contrib` |
| `otel.collector.image.tag`                | Overrides the OpenTelemetry Collector image tag                           | `0.95.0`                               |
| `otel.collector.image.pullPolicy`         | stac-fastapi-eodag image pull policy                                      | `IfNotPresent`                         |
| `otel.collector.ports.otlpReceiver`       | port to receive otel telemetry                                            | `4318`                                 |
| `otel.collector.ports.prometheusExporter` | Port for Prometheus scrapping. Data available under /metrics              | `8000`                                 |
| `otel.collector.config`                   | Optional overwrite of OpenTelemetry Collector default configuration       | `{}`                                   |
| `otel.serviceMonitor.enabled`             | if `true`, creates a Prometheus Operator PodMonitor                       | `false`                                |
| `otel.serviceMonitor.namespace`           | Namespace for the PodMonitor Resource (defaults to the Release Namespace) | `""`                                   |
| `otel.serviceMonitor.interval`            | Interval at which metrics should be scraped.                              | `""`                                   |
| `otel.serviceMonitor.scrapeTimeout`       | Timeout after which the scrape is ended                                   | `""`                                   |
| `otel.serviceMonitor.labels`              | Labels that can be used so PodMonitor will be discovered by Prometheus    | `{}`                                   |
| `otel.serviceMonitor.relabelings`         | RelabelConfigs to apply to samples before scraping                        | `[]`                                   |
| `otel.serviceMonitor.metricRelabelings`   | MetricRelabelConfigs to apply to samples before ingestion                 | `[]`                                   |

Specify each parameter using the `--set key=value[,key=value]` argument to `helm install`. For example,

```console
helm install my-release \
  --set image.pullPolicy=Always \
  stac-fastapi-eodag/stac-fastapi-eodag
```

The above command sets the `image.pullPolicy` to `Always`.

Alternatively, a YAML file that specifies the values for the parameters can be provided while installing the chart. For example,

```console
helm install my-release -f values.yaml stac-fastapi-eodag/stac-fastapi-eodag
```

> **Tip**: You can use the default [values.yaml](values.yaml)

## Configuration and installation details

### Expose the API on a subPath

You can run stac-fasatapi-eodag on a subPath like `/stac`.

```yaml
rootPath: /stac

ingress:
  enabled: true
  path: /stac/?(.*)
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /$1
```

### [Rolling VS Immutable tags](https://docs.bitnami.com/containers/how-to/understand-rolling-tags-containers/)

It is strongly recommended to use immutable tags in a production environment. This ensures your deployment does not change automatically if the same tag is updated with a different image.

CS Group will release a new chart updating its containers if a new version of the main container, significant changes, or critical vulnerabilities exist.

## License

Copyright 5, CS GROUP - France, https://www.cs-soprasteria.com

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

<http://www.apache.org/licenses/LICENSE-2.0>

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
