import { useEffect, useMemo, useState } from 'react'
import { api, mapFinding, verdictSeverity } from './api'
import { auditEvents as seedAudit, patients as seedPatients, scenarios } from './demoData'
import { Icon, type IconName } from './icons'
import { formatHash, highestSeverity, initials } from './lib/risk'
import type { AuditEvent, Finding, Patient, Scenario, Severity, ViewKey } from './types'

const navItems: Array<{ key: ViewKey; label: string; icon: IconName }> = [
  { key: 'workspace', label: 'Verification workspace', icon: 'workspace' },
  { key: 'scenarios', label: 'Scenario launcher', icon: 'scenario' },
  { key: 'audit', label: 'Audit explorer', icon: 'audit' },
  { key: 'knowledge', label: 'Knowledge base', icon: 'database' },
  { key: 'integration', label: 'Integrations', icon: 'plug' },
  { key: 'architecture', label: 'Trust architecture', icon: 'architecture' },
  { key: 'status', label: 'System status', icon: 'status' },
]

const severityLabel: Record<Severity, string> = {
  pass: 'Pass', caution: 'Caution', critical: 'Critical flag', insufficient: 'Insufficient context', integrity: 'Integrity failure',
}

const scenarioIds: Record<string, string> = {
  safe: 'clear-low-risk', allergy: 'penicillin-allergy-amoxicillin', warfarin: 'major-ddi-warfarin-ibuprofen',
  statin: 'major-ddi-statin-macrolide', pregnancy: 'pregnancy-isotretinoin', renal: 'renal-metformin',
  dose: 'high-dose-acetaminophen', missing: 'missing-context', unknown: 'unknown-medication',
  malformed: 'malformed-output', 'invalid-kb': 'invalid-kb-signature', tamper: 'audit-tampering',
}

const scenarioPatients: Record<string, string> = {
  safe: 'demo-clear', allergy: 'demo-allergy', warfarin: 'demo-warfarin', statin: 'demo-simvastatin',
  pregnancy: 'demo-pregnancy', renal: 'demo-renal', dose: 'demo-clear', missing: 'demo-clear',
  unknown: 'demo-clear', malformed: 'demo-clear', 'invalid-kb': 'demo-clear', tamper: 'demo-warfarin',
}

function Badge({ severity, children }: { severity?: Severity; children: React.ReactNode }) {
  return <span className={`badge ${severity ? `badge-${severity}` : ''}`}>{severity && <span className="badge-dot" />}{children}</span>
}

function EmptyState({ icon, title, text }: { icon: IconName; title: string; text: string }) {
  return <div className="empty-state"><span className="empty-icon"><Icon name={icon} size={22} /></span><strong>{title}</strong><p>{text}</p></div>
}

function SectionHeading({ eyebrow, title, aside }: { eyebrow?: string; title: string; aside?: React.ReactNode }) {
  return <div className="section-heading"><div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h2>{title}</h2></div>{aside}</div>
}

function PatientPicker({ patients, selected, onSelect, onCreate }: { patients: Patient[]; selected: Patient; onSelect: (patient: Patient) => void; onCreate: () => void }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const filtered = patients.filter((patient) => `${patient.name} ${patient.mrn}`.toLowerCase().includes(query.toLowerCase()))
  return <div className="patient-picker">
    <label className="field-label">Synthetic patient</label>
    <button className="patient-trigger" type="button" onClick={() => setOpen(!open)} aria-expanded={open}>
      <span className="avatar">{selected.initials}</span>
      <span className="patient-trigger-copy"><strong>{selected.name}</strong><small>{selected.mrn} · {selected.age} y · {selected.sex}</small></span>
      <Icon name="chevron" className={open ? 'rotate' : ''} />
    </button>
    {open && <div className="patient-menu">
      <div className="menu-search"><Icon name="search" size={16} /><input autoFocus placeholder="Search name or MRN" value={query} onChange={(event) => setQuery(event.target.value)} /></div>
      <div className="patient-options">
        {filtered.map((patient) => <button type="button" key={patient.id} onClick={() => { onSelect(patient); setOpen(false); setQuery('') }} className={patient.id === selected.id ? 'selected' : ''}>
          <span className="avatar avatar-small">{patient.initials}</span><span><strong>{patient.name}</strong><small>{patient.mrn} · {patient.age} y</small></span>{patient.id === selected.id && <Icon name="check" size={16} />}
        </button>)}
      </div>
      <button className="create-patient" type="button" onClick={() => { setOpen(false); onCreate() }}><Icon name="plus" size={16} /> Create synthetic patient</button>
    </div>}
  </div>
}

