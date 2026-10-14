import type { ModoSessao } from '../hooks/useSessaoFoco'
import { formatarTempo } from '../utils/tempo'

interface AvisoSaidaProps {
  modo: ModoSessao
  /** Saldo de tempo fora que ainda resta no modo tolerante. */
  toleranciaRestanteMs: number
  /** O estudante saiu da tela cheia e o saldo está sendo descontado. */
  foraDaTelaCheia: boolean
  onVoltarParaTelaCheia: () => void
}

/** Lembrete, durante a sessão, do que acontece ao sair da tela em cada modo. */
export function AvisoSaida({
  modo,
  toleranciaRestanteMs,
  foraDaTelaCheia,
  onVoltarParaTelaCheia,
}: AvisoSaidaProps) {
  const saldo = <b className="numero texto-forte">{formatarTempo(toleranciaRestanteMs)}</b>

  return (
    <div className="aviso-saida">
      {/* Sem aria-live: o saldo muda a cada segundo e o leitor de tela repetiria sem parar. */}
      <div className="aviso">
        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <g fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" />
            <circle cx="12" cy="12" r="3" />
          </g>
        </svg>
        {modo === 'estrito' ? (
          <p>Trocar de aba, de app ou sair da tela cheia poda este neurônio.</p>
        ) : foraDaTelaCheia ? (
          <p>
            Você saiu da tela cheia e o tempo fora está contando: restam {saldo}. Volte para não
            perder o neurônio.
          </p>
        ) : (
          <p>Você ainda pode ficar {saldo} fora da tela. Passou disso, o neurônio é podado.</p>
        )}
      </div>
      {foraDaTelaCheia && (
        <button type="button" className="botao secundario" onClick={onVoltarParaTelaCheia}>
          Voltar para a tela cheia
        </button>
      )}
    </div>
  )
}
