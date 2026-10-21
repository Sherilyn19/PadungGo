import type { FareAmount } from './api'
import { formatFare } from './format'

export interface FareDisplay {
  // Short commuter-facing text, e.g. "₱14.00", "₱14.00 Estimated", "Ask the driver".
  text: string
  // Formatted amount when one is supported, otherwise null.
  amount: string | null
  estimated: boolean
  // Backend explanation, kept for the info tooltip rather than the main screen.
  reason: string | null
}

export const ASK_DRIVER = 'Ask the driver'

// The backend supplies the evidence classification.
// This helper formats it; it never calculates or upgrades a fare.
export function fareDisplay(fare: FareAmount): FareDisplay {
  const validAmount =
    typeof fare.amount_centavos === 'number' &&
    Number.isSafeInteger(fare.amount_centavos) &&
    fare.amount_centavos >= 0

  const supportedStatus = fare.status === 'exact' || fare.status === 'approximate'

  if (!validAmount || !supportedStatus) {
    return {
      text: ASK_DRIVER,
      amount: null,
      estimated: false,
      reason:
        fare.status === 'unavailable'
          ? fare.reason?.trim() || 'No supported fare calculation.'
          : 'No supported fare calculation.',
    }
  }

  const amount = formatFare(fare.amount_centavos)
  const estimated = fare.status === 'approximate'
  return {
    text: estimated ? `${amount} Estimated` : amount,
    amount,
    estimated,
    reason: fare.reason?.trim() || null,
  }
}

// Trip total: only shown when every ride has a supported fare.
export function totalFareDisplay(fare: {
  total_centavos: number | null
  total_is_complete: boolean
  status: FareAmount['status']
  reason: string | null
}): FareDisplay {
  return fareDisplay({
    amount_centavos: fare.total_is_complete ? fare.total_centavos : null,
    status: fare.total_is_complete ? fare.status : 'unavailable',
    reason: fare.reason,
  })
}