function CreatePatientModal({ onClose, onCreate }: { onClose: () => void; onCreate: (patient: Patient) => void }) {
  const [name, setName] = useState('')
  const [dob, setDob] = useState('1985-01-01')
  const [sex, setSex] = useState('Female')
  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    if (!name.trim()) return
    const age = new Date().getFullYear() - new Date(dob).getFullYear()
    onCreate({ id: `pat-local-${Date.now()}`, name: name.trim(), initials: initials(name), age, sex, mrn: `SYN-LOCAL-${Math.floor(Math.random() * 900 + 100)}`, dob, flags: ['Synthetic demo record'] })
  }
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
    <form className="modal" onSubmit={submit} role="dialog" aria-modal="true" aria-labelledby="create-title">
      <div className="modal-head"><div><span className="eyebrow">Demo data only</span><h2 id="create-title">Create synthetic patient</h2></div><button type="button" className="icon-button" onClick={onClose} aria-label="Close"><Icon name="close" /></button></div>
      <p className="muted">This record stays in the prototype and must not contain real patient information.</p>
      <label className="form-field"><span>Name</span><input required value={name} onChange={(event) => setName(event.target.value)} placeholder="Synthetic patient name" /></label>
      <div className="form-row"><label className="form-field"><span>Date of birth</span><input type="date" value={dob} onChange={(event) => setDob(event.target.value)} /></label><label className="form-field"><span>Administrative sex</span><select value={sex} onChange={(event) => setSex(event.target.value)}><option>Female</option><option>Male</option><option>Other</option><option>Unknown</option></select></label></div>
      <div className="modal-actions"><button type="button" className="button button-secondary" onClick={onClose}>Cancel</button><button className="button button-primary" type="submit"><Icon name="plus" size={16} /> Create patient</button></div>
    </form>
  </div>
}

function FindingRow({ finding, expanded, onToggle }: { finding: Finding; expanded: boolean; onToggle: () => void }) {
  return <article className={`finding finding-${finding.severity}`}>
    <button type="button" className="finding-summary" onClick={onToggle} aria-expanded={expanded}>
      <span className="finding-icon"><Icon name={finding.severity === 'pass' ? 'check' : finding.severity === 'integrity' ? 'lock' : 'alert'} size={17} /></span>
      <span className="finding-main"><small>{finding.id}</small><strong>{finding.title}</strong><span>{finding.explanation}</span></span>
      <Badge severity={finding.severity}>{severityLabel[finding.severity]}</Badge><Icon name="chevron" className={expanded ? 'rotate-down' : ''} />
    </button>
    {expanded && <div className="finding-detail">
      <dl><div><dt>Patient fact</dt><dd>{finding.patientFact}</dd></div><div><dt>Evidence</dt><dd>{finding.evidence}</dd></div><div><dt>Source</dt><dd>{finding.source}</dd></div><div><dt>Required action</dt><dd>{finding.action}</dd></div></dl>
      <span className="certainty">{finding.certainty} certainty</span>
    </div>}
  </article>
}

interface WorkspaceProps {
  patients: Patient[]; selected: Patient; setSelected: (patient: Patient) => void; onCreate: () => void; activeScenario: Scenario | null; onClearScenario: () => void; audit: AuditEvent[]; setAudit: React.Dispatch<React.SetStateAction<AuditEvent[]>>
}

