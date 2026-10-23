import { ArrowRight, MousePointerClick, PanelLeftOpen, PanelRightOpen, X } from 'lucide-react'
import { useCallback, useRef, useState } from 'react'
import { ApiError, planJourney, type JourneyOption, type LatLng, type Place, type PlanResponse, type SortBy } from './api'
import BottomSheet, { type SheetSnap } from './components/layout/BottomSheet'
import DataSourcesFooter from './components/layout/DataSourcesFooter'
import PanelHeader from './components/layout/PanelHeader'
import ResizablePanel from './components/layout/ResizablePanel'
import MapView from './components/map/MapView'
import SearchForm, { type PickTarget } from './components/search/SearchForm'
import TripDetails, { TripDetailsHeader } from './components/trips/TripDetails'
import TripResults from './components/trips/TripResults'
import { tripFareDisplay } from './fareEstimates'
import { pendingPoint } from './places'
import { tripFareFor, useFareChoices, vehicleChoicesFor } from './hooks/useFareChoices'
import { useAddressLabel } from './hooks/useAddressLabel'
import { useInteractionMotion } from './hooks/useInteractionMotion'
import { useMediaQuery } from './hooks/useMediaQuery'
import { useResizablePanel } from './hooks/useResizablePanel'
import { rides, tripName } from './tripTimeline'

interface SearchState {
  from: Place
  to: Place
  isReturn: boolean
}

// The search as it was planned, so "Explain this trip" repeats it exactly.
interface PlannedSearch extends SearchState {
  sortBy: SortBy
  maxTransfers: 0 | 1
}

// Phones: bottom sheet. Tablets: trip details slide over the trip list, so the
// map keeps its room. Wide screens: main panel, trip details and map side by side.
const PANELS_QUERY = '(min-width: 768px)'
const WIDE_QUERY = '(min-width: 1100px)'

