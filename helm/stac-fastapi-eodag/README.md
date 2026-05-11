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

## Values

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| affinity | object | `{}` | Affinity for stac-fastapi-eodag pods assignment |
| api.description | string | `"STAC API powered by EODAG and STAC FastAPI"` | API description |
| api.landingId | string | `"eodag-stac-fastapi"` | ID of the landing page |
| api.title | string | `"EODAG STAC FastAPI"` | API title |
| args | list | `[]` | Override default container args (useful when using custom images). Overrides the defaultArgs. |
| clusterDomain | string | `"cluster.local"` | Kubernetes cluster domain name |
| collections | string | `""` | Optional overwrite of product types default configuration |
| command | list | `[]` | Override default container command (useful when using custom images) |
| commonAnnotations | object | `{}` | Annotations to add to all deployed objects |
| commonLabels | object | `{}` | Labels to add to all deployed objects |
| config | string | `nil` | [object] EODAG configuration |
| configExistingSecret.key | string | `""` | Existing secret key for EODAG config. If this is set, value config will be ignored |
| configExistingSecret.name | string | `""` | Existing secret name for EODAG config. If this is set, value config will be ignored |
| containerPorts.http | int | `8080` | stac-fastapi-eodag application HTTP port number |
| containerSecurityContext.allowPrivilegeEscalation | bool | `false` | Set stac-fastapi-eodag containers' Security Context allowPrivilegeEscalation |
| containerSecurityContext.capabilities.drop | list | `["all"]` | Set stac-fastapi-eodag containers' Security Context capabilities to be dropped |
| containerSecurityContext.enabled | bool | `false` | Enabled stac-fastapi-eodag containers' Security Context |
| containerSecurityContext.readOnlyRootFilesystem | bool | `false` | Set stac-fastapi-eodag containers' Security Context readOnlyRootFilesystem |
| containerSecurityContext.runAsNonRoot | bool | `true` | Set stac-fastapi-eodag container's Security Context runAsNonRoot |
| containerSecurityContext.runAsUser | int | `1001` | Set stac-fastapi-eodag containers' Security Context runAsUser |
| customLivenessProbe | object | `{}` | Custom livenessProbe that overrides the default one |
| customReadinessProbe | object | `{}` | Custom readinessProbe that overrides the default one |
| debug | bool | `false` | When set to true, set the EODAG logging level to 3 (DEBUG). Otherwise, set EODAG logging level to 2 (INFO). |
| deployment.annotations | object | `{}` | Additional custom annotations for stac-fastapi-eodag deployment |
| extraDeploy | list | `[]` | Array of extra objects to deploy with the release |
| extraEnvVars | list | `[]` | Array with extra environment variables to add to stac-fastapi-eodag nodes |
| extraEnvVarsCM | string | `""` | Name of existing ConfigMap containing extra env vars for stac-fastapi-eodag nodes |
| extraEnvVarsSecret | string | `""` | Name of existing Secret containing extra env vars for stac-fastapi-eodag nodes |
| extraVolumeMounts | list | `[]` | Optionally specify extra list of additional volumeMounts for the stac-fastapi-eodag container(s) |
| extraVolumes | list | `[]` | Optionally specify extra list of additional volumes for the stac-fastapi-eodag pod(s) |
| fullnameOverride | string | `""` | String to fully override common.names.fullname |
| global.imagePullSecrets | list | `[]` | Global Docker registry secret names as an array |
| global.imageRegistry | string | `""` | Global Docker image registry |
| global.storageClass | string | `""` | Global StorageClass for Persistent Volume(s) |
| horizontalPodAutoscaler.cpuUtilization | int | `50` | The maximum CPU utilization target computed in % of the CPU resources request. |
| horizontalPodAutoscaler.enabled | bool | `false` | Decide to enable or disable the horizontal pod autoscaler |
| horizontalPodAutoscaler.maxReplicas | int | `10` | The maximum number of replicas that are allowed to run simultaneously |
| horizontalPodAutoscaler.memUtilization | int | `50` | The maximum RAM utilization target computed in % of the RAM resources request. |
| hostAliases | list | `[]` | stac-fastapi-eodag pods host aliases |
| image.digest | string | `""` | stac-fastapi-eodag image digest in the way sha256:aa.... Please note this parameter, if set, will override the tag |
| image.pullPolicy | string | `"IfNotPresent"` | stac-fastapi-eodag image pull policy |
| image.pullSecrets | list | `[]` | Specify docker-registry secret names as an array |
| image.registry | string | `"ghcr.io"` | stac-fastapi-eodag image registry |
| image.repository | string | `"cs-si/stac-fastapi-eodag"` | stac-fastapi-eodag image repository |
| image.tag | string | `"v0.3.0-eodag-4.0.0"` | Overrides the stac-fastapi-eodag image tag whose default is the chart appVersion (immutable tags are recommended) |
| ingress.annotations | object | `{}` | Annotations for the stac-fastapi-eodag ingress. To enable certificate autogeneration, place here your cert-manager annotations. |
| ingress.apiVersion | string | `""` | Ingress API version for the stac-fastapi-eodag ingress |
| ingress.enabled | bool | `false` | Enable the creation of an ingress for the stac-fastapi-eodag |
| ingress.extraHosts | list | `[]` | Extra hosts array for the stac-fastapi-eodag ingress |
| ingress.extraPaths | list | `[]` | Extra paths for the stac-fastapi-eodag ingress |
| ingress.extraRules | list | `[]` | Additional rules to be covered with this ingress record |
| ingress.extraTls | list | `[]` | Extra TLS configuration for the stac-fastapi-eodag ingress |
| ingress.hostname | string | `"eodag.local"` | Ingress hostname for the stac-fastapi-eodag ingress |
| ingress.ingressClassName | string | `""` | IngressClass that will be be used to implement the Ingress (Kubernetes 1.18+) |
| ingress.path | string | `"/"` | Path array for the stac-fastapi-eodag ingress |
| ingress.pathType | string | `"ImplementationSpecific"` | Path type for the stac-fastapi-eodag ingress |
| ingress.secrets | list | `[]` | Secrets array to mount into the Ingress |
| ingress.selfSigned | bool | `false` | Create a TLS secret for this ingress record using self-signed certificates generated by Helm |
| ingress.servicePort | string | `"http"` | Backend service port to use |
| ingress.tls | bool | `false` | Enable TLS for the stac-fastapi-eodag ingress |
| initContainers | list | `[]` | Add additional init containers to the stac-fastapi-eodag pod(s) |
| keepOriginUrl | bool | `false` | Keep the original URL in the response headers |
| kubeVersion | string | `""` | Force target Kubernetes version (using Helm capabilities if not set) |
| lifecycleHooks | object | `{}` | for the stac-fastapi-eodag container(s) to automate configuration before or after startup |
| livenessProbe.enabled | bool | `false` | Enable livenessProbe on stac-fastapi-eodag containers |
| livenessProbe.failureThreshold | int | `3` | Failure threshold for livenessProbe |
| livenessProbe.initialDelaySeconds | int | `3` | Initial delay seconds for livenessProbe |
| livenessProbe.periodSeconds | int | `10` | Period seconds for livenessProbe |
| livenessProbe.successThreshold | int | `1` | Success threshold for livenessProbe |
| livenessProbe.timeoutSeconds | int | `1` | Timeout seconds for livenessProbe |
| nameOverride | string | `""` | String to partially override common.names.fullname |
| namespaceOverride | string | `""` | String to fully override common.names.namespaceapi |
| nodeAffinityPreset.key | string | `""` | Node label key to match. Ignored if `affinity` is set |
| nodeAffinityPreset.type | string | `""` | Node affinity preset type. Ignored if `affinity` is set. Allowed values: `soft` or `hard` |
| nodeAffinityPreset.values | list | `[]` | Node label values to match. Ignored if `affinity` is set |
| nodeSelector | object | `{}` | Node labels for stac-fastapi-eodag pods assignment |
| otel.collector.config | string | `"extensions:\n  health_check:\n  pprof:\n    endpoint: 0.0.0.0:1777\n  zpages:\n    endpoint: 0.0.0.0:55679\nreceivers:\n  otlp:\n    protocols:\n      http:\n        endpoint: 0.0.0.0:4318\n  # Collect own metrics\n  prometheus:\n    config:\n      scrape_configs:\n      - job_name: 'otel-collector'\n        scrape_interval: 10s\n        static_configs:\n        - targets: ['0.0.0.0:8888']\nprocessors:\n  batch:\nexporters:\n  debug:\n    verbosity: detailed\n  # Data sources: metrics\n  prometheus:\n    endpoint: 0.0.0.0:8000\n    namespace: eodag-otelcol-exporter\nservice:\n  pipelines:\n    traces:\n      receivers: [otlp]\n      processors: [batch]\n      exporters: [debug]\n    metrics:\n      receivers: [otlp]\n      processors: [batch]\n      exporters: [debug,prometheus]\n  extensions: [health_check, pprof, zpages]"` | [object] Optional overwrite of OpenTelemetry Collector default configuration |
| otel.collector.enabled | bool | `false` | Deploy an otel collector backend as sidecar |
| otel.collector.image.pullPolicy | string | `"IfNotPresent"` | stac-fastapi-eodag image pull policy |
| otel.collector.image.registry | string | `"docker.io"` | OpenTelemetry Collector image registry |
| otel.collector.image.repository | string | `"otel/opentelemetry-collector-contrib"` | OpenTelemetry Collector image repository |
| otel.collector.image.tag | string | `"0.95.0"` | Overrides the OpenTelemetry Collector image tag |
| otel.collector.ports.otlpReceiver | int | `4318` | port to receive otel telemetry |
| otel.collector.ports.prometheusExporter | int | `8000` | Port for Prometheus scrapping. Data available under /metrics |
| otel.enabled | bool | `false` | Enable otel export |
| otel.endpoint | string | `"http://localhost:4318"` | The hostname and port for an otel compatible backend |
| otel.interval | int | `60000` | The |
| otel.serviceMonitor.enabled | bool | `false` | if `true`, creates a Prometheus Operator PodMonitor |
| otel.serviceMonitor.interval | string | `""` | Interval at which metrics should be scraped. |
| otel.serviceMonitor.labels | object | `{}` | Labels that can be used so PodMonitor will be discovered by Prometheus |
| otel.serviceMonitor.metricRelabelings | list | `[]` | MetricRelabelConfigs to apply to samples before ingestion |
| otel.serviceMonitor.namespace | string | `""` | Namespace for the PodMonitor Resource (defaults to the Release Namespace) |
| otel.serviceMonitor.relabelings | list | `[]` | RelabelConfigs to apply to samples before scraping |
| otel.serviceMonitor.scrapeTimeout | string | `""` | Timeout after which the scrape is ended |
| otel.timeout | int | `10` | The timeout for data transfer |
| podAffinityPreset | string | `""` | Pod affinity preset. Ignored if `affinity` is set. Allowed values: `soft` or `hard` |
| podAnnotations | object | `{}` | Annotations for stac-fastapi-eodag pods |
| podAntiAffinityPreset | string | `"soft"` | Pod anti-affinity preset. Ignored if `affinity` is set. Allowed values: `soft` or `hard` |
| podLabels | object | `{}` | Extra labels for stac-fastapi-eodag pods |
| podSecurityContext.enabled | bool | `false` | Enabled stac-fastapi-eodag pods' Security Context |
| podSecurityContext.fsGroup | int | `1001` | Set stac-fastapi-eodag pod's Security Context fsGroup |
| priorityClassName | string | `""` | stac-fastapi-eodag pods' priorityClassName |
| providers | string | `""` | Optional overwrite of providers default configuration |
| readinessProbe.enabled | bool | `false` | Enable readinessProbe on stac-fastapi-eodag containers |
| readinessProbe.failureThreshold | int | `3` | Failure threshold for readinessProbe |
| readinessProbe.initialDelaySeconds | int | `3` | Initial delay seconds for readinessProbe |
| readinessProbe.periodSeconds | int | `10` | Period seconds for readinessProbe |
| readinessProbe.successThreshold | int | `1` | Success threshold for readinessProbe |
| readinessProbe.timeoutSeconds | int | `1` | Timeout seconds for readinessProbe |
| replicaCount | int | `1` | Number of stac-fastapi-eodag replicas |
| resources.limits | object | `{}` | The resources limits for the stac-fastapi-eodag containers |
| resources.requests | object | `{}` | The requested resources for the stac-fastapi-eodag containers |
| rootPath | string | `""` | Application root path |
| runtimeClassName | string | `""` | Name of the runtime class to be used by pod(s) |
| schedulerName | string | `""` | Name of the k8s scheduler (other than default) |
| service.annotations | object | `{}` | Additional custom annotations for stac-fastapi-eodag service |
| service.clusterIP | string | `""` | stac-fastapi-eodag service clusterIP IP |
| service.externalTrafficPolicy | string | `"Cluster"` | Enable client source IP preservation |
| service.extraPorts | list | `[]` | Extra port to expose on stac-fastapi-eodag service |
| service.http.enabled | bool | `true` | Enable http port on service |
| service.loadBalancerIP | string | `""` | loadBalancerIP for the SuiteCRM Service (optional, cloud specific) |
| service.loadBalancerSourceRanges | list | `[]` | Address that are allowed when service is LoadBalancer |
| service.nodePorts | object | `{"http":"","metrics":""}` | [object] Specify the nodePort values for the LoadBalancer and NodePort service types. |
| service.ports.http | int | `8080` | stac-fastapi-eodag service HTTP port |
| service.sessionAffinity | string | `"None"` | Control where client requests go, to the same pod or round-robin |
| service.sessionAffinityConfig | object | `{}` | Additional settings for the sessionAffinity |
| service.type | string | `"ClusterIP"` | Kubernetes service type |
| serviceAccount.annotations | object | `{}` | Additional custom annotations for the ServiceAccount |
| serviceAccount.automountServiceAccountToken | bool | `true` | Automount service account token for the server service account |
| serviceAccount.create | bool | `true` | Specifies whether a ServiceAccount should be created |
| serviceAccount.name | string | `""` | The name of the ServiceAccount to use. |
| shareProcessNamespace | bool | `false` | Enable shared process namespace in a pod. |
| sidecars | list | `[]` | Add additional sidecar containers to the stac-fastapi-eodag pod(s) |
| startupProbe.enabled | bool | `false` | Enable startupProbe on stac-fastapi-eodag containers |
| startupProbe.failureThreshold | int | `3` | Failure threshold for startupProbe |
| startupProbe.initialDelaySeconds | int | `10` | Initial delay seconds for startupProbe |
| startupProbe.periodSeconds | int | `10` | Period seconds for startupProbe |
| startupProbe.successThreshold | int | `1` | Success threshold for startupProbe |
| startupProbe.timeoutSeconds | int | `1` | Timeout seconds for startupProbe |
| terminationGracePeriodSeconds | int | `30` | Termination grace period in seconds for pods |
| tolerations | list | `[]` | Tolerations for stac-fastapi-eodag pods assignment |
| topologySpreadConstraints | list | `[]` | Topology Spread Constraints for pod assignment |
| updateStrategy.type | string | `"RollingUpdate"` | stac-fastapi-eodag statefulset strategy type |

