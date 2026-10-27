import { select } from 'd3-selection'
import { zoom } from 'd3-zoom'
import {
  memo,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type MouseEvent,
  type PointerEvent,
} from 'react'
import type { NeuronioRede, SinapseRede } from '../services/rede'
import { classeDoEfeito, type Efeito } from '../utils/efeitos'
import { NOME_TIPO_NEURONIO } from '../utils/neuronio'
import {
  dendritos,
  posicionarRede,
  raioDoNeuronio,
  RAIO_TIPO,
  vizinhanca,
} from '../utils/redeNeural'

/** Quanto o neurônio tocado cresce para se destacar (como no protótipo). */
const AUMENTO_FOCO = 1.35
/** Área de toque mínima em volta de cada neurônio, para acertar com o dedo. */
const RAIO_TOQUE = 11

type EstadoNeuronio = 'foco' | 'vizinho' | 'segundo' | undefined
type EstadoSinapse = 'direta' | 'indireta' | undefined

interface NeuronioGrafoProps {
  neuronio: NeuronioRede
  x: number
  y: number
  cor: string
  /** Animação da cor da matéria (#34); o podado nunca tem. */
  efeito: Efeito | null
  estado: EstadoNeuronio
  onAtivar: (id: string) => void
}

/** Um neurônio do grafo: dendritos e corpo celular (vivo) ou só o contorno (podado). */
const NeuronioGrafo = memo(function NeuronioGrafo({
  neuronio,
  x,
  y,
  cor,
  efeito,
  estado,
  onAtivar,
}: NeuronioGrafoProps) {
  const raio = raioDoNeuronio(neuronio) * (estado === 'foco' ? AUMENTO_FOCO : 1)
  const comEfeito = neuronio.vivo ? efeito : null
  const classes = [
    'rede-neuronio',
    estado,
    neuronio.vivo ? undefined : 'podado',
    classeDoEfeito(comEfeito),
  ]

  return (
    <g
      className={classes.filter(Boolean).join(' ')}
      style={comEfeito ? ({ '--cor-neuronio': cor } as CSSProperties) : undefined}
      transform={`translate(${x.toFixed(1)} ${y.toFixed(1)})`}
      data-id={neuronio.id}
      onPointerEnter={(evento: PointerEvent) => {
        // No toque, quem acende é o clique; o pointerenter do dedo viria antes do arrasto.
        if (evento.pointerType === 'mouse') onAtivar(neuronio.id)
      }}
      onClick={() => onAtivar(neuronio.id)}
    >
      {neuronio.vivo ? (
        <>
          <path
            className="rede-dendritos"
            d={dendritos(neuronio.tipo, RAIO_TIPO[neuronio.tipo])}
            stroke={cor}
            strokeWidth={RAIO_TIPO[neuronio.tipo] * 0.28}
          />
          <circle className="rede-corpo" r={raio} fill={cor} />
          {(comEfeito === 'tempestade' || comEfeito === 'galaxia') && (
            <circle className="rede-aura" r={raio + 3.5} />
          )}
        </>
      ) : (
        <circle className="rede-contorno-podado" r={raio} />
      )}
      <circle className="rede-alvo" r={Math.max(raio, RAIO_TOQUE)} />
    </g>
  )
})

interface SinapseGrafoProps {
  x1: number
  y1: number
  x2: number
  y2: number
  peso: number
  estado: EstadoSinapse
}

/** Uma sinapse: mais grossa quanto maior o peso. Só redesenha se o estado mudar. */
const SinapseGrafo = memo(function SinapseGrafo({
  x1,
  y1,
  x2,
  y2,
  peso,
  estado,
}: SinapseGrafoProps) {
  return (
    <line
      className={estado ? `rede-sinapse ${estado}` : 'rede-sinapse'}
      x1={x1.toFixed(1)}
      y1={y1.toFixed(1)}
      x2={x2.toFixed(1)}
      y2={y2.toFixed(1)}
      strokeWidth={0.7 + peso * 0.4}
    />
  )
})

/**
 * Proporção (altura ÷ largura) da área da rede, estimada pelo tamanho da janela com
 * as mesmas medidas do CSS (rede.css e .conteudo), para o layout já sair no formato
 * certo, sem calcular duas vezes.
 */
