import type { AuditEvent, Finding, Patient, Severity } from './types'

const API_BASE = '/api/v1'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = body?.detail?.message ?? body?.detail ?? `API request failed (${response.status})`
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return body as T
}

const age = (birthDate: string) => Math.max(0, new Date().getFullYear() - Number(birthDate.slice(0, 4)))
const findingSeverity = (value: string): Severity => value === 'critical' ? 'critical' : value === 'warning' ? 'caution' : 'pass'

export function mapPatient(raw: any): Patient {
  const first = raw.first_name ?? 'Synthetic'
  const last = raw.last_name ?? 'Patient'
  return {
    id: raw.id,
    name: `${first} ${last}`,
    initials: `${first[0] ?? 'S'}${last[0] ?? 'P'}`.toUpperCase(),
    age: age(raw.birth_date),
    sex: ({ M: 'Male', F: 'Female', X: 'Other', U: 'Unknown' } as Record<string, string>)[raw.gender] ?? raw.gender,
    mrn: raw.id.startsWith('demo-') ? raw.id.toUpperCase() : `SYN-${raw.id.slice(0, 8).toUpperCase()}`,
    dob: raw.birth_date,
    flags: raw.source === 'user_created_synthetic' ? ['User-created synthetic record'] : ['Synthetic record'],
  }
}

export function mapFinding(raw: any): Finding {
  const evidence = Array.isArray(raw.evidence) ? raw.evidence : []
  return {
    id: raw.rule_id ?? 'PRX-UNKNOWN',
    severity: raw.certainty === 'insufficient_context' ? 'insufficient' : findingSeverity(raw.severity),
    title: raw.title,
    explanation: raw.explanation,
    patientFact: raw.patient_fact ?? 'No patient-specific fact was available.',
    evidence: evidence.map((item: any) => item.section ?? item.source_record ?? item.source ?? 'Local policy evidence').join(' · ') || 'Prototype policy evidence',
    source: evidence.map((item: any) => `${item.source ?? 'PramanRx'} ${item.source_file ?? ''}`.trim()).join(' · ') || 'PramanRx prototype policy',
    action: raw.recommended_next_action,
    certainty: raw.certainty === 'deterministic_match' ? 'high' : raw.certainty === 'conservative_policy' ? 'moderate' : 'low',
  }
}

export function verdictSeverity(verdict: string): Severity {
  return ({ pass: 'pass', caution: 'caution', critical_flag: 'critical', insufficient_context: 'insufficient', integrity_failure: 'integrity' } as Record<string, Severity>)[verdict] ?? 'insufficient'
}

export const api = {
  patients: async (q = '') => {
    const result = await request<{ items: any[] }>(`/patients?limit=1200&q=${encodeURIComponent(q)}`)
    return result.items.map(mapPatient)
  },
  createPatient: async (payload: unknown) => mapPatient(await request('/patients', { method: 'POST', body: JSON.stringify(payload) })),
  context: (patientId: string) => request<any>(`/patients/${patientId}/context`),
  status: () => request<Record<string, any>>('/system/status'),
  kbStatus: () => request<Record<string, any>>('/kb/status'),
  adapters: () => request<{ items: any[] }>('/adapters'),
  generate: (payload: unknown) => request<any>('/ai/generate', { method: 'POST', body: JSON.stringify(payload) }),
  evaluate: (payload: unknown) => request<any>('/evaluations', { method: 'POST', body: JSON.stringify(payload) }),
  runScenario: (scenarioId: string) => request<any>(`/scenarios/${scenarioId}/run`, { method: 'POST' }),
  action: (evaluationId: string, payload: unknown) => request<any>(`/evaluations/${evaluationId}/actions`, { method: 'POST', body: JSON.stringify(payload) }),
  timeline: (evaluationId: string) => request<{ items: any[] }>(`/evaluations/${evaluationId}/timeline`),
  auditVerify: () => request<any>('/audit/verify'),
  auditEvents: async (): Promise<AuditEvent[]> => {
    const result = await request<{ items: any[] }>('/audit/events?limit=100')
    return result.items.reverse().map((event) => ({
      id: event.id, time: new Date(event.created_at).toLocaleTimeString(),
      title: event.kind === 'evaluation' ? 'Recommendation evaluated' : 'Clinician action recorded',
      actor: event.kind === 'evaluation' ? 'pramanrx:policy' : 'demo clinician',
      detail: `${event.kind} · ${event.subject}`, hash: event.record_hash, verified: true,
    }))
  },
}
