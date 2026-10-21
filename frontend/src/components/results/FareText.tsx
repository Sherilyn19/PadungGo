import type { FareDisplay } from '../../fareDisplay'
import InfoTip from '../ui/InfoTip'

// Why PadungGo sometimes has no price: fares are only shown when backed by the
// official fare guide and verified route data, never guessed.
const NO_FARE_INFO =
  'PadungGo only shows a fare when it can be checked against the official LTFRB fare guide and verified route data, so it never guesses. The driver can tell you the exact amount.'

export default function FareText({ fare, withInfo = true, short = false }: { fare: FareDisplay; withInfo?: boolean; short?: boolean }) {
  if (!fare.amount) {
    return (
      <span className="inline-flex items-center gap-1">
        <span>{short ? 'Ask driver' : 'Ask the driver for the fare'}</span>
        {withInfo && (
          <InfoTip label="About the fare">
            {NO_FARE_INFO}
            {fare.reason && <span className="mt-1 block text-ink-soft">Details: {fare.reason}</span>}
          </InfoTip>
        )}
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="font-semibold text-ink">{fare.amount}</span>
      {fare.estimated && <span className="badge badge-blue h-5 px-1 text-[10px]">Estimated</span>}
      {withInfo && fare.reason && <InfoTip label="About the fare">{fare.reason}</InfoTip>}
    </span>
  )
}
