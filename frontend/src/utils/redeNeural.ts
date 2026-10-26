import {
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
  type SimulationNodeDatum,
} from 'd3-force'
import type { NeuronioRede, SinapseRede } from '../services/rede'
import type { TipoNeuronio } from './neuronio'

/** Raio do corpo celular de cada tipo no grafo, o mesmo do protótipo (docs/design). */
export const RAIO_TIPO: Record<TipoNeuronio, number> = {
  granular: 4.5,
  piramidal: 6.5,
  purkinje: 9,
}

/** O podado aparece recolhido: só o contorno, menor e sem dendritos. */
export const ESCALA_PODADO = 0.8

/** Folga em volta da rede, na mesma unidade das posições. */
const MARGEM = 24

/** Sorteio com semente fixa (mulberry32): o mesmo desenho a cada vez que a tela abre. */
function sorteador(semente: number): () => number {
  let estado = semente
  return () => {
    estado = (estado + 0x6d2b79f5) | 0
    let t = Math.imul(estado ^ (estado >>> 15), 1 | estado)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

export interface Posicao {
  x: number
  y: number
}

export interface Layout {
  posicoes: Map<string, Posicao>
  /** Área ocupada pela rede, com margem (vira o `viewBox` do SVG). */
  caixa: { x: number; y: number; largura: number; altura: number }
}

interface No extends SimulationNodeDatum {
  id: string
  raio: number
}

export function raioDoNeuronio(neuronio: Pick<NeuronioRede, 'tipo' | 'vivo'>): number {
  const raio = RAIO_TIPO[neuronio.tipo]
  return neuronio.vivo ? raio : raio * ESCALA_PODADO
}

/**
 * Posiciona a rede por simulação de forças (d3-force, como sugere a issue #26): os
 * neurônios se repelem, as sinapses puxam como molas e tudo é atraído levemente para
 * o centro. A simulação roda de uma vez, sem animação, e parte de posições sorteadas
 * com semente fixa, então a mesma rede sempre fica com o mesmo desenho.
 */
export function posicionarRede(
  neuronios: NeuronioRede[],
  sinapses: SinapseRede[],
  /** Altura ÷ largura da área: numa tela em pé (> 1), a rede fica mais alta que larga. */
  proporcao = 1,
): Layout {
  // A atração para o centro é mais forte no eixo menor, e o ponto de partida é uma
  // elipse com a forma da área: assim a rede ocupa a tela, em vez de uma faixa.
  const esticar = Math.sqrt(Math.min(Math.max(proporcao, 0.5), 2.5))
  // Começa espalhado num disco, e não na espiral padrão do d3: como cada neurônio se
  // liga aos mais recentes, a espiral virava uma corrente em arco, e não uma rede.
  const sortear = sorteador(42)
  const alcance = 30 * Math.sqrt(neuronios.length)
  const nos: No[] = neuronios.map((n) => {
    const angulo = sortear() * 2 * Math.PI
    const distancia = alcance * Math.sqrt(sortear())
    return {
      id: n.id,
      raio: raioDoNeuronio(n),
      x: (Math.cos(angulo) * distancia) / esticar,
      y: Math.sin(angulo) * distancia * esticar,
    }
  })
  const ligacoes = sinapses.map((s) => ({ source: s.origem_id, target: s.destino_id }))
  const ligados = new Set(sinapses.flatMap((s) => [s.origem_id, s.destino_id]))
  const atracao = (n: No) => (ligados.has(n.id) ? 0.05 : 0.25)
  const atracaoX = (n: No) => atracao(n) * esticar
  const atracaoY = (n: No) => atracao(n) / esticar

  const simulacao = forceSimulation(nos)
    // Assenta em 135 passos, e não nos 300 do padrão: como já começa espalhado, o
    // desenho muda pouco e o cálculo cai de ~0,5 s para ~0,2 s com 300 neurônios.
    .alphaDecay(0.05)
    .force('repulsao', forceManyBody<No>().strength(-70).distanceMax(260))
    .force(
      'sinapses',
      forceLink<No, (typeof ligacoes)[number]>(ligacoes)
        .id((n) => n.id)
        .distance(44)
        .strength(0.35),
    )
    .force(
      'colisao',
      forceCollide<No>((n) => n.raio + 4),
    )
    // Puxa tudo para o centro; mais forte nos neurônios sem sinapses (como os podados),
    // que senão a repulsão empurra para longe e a rede fica pequena na tela.
    .force('x', forceX<No>(0).strength(atracaoX))
    .force('y', forceY<No>(0).strength(atracaoY))
    .stop()

  const passos = Math.ceil(Math.log(simulacao.alphaMin()) / Math.log(1 - simulacao.alphaDecay()))
  for (let i = 0; i < passos; i++) simulacao.tick()

  const posicoes = new Map(nos.map((n) => [n.id, { x: n.x ?? 0, y: n.y ?? 0 }]))
  return { posicoes, caixa: caixaDe(nos) }
}

function caixaDe(nos: No[]): Layout['caixa'] {
  if (nos.length === 0) return { x: -MARGEM, y: -MARGEM, largura: 2 * MARGEM, altura: 2 * MARGEM }
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  for (const n of nos) {
    // Folga para os dendritos, que passam do corpo celular.
    const alcance = n.raio * 2.4
    minX = Math.min(minX, (n.x ?? 0) - alcance)
    minY = Math.min(minY, (n.y ?? 0) - alcance)
    maxX = Math.max(maxX, (n.x ?? 0) + alcance)
    maxY = Math.max(maxY, (n.y ?? 0) + alcance)
  }
  return {
    x: minX - MARGEM,
    y: minY - MARGEM,
    largura: maxX - minX + 2 * MARGEM,
    altura: maxY - minY + 2 * MARGEM,
  }
}

export interface Vizinhanca {
  /** O neurônio e os ligados diretamente a ele. */
  vizinhos: Set<string>
  /** Os ligados aos vizinhos: até onde o brilho se propaga. */
  segundoNivel: Set<string>
}

/** Quem acende quando um neurônio é tocado: ele, os vizinhos e os vizinhos deles. */
export function vizinhanca(id: string, sinapses: SinapseRede[]): Vizinhanca {
  const vizinhos = new Set([id])
  for (const s of sinapses) {
    if (s.origem_id === id) vizinhos.add(s.destino_id)
    if (s.destino_id === id) vizinhos.add(s.origem_id)
  }
  const segundoNivel = new Set<string>()
  for (const s of sinapses) {
    if (vizinhos.has(s.origem_id) && !vizinhos.has(s.destino_id)) segundoNivel.add(s.destino_id)
    if (vizinhos.has(s.destino_id) && !vizinhos.has(s.origem_id)) segundoNivel.add(s.origem_id)
  }
  return { vizinhos, segundoNivel }
}

function raios(raio: number, angulos: number[], comprimento: number): string {
  return angulos
    .map((graus) => {
      const rad = (graus * Math.PI) / 180
      const [cos, sen] = [Math.cos(rad), Math.sin(rad)]
      const [x1, y1] = [cos * raio * 0.9, sen * raio * 0.9]
      const [x2, y2] = [cos * comprimento, sen * comprimento]
      return `M${x1.toFixed(2)} ${y1.toFixed(2)}L${x2.toFixed(2)} ${y2.toFixed(2)}`
    })
    .join('')
}

/**
 * Dendritos do neurônio no grafo, em volta do centro (0, 0), com a forma de cada tipo
 * do design: granular em estrela curta, piramidal com um dendrito longo para cima e
 * dois para os lados, Purkinje com um leque para cima.
 */
export function dendritos(tipo: TipoNeuronio, raio: number): string {
  switch (tipo) {
    case 'granular':
      return raios(raio, [-90, -18, 54, 126, 198], raio * 1.75)
    case 'piramidal':
      return raios(raio, [-90], raio * 2.2) + raios(raio, [150, 30], raio * 1.6)
    case 'purkinje':
      return raios(raio, [-150, -120, -90, -60, -30], raio * 2)
  }
}

export type Periodo = 'sempre' | '7' | '30'

/** Começo do período: meia-noite (no horário local) do primeiro dia dos últimos N dias. */
export function inicioDoPeriodo(periodo: Periodo, agora: Date = new Date()): Date | undefined {
  if (periodo === 'sempre') return undefined
  const inicio = new Date(agora)
  inicio.setHours(0, 0, 0, 0)
  inicio.setDate(inicio.getDate() - (Number(periodo) - 1))
  return inicio
}
