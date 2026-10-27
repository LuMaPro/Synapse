import { Link } from 'react-router'
import type { CorLojaApi } from '../services/loja'
import { amostraDaCor } from '../utils/efeitos'

interface PaletaCoresProps {
  cores: CorLojaApi[]
  /** Hexadecimal escolhido. */
  valor: string
  onEscolher: (cor: string) => void
  /** Id do rótulo do campo, para o grupo de opções. */
  rotuloId: string
  desabilitada?: boolean
}

function Cadeado() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
      <path d="M7.5 11V8a4.5 4.5 0 0 1 9 0v3" fill="none" stroke="currentColor" strokeWidth="2.4" />
      <rect x="5" y="10.5" width="14" height="10" rx="2.5" fill="currentColor" />
    </svg>
  )
}

/**
 * As cores que o estudante pode dar a uma matéria (issues #28 e #34): as 8 da paleta
 * e as da loja. As que ainda não foram compradas aparecem com cadeado e o preço.
 */
export function PaletaCores({
  cores,
  valor,
  onEscolher,
  rotuloId,
  desabilitada = false,
}: PaletaCoresProps) {
  const daLoja = cores.filter((cor) => cor.preco > 0)

  function amostra(cor: CorLojaApi) {
    const bloqueada = !cor.desbloqueada
    const ativa = valor.toUpperCase() === cor.cor.toUpperCase()
    const classes = ['amostra-cor', ativa && 'ativa', bloqueada && 'bloqueada']
    const { className, style } = amostraDaCor(
      cor.cor,
      bloqueada ? null : cor.efeito,
      classes.filter(Boolean).join(' '),
    )
    return (
      <button
        key={cor.codigo}
        type="button"
        className={className}
        style={style}
        role="radio"
        aria-checked={ativa}
        aria-label={
          bloqueada ? `Cor ${cor.nome}, bloqueada: ${cor.preco} ATP na loja` : `Cor ${cor.nome}`
        }
        title={bloqueada ? `${cor.nome}: ${cor.preco} ATP na loja` : cor.nome}
        disabled={desabilitada || bloqueada}
        onClick={() => onEscolher(cor.cor)}
      >
        {bloqueada && <Cadeado />}
      </button>
    )
  }

  return (
    <>
      <div className="paleta-cores" role="radiogroup" aria-labelledby={rotuloId}>
        {cores.filter((cor) => cor.preco === 0).map(amostra)}
        {daLoja.length > 0 && <span className="paleta-separador" aria-hidden="true" />}
        {daLoja.map(amostra)}
      </div>
      {daLoja.some((cor) => !cor.desbloqueada) && (
        <p className="paleta-dica">
          As cores com cadeado são exclusivas da <Link to="/loja">Loja</Link>.
        </p>
      )}
    </>
  )
}
