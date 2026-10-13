import type { ModoSessao } from '../hooks/useSessaoFoco'
import { formatarTempo } from '../utils/tempo'

interface SeletorModoProps {
  modo: ModoSessao
  /** Quanto tempo fora da tela o modo tolerante perdoa na duração escolhida. */
  toleranciaMs: number
  onEscolher: (modo: ModoSessao) => void
}

export function SeletorModo({ modo, toleranciaMs, onEscolher }: SeletorModoProps) {
  const opcoes: { valor: ModoSessao; titulo: string; descricao: string }[] = [
    {
      valor: 'estrito',
      titulo: 'Estrito',
      descricao: 'Saiu da tela, o neurônio é podado na hora.',
    },
    {
      valor: 'tolerante',
      titulo: 'Tolerante',
      descricao: `Até ${formatarTempo(toleranciaMs)} fora, somando todas as saídas.`,
    },
  ]

  return (
    <fieldset className="seletor-modo">
      <legend className="rotulo-campo">Modo</legend>
      {opcoes.map(({ valor, titulo, descricao }) => (
        <label key={valor} className="segmento">
          <input
            type="radio"
            name="modo"
            value={valor}
            checked={modo === valor}
            onChange={() => onEscolher(valor)}
          />
          <b>{titulo}</b>
          <span>{descricao}</span>
        </label>
      ))}
    </fieldset>
  )
}
