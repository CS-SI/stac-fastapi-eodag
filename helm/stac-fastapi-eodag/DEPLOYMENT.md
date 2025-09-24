# Deployment Guide for stac-fastapi-eodag

This document provides guidance on deploying stac-fastapi-eodag in production environments, with specific focus on configuration management and graceful shutdowns.

## Automatic Configuration Reloading with Reloader

The stac-fastapi-eodag Helm chart supports automatic configuration reloading using [Reloader](https://github.com/stakater/Reloader). This allows pods to be automatically restarted when ConfigMaps or Secrets are updated.

### Available Reloader Annotations

| Annotation | Purpose | Example |
|------------|---------|---------|
| `configmap.reloader.stakater.com/reload` | Restart pods when specified ConfigMaps change | `"config-name1,config-name2"` |
| `secret.reloader.stakater.com/reload` | Restart pods when specified Secrets change | `"secret-name1,secret-name2"` |
| `reloader.stakater.com/auto` | Auto-discover and reload on any ConfigMap/Secret change | `"true"` |

### Example Configuration

```yaml
# values.yaml
deployment:
  annotations:
    # Reload when main config changes
    configmap.reloader.stakater.com/reload: "stac-fastapi-eodag-config,data-repo-commit-hash"
    # Reload when credentials change
    secret.reloader.stakater.com/reload: "eodag-server-credentials"
```

### Installing Reloader

If Reloader is not already installed in your cluster, you can install it using:

```bash
# Using Helm
helm repo add stakater https://stakater.github.io/stakater-charts
helm repo update
helm install reloader stakater/reloader

# Or using kubectl
kubectl apply -f https://raw.githubusercontent.com/stakater/Reloader/master/deployments/kubernetes/reloader.yaml
```

## Graceful Shutdown with terminationGracePeriodSeconds

The `terminationGracePeriodSeconds` parameter controls how long Kubernetes waits before forcefully killing a pod during shutdown. This is crucial for stac-fastapi-eodag when handling long-running operations like data downloads.

### Configuring Termination Grace Period

```yaml
# values.yaml
# Default Kubernetes value is 30 seconds
terminationGracePeriodSeconds: 7200  # 2 hours for long downloads
```

### Troubleshooting

If pods are being forcefully killed:

1. **Increase Grace Period**: Adjust `terminationGracePeriodSeconds`
2. **Check Application Logs**: Ensure the app handles SIGTERM
3. **Monitor Resource Usage**: High CPU/memory might slow shutdown
4. **Review Health Checks**: Ensure probes don't interfere with shutdown
