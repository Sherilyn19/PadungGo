import { describe, expect, it } from 'vitest'
import { hasSortChoice, SORT_OPTIONS } from './sortOptions'

// These orders fall back to "fewest transfers" on the server today, so the app
// must not offer them. When the data exists, add the option and update this test.
describe('sort options', () => {
  it('offers only orders the planner can really apply', () => {
    expect(SORT_OPTIONS.map((o) => o.value)).toEqual(['fewest_transfers'])
  })

  it.each(['cheapest', 'fastest', 'least_walking'])('does not offer %s while it cannot be applied', (value) => {
    expect(SORT_OPTIONS.some((o) => o.value === value)).toBe(false)
  })

  it('hides the picker while there is nothing to choose', () => {
    expect(hasSortChoice).toBe(SORT_OPTIONS.length > 1)
    expect(hasSortChoice).toBe(false)
  })

  it('always includes the default order the app starts with', () => {
    expect(SORT_OPTIONS.some((o) => o.value === 'fewest_transfers')).toBe(true)
  })
})
