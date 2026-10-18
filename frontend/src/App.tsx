import { useCallback, useState } from 'react'
import { ApiError, planJourney, type LatLng, type Place, type PlanResponse, type SortBy } from './api'
import MapView from './components/MapView'
import PlaceInput from './components/PlaceInput'
import Results from './components/Results'

type Target = 'origin' | 'destination'

export default function App() {
  const [origin, setOrigin] = useState<Place | null>(null)
  const [destination, setDestination] = useState<Place | null>(null)
  const [picking, setPicking] = useState<Target | null>(null)
  const [sortBy, setSortBy] = useState<SortBy>('fewest_transfers')
  const [maxTransfers, setMaxTransfers] = useState<0 | 1>(1)
  const [plan, setPlan] = useState<PlanResponse | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [slow, setSlow] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isReturn, setIsReturn] = useState(false)

  const run = useCallback(
    async (from: Place, to: Place, returnTrip: boolean) => {
      setLoading(true)
      setSlow(false)
      setError(null)
      setPlan(null)
      setSelectedId(null)
      const slowTimer = window.setTimeout(() => setSlow(true), 5000)
      try {
        const result = await planJourney(from, to, sortBy, maxTransfers)
        setPlan(result)
        setIsReturn(returnTrip)
        setSelectedId(result.journey_options[0]?.id ?? null)
      } catch (e) {
        setError(e instanceof ApiError ? e.message : 'Something went wrong. Please try again.')
      } finally {
        window.clearTimeout(slowTimer)
        setLoading(false)
      }
    },
    [sortBy, maxTransfers],
  )

  const onMapClick = useCallback(
    (p: LatLng) => {
      if (!picking) return
      const place: Place = { ...p, name: `Map point (${p.latitude.toFixed(4)}, ${p.longitude.toFixed(4)})`, source: 'map' }
      if (picking === 'origin') setOrigin(place)
      else setDestination(place)
      setPicking(null)
    },
    [picking],
  )

  const canPlan = Boolean(origin && destination) && !loading
  const selected = plan?.journey_options.find((o) => o.id === selectedId) ?? null

  const planReturn = () => {
    if (!origin || !destination) return
    // Independent second search with swapped endpoints — never reversed instructions.
    const [from, to] = [destination, origin]
    setOrigin(from)
    setDestination(to)
    void run(from, to, !isReturn)
  }

  return (
    <div className="flex h-full flex-col bg-slate-50 text-slate-900 md:flex-row">
      <aside className="flex w-full flex-col overflow-y-auto border-slate-200 bg-white md:h-full md:w-[420px] md:border-r">
        <header className="border-b border-slate-200 px-4 py-3">
          <h1 className="text-xl font-bold text-emerald-700">PadungGo</h1>
          <p className="text-xs text-slate-600">Jeepney journeys in Metro Cebu — direct or with one transfer.</p>
        </header>

        <form
          className="space-y-3 px-4 py-3"
          onSubmit={(e) => {
            e.preventDefault()
            if (origin && destination) void run(origin, destination, false)
          }}
        >
          <PlaceInput
            label="From"
            value={origin}
            onChange={setOrigin}
            picking={picking === 'origin'}
            onPickOnMap={() => setPicking(picking === 'origin' ? null : 'origin')}
          />
          <PlaceInput
            label="To"
            value={destination}
            onChange={setDestination}
            picking={picking === 'destination'}
            onPickOnMap={() => setPicking(picking === 'destination' ? null : 'destination')}
          />
          <div className="flex gap-2 text-sm">
            <label className="flex-1">
              <span className="block text-xs text-slate-600">Sort by</span>
              <select
                className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-1.5"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortBy)}
              >
                <option value="fewest_transfers">Fewest transfers</option>
                <option value="cheapest">Cheapest</option>
                <option value="fastest">Fastest</option>
                <option value="least_walking">Least walking</option>
              </select>
            </label>
            <label className="flex-1">
              <span className="block text-xs text-slate-600">Transfers</span>
              <select
                className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-1.5"
                value={maxTransfers}
                onChange={(e) => setMaxTransfers(Number(e.target.value) as 0 | 1)}
              >
                <option value={1}>Up to 1</option>
                <option value={0}>Direct only</option>
              </select>
            </label>
          </div>
          <button
            type="submit"
            disabled={!canPlan}
            className="w-full rounded-lg bg-emerald-600 py-2 font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {loading ? 'Finding routes…' : 'Find routes'}
          </button>
          {!origin || !destination ? (
            <p className="text-xs text-slate-500">Choose both places: search, use 📍 your location, or 🗺️ tap the map.</p>
          ) : null}
        </form>

        <section className="flex-1 space-y-3 px-4 pb-4" aria-live="polite">
          {loading && slow && (
            <p className="rounded-lg bg-slate-100 p-3 text-sm text-slate-700">
              The server is waking up (free hosting sleeps when idle). This can take up to a minute…
            </p>
          )}
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">
              {error}
              {origin && destination && (
                <button type="button" className="ml-2 underline" onClick={() => run(origin, destination, isReturn)}>
                  Retry
                </button>
              )}
            </div>
          )}
          {plan && (
            <>
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold">{isReturn ? 'Return trip' : 'Your trip'}</h2>
                <button type="button" onClick={planReturn} className="text-sm text-emerald-700 underline">
                  {isReturn ? 'Back to outbound' : 'Plan the return trip'}
                </button>
              </div>
              {plan.warnings.map((w) => (
                <p key={w} className="rounded-lg bg-amber-50 p-2 text-xs text-amber-900">
                  {w}
                </p>
              ))}
              <Results plan={plan} selectedId={selectedId} onSelect={setSelectedId} />
            </>
          )}
        </section>

        <footer className="border-t border-slate-200 px-4 py-3 text-[11px] leading-snug text-slate-500">
          Routes come from the Cebu DOTC GTFS archive (2014–2017) via Transitland and are not field-verified. Fares,
          waiting times and walking paths are not included. Always confirm with drivers or signboards. Map ©
          OpenStreetMap contributors, OpenFreeMap.
        </footer>
      </aside>

      <main className="h-[55vh] w-full md:h-full md:flex-1">
        <MapView
          origin={origin}
          destination={destination}
          option={selected}
          onMapClick={picking ? onMapClick : null}
        />
      </main>
    </div>
  )
}
