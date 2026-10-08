import { describe, expect, it } from 'vitest'
import { formatHash, highestSeverity, initials } from './risk'

describe('risk helpers', () => {
  it('returns the most restrictive severity', () => {
    expect(highestSeverity(['pass', 'critical', 'caution'])).toBe('critical')
    expect(highestSeverity(['critical', 'integrity'])).toBe('integrity')
  })

  it('formats identifiers for scanning', () => {
    expect(formatHash('sha256:2f9e87a13e11cfe3')).toBe('sha256:2...11cfe3')
    expect(initials('Maya Thompson')).toBe('MT')
  })
})
