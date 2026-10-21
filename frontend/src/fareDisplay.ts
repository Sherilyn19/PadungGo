import type { FareAmount } from './api'
import { formatFare } from './format'

export interface FareDisplay {
  text: string
  reason: string | null
}

// The backend supplies the evidence classification.
// This helper formats it; it never calculates or upgrades a fare.
export function fareDisplay(fare: FareAmount): FareDisplay {
  const validAmount =
    typeof fare.amount_centavos === 'number' &&
    Number.isSafeInteger(fare.amount_centavos) &&
    fare.amount_centavos >= 0

  const supportedStatus =
    fare.status === 'exact' || fare.status === 'approximate'

  if (!validAmount || !supportedStatus) {
    return {
      text: 'Fare unavailable',
      reason:
        fare.status === 'unavailable'
          ? fare.reason?.trim() || 'No supported fare calculation.'
          : 'No supported fare calculation.',
    }
  }

  const amount = formatFare(fare.amount_centavos)

  return {
    text:
      fare.status === 'approximate'
        ? `${amount} · Approximate`
        : amount,
    reason: fare.reason?.trim() || null,
  }
}
