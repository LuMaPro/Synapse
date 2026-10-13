import { DURACAO_MAXIMA, DURACAO_MINIMA, PASSO_DURACAO } from '../hooks/useSessaoFoco'
import { NOME_TIPO_NEURONIO, tipoNeuronio } from '../utils/neuronio'
import { AnelProgresso } from './AnelProgresso'

interface SeletorDuracaoProps {
  minutos: number
  podeDiminuir: boolean
  podeAumentar: boolean
  onDiminuir: () => void
  onAumentar: () => void
}

export function SeletorDuracao({
  minutos,
  podeDiminuir,
  podeAumentar,
  onDiminuir,
  onAumentar,
}: SeletorDuracaoProps) {
  return (
    <div className="seletor-duracao">
      <div className="seletor-duracao-controles">
        <button
          type="button"
          className="botao-redondo"
          onClick={onDiminuir}
          disabled={!podeDiminuir}
          aria-label={`Diminuir ${PASSO_DURACAO} minutos`}
        >
          −
        </button>
        <AnelProgresso progresso={minutos / DURACAO_MAXIMA}>
          <output className="seletor-duracao-valor numero" aria-live="polite">
            {minutos}
            <span className="sr-only"> minutos</span>
          </output>
          <span className="texto-fraco" aria-hidden="true">
            minutos
          </span>
        </AnelProgresso>
        <button
          type="button"
          className="botao-redondo"
          onClick={onAumentar}
          disabled={!podeAumentar}
          aria-label={`Aumentar ${PASSO_DURACAO} minutos`}
        >
          +
        </button>
      </div>
      <p className="texto-fraco">
        De {DURACAO_MINIMA} a {DURACAO_MAXIMA} min · gera um neurônio{' '}
        <b className="destaque-suave">{NOME_TIPO_NEURONIO[tipoNeuronio(minutos)]}</b>
      </p>
    </div>
  )
}