function Workspace({ patients, selected, setSelected, onCreate, activeScenario, onClearScenario, audit, setAudit }: WorkspaceProps) {
  const [request, setRequest] = useState('Recommend an option for acute lower back pain while considering the patient’s current medications.')
  const [adapter, setAdapter] = useState('deterministic')
  const [phase, setPhase] = useState<'idle' | 'generating' | 'complete'>('idle')
  const [output, setOutput] = useState('')
  const [findings, setFindings] = useState<Finding[]>([])
  const [expanded, setExpanded] = useState<string | null>(null)
  const [action, setAction] = useState<string | null>(null)
  const [overrideOpen, setOverrideOpen] = useState(false)
  const [overrideReason, setOverrideReason] = useState('')
  const [evaluationId, setEvaluationId] = useState<string | null>(null)
  const [resultVerdict, setResultVerdict] = useState<Severity | null>(null)
  const [context, setContext] = useState<any>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!activeScenario) return
    const patient = patients.find((item) => item.id === scenarioPatients[activeScenario.id])
    if (patient) setSelected(patient)
    setRequest(activeScenario.prompt)
    setOutput('')
    setFindings([])
    setPhase('idle')
    setAction(null)
    setExpanded(activeScenario.findings[0]?.id ?? null)
  }, [activeScenario, patients, setSelected])

  const verdict = resultVerdict ?? highestSeverity(findings.map((finding) => finding.severity))
  const run = async () => {
    if (!request.trim()) return
    const scenario = activeScenario
    setPhase('generating'); setOutput(''); setFindings([]); setAction(null); setError(''); setContext(null); setResultVerdict(null)
    try {
      const patientId = scenario ? scenarioPatients[scenario.id] : selected.id
      if (scenario) {
        const result = await api.runScenario(scenarioIds[scenario.id] ?? scenario.id)
        setOutput(scenario.output)
        setFindings((result.findings ?? []).map(mapFinding))
        setResultVerdict(verdictSeverity(result.verdict))
        setEvaluationId(result.evaluation_id ?? null)
        if (!result.simulated) setContext(await api.context(patientId))
      } else {
        const generated = adapter === 'external'
          ? { text: request, model: 'direct-ingestion' }
          : await api.generate({ prompt: request, adapter })
        setOutput(generated.text)
        const result = await api.evaluate({
          patient_id: patientId, ai_response: generated.text,
          source_adapter: adapter === 'external' ? 'direct' : adapter, source_model: generated.model,
        })
        setFindings((result.findings ?? []).map(mapFinding))
        setResultVerdict(verdictSeverity(result.verdict))
        setEvaluationId(result.evaluation_id)
        setContext(await api.context(patientId))
      }
      setAudit(await api.auditEvents())
      onClearScenario()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Verification failed')
      setPhase('idle')
      return
    }
    setExpanded(null); setPhase('complete')
  }

  const commitAction = async (nextAction: 'accept' | 'reject' | 'override', reason?: string) => {
    if (!evaluationId) return
    try {
      await api.action(evaluationId, { action: nextAction, actor: 'Dr. Lena Ortiz', reason: reason ?? `Clinician selected ${nextAction}` })
      setAction(nextAction); setOverrideOpen(false); setOverrideReason(''); setAudit(await api.auditEvents())
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Action could not be recorded') }
  }

  return <div className="workspace-view">
    <div className="workspace-topline"><div><span className="eyebrow">Clinical assurance session</span><h1>Verify an AI recommendation</h1><p>AI output is isolated until PramanRx independently retrieves and verifies patient context.</p>{error && <div className="callout callout-warning"><Icon name="alert" /><span>{error}</span></div>}</div><div className="session-id"><Icon name="lock" size={15} /><span>Request</span><strong>{evaluationId ? evaluationId.slice(0, 12) : 'not started'}</strong></div></div>

    <div className="workflow-strip" aria-label="Verification sequence">
      {['Clinical request', 'Untrusted AI output', 'Trusted retrieval', 'Policy verification', 'Clinician action'].map((label, index) => <div className={phase === 'complete' || index === 0 ? 'done' : phase === 'generating' && index <= 1 ? 'active' : ''} key={label}><span>{index + 1}</span>{label}{index < 4 && <Icon name="arrow" size={15} />}</div>)}
    </div>

    <section className="request-band">
      <div className="request-patient"><PatientPicker patients={patients} selected={selected} onSelect={(patient) => { setSelected(patient); setPhase('idle'); setOutput(''); setFindings([]) }} onCreate={onCreate} /><div className="patient-flags">{selected.flags.map((flag) => <span key={flag}>{flag}</span>)}</div></div>
      <div className="request-input"><label className="field-label" htmlFor="clinical-request">Clinical request or proposed plan</label><textarea id="clinical-request" rows={4} value={request} onChange={(event) => setRequest(event.target.value)} /><div className="input-meta"><span><Icon name="info" size={14} /> Sent to the selected AI adapter without the FHIR record</span><span>{request.length}/1,500</span></div></div>
      <div className="adapter-control"><label className="field-label" htmlFor="adapter">Recommendation source</label><select id="adapter" value={adapter} onChange={(event) => setAdapter(event.target.value)}><option value="deterministic">Deterministic demo</option><option value="ollama">Ollama · llama3.2:3b</option><option value="external">External AI ingestion</option></select><div className="adapter-note"><span className={`status-pulse ${adapter === 'ollama' ? 'status-warn' : ''}`} />{adapter === 'ollama' ? 'Local runtime selected' : adapter === 'external' ? 'Paste or POST a response' : 'Reliable scenario output'}</div><button type="button" className="button button-primary button-wide" onClick={run} disabled={phase === 'generating' || !request.trim()}>{phase === 'generating' ? <><span className="spinner" /> Verifying…</> : <><Icon name="spark" size={17} /> Generate & verify</>}</button></div>
    </section>

    <div className="trust-grid">
      <section className="panel untrusted-panel">
        <SectionHeading eyebrow="Untrusted boundary" title="AI recommendation" aside={<Badge>UNTRUSTED INPUT</Badge>} />
        {phase === 'idle' && <EmptyState icon="spark" title="No recommendation yet" text="The source output will appear here exactly as received, then be frozen for verification." />}
        {phase === 'generating' && <div className="loading-state"><span className="spinner spinner-dark" /><strong>Waiting for adapter</strong><p>Patient clinical context has not been shared.</p></div>}
        {phase === 'complete' && <><div className="provenance-row"><span><Icon name="server" size={14} /> {adapter === 'ollama' ? 'ollama / llama3.2:3b' : adapter === 'external' ? 'external / direct-ingestion' : 'demo / deterministic-v1'}</span><span><Icon name="clock" size={14} /> {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span><span><Icon name="lock" size={14} /> Frozen</span></div><pre className="ai-output">{output}</pre><div className="digest"><span>Recommendation digest</span><code>{formatHash('sha256:2f9e87a13e11cfe3')}</code><button className="icon-button compact" aria-label="Copy digest"><Icon name="copy" size={14} /></button></div></>}
      </section>

      <section className="panel trusted-panel">
        <SectionHeading eyebrow="Trusted boundary" title="Authoritative patient context" aside={<Badge><Icon name="shield" size={13} /> FHIR SOURCE</Badge>} />
        {phase !== 'complete' ? <EmptyState icon="lock" title="Context retrieval is gated" text="PramanRx retrieves the patient record only after the AI recommendation is frozen." /> : <>
          <div className="context-patient"><span className="avatar">{selected.initials}</span><div><strong>{selected.name}</strong><span>{selected.dob} · {selected.sex} · {selected.mrn}</span></div><Badge>Matched</Badge></div>
          <div className="context-grid">
            <div><span>Allergies</span><strong>{context?.allergies?.map((item: any) => item.description).join(', ') || 'None documented'}</strong><small>Authoritative synthetic record</small></div>
            <div><span>Active medications</span><strong>{context?.medications?.slice(0, 2).map((item: any) => item.description).join(', ') || 'None documented'}</strong><small>{context?.medications?.length ?? 0} medication records</small></div>
            <div><span>Renal function</span><strong>{context?.observations?.find((item: any) => ['33914-3','48642-3','48643-1'].includes(item.code))?.value ?? 'Not documented'}</strong><small>Latest normalized observation</small></div>
            <div><span>Pregnancy</span><strong>{context?.conditions?.some((item: any) => item.description.toLowerCase().includes('pregnan')) ? 'Active indicator' : 'Not documented'}</strong><small>Condition record</small></div>
          </div>
          <div className="context-footer"><span><Icon name="file" size={15} /> 14 FHIR resources normalized</span><button className="text-button" type="button">View source bundle <Icon name="external" size={13} /></button></div>
        </>}
      </section>
    </div>

    <section className="decision-panel">
      <div className="decision-summary">
        <div className={`verdict-mark verdict-${phase === 'complete' ? verdict : 'pending'}`}><Icon name={verdict === 'pass' ? 'check' : verdict === 'integrity' ? 'lock' : 'alert'} size={25} /></div>
        <div><span className="eyebrow">PramanRx decision</span><h2>{phase === 'complete' ? severityLabel[verdict] : 'Awaiting verification'}</h2><p>{phase === 'complete' ? findings.length ? `${findings.length} enforceable finding${findings.length === 1 ? '' : 's'} require attention before this recommendation influences care.` : 'No configured conflicts were identified with the available context.' : 'Generate or ingest a recommendation to begin independent verification.'}</p></div>
        {phase === 'complete' && <div className="decision-metrics"><span><strong>{findings.length}</strong> findings</span><span><strong>5</strong> prototype policies</span><span><strong>Local</strong> execution</span></div>}
      </div>
      {phase === 'complete' && <div className="findings-list">{findings.length ? findings.map((finding) => <FindingRow key={finding.id} finding={finding} expanded={expanded === finding.id} onToggle={() => setExpanded(expanded === finding.id ? null : finding.id)} />) : <div className="pass-message"><Icon name="check" /><div><strong>No configured conflicts found</strong><span>This is not a guarantee of clinical safety; independent clinician judgment remains required.</span></div></div>}</div>}
      {phase === 'complete' && <div className="action-bar"><div><span className="eyebrow">Clinician disposition</span><strong>{action ? `Recorded: ${action}` : evaluationId ? 'Review and record a final action' : 'Integrity simulations cannot be actioned'}</strong></div><div className="action-buttons"><button type="button" className="button button-secondary" onClick={() => commitAction('reject')} disabled={!!action || !evaluationId}><Icon name="x" size={16} /> Reject</button><button type="button" className="button button-warning" onClick={() => setOverrideOpen(true)} disabled={!!action || !evaluationId}><Icon name="alert" size={16} /> Override</button><button type="button" className="button button-success" onClick={() => commitAction('accept')} disabled={!!action || !evaluationId || verdict === 'critical' || verdict === 'integrity'}><Icon name="check" size={16} /> Accept</button></div></div>}
    </section>

    <section className="audit-inline"><SectionHeading eyebrow="This request" title="Tamper-evident audit trail" aside={<span className="verified-chain"><Icon name="shield" size={14} /> Chain verified</span>} /><div className="timeline">{audit.slice(-5).map((event, index) => <div className="timeline-event" key={event.id}><span className="timeline-node"><Icon name={event.verified ? 'check' : 'x'} size={12} /></span><time>{event.time}</time><div><strong>{event.title}</strong><span>{event.detail}</span></div><code>{formatHash(event.hash)}</code>{index < audit.slice(-5).length - 1 && <span className="timeline-line" />}</div>)}</div></section>

    {overrideOpen && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setOverrideOpen(false)}><form className="modal" onSubmit={(event) => { event.preventDefault(); if (overrideReason.trim().length >= 12) commitAction('override', overrideReason.trim()) }} role="dialog" aria-modal="true"><div className="modal-head"><div><span className="eyebrow">Audited action</span><h2>Override safety verdict</h2></div><button type="button" className="icon-button" onClick={() => setOverrideOpen(false)} aria-label="Close"><Icon name="close" /></button></div><div className="callout callout-warning"><Icon name="alert" /><span>This does not remove the finding. Your identity, reason, timestamp, and current chain hash will be recorded.</span></div><label className="form-field"><span>Clinical rationale <em>required</em></span><textarea autoFocus rows={4} value={overrideReason} onChange={(event) => setOverrideReason(event.target.value)} placeholder="Document the clinical rationale and mitigation plan…" /><small>{overrideReason.trim().length}/12 minimum characters</small></label><div className="modal-actions"><button type="button" className="button button-secondary" onClick={() => setOverrideOpen(false)}>Cancel</button><button className="button button-warning" type="submit" disabled={overrideReason.trim().length < 12}><Icon name="key" size={16} /> Record override</button></div></form></div>}
  </div>
}

