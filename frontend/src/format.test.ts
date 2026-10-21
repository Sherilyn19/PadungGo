import { describe, expect, it } from 'vitest'
import { explainRanking, explainReason, formatDistance, formatDuration, formatFare, titleCase } from './format'

describe('format helpers', () => {
  it('never shows unknown values as zero', () => {
    expect(formatFare(null)).toBe('Unknown')
    expect(formatDuration(null)).toBe('Unknown')
    expect(formatDistance(undefined)).toBe('Unknown')
    expect(formatFare(0)).toBe('₱0.00')
  })

  it('formats money, time and distance', () => {
    expect(formatFare(1300)).toBe('₱13.00')
    expect(formatDuration(605)).toBe('10 min')
    expect(formatDuration(3900)).toBe('1 h 5 min')
    expect(formatDistance(3410)).toBe('3.4 km')
    expect(formatDistance(450)).toBe('450 m')
  })

  it('explains empty-result reasons', () => {
    expect(explainReason(null)).toBe('')
    expect(explainReason('same_location')).toMatch(/same place/)
    expect(explainReason('something_new')).toMatch(/No journey/)
  })

  it('title-cases route names', () => {
    expect(titleCase('GUADALUPE - CARBON - CAPITOL')).toBe('Guadalupe - Carbon - Capitol')
    expect(titleCase('PARDO (BULACAO/ST. PAUL)')).toBe('Pardo (Bulacao/St. Paul)')
  })

  it('explains ranking fallbacks in plain language', () => {
    expect(explainRanking({ requested: 'fastest', applied: 'fewest_transfers', warning: 'Cannot fairly rank' })).toBe(
      'Sorted by fewest transfers, because not every trip has a known value for “fastest”.',
    )
    expect(explainRanking({ requested: 'cheapest', applied: 'cheapest', warning: null })).toBeNull()
  })
})
