{{- define "triton.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "triton.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s" (include "triton.name" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{- define "triton.labels" -}}
app.kubernetes.io/name: {{ include "triton.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
infergrid.io/backend: triton
{{- end }}
