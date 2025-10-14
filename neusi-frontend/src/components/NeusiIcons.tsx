// src/components/NeusiIcons.tsx
export function IconBacklog(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden {...props}>
      <rect x="4" y="3" width="16" height="18" rx="3" fill="currentColor" opacity=".15" />
      <rect x="7" y="7" width="10" height="2" rx="1" fill="currentColor" />
      <rect x="7" y="11" width="10" height="2" rx="1" fill="currentColor" />
      <rect x="7" y="15" width="7" height="2" rx="1" fill="currentColor" />
      <rect x="4" y="3" width="16" height="18" rx="3" stroke="currentColor" strokeWidth="1.4" fill="none" />
    </svg>
  );
}
export function IconMatrix(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden {...props}>
      <rect x="3" y="3" width="18" height="18" rx="3" stroke="currentColor" strokeWidth="1.4" fill="none" />
      <line x1="12" y1="3" x2="12" y2="21" stroke="currentColor" strokeWidth="1.4" />
      <line x1="3" y1="12" x2="21" y2="12" stroke="currentColor" strokeWidth="1.4" />
      <circle cx="16.5" cy="7.5" r="1.8" fill="currentColor" />
      <circle cx="7.5" cy="16.5" r="1.8" fill="currentColor" />
    </svg>
  );
}
export function IconKanban(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden {...props}>
      <rect x="3" y="4" width="6" height="16" rx="1.6" fill="currentColor" opacity=".15" />
      <rect x="10" y="4" width="4" height="16" rx="1.6" fill="currentColor" />
      <rect x="15.5" y="4" width="5.5" height="16" rx="1.6" fill="currentColor" opacity=".15" />
      <rect x="3" y="4" width="18" height="16" rx="2" stroke="currentColor" strokeWidth="1.4" fill="none" />
    </svg>
  );
}
export function IconAvailability(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden {...props}>
      <circle cx="12" cy="8" r="3.2" stroke="currentColor" strokeWidth="1.4" fill="currentColor" opacity=".15" />
      <path d="M5 19c0-3.2 3-5.2 7-5.2s7 2 7 5.2" stroke="currentColor" strokeWidth="1.4" fill="none" />
      <circle cx="12" cy="8" r="3.2" stroke="currentColor" strokeWidth="1.4" fill="none" />
    </svg>
  );
}
