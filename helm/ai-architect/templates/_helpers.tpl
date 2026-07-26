{{/*
Common labels
*/}}
{{- define "ai-architect.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{/*
Selector labels for a specific component
*/}}
{{- define "ai-architect.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{/*
Full image reference with optional global registry
*/}}
{{- define "ai-architect.image" -}}
{{- if .global.imageRegistry -}}
{{ .global.imageRegistry }}/{{ .image.repository }}:{{ .image.tag }}
{{- else -}}
{{ .image.repository }}:{{ .image.tag }}
{{- end -}}
{{- end }}

{{/*
Global tolerations — applied to every pillar pod.

The agent node pool carries workload=agent:NoSchedule so that non-agent
workloads are not scheduled there by default. However, the system node
has limited CPU so all pillar API and agent pods also need to tolerate
the agent taint to be schedulable on that pool when the system node is
full. The standard Kubernetes node-condition tolerations are kept for
graceful handling of transient node problems.
*/}}
{{- define "ai-architect.tolerations" -}}
- key: workload
  operator: Equal
  value: agent
  effect: NoSchedule
- key: node.kubernetes.io/memory-pressure
  operator: Exists
  effect: NoSchedule
- key: node.kubernetes.io/not-ready
  operator: Exists
  effect: NoExecute
  tolerationSeconds: 300
- key: node.kubernetes.io/unreachable
  operator: Exists
  effect: NoExecute
  tolerationSeconds: 300
{{- end }}
