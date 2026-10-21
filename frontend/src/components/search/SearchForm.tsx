import { ArrowDownWideNarrow, ArrowUpDown, ChevronDown, Search } from 'lucide-react'
import type { Place, SortBy } from '../../api'
import LoadingButton from '../ui/LoadingButton'
import PlaceInput from './PlaceInput'

export type PickTarget = 'origin' | 'destination'

interface Props {
  origin: Place | null
  destination: Place | null
  onOriginChange: (place: Place | null) => void
  onDestinationChange: (place: Place | null) => void
  picking: PickTarget | null
  onPick: (target: PickTarget | null) => void
  onSwap: () => void
  sortBy: SortBy
  onSortChange: (sort: SortBy) => void
  maxTransfers: 0 | 1
  onMaxTransfersChange: (value: 0 | 1) => void
  loading: boolean
  onSubmit: () => void
}

const SORT_OPTIONS: { value: SortBy; label: string }[] = [
  { value: 'fewest_transfers', label: 'Fewest transfers' },
  { value: 'cheapest', label: 'Cheapest' },
  { value: 'fastest', label: 'Fastest' },
  { value: 'least_walking', label: 'Least walking' },
]

export default function SearchForm(props: Props) {
  const { origin, destination, picking, onPick, loading } = props
  const ready = Boolean(origin && destination)

  return (
    <form
      className="card p-3"
      aria-label="Plan a trip"
      onSubmit={(e) => {
        e.preventDefault()
        if (ready && !loading) props.onSubmit()
      }}
    >
      <div className="flex gap-2.5">
        {/* Start and destination markers joined by a dotted line, matching the map. */}
        <div className="flex w-4 shrink-0 flex-col items-center pt-[30px] pb-[14px]" aria-hidden="true">
          <span className="h-3.5 w-3.5 rounded-full border-[3px] border-brand-500 bg-white" />
          <span className="my-1 w-0 flex-1 border-l-2 border-dotted border-brand-300" />
          <span className="h-3.5 w-3.5 rounded-[3px] bg-alert ring-2 ring-white outline outline-1 outline-alert" />
        </div>
        <div className="min-w-0 flex-1 space-y-2.5">
          <PlaceInput
            label="From"
            placeholder="Where are you starting?"
            value={origin}
            onChange={props.onOriginChange}
            picking={picking === 'origin'}
            onPickOnMap={() => onPick(picking === 'origin' ? null : 'origin')}
          />
          <PlaceInput
            label="To"
            placeholder="Where are you going?"
            value={destination}
            onChange={props.onDestinationChange}
            picking={picking === 'destination'}
            onPickOnMap={() => onPick(picking === 'destination' ? null : 'destination')}
          />
        </div>
      </div>

      <div className="mt-2 flex items-center justify-between gap-2 pl-[26px]">
        <button
          type="button"
          onClick={props.onSwap}
          disabled={!origin && !destination}
          className="btn min-h-8 px-2.5 text-xs"
          aria-label="Swap start and destination"
        >
          <ArrowUpDown size={14} aria-hidden="true" />
          Swap
        </button>
        <div className="flex items-center gap-1.5">
          <div className="flex rounded-[4px] border border-line-strong bg-white p-0.5" role="group" aria-label="Transfers">
            {([1, 0] as const).map((value) => (
              <button
                key={value}
                type="button"
                aria-pressed={props.maxTransfers === value}
                onClick={() => props.onMaxTransfersChange(value)}
                className={`focus-ring h-7 rounded-[3px] px-2 text-xs font-semibold transition-colors ${
                  props.maxTransfers === value ? 'bg-brand-500 text-white' : 'text-ink-muted hover:bg-brand-50'
                }`}
              >
                {value === 1 ? 'Up to 1 transfer' : 'Direct only'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Fixed columns: the button keeps its place and size while searching. */}
      <div className="mt-2.5 grid grid-cols-[minmax(0,1fr)_8.75rem] gap-2">
        <label className="relative min-w-0">
          <span className="sr-only">Sort trips by</span>
          <ArrowDownWideNarrow size={16} className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-brand-600" aria-hidden="true" />
          <select
            className="field cursor-pointer appearance-none pr-8 pl-9 font-medium"
            value={props.sortBy}
            onChange={(e) => props.onSortChange(e.target.value as SortBy)}
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <ChevronDown size={16} className="pointer-events-none absolute top-1/2 right-2.5 -translate-y-1/2 text-brand-600" aria-hidden="true" />
        </label>
        <LoadingButton type="submit" disabled={!ready} loading={loading} loadingLabel="Finding…" icon={<Search size={17} aria-hidden="true" />} className="btn-primary w-full px-2">
          Find trips
        </LoadingButton>
      </div>
    </form>
  )
}
