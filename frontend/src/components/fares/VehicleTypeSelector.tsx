import { VEHICLE_CHOICES, type VehicleChoice } from '../../fareEstimates'
import SegmentedControl from '../ui/SegmentedControl'

interface Props {
  routeCode: string
  value: VehicleChoice
  onChange: (value: VehicleChoice) => void
  // The ride's colour, so the choice matches its timeline and map line.
  accent: string
}

export default function VehicleTypeSelector({ routeCode, value, onChange, accent }: Props) {
  return (
    <div>
      <p className="mb-1 text-xs font-semibold text-ink-muted">Jeepney type</p>
      <SegmentedControl label={`Jeepney type for ${routeCode}`} value={value} onChange={onChange} accent={accent} options={VEHICLE_CHOICES} />
    </div>
  )
}
