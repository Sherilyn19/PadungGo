import { describe, expect, it } from 'vitest'
import { fareDisplay, totalFareDisplay } from './fareDisplay'

describe('fareDisplay', () => {
  it('shows an exact amount without an uncertainty label', () => {
    expect(
      fareDisplay({
        amount_centavos: 1950,
        status: 'exact',
        reason: null,
      }),
    ).toEqual({
      text: '₱19.50',
      amount: '₱19.50',
      estimated: false,
      reason: null,
    })
  })

  it('labels approximate fares Estimated and preserves the explanation', () => {
    expect(
      fareDisplay({
        amount_centavos: 1950,
        status: 'approximate',
        reason: 'Based on an estimated ride distance.',
      }),
    ).toEqual({
      text: '₱19.50 Estimated',
      amount: '₱19.50',
      estimated: true,
      reason: 'Based on an estimated ride distance.',
    })
  })

  it('shows the backend reason when no amount is supported', () => {
    expect(
      fareDisplay({
        amount_centavos: null,
        status: 'unavailable',
        reason: 'Fare depends on the vehicle you board.',
      }),
    ).toEqual({
      text: 'Ask the driver',
      amount: null,
      estimated: false,
      reason: 'Fare depends on the vehicle you board.',
    })
  })

  it('never displays a stale amount classified as unavailable', () => {
    expect(
      fareDisplay({
        amount_centavos: 1950,
        status: 'unavailable',
        reason: 'No applicable fare rule.',
      }),
    ).toEqual({
      text: 'Ask the driver',
      amount: null,
      estimated: false,
      reason: 'No applicable fare rule.',
    })
  })

  it('uses a truthful fallback when no reason is supplied', () => {
    expect(
      fareDisplay({
        amount_centavos: null,
        status: 'unavailable',
        reason: '   ',
      }),
    ).toEqual({
      text: 'Ask the driver',
      amount: null,
      estimated: false,
      reason: 'No supported fare calculation.',
    })
  })

  it('rejects missing, negative, fractional and non-finite amounts', () => {
    for (const amount of [
      null,
      -1,
      19.5,
      Number.NaN,
      Number.POSITIVE_INFINITY,
      Number.MAX_SAFE_INTEGER + 1,
    ]) {
      expect(
        fareDisplay({
          amount_centavos: amount,
          status: 'exact',
          reason: null,
        }),
      ).toEqual({
        text: 'Ask the driver',
      amount: null,
      estimated: false,
        reason: 'No supported fare calculation.',
      })
    }
  })

  it('preserves an explicitly supported zero amount', () => {
    expect(
      fareDisplay({
        amount_centavos: 0,
        status: 'exact',
        reason: null,
      }),
    ).toEqual({
      text: '₱0.00',
      amount: '₱0.00',
      estimated: false,
      reason: null,
    })
  })

  it('shows a trip total only when every ride has a supported fare', () => {
    const base = { total_centavos: 2800, status: 'approximate' as const, reason: null }
    expect(totalFareDisplay({ ...base, total_is_complete: true }).text).toBe('₱28.00 Estimated')
    const partial = totalFareDisplay({ ...base, total_is_complete: false, reason: 'One ride has no fare.' })
    expect(partial).toEqual({ text: 'Ask the driver', amount: null, estimated: false, reason: 'One ride has no fare.' })
  })
})
