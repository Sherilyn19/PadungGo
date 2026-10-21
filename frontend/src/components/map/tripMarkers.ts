// Works out which stop markers to draw for a trip: where to board, where to
// transfer and where to get off. Pure data, so it can be unit-tested.
import type { JourneyOption, LatLng, RideSegment } from '../../api'
import { rideColor, stopName } from '../../tripTimeline'

export type TripMarkerKind = 'board' | 'transfer' | 'alight'

export interface TripMarker {
  kind: TripMarkerKind
  point: LatLng
  label: string
  color: string
}

export function tripMarkers(option: JourneyOption | null): TripMarker[] {
  if (!option) return []
  const markers: TripMarker[] = []
  const rides = option.segments.filter((s): s is RideSegment => s.mode === 'ride')
  rides.forEach((ride, i) => {
    const color = rideColor(i)
    if (ride.start) {
      markers.push({
        kind: i === 0 ? 'board' : 'transfer',
        point: ride.start,
        label: i === 0 ? `Board ${ride.route_code} at ${stopName(ride.board_stop_name, 'this stop')}` : `Transfer to ${ride.route_code} at ${stopName(ride.board_stop_name, 'this stop')}`,
        color,
      })
    }
    const next = rides[i + 1]
    // Skip the exit marker when the next ride boards at the same point; the
    // transfer marker already covers it.
    const sameSpotAsNext =
      next?.start && ride.end && next.start.latitude === ride.end.latitude && next.start.longitude === ride.end.longitude
    if (ride.end && !sameSpotAsNext) {
      markers.push({
        kind: 'alight',
        point: ride.end,
        label: `Get off ${ride.route_code} at ${stopName(ride.alight_stop_name, 'this stop')}`,
        color,
      })
    }
  })
  return markers
}
