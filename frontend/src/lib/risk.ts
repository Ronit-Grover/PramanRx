import type { Severity } from '../types'

const rank: Record<Severity, number> = {
  pass: 0,
  caution: 1,
  insufficient: 2,
  critical: 3,
  integrity: 4,
}

export function highestSeverity(values: Severity[]): Severity {
  return values.reduce<Severity>((highest, value) => rank[value] > rank[highest] ? value : highest, 'pass')
}

export function formatHash(value: string): string {
  return value.length <= 16 ? value : `${value.slice(0, 8)}...${value.slice(-6)}`
}

export function initials(name: string): string {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join('')
}
