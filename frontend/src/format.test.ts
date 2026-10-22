import { describe, expect, it } from 'vitest'
import { explainRanking, explainReason, formatCalendarDate, formatDistance, formatMinimumDistance, formatDuration, formatFare, formatFareRange, titleCase } from './format'

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
    expect(formatDuration(3900)).toBe('1 hr 5 min')
    expect(formatDistance(3410)).toBe('3.4 km')
    expect(formatDistance(450)).toBe('450 meters')
  })

  it('explains empty-result reasons', () => {
    expect(explainReason(null)).toBe('')
    expect(explainReason('same_location')).toMatch(/same place/)
    expect(explainReason('something_new')).toMatch(/couldn’t find a trip/)
  })

  it('title-cases route names', () => {
    expect(titleCase('GUADALUPE - CARBON - CAPITOL')).toBe('Guadalupe - Carbon - Capitol')
    expect(titleCase('PARDO (BULACAO/ST. PAUL)')).toBe('Pardo (Bulacao/St. Paul)')
  })

  it('explains ranking fallbacks in plain language', () => {
    expect(explainRanking({ requested: 'fastest', applied: 'fewest_transfers', warning: 'Cannot fairly rank' })).toBe(
      'Can’t sort by fastest yet, so trips are shown by fewest transfers.',
    )
    expect(explainRanking({ requested: 'cheapest', applied: 'cheapest', warning: null })).toBeNull()
  })
})

describe('money formatting with whole centavos', () => {
  it('always shows exactly two decimals without floating-point drift', () => {
    expect(formatFare(1825)).toBe('₱18.25')
    expect(formatFare(1835)).toBe('₱18.35')
    expect(formatFare(5)).toBe('₱0.05')
    expect(formatFare(12750)).toBe('₱127.50')
  })

  it('refuses fractional or negative centavos', () => {
    expect(formatFare(18.5)).toBe('Unknown')
    expect(formatFare(-100)).toBe('Unknown')
  })

  it('shows one amount when the range has no spread', () => {
    expect(formatFareRange(1800, 1800)).toBe('₱18.00')
    expect(formatFareRange(1800, 2175)).toBe('₱18.00–₱21.75')
  })
})

describe('commuter-friendly time and distance', () => {
  it('shows hours and minutes for long rides', () => {
    expect(formatDuration(75 * 60)).toBe('1 hr 15 min')
    expect(formatDuration(120 * 60)).toBe('2 hr')
    expect(formatDuration(224 * 60)).toBe('3 hr 44 min')
  })

  it('spells out meters', () => {
    expect(formatDistance(224)).toBe('224 meters')
    expect(formatDistance(1)).toBe('1 meter')
    expect(formatDistance(999.6)).toBe('1.0 km')
    expect(formatDistance(1260)).toBe('1.3 km')
  })
})

describe('formatCalendarDate', () => {
  it('formats the server date without time-zone shifts', () => {
    expect(formatCalendarDate('2026-10-18')).toBe('Oct 18, 2026')
    expect(formatCalendarDate('2026-01-01')).toBe('Jan 1, 2026')
  })

  it('returns nothing for missing or malformed dates', () => {
    expect(formatCalendarDate(null)).toBeNull()
    expect(formatCalendarDate(undefined)).toBeNull()
    expect(formatCalendarDate('2026-13-01')).toBeNull()
    expect(formatCalendarDate('Oct 18')).toBeNull()
  })
})

describe('formatMinimumDistance', () => {
  it('puts the plus before the unit', () => {
    expect(formatMinimumDistance(547)).toBe('547+ meters')
    expect(formatMinimumDistance(1240)).toBe('1.2+ km')
  })
})