function ScenariosView({ onLaunch }: { onLaunch: (scenario: Scenario) => void }) {
  const [filter, setFilter] = useState('all')
  const visible = scenarios.filter((scenario) => filter === 'all' || scenario.severity === filter)
  return <div className="page-view"><div className="page-title"><div><span className="eyebrow">Demonstration suite</span><h1>Scenario launcher</h1><p>Exercise known safety and integrity paths with repeatable synthetic cases.</p></div><Badge><Icon name="shield" size={13} /> SYNTHETIC DATA</Badge></div>
    <div className="toolbar"><div className="segmented" role="group" aria-label="Scenario filter">{[['all', 'All'], ['critical', 'Critical'], ['insufficient', 'Context'], ['integrity', 'Integrity']].map(([key, label]) => <button type="button" key={key} className={filter === key ? 'active' : ''} onClick={() => setFilter(key)}>{label}</button>)}</div><span>{visible.length} scenarios</span></div>
    <div className="scenario-grid">{visible.map((scenario, index) => <article className="scenario-card" key={scenario.id}><div className="scenario-top"><span className="scenario-number">{String(index + 1).padStart(2, '0')}</span><Badge severity={scenario.severity}>{severityLabel[scenario.severity]}</Badge></div><h2>{scenario.title}</h2><p>{scenario.summary}</p><div className="scenario-rule"><span>Expected result</span><strong>{scenario.findings[0]?.id ?? 'No finding'}</strong></div><button className="button button-secondary button-wide" type="button" onClick={() => onLaunch(scenario)}><Icon name="play" size={15} /> Run scenario</button></article>)}</div>
  </div>
}

