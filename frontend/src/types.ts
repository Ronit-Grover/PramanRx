export type Severity = 'pass' | 'caution' | 'critical' | 'insufficient' | 'integrity'
export type ViewKey = 'workspace' | 'scenarios' | 'audit' | 'knowledge' | 'integration' | 'architecture' | 'status'

export interface Patient {
  id: string
  name: string
  initials: string
  age: number
  sex: string
  mrn: string
  dob: string
  flags: string[]
}

export interface Finding {
  id: string
  severity: Severity
  title: string
  explanation: string
  patientFact: string
  evidence: string
  source: string
  action: string
  certainty: 'high' | 'moderate' | 'low'
}

export interface AuditEvent {
  id: string
  time: string
  title: string
  actor: string
  detail: string
  hash: string
  verified: boolean
}

export interface Scenario {
  id: string
  title: string
  summary: string
  severity: Severity
  prompt: string
  output: string
  patientId: string
  findings: Finding[]
}