function proporcaoDaArea(): number {
  const largura = Math.min(window.innerWidth, 960) - 48
  const altura = Math.min(Math.max(window.innerHeight * 0.68, 340), 620)
  return largura > 0 ? altura / largura : 1
}

function ultimoVivo(neuronios: NeuronioRede[]): string | null {
  return neuronios.findLast((n) => n.vivo)?.id ?? null
}

function dataCurta(iso: string): string {
  return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
}

interface GrafoRedeProps {
  neuronios: NeuronioRede[]
  sinapses: SinapseRede[]
  /** Cor do neurônio vivo: a da matéria ou, sem matéria, a do tipo. */
  corDe: (neuronio: NeuronioRede) => string
  /** Animação da cor da matéria, se for uma cor com efeito da loja (#34). */
  efeitoDe?: (neuronio: NeuronioRede) => Efeito | null
  nomeDaMateria: (neuronio: NeuronioRede) => string | null
}

/**
 * A rede neural interativa (issue #26), no desenho do protótipo (docs/design).
 *
 * Passar o mouse ou tocar num neurônio o acende, junto com as sinapses dele, e o
 * brilho se propaga para os vizinhos e, mais fraco, para os vizinhos deles. A roda do
 * mouse e a pinça aproximam; arrastar move a rede (d3-zoom). O zoom muda só o
 * `transform` de um grupo, direto no DOM: o React não redesenha os neurônios a cada
 * quadro, o que mantém o movimento fluido com centenas deles.
 */
