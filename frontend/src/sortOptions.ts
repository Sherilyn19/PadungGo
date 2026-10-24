import type { SortBy } from './api'

// The orders the planner can honestly apply today. The API accepts four, but
// it falls back to "fewest transfers" for the rest (and says so):
//   cheapest      needs verified fares for every trip; none are verified yet
//   fastest       needs known waiting times; there is no frequency data
//   least_walking needs real walking routes; walks are straight-line estimates
// Offering them would be a control that never does anything. Add an option
// here when the data behind it exists.
export const SORT_OPTIONS: { value: SortBy; label: string }[] = [
  { value: 'fewest_transfers', label: 'Fewest transfers' },
]

// Only worth showing a picker when there is something to pick.
export const hasSortChoice = SORT_OPTIONS.length > 1
