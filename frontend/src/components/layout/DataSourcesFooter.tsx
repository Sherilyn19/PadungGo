import { BusFront, Coins, ExternalLink, MessageCircleHeart } from 'lucide-react'

// Where the jeepney information comes from, at the end of the planner panel.
const SOURCES = [
  {
    icon: BusFront,
    tone: 'bg-moss-50 text-moss-800 border-moss-200',
    title: 'Routes and stops',
    text: 'Cebu DOTC jeepney routes and stops, shared through Transitland.',
    link: { text: 'View data', url: 'https://www.transit.land/feeds/f-wcb4-cebu~dotc' },
  },
  {
    icon: Coins,
    tone: 'bg-caution-50 text-caution border-cream-line',
    title: 'Fare estimates',
    text: 'The LTFRB jeepney fare guide.',
    link: { text: 'LTFRB fares', url: 'https://ltfrb.gov.ph/fare-rates/' },
  },
  {
    icon: MessageCircleHeart,
    tone: 'bg-coral-50 text-coral-600 border-coral-200',
    title: 'Route updates',
    text: 'Scarce and stopped routes come from Cebu commuters’ reports.',
  },
]

export default function DataSourcesFooter() {
  return (
    <footer className="rounded-md border border-cream-line bg-cream p-3">
      <details>
        <summary className="section-label cursor-pointer rounded text-[11px] text-ink focus-visible:outline-2 focus-visible:outline-brand-700">
          Where our jeepney info comes from
        </summary>

        <ul className="mt-3 space-y-2">
          {SOURCES.map(({ icon: Icon, tone, title, text, link }) => (
            <li key={title} className="flex gap-2.5">
              <span
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border ${tone}`}
              >
                <Icon size={14} aria-hidden="true" />
              </span>

              <span className="min-w-0 text-xs">
                <span className="block font-semibold text-ink">{title}</span>
                <span className="block text-ink-muted">{text}</span>
                {link && (
                  <a
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-0.5 inline-flex items-center gap-1 font-medium text-brand-700 underline-offset-2 hover:underline"
                  >
                    {link.text}
                    <ExternalLink size={11} aria-hidden="true" />
                  </a>
                )}
              </span>
            </li>
          ))}
        </ul>
      </details>
    </footer>
  )
}