function AuditView({ events }: { events: AuditEvent[] }) {
  const [selected, setSelected] = useState(events[events.length - 1] ?? seedAudit[0])
  const [query, setQuery] = useState('')
  const filtered = [...events].reverse().filter((event) => `${event.title} ${event.detail} ${event.actor}`.toLowerCase().includes(query.toLowerCase()))
  return <div className="page-view"><div className="page-title"><div><span className="eyebrow">Forensic record</span><h1>Audit explorer</h1><p>Inspect provenance, actions, and the SHA-256 chain for every assurance request.</p></div><div className="page-actions"><button className="button button-secondary"><Icon name="refresh" size={15} /> Verify chain</button><button className="button button-secondary"><Icon name="external" size={15} /> Export record</button></div></div>
    <div className="stats-row"><div><span>Chain state</span><strong className="good-text"><Icon name="shield" size={17} /> Verified</strong></div><div><span>Events indexed</span><strong>1,284</strong></div><div><span>Last verification</span><strong>34 sec ago</strong></div><div><span>Hash algorithm</span><strong>SHA-256</strong></div></div>
    <div className="audit-layout"><section className="table-panel"><div className="table-toolbar"><div className="menu-search"><Icon name="search" size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search events" /></div><button className="icon-button" aria-label="Filter events"><Icon name="filter" size={17} /></button></div><div className="audit-table" role="table"><div className="audit-row audit-header" role="row"><span>Time</span><span>Event</span><span>Actor</span><span>Integrity</span></div>{filtered.map((event) => <button type="button" className={`audit-row ${selected.id === event.id ? 'selected' : ''}`} key={event.id} onClick={() => setSelected(event)}><time>{event.time}</time><span><strong>{event.title}</strong><small>{event.detail}</small></span><span>{event.actor}</span><span className={event.verified ? 'good-text' : 'critical-text'}><Icon name={event.verified ? 'check' : 'x'} size={14} /> {event.verified ? 'Verified' : 'Failed'}</span></button>)}</div></section>
      <aside className="detail-panel"><span className="eyebrow">Event detail</span><h2>{selected.title}</h2><p>{selected.detail}</p><dl className="detail-list"><div><dt>Event ID</dt><dd><code>{selected.id}</code></dd></div><div><dt>Timestamp</dt><dd>{selected.time}</dd></div><div><dt>Actor</dt><dd>{selected.actor}</dd></div><div><dt>Event hash</dt><dd><code>{selected.hash}</code></dd></div><div><dt>Previous hash</dt><dd><code>sha256:913ac514e618bf99</code></dd></div></dl><div className="callout callout-success"><Icon name="shield" /><span><strong>Cryptographically linked</strong>This event matches its payload and previous chain hash.</span></div></aside>
    </div>
  </div>
}

const kbSources = [
  { name: 'RxTerms', version: '2026.10', records: '18,432 concepts', use: 'Medication normalization', state: 'Verified' },
  { name: 'RxNorm / RxClass', version: '2026.10', records: '4 selected snapshots', use: 'Ingredient and class mapping', state: 'Verified' },
  { name: 'DDInter', version: '2025 snapshot', records: '222,383 pairs', use: 'Drug-drug interactions', state: 'Verified' },
  { name: 'openFDA labels', version: '2026-09-18', records: 'Selected labels', use: 'Warnings and dosing evidence', state: 'Verified' },
  { name: 'PramanRx policies', version: '0.4.0', records: '18 policies', use: 'Enforceable local rules', state: 'Signed' },
]