export function GrafoRede({ neuronios, sinapses, corDe, efeitoDe, nomeDaMateria }: GrafoRedeProps) {
  const areaRef = useRef<HTMLDivElement>(null)
  const svgRef = useRef<SVGSVGElement>(null)
  const camadaRef = useRef<SVGGElement>(null)
  const dicaRef = useRef<HTMLDivElement>(null)
  // Começa com o neurônio mais recente aceso, como no protótipo.
  const [realce, setRealce] = useState<string | null>(() => ultimoVivo(neuronios))
  const realceRef = useRef(realce)

  const [proporcao] = useState(proporcaoDaArea)
  const { posicoes, caixa } = useMemo(
    () => posicionarRede(neuronios, sinapses, proporcao),
    [neuronios, sinapses, proporcao],
  )
  const porId = useMemo(() => new Map(neuronios.map((n) => [n.id, n])), [neuronios])
  const aceso = useMemo(
    () => (realce === null ? null : vizinhanca(realce, sinapses)),
    [realce, sinapses],
  )

  /** Põe a dica logo abaixo do neurônio aceso (ou acima, perto da borda de baixo). */
  const posicionarDica = useCallback(() => {
    const area = areaRef.current
    const dica = dicaRef.current
    const id = realceRef.current
    if (!area || !dica || id === null) return
    const alvo = area.querySelector(`[data-id="${id}"] .rede-alvo`)
    if (!alvo) return
    const caixaArea = area.getBoundingClientRect()
    const caixaAlvo = alvo.getBoundingClientRect()
    const centroX = caixaAlvo.left + caixaAlvo.width / 2 - caixaArea.left
    const largura = dica.offsetWidth
    const esquerda = Math.min(Math.max(centroX - largura / 2, 8), caixaArea.width - largura - 8)
    const embaixo = caixaAlvo.bottom - caixaArea.top + 6
    const emCima = caixaAlvo.top - caixaArea.top - dica.offsetHeight - 6
    const topo = embaixo + dica.offsetHeight > caixaArea.height - 8 ? emCima : embaixo
    dica.style.left = `${esquerda}px`
    dica.style.top = `${topo}px`
  }, [])

  useLayoutEffect(() => {
    realceRef.current = realce
    posicionarDica()
  }, [realce, posicionarDica])

  useEffect(() => {
    const svg = svgRef.current
    const camada = camadaRef.current
    if (!svg || !camada) return
    const comportamento = zoom<SVGSVGElement, unknown>()
      // O viewBox já enquadra a rede inteira: a escala 1 é a visão geral.
      .extent([
        [caixa.x, caixa.y],
        [caixa.x + caixa.largura, caixa.y + caixa.altura],
      ])
      .scaleExtent([0.6, 8])
      // Um toque que mexe poucos pixels ainda conta como toque, e não como arrasto.
      .clickDistance(6)
      .on('zoom', ({ transform }) => {
        camada.setAttribute('transform', transform.toString())
        posicionarDica()
      })
    const selecao = select(svg).call(comportamento)
    // A rede acompanha o tamanho da tela; a dica precisa ir junto.
    window.addEventListener('resize', posicionarDica)
    return () => {
      selecao.on('.zoom', null)
      window.removeEventListener('resize', posicionarDica)
    }
  }, [caixa, posicionarDica])

  const ativar = useCallback((id: string) => setRealce(id), [])

  function aoClicarNoFundo(evento: MouseEvent<SVGSVGElement>) {
    if (!(evento.target as Element).closest('.rede-neuronio')) setRealce(null)
  }

  const vivos = neuronios.filter((n) => n.vivo).length
  const focado = realce === null ? undefined : porId.get(realce)
  const materiaFocada = focado ? nomeDaMateria(focado) : null

  function estadoDoNeuronio(id: string): EstadoNeuronio {
    if (!aceso) return undefined
    if (id === realce) return 'foco'
    if (aceso.vizinhos.has(id)) return 'vizinho'
    if (aceso.segundoNivel.has(id)) return 'segundo'
    return undefined
  }

  function estadoDaSinapse(s: SinapseRede): EstadoSinapse {
    if (!aceso || realce === null) return undefined
    if (s.origem_id === realce || s.destino_id === realce) return 'direta'
    const { vizinhos, segundoNivel } = aceso
    const tocaVizinho = vizinhos.has(s.origem_id) || vizinhos.has(s.destino_id)
    const tocaRede =
      (vizinhos.has(s.origem_id) || segundoNivel.has(s.origem_id)) &&
      (vizinhos.has(s.destino_id) || segundoNivel.has(s.destino_id))
    return tocaVizinho && tocaRede ? 'indireta' : undefined
  }

  return (
    <div className={aceso ? 'rede-area com-realce' : 'rede-area'} ref={areaRef}>
      <svg
        ref={svgRef}
        viewBox={`${caixa.x} ${caixa.y} ${caixa.largura} ${caixa.altura}`}
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label={`Rede com ${vivos} neurônios vivos, ${neuronios.length - vivos} podados e ${sinapses.length} sinapses`}
        onClick={aoClicarNoFundo}
      >
        <defs>
          {/* Nas linhas, a área do filtro precisa ser fixa: uma linha reta não tem altura. */}
          <filter
            id="rede-brilho-sinapse"
            filterUnits="userSpaceOnUse"
            x={caixa.x}
            y={caixa.y}
            width={caixa.largura}
            height={caixa.altura}
          >
            <feGaussianBlur stdDeviation="1.6" result="borrado" />
            <feMerge>
              <feMergeNode in="borrado" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="rede-brilho" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="2.2" result="borrado" />
            <feMerge>
              <feMergeNode in="borrado" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="rede-brilho-forte" x="-150%" y="-150%" width="400%" height="400%">
            <feGaussianBlur stdDeviation="4.5" result="borrado" />
            <feMerge>
              <feMergeNode in="borrado" />
              <feMergeNode in="borrado" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <g ref={camadaRef}>
          <g className="rede-sinapses">
            {sinapses.map((s) => {
              const a = posicoes.get(s.origem_id)
              const b = posicoes.get(s.destino_id)
              if (!a || !b) return null
              return (
                <SinapseGrafo
                  key={s.id}
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  peso={s.peso}
                  estado={estadoDaSinapse(s)}
                />
              )
            })}
          </g>
          <g className="rede-neuronios">
            {neuronios.map((n) => {
              const posicao = posicoes.get(n.id)
              if (!posicao) return null
              return (
                <NeuronioGrafo
                  key={n.id}
                  neuronio={n}
                  x={posicao.x}
                  y={posicao.y}
                  cor={n.vivo ? corDe(n) : n.cor}
                  efeito={efeitoDe?.(n) ?? null}
                  estado={estadoDoNeuronio(n.id)}
                  onAtivar={ativar}
                />
              )
            })}
          </g>
        </g>
      </svg>
      {focado && (
        <div className="dica-no" ref={dicaRef}>
          <b>
            {materiaFocada ?? 'Sem matéria'} · {focado.duracao_minutos} min
          </b>
          {NOME_TIPO_NEURONIO[focado.tipo]}
          {focado.vivo ? '' : ' podado'} · {dataCurta(focado.criado_em)}
        </div>
      )}
    </div>
  )
}
