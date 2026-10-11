{{- define "mock.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "mock.fullname" -}}
{{- printf "%s" (include "mock.name" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "mock.labels" -}}
app.kubernetes.io/name: {{ include "mock.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}
