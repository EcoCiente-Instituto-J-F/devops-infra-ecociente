{{- define "ecociente-api.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "ecociente-api.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name (include "ecociente-api.name" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{- define "ecociente-api.selectorLabels" -}}
app: {{ include "ecociente-api.fullname" . }}
{{- end }}

{{- define "ecociente-api.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{ include "ecociente-api.selectorLabels" . }}
app.kubernetes.io/name: {{ include "ecociente-api.fullname" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: ecociente
{{- end }}

{{- define "ecociente-api.configMapName" -}}
{{- if .Values.configMap.nameOverride }}
{{- .Values.configMap.nameOverride }}
{{- else }}
{{- printf "%s-config" (include "ecociente-api.fullname" .) }}
{{- end }}
{{- end }}