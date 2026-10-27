import { useEffect, useState, type CSSProperties } from 'react'
import '../styles/neuronio.css'
import { desenharNeuronio } from '../utils/geometriaNeuronio'
import { COR_PADRAO_TIPO_NEURONIO, NOME_TIPO_NEURONIO, type TipoNeuronio } from '../utils/neuronio'

interface TracoProps {
  d: string
  largura: number
  /** De 0 a 1: quanto do traço já está desenhado. */
  crescimento: number
}

/** Dendrito ou axônio que se "desenha" do início ao fim com o crescimento. */
function Traco({ d, largura, crescimento }: TracoProps) {
  return (
    <path
      className={crescimento > 0 ? 'neuronio-traco' : 'neuronio-traco neuronio-traco-vazio'}
      d={d}
      pathLength={1}
      strokeDasharray={1}
      strokeWidth={largura}
      style={{ strokeDashoffset: 1 - crescimento }}
    />
  )
}

interface NeuronioAnimadoProps {
  tipo: TipoNeuronio
  /** De 0 (só o corpo celular) a 1 (completo, com axônio). */
  progresso: number
  /** Sessão interrompida: recolhe os ramos e fica cinza, sem brilho. */
  podado?: boolean
  /** Cor da matéria (#28) ou do tipo escolhido na loja (#34). Sem ela, a padrão. */
  cor?: string
  /** Brilho mais forte para o neurônio recém-formado (tela de sucesso). */
  brilho?: 'normal' | 'forte'
  /** Largura e altura em px. */
  tamanho?: number
  /** Descrição para leitores de tela; sem ela, diz o tipo e quanto está formado. */
  rotulo?: string
}

/**
 * Neurônio em SVG que cresce com o progresso da sessão (issue #19).
 *
 * O desenho vem de `desenharNeuronio`; a animação entre um estado e outro é feita
 * por transições CSS (styles/neuronio.css), que respeitam `prefers-reduced-motion`.
 */
export function NeuronioAnimado({
  tipo,
  progresso,
  podado = false,
  cor,
  brilho = 'normal',
  tamanho = 260,
  rotulo,
}: NeuronioAnimadoProps) {
  // O primeiro quadro mostra o neurônio vivo e com brilho normal; só depois aplica a
  // poda ou o brilho forte. Assim a transição acontece na frente do estudante.
  const [montado, setMontado] = useState(false)
  useEffect(() => {
    const quadro = requestAnimationFrame(() => setMontado(true))
    return () => cancelAnimationFrame(quadro)
  }, [])

  const podadoAgora = podado && montado
  const brilhoForte = brilho === 'forte' && montado && !podado
  const desenho = desenharNeuronio(tipo, progresso, podadoAgora)

  const classes = ['neuronio']
  if (podadoAgora) classes.push('neuronio-podado')
  if (brilhoForte) classes.push('neuronio-brilho-forte')

  // Podado, a cor cinza vem do CSS (.neuronio-podado); vivo, a da matéria ou a do tipo.
  // O raio equivale ao feGaussianBlur (stdDeviation 2.6) do protótipo, na escala do SVG.
  const estilo = {
    '--raio-brilho': `${((tamanho / 160) * 5).toFixed(1)}px`,
    ...(podadoAgora ? {} : { '--cor-neuronio': cor ?? COR_PADRAO_TIPO_NEURONIO[tipo] }),
  } as CSSProperties

  const descricao =
    rotulo ??
    (podado
      ? `Neurônio ${NOME_TIPO_NEURONIO[tipo]} podado`
      : `Neurônio ${NOME_TIPO_NEURONIO[tipo]}, ${Math.round(desenho.progresso * 100)}% formado`)

  const { corpo, axonio } = desenho

  return (
    <svg
      className={classes.join(' ')}
      viewBox="-80 -80 160 160"
      width={tamanho}
      height={tamanho}
      role="img"
      aria-label={descricao}
      style={estilo}
    >
      <g className="neuronio-desenho">
        {desenho.dendritos.map((dendrito, i) => (
          <Traco key={i} {...dendrito} />
        ))}
        {desenho.dendritos.map(
          (dendrito, i) =>
            dendrito.ponta && (
              <circle
                key={`ponta-${i}`}
                className="neuronio-ponta"
                cx={dendrito.ponta.cx}
                cy={dendrito.ponta.cy}
                r={1.4}
                style={{ opacity: dendrito.ponta.visivel ? 1 : 0 }}
              />
            ),
        )}
        <Traco {...axonio} />
        <circle
          className="neuronio-terminal"
          cx={0}
          cy={axonio.terminal.cy}
          r={3.6}
          style={{ opacity: axonio.terminal.visivel ? 1 : 0 }}
        />
        {corpo.forma === 'triangulo' ? (
          <path
            className="neuronio-corpo"
            d={corpo.d}
            strokeWidth={2}
            strokeLinejoin="round"
            style={{ transform: `scale(${corpo.escala})` }}
          />
        ) : (
          <circle
            className="neuronio-corpo"
            cx={0}
            cy={corpo.cy}
            r={corpo.raio}
            style={{ transform: `scale(${corpo.escala})` }}
          />
        )}
      </g>
    </svg>
  )
}
