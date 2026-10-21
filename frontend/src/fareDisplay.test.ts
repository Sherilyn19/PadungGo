import { describe, expect, it } from 'vitest'
import { fareDisplay } from './fareDisplay'

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
      reason: null,
    })
  })

  it('uses the single label Approximate and preserves the explanation', () => {
    expect(
      fareDisplay({
        amount_centavos: 1950,
        status: 'approximate',
        reason: 'Based on an estimated ride distance.',
      }),
    ).toEqual({
      text: '₱19.50 · Approximate',
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
      text: 'Fare unavailable',
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
      text: 'Fare unavailable',
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
      text: 'Fare unavailable',
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
        text: 'Fare unavailable',
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
      reason: null,
    })
  })
})