function KnowledgeView() {
  const [selected, setSelected] = useState(kbSources[0])
  return <div className="page-view"><div className="page-title"><div><span className="eyebrow">Verified local artifact</span><h1>Knowledge base inspector</h1><p>Trace every compiled rule back to immutable source snapshots and transformation metadata.</p></div><Badge><Icon name="shield" size={13} /> SIGNATURE VALID</Badge></div>
    <div className="kb-banner"><div className="kb-seal"><Icon name="shield" size={25} /></div><div><span className="eyebrow">Active artifact</span><h2>prx-kb-2026.10.0</h2><p>Compiled 06 Oct 2026 · schema 1.3 · transformation prx-compiler 0.4.0</p></div><div className="kb-signature"><span>Ed25519 fingerprint</span><code>7A:31:8C:91:0F:2D:44:A8</code><strong><Icon name="check" size={14} /> Verified at startup</strong></div></div>
    <div className="content-split"><section className="table-panel"><div className="table-title"><div><h2>Source inventory</h2><span>5 immutable snapshots</span></div><button className="button button-secondary"><Icon name="refresh" size={15} /> Re-verify</button></div><div className="source-table"><div className="source-row source-head"><span>Source</span><span>Version</span><span>Records</span><span>State</span></div>{kbSources.map((source) => <button type="button" className={`source-row ${selected.name === source.name ? 'selected' : ''}`} key={source.name} onClick={() => setSelected(source)}><span><Icon name="database" size={16} /><strong>{source.name}</strong><small>{source.use}</small></span><span>{source.version}</span><span>{source.records}</span><span className="good-text"><Icon name="check" size={14} /> {source.state}</span></button>)}</div></section>
      <aside className="detail-panel"><span className="eyebrow">Source provenance</span><h2>{selected.name}</h2><p>{selected.use}</p><dl className="detail-list"><div><dt>Source file</dt><dd><code>{selected.name.toLowerCase().replaceAll(' ', '_')}_snapshot.json</code></dd></div><div><dt>Retrieved</dt><dd>22 Sep 2026</dd></div><div><dt>Checksum</dt><dd><code>0a91c77b…f64e82</code></dd></div><div><dt>License / terms</dt><dd>{selected.name === 'DDInter' ? 'CC BY-NC-SA 4.0' : 'See source manifest'}</dd></div><div><dt>Policy author</dt><dd>PramanRx research team</dd></div></dl><button className="text-button">Open source manifest <Icon name="external" size={13} /></button></aside>
    </div>
    <div className="callout callout-neutral"><Icon name="info" /><span><strong>Prototype knowledge scope</strong>These selected sources demonstrate traceable verification. They are not complete, clinically validated, or suitable for patient care.</span></div>
  </div>
}

function IntegrationView() {
  const adapters = [
    { icon: 'spark' as IconName, name: 'Deterministic demo', id: 'deterministic-v1', status: 'Ready', detail: 'Repeatable outputs for all demonstration scenarios.' },
    { icon: 'server' as IconName, name: 'Ollama local model', id: 'llama3.2:3b', status: 'Available', detail: 'Local recommendation generation through Ollama.' },
    { icon: 'plug' as IconName, name: 'Direct ingestion', id: 'external-v1', status: 'Ready', detail: 'Accepts recommendations from any external AI product.' },
  ]
  return <div className="page-view"><div className="page-title"><div><span className="eyebrow">AI-agnostic boundary</span><h1>Integrations & adapters</h1><p>Connect recommendation sources through one strict contract without granting access to trusted context.</p></div><button className="button button-primary"><Icon name="plus" size={16} /> Register adapter</button></div>
    <div className="adapter-grid">{adapters.map((adapter) => <article className="adapter-card" key={adapter.id}><div className="adapter-card-top"><span className="adapter-icon"><Icon name={adapter.icon} /></span><span className="good-text"><span className="status-pulse" /> {adapter.status}</span></div><h2>{adapter.name}</h2><code>{adapter.id}</code><p>{adapter.detail}</p><div className="adapter-permissions"><span><Icon name="check" size={13} /> Clinical request</span><span><Icon name="x" size={13} /> Patient FHIR record</span><span><Icon name="x" size={13} /> Knowledge artifact</span></div><button className="button button-secondary button-wide">Configure <Icon name="chevron" size={14} /></button></article>)}</div>
    <div className="integration-lower"><section className="code-panel"><div className="code-head"><div><span className="eyebrow">Recommendation contract</span><h2>POST /api/recommendations/ingest</h2></div><Badge>v1.2</Badge></div><pre>{`{
  "request_id": "req_8F31",
  "patient_id": "pat-01091",
  "recommendation": {
    "raw_text": "Start ibuprofen 600 mg...",
    "medications": [{ "name": "ibuprofen", "dose": "600 mg" }]
  },
  "source": {
    "adapter_id": "external-v1",
    "model": "vendor/model-version",
    "generated_at": "2026-10-06T14:42:18Z"
  }
}`}</pre><button className="copy-code"><Icon name="copy" size={14} /> Copy example</button></section>
      <section className="contract-rules"><span className="eyebrow">Boundary guarantees</span><h2>Adapter isolation</h2>{[['lock', 'No trusted context', 'Adapters never receive the authoritative FHIR bundle in the primary demo flow.'], ['file', 'Raw output preserved', 'Malformed and partial responses remain visible and are never silently discarded.'], ['key', 'Replay-resistant identity', 'Request IDs, timestamps, and recommendation digests bind every evaluation.']].map(([icon, title, text]) => <div className="guarantee" key={title}><span><Icon name={icon as IconName} size={17} /></span><div><strong>{title}</strong><p>{text}</p></div></div>)}</section>
    </div>
  </div>
}

