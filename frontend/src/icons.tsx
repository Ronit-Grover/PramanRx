import type { SVGProps } from 'react'

export type IconName = 'workspace' | 'scenario' | 'audit' | 'database' | 'plug' | 'architecture' | 'status' | 'search' | 'plus' | 'shield' | 'chevron' | 'spark' | 'check' | 'x' | 'alert' | 'clock' | 'copy' | 'filter' | 'external' | 'menu' | 'close' | 'user' | 'lock' | 'key' | 'file' | 'server' | 'arrow' | 'play' | 'refresh' | 'info'

const paths: Record<IconName, React.ReactNode> = {
  workspace: <><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M8 9h8M8 13h5M8 17h3"/></>,
  scenario: <><path d="M8 5v14l11-7z"/><path d="M4 4v16"/></>,
  audit: <><path d="M9 3h6l1 2h3v16H5V5h3z"/><path d="m9 13 2 2 4-5"/></>,
  database: <><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/></>,
  plug: <><path d="m8 12 8-8M14 3l7 7M5 13l6 6M3 21l5-5"/><path d="m9 11 4 4"/></>,
  architecture: <><rect x="9" y="3" width="6" height="5"/><rect x="3" y="16" width="6" height="5"/><rect x="15" y="16" width="6" height="5"/><path d="M12 8v4M6 16v-4h12v4"/></>,
  status: <><path d="M3 12h4l2-5 4 10 2-5h6"/></>,
  search: <><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></>, plus: <path d="M12 5v14M5 12h14"/>,
  shield: <><path d="M12 3 4 6v5c0 5 3.4 8.7 8 10 4.6-1.3 8-5 8-10V6z"/><path d="m9 12 2 2 4-5"/></>,
  chevron: <path d="m9 18 6-6-6-6"/>, spark: <><path d="m12 3 1.4 4.2L18 9l-4.6 1.8L12 15l-1.4-4.2L6 9l4.6-1.8z"/><path d="m19 15 .6 1.8L22 18l-2.4 1.2L19 21l-.6-1.8L16 18l2.4-1.2z"/></>,
  check: <path d="m5 12 4 4L19 6"/>, x: <path d="M6 6l12 12M18 6 6 18"/>, alert: <><path d="M12 3 2.5 20h19z"/><path d="M12 9v4M12 17h.01"/></>,
  clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>, copy: <><rect x="8" y="8" width="11" height="12" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h3"/></>,
  filter: <path d="M3 5h18l-7 8v6l-4 2v-8z"/>, external: <><path d="M14 3h7v7M10 14 21 3"/><path d="M18 13v7H4V6h7"/></>, menu: <path d="M4 6h16M4 12h16M4 18h16"/>, close: <path d="M6 6l12 12M18 6 6 18"/>,
  user: <><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></>, lock: <><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></>,
  key: <><circle cx="8" cy="15" r="4"/><path d="m11 12 9-9M16 7l3 3"/></>, file: <><path d="M6 2h8l4 4v16H6z"/><path d="M14 2v5h5M9 13h6M9 17h6"/></>,
  server: <><rect x="3" y="4" width="18" height="6" rx="2"/><rect x="3" y="14" width="18" height="6" rx="2"/><path d="M7 7h.01M7 17h.01"/></>, arrow: <path d="M5 12h14M14 7l5 5-5 5"/>,
  play: <path d="M8 5v14l11-7z"/>, refresh: <><path d="M20 11a8 8 0 1 0-2 6"/><path d="M20 4v7h-7"/></>, info: <><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/></>,
}

export function Icon({ name, size = 18, ...props }: { name: IconName; size?: number } & SVGProps<SVGSVGElement>) {
  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>{paths[name]}</svg>
}