Specify each parameter using the `--set key=value[,key=value]` argument to `helm install`. For example,

```console
helm install my-release \
  --set image.pullPolicy=Always \
  stac-fastapi-eodag/stac-fastapi-eodag
```

Alternatively, a YAML file that specifies the values for the parameters can be provided while installing the chart:

```console
helm install my-release -f values.yaml stac-fastapi-eodag/stac-fastapi-eodag
```

> **Tip**: You can use the default [values.yaml](values.yaml)

## Configuration and installation details

### EODAG provider configuration

EODAG credentials and provider settings are passed via the `config` value, which maps directly to the [EODAG user configuration](https://eodag.readthedocs.io/en/stable/getting_started_guide/configure.html).

```yaml
config:
  cop_dataspace:
    priority: 1
    auth:
      credentials:
        username: your-username
        password: your-password
```

For production deployments, use an existing Kubernetes secret instead of embedding credentials in values:

```yaml
configExistingSecret:
  name: eodag-credentials
  key: eodag-config.yml
```

### Expose the API on a subpath

To run stac-fastapi-eodag under a path prefix such as `/stac`, set `rootPath` and configure the ingress rewrite accordingly:

```yaml
rootPath: /stac

ingress:
  enabled: true
  hostname: my-cluster.example.com
  path: /stac/?(.*)
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /$1
```

### Immutable image tags

Always pin the image to an immutable tag in production. The default tag follows the pattern `<app-version>-eodag-<eodag-version>` (e.g. `v0.3.0-eodag-4.0.0`). Avoid using `latest` or floating tags — they make rollbacks unreliable and deployments non-deterministic.

### Horizontal Pod Autoscaling

Enable HPA to automatically scale the API under load:

```yaml
horizontalPodAutoscaler:
  enabled: true
  maxReplicas: 5
  cpuUtilization: 70
```

Ensure `resources.requests` are set, as HPA requires them to compute utilization ratios.

### OpenTelemetry / observability

The chart ships with an optional OpenTelemetry Collector sidecar. Enable it to export traces and metrics to any OTLP-compatible backend (Jaeger, Tempo, etc.):

```yaml
otel:
  enabled: true
  endpoint: "http://tempo.monitoring.svc:4318"
  collector:
    enabled: true
```

Prometheus metrics are exposed by the collector on port `8000` under `/metrics`. A `ServiceMonitor` resource for the Prometheus Operator can be enabled via `otel.serviceMonitor.enabled`.

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