function ArchitectureView() {
  return <div className="page-view"><div className="page-title"><div><span className="eyebrow">System model</span><h1>Architecture & trust boundary</h1><p>See where untrusted recommendations stop and independent verification begins.</p></div><Badge>PRIMARY DEMO FLOW</Badge></div>
    <section className="architecture-map" aria-label="PramanRx architecture diagram">
      <div className="zone zone-untrusted"><div className="zone-label"><Icon name="alert" size={15} /><span>Untrusted zone</span></div><div className="arch-node"><span className="arch-icon"><Icon name="user" /></span><strong>Clinician request</strong><small>Question or proposed plan</small></div><Icon name="arrow" className="arch-arrow" /><div className="arch-node"><span className="arch-icon"><Icon name="spark" /></span><strong>AI adapter</strong><small>Local or external model</small></div><Icon name="arrow" className="arch-arrow" /><div className="arch-node emphasized"><span className="arch-icon"><Icon name="lock" /></span><strong>Frozen output</strong><small>Immutable + provenance</small></div></div>
      <div className="boundary-line"><span>PRAMANRX TRUST BOUNDARY</span></div>
      <div className="zone zone-trusted"><div className="zone-label"><Icon name="shield" size={15} /><span>Verified zone</span></div><div className="arch-node"><span className="arch-icon"><Icon name="database" /></span><strong>Patient context</strong><small>FHIR-compatible source</small></div><span className="plus-symbol">+</span><div className="arch-node"><span className="arch-icon"><Icon name="shield" /></span><strong>Signed knowledge</strong><small>Versioned local artifact</small></div><span className="plus-symbol">+</span><div className="arch-node"><span className="arch-icon"><Icon name="architecture" /></span><strong>Policy engine</strong><small>Deterministic rules</small></div><Icon name="arrow" className="arch-arrow" /><div className="arch-node emphasized trusted"><span className="arch-icon"><Icon name="check" /></span><strong>Decision package</strong><small>Findings + evidence</small></div></div>
      <div className="arch-audit"><Icon name="audit" /><div><strong>Tamper-evident audit chain</strong><span>Every transition, verdict, and clinician action is hash-linked and attributable.</span></div><code>evt₁ → evt₂ → evt₃ → evtₙ</code></div>
    </section>
    <div className="threat-grid"><div className="threat-intro"><span className="eyebrow">Threat model</span><h2>Designed for compromised inputs</h2><p>PramanRx assumes a recommendation source can be wrong, manipulated, malformed, stale, or malicious.</p></div>{['Prompt injection in output', 'Patient identity mismatch', 'Stale knowledge artifact', 'Unauthorized override', 'Audit record tampering', 'Malformed recommendation'].map((threat) => <div className="threat-item" key={threat}><Icon name="shield" size={16} /><span>{threat}</span><Badge>Mitigated</Badge></div>)}</div>
  </div>
}

function StatusView({ apiOnline }: { apiOnline: boolean }) {
  const services = [
    { name: 'PramanRx API', detail: '/api/status', status: apiOnline ? 'Connected' : 'Demo fallback', tone: apiOnline ? 'good' : 'warn', latency: apiOnline ? '12 ms' : 'Local UI' },
    { name: 'SQLite persistence', detail: 'Patient, evaluation, and audit store', status: 'Ready', tone: 'good', latency: '4 ms' },
    { name: 'Knowledge artifact', detail: 'prx-kb-2026.10.0', status: 'Verified', tone: 'good', latency: '124 ms' },
    { name: 'Ollama runtime', detail: 'llama3.2:3b', status: 'Available', tone: 'good', latency: 'Local' },
    { name: 'Audit chain', detail: '1,284 events', status: 'Verified', tone: 'good', latency: '34 sec ago' },
  ]
  return <div className="page-view"><div className="page-title"><div><span className="eyebrow">Operational readiness</span><h1>System status</h1><p>Runtime health, integrity controls, and local service availability.</p></div><div className={`overall-status ${apiOnline ? '' : 'degraded'}`}><span className="status-pulse" /><div><strong>{apiOnline ? 'All systems operational' : 'Frontend demo mode'}</strong><small>{apiOnline ? 'Last checked just now' : 'API unavailable · fallback data active'}</small></div></div></div>
    <section className="status-list"><div className="status-list-head"><h2>Local services</h2><button className="button button-secondary"><Icon name="refresh" size={15} /> Run checks</button></div>{services.map((service) => <div className="service-row" key={service.name}><span className={`service-icon ${service.tone}`}><Icon name={service.name.includes('Knowledge') ? 'database' : service.name.includes('Audit') ? 'audit' : 'server'} /></span><div><strong>{service.name}</strong><small>{service.detail}</small></div><span className={`service-state ${service.tone}`}><span className="status-pulse" /> {service.status}</span><code>{service.latency}</code></div>)}</section>
    <div className="status-lower"><section><span className="eyebrow">Integrity checks</span><h2>Startup verification</h2>{['Source manifest checksums', 'Compiled artifact schema', 'Ed25519 artifact signature', 'Audit chain head', 'Database migrations'].map((check) => <div className="check-row" key={check}><Icon name="check" size={15} /><span>{check}</span><small>Passed</small></div>)}</section><section><span className="eyebrow">Environment</span><h2>Research prototype</h2><dl className="detail-list"><div><dt>Deployment</dt><dd>Local workstation</dd></div><div><dt>API contract</dt><dd>v1.2</dd></div><div><dt>Policy set</dt><dd>0.4.0</dd></div><div><dt>Data</dt><dd>Synthetic only</dd></div></dl><div className="callout callout-warning"><Icon name="alert" /><span>Not clinically validated or suitable for patient care.</span></div></section></div>
  </div>
}

