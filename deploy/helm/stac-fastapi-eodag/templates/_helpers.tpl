{{/*
Create the name of the service account to use
*/}}
{{- define "stac-fastapi-eodag.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
    {{ default (include "common.names.fullname" .) .Values.serviceAccount.name | trunc 63 | trimSuffix "-" }}
{{- else -}}
    {{ default "default" .Values.serviceAccount.name }}
{{- end -}}
{{- end -}}

{{/*
Return the proper Docker Image Registry Secret Names
*/}}
{{- define "stac-fastapi-eodag.imagePullSecrets" -}}
{{- include "common.images.pullSecrets" (dict "images" (list .Values.image) "global" .Values.global) -}}
{{- end -}}

{{/*
Get the config secret.
*/}}
{{- define "stac-fastapi-eodag.configSecretName" -}}
{{- if .Values.configExistingSecret.name }}
    {{- printf "%s" (tpl .Values.configExistingSecret.name $) -}}
{{- else -}}
    {{- printf "%s-config" (include "common.names.fullname" .) -}}
{{- end -}}
{{- end -}}

{{/*
Get the client secret key.
*/}}
{{- define "stac-fastapi-eodag.configSecretKey" -}}
{{- if .Values.configExistingSecret.key }}
    {{- printf "%s" (tpl .Values.configExistingSecret.key $) -}}
{{- else -}}
    {{- "eodag.yml" -}}
{{- end -}}
{{- end -}}

{{/*
Return  the proper Storage Class
*/}}
{{- define "stac-fastapi-eodag.storageClass" -}}
{{- include "common.storage.class" (dict "persistence" .Values.persistence "global" .Values.global) -}}
{{- end -}}

{{/*
Create EODAG Server app version
*/}}
{{- define "stac-fastapi-eodag.defaultTag" -}}
{{- default .Chart.AppVersion .Values.image.tag }}
{{- end -}}

{{/*
Return the proper EODAG server image name
*/}}
{{- define "stac-fastapi-eodag.image" -}}
{{- $registryName := .Values.image.registry -}}
{{- $repositoryName := .Values.image.repository -}}
{{- $separator := ":" -}}
{{- $termination := .Values.image.tag | default .Chart.AppVersion | toString -}}
{{- if .Values.global }}
    {{- if .Values.global.imageRegistry }}
     {{- $registryName = .Values.global.imageRegistry -}}
    {{- end -}}
{{- end -}}
{{- if .Values.image.digest }}
    {{- $separator = "@" -}}
    {{- $termination = .Values.image.digest | toString -}}
{{- end -}}
{{- if $registryName }}
    {{- printf "%s/%s%s%s" $registryName $repositoryName $separator $termination -}}
{{- else -}}
    {{- printf "%s%s%s"  $repositoryName $separator $termination -}}
{{- end -}}
{{- end -}}

{{/*
Return the proper OpenTelemetry Collector image name
*/}}
{{- define "otel-collector.image" -}}
{{- $registryName := .Values.otel.collector.image.registry -}}
{{- $repositoryName := .Values.otel.collector.image.repository -}}
{{- $separator := ":" -}}
{{- $termination := .Values.otel.collector.image.tag | toString -}}
{{- if .Values.global }}
    {{- if .Values.global.imageRegistry }}
     {{- $registryName = .Values.global.imageRegistry -}}
    {{- end -}}
{{- end -}}
{{- if .Values.otel.collector.image.digest }}
    {{- $separator = "@" -}}
    {{- $termination = .Values.otel.collector.image.digest | toString -}}
{{- end -}}
{{- if $registryName }}
    {{- printf "%s/%s%s%s" $registryName $repositoryName $separator $termination -}}
{{- else -}}
    {{- printf "%s%s%s"  $repositoryName $separator $termination -}}
{{- end -}}
{{- end -}}
