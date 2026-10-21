import { ArrowRight, MousePointerClick, PanelLeftOpen, X } from 'lucide-react'
import { useCallback, useRef, useState } from 'react'
import { ApiError, planJourney, type LatLng, type Place, type PlanResponse, type SortBy } from './api'
import BottomSheet, { type SheetSnap } from './components/layout/BottomSheet'
import DesktopSidebar from './components/layout/DesktopSidebar'
import PanelHeader from './components/layout/PanelHeader'
import MapView from './components/map/MapView'
import ResultsPanel from './components/results/ResultsPanel'
import SearchForm, { type PickTarget } from './components/search/SearchForm'
import InfoTip from './components/ui/InfoTip'
import { DESKTOP_QUERY, useMediaQuery } from './hooks/useMediaQuery'
import { useResizableSidebar } from './hooks/useResizableSidebar'
import { rides, tripName } from './tripTimeline'

interface SearchState {
  from: Place
  to: Place
  isReturn: boolean
}

export default function App() {
  const isDesktop = useMediaQuery(DESKTOP_QUERY)
  const sidebar = useResizableSidebar()
  const [sheetSnap, setSheetSnap] = useState<SheetSnap>('half')
  const [sheetHeight, setSheetHeight] = useState(0)

  const [origin, setOrigin] = useState<Place | null>(null)
  const [destination, setDestination] = useState<Place | null>(null)
  const [picking, setPicking] = useState<PickTarget | null>(null)
  const [sortBy, setSortBy] = useState<SortBy>('fewest_transfers')
  const [maxTransfers, setMaxTransfers] = useState<0 | 1>(1)
  const [plan, setPlan] = useState<PlanResponse | null>(null)
  const [search, setSearch] = useState<SearchState | null>(null)
  // "Selected" is the trip drawn on the map; "expanded" is the open card.
  // Collapsing a card keeps its trip on the map.
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [slow, setSlow] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const latestRequest = useRef(0)

  const run = useCallback(async (next: SearchState, sort: SortBy, transfers: 0 | 1) => {
    // Only the newest request may update the screen.
    const requestId = ++latestRequest.current
    setLoading(true)
    setSlow(false)
    setError(null)
    setPlan(null)
    setSelectedId(null)
    setExpandedId(null)
    setSearch(next)
    setSheetSnap('half')
    const slowTimer = window.setTimeout(() => setSlow(true), 5000)
    try {
      const result = await planJourney(next.from, next.to, sort, transfers)
      if (requestId !== latestRequest.current) return
      setPlan(result)
      setSelectedId(result.journey_options[0]?.id ?? null)
    } catch (e) {
      if (requestId !== latestRequest.current) return
      setError(e instanceof ApiError ? e.message : 'Something went wrong. Please try again.')
    } finally {
      window.clearTimeout(slowTimer)
      if (requestId === latestRequest.current) setLoading(false)
    }
  }, [])

  const rerun = (sort: SortBy, transfers: 0 | 1) => {
    if (search && (plan || error)) void run(search, sort, transfers)
  }

  const onMapClick = useCallback(
    (p: LatLng) => {
      if (!picking) return
      const place: Place = { ...p, name: `Pinned point (${p.latitude.toFixed(4)}, ${p.longitude.toFixed(4)})`, source: 'map' }
      if (picking === 'origin') setOrigin(place)
      else setDestination(place)
      setPicking(null)
      setSheetSnap('half')
    },
    [picking],
  )

  const onPick = (target: PickTarget | null) => {
    setPicking(target)
    // On phones, lower the sheet so the map can be tapped.
    if (target) setSheetSnap('peek')
  }

  // The return trip is an independent search with swapped endpoints, never reversed instructions.
  const swap = () => {
    setOrigin(destination)
    setDestination(origin)
    if (origin && destination && (plan || error)) {
      void run({ from: destination, to: origin, isReturn: !(search?.isReturn ?? false) }, sortBy, maxTransfers)
    }
  }

  const onToggle = useCallback((id: string) => {
    setSelectedId(id)
    setExpandedId((current) => (current === id ? null : id))
  }, [])

  const selected = plan?.journey_options.find((o) => o.id === selectedId) ?? null
  const endpoints = {
    originName: search?.from.name ?? origin?.name ?? 'Start',
    destinationName: search?.to.name ?? destination?.name ?? 'Destination',
  }

  const panelBody = (
    <div className="space-y-3 p-3">
      <SearchForm
        origin={origin}
        destination={destination}
        onOriginChange={setOrigin}
        onDestinationChange={setDestination}
        picking={picking}
        onPick={onPick}
        onSwap={swap}
        sortBy={sortBy}
        onSortChange={(s) => {
          setSortBy(s)
          rerun(s, maxTransfers)
        }}
        maxTransfers={maxTransfers}
        onMaxTransfersChange={(t) => {
          setMaxTransfers(t)
          rerun(sortBy, t)
        }}
        loading={loading}
        onSubmit={() => origin && destination && void run({ from: origin, to: destination, isReturn: false }, sortBy, maxTransfers)}
      />
      <ResultsPanel
        plan={plan}
        loading={loading}
        slow={slow}
        error={error}
        onRetry={search ? () => void run(search, sortBy, maxTransfers) : null}
        isReturn={search?.isReturn ?? false}
        onSwitchDirection={search ? swap : null}
        selectedId={selectedId}
        expandedId={expandedId}
        onToggle={onToggle}
        endpoints={endpoints}
        maxTransfers={maxTransfers}
        onAllowTransfer={() => {
          setMaxTransfers(1)
          rerun(sortBy, 1)
        }}
      />
      <footer className="flex items-center gap-1.5 px-1 pb-2 text-[11px] text-ink-soft">
        <span>About the route data</span>
        <InfoTip label="About the route data">
          Routes come from the Cebu DOTC GTFS archive (2014–2017) via Transitland and have not been checked on the ground.
          Fares, waiting times and walking paths are shown only when the data supports them. Always confirm with drivers or
          signboards.
        </InfoTip>
      </footer>
    </div>
  )

  const shownName = selected ? tripName(selected) : null

  return (
    <div className="flex h-full overflow-hidden bg-surface text-ink">
      {isDesktop ? (
        <DesktopSidebar sidebar={sidebar}>
          <PanelHeader onCollapse={sidebar.toggleCollapsed} />
          <div className="bg-grid min-h-0 flex-1 overflow-y-auto">{panelBody}</div>
        </DesktopSidebar>
      ) : null}

      <main className="relative h-full min-w-0 flex-1">
        <MapView
          origin={origin}
          destination={destination}
          option={selected}
          onMapClick={picking ? onMapClick : null}
          insets={{ left: 0, bottom: isDesktop ? 0 : sheetHeight }}
        />

        {/* Which trip the map shows, and a way back to the panel when it is hidden. */}
        <div className="pointer-events-none absolute top-3 right-16 left-3 z-10 flex items-start gap-2">
          {isDesktop && sidebar.collapsed && (
            <button
              type="button"
              onClick={sidebar.toggleCollapsed}
              aria-controls="trip-panel"
              aria-expanded={false}
              className="btn btn-primary fade-up pointer-events-auto shadow-[0_2px_6px_rgb(6_47_87/0.25)]"
            >
              <PanelLeftOpen size={17} aria-hidden="true" />
              Show trips
            </button>
          )}
          {shownName && selected && (
            <p
              key={selected.id}
              className="fade-up flex min-w-0 items-center gap-1.5 rounded-[4px] border border-line bg-white/95 px-2.5 py-2 text-xs text-ink shadow-[0_2px_6px_rgb(6_47_87/0.12)]"
              aria-live="polite"
            >
              <span className="shrink-0 font-pixel text-[11px] font-semibold tracking-wide text-brand-600 uppercase">On map</span>
              <span className="shrink-0 font-semibold">{rides(selected).map((r) => r.route_code).join(' + ')}</span>
              <span className="truncate text-ink-muted">
                {shownName.from} <ArrowRight size={11} className="inline" aria-label="to" /> {shownName.to}
              </span>
            </p>
          )}
        </div>

        {picking && (
          <div className="pointer-events-none absolute inset-x-0 top-16 z-20 flex justify-center px-3">
            <div className="fade-up pointer-events-auto relative flex items-center gap-2 rounded-[4px] border border-brand-900 bg-brand-500 py-2 pr-1.5 pl-3 text-sm font-medium text-white shadow-[0_4px_12px_rgb(6_47_87/0.3)]" role="status">
              <MousePointerClick size={16} aria-hidden="true" />
              Tap the map to set your {picking === 'origin' ? 'start' : 'destination'}
              <button
                type="button"
                onClick={() => setPicking(null)}
                className="ml-1 flex h-7 w-7 items-center justify-center rounded-[3px] hover:bg-white/20 focus-visible:outline-2 focus-visible:outline-white"
                aria-label="Cancel picking on the map"
              >
                <X size={15} aria-hidden="true" />
              </button>
              {/* Speech-bubble tail, as in the reference toast. */}
              <span className="absolute -bottom-[7px] left-6 h-3 w-3 rotate-45 border-r border-b border-brand-900 bg-brand-500" aria-hidden="true" />
            </div>
          </div>
        )}

        {!isDesktop && (
          <BottomSheet
            snap={sheetSnap}
            onSnapChange={setSheetSnap}
            onHeightChange={setSheetHeight}
            header={<PanelHeader />}
          >
            {panelBody}
          </BottomSheet>
        )}
      </main>
    </div>
  )
}