export default function App() {
  const [view, setView] = useState<ViewKey>('workspace')
  const [mobileNav, setMobileNav] = useState(false)
  const [patientList, setPatientList] = useState(seedPatients)
  const [selectedPatient, setSelectedPatient] = useState(seedPatients[1])
  const [createOpen, setCreateOpen] = useState(false)
  const [activeScenario, setActiveScenario] = useState<Scenario | null>(null)
  const [audit, setAudit] = useState(seedAudit)
  const [apiOnline, setApiOnline] = useState(false)

  useEffect(() => {
    Promise.all([api.status(), api.patients()]).then(([, loaded]) => {
      setApiOnline(true)
      setPatientList(loaded)
      setSelectedPatient(loaded.find((patient) => patient.id === 'demo-warfarin') ?? loaded[0] ?? seedPatients[1])
    }).catch(() => setApiOnline(false))
    api.auditEvents().then(setAudit).catch(() => undefined)
  }, [])
  const currentLabel = useMemo(() => navItems.find((item) => item.key === view)?.label, [view])
  const navigate = (next: ViewKey) => { setView(next); setMobileNav(false); window.scrollTo({ top: 0, behavior: 'smooth' }) }
  const launchScenario = (scenario: Scenario) => { setActiveScenario(scenario); navigate('workspace') }

  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Skip to main content</a>
    <aside className={`sidebar ${mobileNav ? 'open' : ''}`}>
      <div className="brand"><span className="brand-mark"><Icon name="shield" size={23} /></span><div><strong>Praman<span>Rx</span></strong><small>Clinical AI assurance</small></div><button className="icon-button nav-close" aria-label="Close navigation" onClick={() => setMobileNav(false)}><Icon name="close" /></button></div>
      <nav aria-label="Main navigation">{navItems.map((item) => <button type="button" key={item.key} className={view === item.key ? 'active' : ''} onClick={() => navigate(item.key)}><Icon name={item.icon} /><span>{item.label}</span>{item.key === 'status' && <span className="nav-live" />}</button>)}</nav>
      <div className="sidebar-foot"><div className="environment"><span className="status-pulse" /><div><strong>Research environment</strong><small>Synthetic data only</small></div></div><div className="user-chip"><span className="avatar avatar-small">LO</span><div><strong>Dr. Lena Ortiz</strong><small>Demo clinician</small></div><Icon name="chevron" size={14} /></div></div>
    </aside>
    {mobileNav && <button className="nav-scrim" aria-label="Close navigation" onClick={() => setMobileNav(false)} />}
    <div className="app-main">
      <header className="topbar"><button className="icon-button menu-button" aria-label="Open navigation" onClick={() => setMobileNav(true)}><Icon name="menu" /></button><span className="mobile-title">{currentLabel}</span><div className="topbar-context"><Icon name="shield" size={15} /><span>Independent verification active</span></div><div className="topbar-right"><span className={`api-indicator ${apiOnline ? '' : 'offline'}`}><span className="status-pulse" /> {apiOnline ? 'API connected' : 'Demo mode'}</span><button className="icon-button" aria-label="System information"><Icon name="info" /></button></div></header>
      <main id="main-content">
        {view === 'workspace' && <Workspace patients={patientList} selected={selectedPatient} setSelected={setSelectedPatient} onCreate={() => setCreateOpen(true)} activeScenario={activeScenario} onClearScenario={() => setActiveScenario(null)} audit={audit} setAudit={setAudit} />}
        {view === 'scenarios' && <ScenariosView onLaunch={launchScenario} />}
        {view === 'audit' && <AuditView events={audit} />}
        {view === 'knowledge' && <KnowledgeView />}
        {view === 'integration' && <IntegrationView />}
        {view === 'architecture' && <ArchitectureView />}
        {view === 'status' && <StatusView apiOnline={apiOnline} />}
      </main>
    </div>
    {createOpen && <CreatePatientModal onClose={() => setCreateOpen(false)} onCreate={(draft) => {
      const [firstName, ...rest] = draft.name.split(' ')
      api.createPatient({ first_name: firstName, last_name: rest.join(' ') || 'Synthetic', birth_date: draft.dob,
        gender: draft.sex === 'Female' ? 'F' : draft.sex === 'Male' ? 'M' : draft.sex === 'Other' ? 'X' : 'U' })
        .then((patient) => { setPatientList((list) => [patient, ...list]); setSelectedPatient(patient); setCreateOpen(false) })
        .catch(() => undefined)
    }} />}
  </div>
}
