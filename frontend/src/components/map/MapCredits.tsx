import { Info, X } from 'lucide-react'
import { useId } from 'react'

// All third-party credits in one place: the map's bottom-right (i) button.
// It opens briefly when the app starts and closes after five seconds or the
// first map interaction, which the OpenStreetMap attribution guideline allows.
const CREDITS = [
  {
    label: 'Map',
    links: [
      { text: 'OpenFreeMap', url: 'https://openfreemap.org/' },
      { text: '© OpenMapTiles', url: 'https://www.openmaptiles.org/' },
      { text: '© OpenStreetMap contributors', url: 'https://www.openstreetmap.org/copyright' },
      { text: 'MapLibre', url: 'https://maplibre.org/' },
    ],
  },
  {
    label: 'Addresses and place search',
    links: [
      { text: 'Powered by Geoapify', url: 'https://www.geoapify.com/' },
      { text: '© OpenStreetMap contributors', url: 'https://www.openstreetmap.org/copyright' },
    ],
    note: 'When you use your location or pin the map, those coordinates are sent to Geoapify to find the address.',
  },
]

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function MapCredits({ open, onOpenChange }: Props) {
  const panelId = useId()
  return (
    <div
      className="absolute right-2 z-10 flex flex-col items-end gap-1.5 transition-[bottom] duration-300"
      style={{ bottom: 'calc(var(--map-bottom-inset, 0px) + 8px)' }}
    >
      {open && (
        <section
          id={panelId}
          aria-label="Map and data credits"
          className="fade-up w-64 max-w-[calc(100vw-1rem)] rounded-[6px] border border-cream-line bg-cream p-2.5 text-[11px] leading-snug text-ink-muted shadow-[0_4px_12px_rgb(6_47_87/0.16)]"
        >
          <div className="mb-1.5 flex items-center justify-between">
            <h2 className="section-label text-[11px]">Credits</h2>
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="focus-ring flex h-6 w-6 items-center justify-center rounded-full text-ink-soft hover:bg-cream-line"
              aria-label="Close credits"
            >
              <X size={13} aria-hidden="true" />
            </button>
          </div>
          <dl className="space-y-1.5">
            {CREDITS.map((group) => (
              <div key={group.label}>
                <dt className="font-semibold text-ink">{group.label}</dt>
                <dd>
                  {group.links.map((link, i) => (
                    <span key={link.text}>
                      {i > 0 && ' · '}
                      <a href={link.url} target="_blank" rel="noopener noreferrer" className="text-brand-700 underline-offset-2 hover:underline">
                        {link.text}
                      </a>
                    </span>
                  ))}
                  {group.note && <span className="mt-0.5 block text-ink-soft">{group.note}</span>}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      )}
      <button
        type="button"
        onClick={() => onOpenChange(!open)}
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        aria-label={open ? 'Hide credits' : 'Show map and data credits'}
        title="Credits"
        className="focus-ring flex h-8 w-8 items-center justify-center rounded-full border border-cream-line bg-white text-brand-600 shadow-[0_2px_6px_rgb(6_47_87/0.15)] hover:bg-cream"
      >
        <Info size={17} aria-hidden="true" />
      </button>
    </div>
  )
}