export default function App() {
  const motionRoot = useInteractionMotion()
  const hasPanels = useMediaQuery(PANELS_QUERY)
  const isWide = useMediaQuery(WIDE_QUERY)
  const main = useResizablePanel({ storageKey: 'padunggo.sidebar', min: 320, max: 560, defaultWidth: 380, persistCollapsed: true })
  const mainVisible = !main.collapsed
  const details = useResizablePanel({
    storageKey: 'padunggo.details',
    min: 320,
    max: 520,
    defaultWidth: 380,
    reservedWidth: mainVisible ? main.width : 0,
  })
  const [sheetSnap, setSheetSnap] = useState<SheetSnap>('half')
  const [sheetHeight, setSheetHeight] = useState(0)

  const [origin, setOrigin] = useState<Place | null>(null)
  const [destination, setDestination] = useState<Place | null>(null)
  // GPS and map points get a readable address once the lookup returns.
  useAddressLabel(origin, setOrigin)
  useAddressLabel(destination, setDestination)
  const [picking, setPicking] = useState<PickTarget | null>(null)
  const [sortBy, setSortBy] = useState<SortBy>('fewest_transfers')
  const [maxTransfers, setMaxTransfers] = useState<0 | 1>(1)
  const [plan, setPlan] = useState<PlanResponse | null>(null)
  const [search, setSearch] = useState<PlannedSearch | null>(null)
  // The selected trip is drawn on the map; the details panel may be open or hidden.
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [slow, setSlow] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const latestRequest = useRef(0)
  // Passenger and jeepney choices only change displayed fares, never route data.
  const { choices: fareChoices, setPassenger, setVehicle, resetVehicles } = useFareChoices()

  const run = useCallback(async (next: SearchState, sort: SortBy, transfers: 0 | 1) => {
    // Only the newest request may update the screen.
    const requestId = ++latestRequest.current
    setLoading(true)
    setSlow(false)
    setError(null)
    setPlan(null)
    setSelectedId(null)
    setDetailsOpen(false)
    resetVehicles()
    setSearch({ ...next, sortBy: sort, maxTransfers: transfers })
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
  }, [resetVehicles])

  const rerun = (sort: SortBy, transfers: 0 | 1) => {
    if (search && (plan || error)) void run(search, sort, transfers)
  }

  const onMapClick = useCallback(
    (p: LatLng) => {
      if (!picking) return
      const place: Place = pendingPoint(p, 'map')
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

  const openDetails = useCallback(
    (id: string) => {
      setSelectedId(id)
      setDetailsOpen(true)
      details.setCollapsed(false)
      setSheetSnap('full')
    },
    [details],
  )

  const closeDetails = () => {
    setDetailsOpen(false)
    setSheetSnap('half')
  }

  const selected = plan?.journey_options.find((o) => o.id === selectedId) ?? null
  const detailsVisible = Boolean(selected) && detailsOpen && (!isWide || !details.collapsed)
  const endpoints = {
    originName: search?.from.name ?? origin?.name ?? 'Start',
    destinationName: search?.to.name ?? destination?.name ?? 'Destination',
  }

  // Cards and details read the same choices, so their totals always agree.
  const fareFor = useCallback((option: JourneyOption) => tripFareDisplay(tripFareFor(fareChoices, option)), [fareChoices])

  const tripDetails = selected && (
    <TripDetails
      key={selected.id}
      option={selected}
      endpoints={endpoints}
      search={search}
      dataUpdatedOn={plan?.data_updated_on}
      passenger={fareChoices.passenger}
      vehicles={vehicleChoicesFor(fareChoices, selected)}
      onPassengerChange={setPassenger}
      onVehicleChange={(rideIndex, vehicle) => setVehicle(selected, rideIndex, vehicle)}
    />
  )

  const searchAndResults = (
    <div className="planner-entrance space-y-3 p-3">
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
      <TripResults
        plan={plan}
        loading={loading}
        slow={slow}
        error={error}
        onRetry={search ? () => void run(search, sortBy, maxTransfers) : null}
        isReturn={search?.isReturn ?? false}
        onSwitchDirection={search ? swap : null}
        selectedId={selectedId}
        onSelect={openDetails}
        fareFor={fareFor}
        maxTransfers={maxTransfers}
        onAllowTransfer={() => {
          setMaxTransfers(1)
          rerun(sortBy, 1)
        }}
      />
      <DataSourcesFooter />
    </div>
  )

  const detailsPanel = selected && (
    <ResizablePanel
      id="trip-details"
      label="Trip details"
      // Tablets: the details exactly cover the trip list, sharing its width and resize edge.
      panel={isWide ? details : { ...main, collapsed: false }}
      open={detailsOpen}
      className={isWide ? 'border-r border-brand-900/20' : 'shadow-[4px_0_18px_rgb(6_47_87/0.18)]'}
    >
      <TripDetailsHeader closeMode={isWide ? 'hide' : 'back'} onClose={closeDetails} />
      <div className="bg-grid min-h-0 flex-1 overflow-y-auto">
        {tripDetails}
      </div>
    </ResizablePanel>
  )

  const shownName = selected ? tripName(selected) : null
  // On tablets the details cover the trip list; if the list is hidden they sit
  // over the map, so the camera keeps the trip clear of them.
  const mapLeftInset = hasPanels && !isWide && detailsOpen && selected && main.collapsed ? main.width : 0

  return (
    <div ref={motionRoot} className="app-entrance relative flex h-full overflow-hidden bg-surface text-ink">
      {hasPanels ? (
        <ResizablePanel id="trip-panel" label="Trip planner" panel={main} className={mainVisible ? 'border-r border-brand-900/20' : ''}>
          <PanelHeader onCollapse={main.toggleCollapsed} />
          <div className="bg-grid min-h-0 flex-1 overflow-y-auto">{searchAndResults}</div>
        </ResizablePanel>
      ) : null}
      {hasPanels && isWide ? detailsPanel : null}
      {hasPanels && !isWide && selected ? <div className="absolute inset-y-0 left-0 z-30 flex">{detailsPanel}</div> : null}

      <main className="relative h-full min-w-0 flex-1">
        <MapView
          origin={origin}
          destination={destination}
          option={selected}
          onMapClick={picking ? onMapClick : null}
          insets={{ left: mapLeftInset, bottom: hasPanels ? 0 : sheetHeight }}
        />


        {/* Which trip the map shows, plus ways back to hidden panels. */}
        <div
          className="pointer-events-none absolute top-3 right-16 z-10 flex flex-wrap items-start gap-2 transition-[left] duration-300"
          style={{ left: 12 + mapLeftInset }}
        >
          {hasPanels && main.collapsed && (
            <button
              type="button"
              onClick={main.toggleCollapsed}
              aria-controls="trip-panel"
              aria-expanded={false}
              className="btn btn-primary fade-up pointer-events-auto shadow-[0_2px_6px_rgb(6_47_87/0.25)]"
            >
              <PanelLeftOpen size={17} aria-hidden="true" />
              Trips
            </button>
          )}
          {hasPanels && selected && !detailsVisible && (
            <button
              type="button"
              onClick={() => openDetails(selected.id)}
              aria-controls="trip-details"
              aria-expanded={false}
              className="btn fade-up pointer-events-auto shadow-[0_2px_6px_rgb(6_47_87/0.18)]"
            >
              <PanelRightOpen size={17} aria-hidden="true" />
              Trip details
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
            <div
              className="fade-up pointer-events-auto relative flex items-center gap-2 rounded-[4px] border border-brand-900 bg-brand-500 py-2 pr-1.5 pl-3 text-sm font-medium text-white shadow-[0_4px_12px_rgb(6_47_87/0.3)]"
              role="status"
            >
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

        {!hasPanels && (
          <BottomSheet
            snap={sheetSnap}
            onSnapChange={setSheetSnap}
            onHeightChange={setSheetHeight}
            header={selected && detailsOpen ? <TripDetailsHeader closeMode="back" onClose={closeDetails} /> : <PanelHeader />}
            contentKey={selected && detailsOpen ? `trip-${selected.id}` : 'list'}
          >
            {detailsOpen && tripDetails}
            {/* Kept mounted so "All trips" returns to the same list and scroll position. */}
            <div hidden={Boolean(selected && detailsOpen)}>{searchAndResults}</div>
          </BottomSheet>
        )}
      </main>
    </div>
  )
}
