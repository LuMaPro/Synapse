import type { ModoSessao } from '../hooks/useSessaoFoco'
import { formatarTempo } from '../utils/tempo'

interface AvisoSaidaProps {
  modo: ModoSessao
  /** Saldo de tempo fora que ainda resta no modo tolerante. */
  toleranciaRestanteMs: number
}

/** Lembrete, durante a sessão, do que acontece ao sair da tela em cada modo. */
export function AvisoSaida({ modo, toleranciaRestanteMs }: AvisoSaidaProps) {
  return (
    <div className="aviso">
      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <g fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" />
          <circle cx="12" cy="12" r="3" />
        </g>
      </svg>
      {modo === 'estrito' ? (
        <p>Trocar de aba, de app ou sair da tela cheia poda este neurônio.</p>
      ) : (
        <p>
          Você ainda pode ficar{' '}
          <b className="numero texto-forte">{formatarTempo(toleranciaRestanteMs)}</b> fora da tela.
          Passou disso, o neurônio é podado.
        </p>
      )}
    </div>
  )
}
