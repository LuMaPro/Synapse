/**
 * Fundo decorativo com rede neural bioluminescente (docs/design/prototipo.html).
 * Renderiza conexões sinápticas sutis e corpos neuronais brilhantes.
 */

export function RedeFundo() {
  return (
    <svg
      className="auth-fundo-rede"
      viewBox="0 0 400 700"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <radialGradient id="brilho-no-ciano" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#3ee6e0" stopOpacity="0.9" />
          <stop offset="60%" stopColor="#3ee6e0" stopOpacity="0.4" />
          <stop offset="100%" stopColor="#3ee6e0" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="brilho-no-violeta" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#8b7bff" stopOpacity="0.9" />
          <stop offset="60%" stopColor="#8b7bff" stopOpacity="0.4" />
          <stop offset="100%" stopColor="#8b7bff" stopOpacity="0" />
        </radialGradient>
        <filter id="filtro-brilho" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>

      {/* Conexões (Sinapses) */}
      <g stroke="#2A2F55" strokeWidth="1.2" strokeLinecap="round" opacity="0.65">
        <line x1="50" y1="90" x2="130" y2="150" />
        <line x1="130" y1="150" x2="220" y2="110" />
        <line x1="220" y1="110" x2="330" y2="170" />
        <line x1="130" y1="150" x2="170" y2="260" />
        <line x1="170" y1="260" x2="70" y2="340" />
        <line x1="170" y1="260" x2="270" y2="310" />
        <line x1="270" y1="310" x2="350" y2="250" />
        <line x1="270" y1="310" x2="320" y2="420" />
        <line x1="70" y1="340" x2="140" y2="450" />
        <line x1="140" y1="450" x2="220" y2="480" />
        <line x1="220" y1="480" x2="320" y2="420" />
        <line x1="140" y1="450" x2="80" y2="570" />
        <line x1="220" y1="480" x2="260" y2="590" />
        <line x1="320" y1="420" x2="360" y2="560" />
        <line x1="80" y1="570" x2="180" y2="640" />
        <line x1="260" y1="590" x2="180" y2="640" />
        <line x1="260" y1="590" x2="340" y2="660" />
      </g>

      {/* Sinapses Ativas (Impulsos) */}
      <g stroke="#3ee6e0" strokeWidth="1.6" strokeLinecap="round" opacity="0.8" filter="url(#filtro-brilho)">
        <line x1="130" y1="150" x2="170" y2="260" />
        <line x1="170" y1="260" x2="270" y2="310" />
        <line x1="220" y1="480" x2="320" y2="420" />
        <line x1="220" y1="480" x2="260" y2="590" />
      </g>

      {/* Neurônios (Nós) */}
      <g>
        <circle cx="50" cy="90" r="5" fill="#8b7bff" opacity="0.6" />
        <circle cx="130" cy="150" r="6" fill="#3ee6e0" filter="url(#filtro-brilho)" />
        <circle cx="220" cy="110" r="4.5" fill="#5be49b" opacity="0.7" />
        <circle cx="330" cy="170" r="5.5" fill="#ffc857" opacity="0.6" />
        <circle cx="170" cy="260" r="7" fill="#8b7bff" filter="url(#filtro-brilho)" />
        <circle cx="70" cy="340" r="4" fill="#4a4f6e" opacity="0.5" />
        <circle cx="270" cy="310" r="6.5" fill="#3ee6e0" filter="url(#filtro-brilho)" />
        <circle cx="350" cy="250" r="4.5" fill="#8b7bff" opacity="0.6" />
        <circle cx="320" cy="420" r="7.5" fill="#8b7bff" filter="url(#filtro-brilho)" />
        <circle cx="140" cy="450" r="5" fill="#5be49b" opacity="0.7" />
        <circle cx="220" cy="480" r="7" fill="#3ee6e0" filter="url(#filtro-brilho)" />
        <circle cx="80" cy="570" r="5.5" fill="#ffc857" opacity="0.6" />
        <circle cx="260" cy="590" r="6" fill="#8b7bff" filter="url(#filtro-brilho)" />
        <circle cx="360" cy="560" r="4" fill="#4a4f6e" opacity="0.5" />
        <circle cx="180" cy="640" r="5" fill="#3ee6e0" opacity="0.7" />
        <circle cx="340" cy="660" r="4.5" fill="#5be49b" opacity="0.6" />
      </g>
    </svg>
  )
}
