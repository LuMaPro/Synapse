interface SimboloLogoProps {
  tamanho?: number
  className?: string
}

export function SimboloLogo({ tamanho = 64, className = '' }: SimboloLogoProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 64 64"
      width={tamanho}
      height={tamanho}
      className={className}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="simbolo-gradiente" gradientUnits="userSpaceOnUse" x1="8" y1="6" x2="56" y2="58">
          <stop offset="0%" stopColor="#8b7bff" />
          <stop offset="100%" stopColor="#3ee6e0" />
        </linearGradient>
      </defs>
      <g fill="none" stroke="url(#simbolo-gradiente)" strokeWidth="3.4" strokeLinecap="round">
        <path d="M29 25 C27 18 22 13 15 10" />
        <path d="M21 14 L19 6" />
        <path d="M35 25 C37 18 42 14 49 11" />
        <path d="M43 15 L48 6" />
        <path d="M26 31 C19 31 13 35 7 32" />
        <path d="M38 31 C45 31 51 34 57 31" />
        <path d="M32 37 L32 51" />
      </g>
      <circle cx="32" cy="30" r="7.5" fill="url(#simbolo-gradiente)" />
      <circle cx="32" cy="56" r="4" fill="#3ee6e0" />
    </svg>
  )
}
