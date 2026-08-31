/**
 * Discipline icons as inline SVG.
 *
 * These were emoji, which render at a different size and weight on every OS,
 * cannot inherit color, and are announced by screen readers as their unicode
 * name. SVG solves all three: currentColor works, the stroke weight matches
 * the rest of the UI, and aria-hidden keeps them out of the accessibility tree
 * since the label beside them already says what the session is.
 */
type Props = { className?: string; style?: React.CSSProperties };

const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
  focusable: false,
};

export function SwimIcon({ className, style }: Props) {
  return (
    <svg {...base} className={className} style={style}>
      <circle cx="16" cy="6.5" r="1.6" />
      <path d="M4 10.5l4.2-2.8 3.4 3.1-2.6 2" />
      <path d="M11.6 10.8L16 13" />
      <path d="M2 18.2c1.6 0 1.6 1.2 3.2 1.2s1.6-1.2 3.2-1.2 1.6 1.2 3.2 1.2 1.6-1.2 3.2-1.2 1.6 1.2 3.2 1.2 1.6-1.2 3.2-1.2" />
    </svg>
  );
}

export function BikeIcon({ className, style }: Props) {
  return (
    <svg {...base} className={className} style={style}>
      <circle cx="5.5" cy="17" r="3.5" />
      <circle cx="18.5" cy="17" r="3.5" />
      <circle cx="15" cy="4.5" r="1.3" />
      <path d="M12 17l-2.5-6 3-2.5 2.5 3h2.5" />
      <path d="M5.5 17l4-8.5" />
    </svg>
  );
}

export function RunIcon({ className, style }: Props) {
  return (
    <svg {...base} className={className} style={style}>
      <circle cx="14" cy="4.2" r="1.4" />
      <path d="M13.5 21l-1.2-5-2.8-2.4.9-4.6" />
      <path d="M10.4 9l-2.6 2.2-2.3-.6" />
      <path d="M10.4 9l3.4 1.4 1.6 3 2.9 1.1" />
      <path d="M12.3 16l-3.6 1.8L7 21" />
    </svg>
  );
}

export function BrickIcon({ className, style }: Props) {
  return (
    <svg {...base} className={className} style={style}>
      <path d="M13 2L4.5 13.2h6L10 22l9.5-11.2h-6L14 2z" />
    </svg>
  );
}

export function RestIcon({ className, style }: Props) {
  return (
    <svg {...base} className={className} style={style}>
      <path d="M20.5 14.2A8.5 8.5 0 1 1 9.8 3.5a6.8 6.8 0 0 0 10.7 10.7z" />
    </svg>
  );
}

export function CheckIcon({ className }: Props) {
  return (
    <svg {...base} strokeWidth={3} className={className}>
      <path d="M4.5 12.5l5 5 10-11" />
    </svg>
  );
}

export const DISCIPLINE_ICON = {
  swim: SwimIcon,
  bike: BikeIcon,
  run: RunIcon,
  brick: BrickIcon,
  rest: RestIcon,
} as const;
