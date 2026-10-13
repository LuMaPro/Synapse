import type { TipoNeuronio } from './neuronio'

/*
 * Geometria do neurônio, portada de docs/design/prototipo.html (função
 * desenharNeuronio). O desenho é gerado por código a partir do tipo e do progresso
 * da sessão, com uma semente fixa por tipo: o mesmo neurônio sai sempre igual.
 */

interface Tronco {
  /** Ângulo de saída em graus (0 = direita, -90 = para cima). */
  ang: number
  len: number
  /** Quantas vezes o tronco se bifurca. */
  prof: number
}

interface ConfigTipo {
  semente: number
  corpo: 'circulo' | 'triangulo'
  raio: number
  centroY: number
  axonio: number
  largura: number
  abertura: number
  encurta: number
  troncos: Tronco[]
}

const TIPOS: Record<TipoNeuronio, ConfigTipo> = {
  granular: {
    semente: 7,
    corpo: 'circulo',
    raio: 8,
    centroY: 0,
    axonio: 44,
    largura: 2.4,
    abertura: 0.6,
    encurta: 0.62,
    troncos: [
      { ang: -140, len: 28, prof: 1 },
      { ang: -50, len: 26, prof: 1 },
      { ang: 30, len: 24, prof: 1 },
      { ang: 150, len: 26, prof: 1 },
    ],
  },
  piramidal: {
    semente: 11,
    corpo: 'triangulo',
    raio: 13,
    centroY: 14,
    axonio: 50,
    largura: 2.8,
    abertura: 0.52,
    encurta: 0.68,
    troncos: [
      { ang: -90, len: 31, prof: 3 },
      { ang: 155, len: 26, prof: 1 },
      { ang: 25, len: 26, prof: 1 },
      { ang: 120, len: 18, prof: 0 },
    ],
  },
  purkinje: {
    semente: 5,
    corpo: 'circulo',
    raio: 11,
    centroY: 22,
    axonio: 46,
    largura: 2.6,
    abertura: 0.42,
    encurta: 0.74,
    troncos: [
      { ang: -118, len: 26, prof: 4 },
      { ang: -62, len: 26, prof: 4 },
    ],
  },
}

/** Até onde o neurônio podado fica: recolhido em cerca de 40% (design da #8). */
export const PROGRESSO_PODADO = 0.42

/** Fatias do progresso: corpo celular, depois os dendritos nível a nível, e o axônio. */
const FIM_CORPO = 0.12
const FATIA_DENDRITOS = 0.66
const INICIO_AXONIO = 0.8

interface Ramo {
  d: string
  nivel: number
  largura: number
  fim: [number, number]
}

/** mulberry32: números "aleatórios" reproduzíveis a partir de uma semente. */
function aleatorio(semente: number) {
  let estado = semente
  return () => {
    estado |= 0
    estado = (estado + 0x6d2b79f5) | 0
    let t = Math.imul(estado ^ (estado >>> 15), 1 | estado)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const limitar = (valor: number) => Math.max(0, Math.min(1, valor))
const radianos = (graus: number) => (graus * Math.PI) / 180
const fmt = (n: number) => n.toFixed(1)

function gerarRamos(cfg: ConfigTipo) {
  const rnd = aleatorio(cfg.semente)
  const ramos: Ramo[] = []

  function ramo(x: number, y: number, ang: number, len: number, prof: number, nivel: number) {
    const a = ang + (rnd() - 0.5) * 0.25
    const x2 = x + Math.cos(a) * len
    const y2 = y + Math.sin(a) * len
    const curva = (rnd() - 0.5) * len * 0.35
    const cx = (x + x2) / 2 - Math.sin(a) * curva
    const cy = (y + y2) / 2 + Math.cos(a) * curva
    ramos.push({
      d: `M${fmt(x)} ${fmt(y)}Q${fmt(cx)} ${fmt(cy)} ${fmt(x2)} ${fmt(y2)}`,
      nivel,
      largura: Math.max(0.9, cfg.largura * (1 - nivel * 0.2)),
      fim: [x2, y2],
    })
    if (prof > 0) {
      ramo(x2, y2, a - cfg.abertura + (rnd() - 0.5) * 0.2, len * cfg.encurta, prof - 1, nivel + 1)
      ramo(x2, y2, a + cfg.abertura + (rnd() - 0.5) * 0.2, len * cfg.encurta, prof - 1, nivel + 1)
    }
  }

  for (const tronco of cfg.troncos) {
    const a = radianos(tronco.ang)
    const x = Math.cos(a) * cfg.raio * 0.8
    const y = cfg.centroY + Math.sin(a) * cfg.raio * 0.8
    ramo(x, y, a, tronco.len, tronco.prof, 0)
  }
  const niveis = Math.max(...ramos.map((r) => r.nivel)) + 1
  return { ramos, niveis }
}

const cache = new Map<TipoNeuronio, ReturnType<typeof gerarRamos>>()

function ramosDoTipo(tipo: TipoNeuronio) {
  let ramos = cache.get(tipo)
  if (!ramos) {
    ramos = gerarRamos(TIPOS[tipo])
    cache.set(tipo, ramos)
  }
  return ramos
}

export interface DesenhoNeuronio {
  /** Progresso efetivo (no podado, limitado a PROGRESSO_PODADO). */
  progresso: number
  dendritos: {
    d: string
    largura: number
    /** Quanto do traço já está desenhado, de 0 a 1. */
    crescimento: number
    /** Ponto na ponta dos ramos mais finos, aceso quando o ramo termina de crescer. */
    ponta: { cx: number; cy: number; visivel: boolean } | null
  }[]
  axonio: {
    d: string
    largura: number
    crescimento: number
    terminal: { cy: number; visivel: boolean }
  }
  corpo: {
    forma: 'circulo' | 'triangulo'
    /** Contorno no tamanho final; a escala faz o corpo crescer no início. */
    d: string
    cy: number
    raio: number
    escala: number
  }
}

/**
 * Calcula o desenho do neurônio para um progresso de 0 a 1.
 *
 * O corpo celular aparece primeiro (até 12%), os dendritos crescem nível a nível
 * (do tronco às pontas) e o axônio surge no fim (de 80% a 100%). Podado, o
 * neurônio recolhe até 42%: perde o axônio, as pontas e as ramificações finas.
 */
export function desenharNeuronio(
  tipo: TipoNeuronio,
  progresso: number,
  podado = false,
): DesenhoNeuronio {
  const cfg = TIPOS[tipo]
  const { ramos, niveis } = ramosDoTipo(tipo)
  const p = podado ? Math.min(limitar(progresso), PROGRESSO_PODADO) : limitar(progresso)
  const janela = FATIA_DENDRITOS / niveis

  const dendritos = ramos.map((r) => {
    const crescimento = limitar((p - FIM_CORPO - r.nivel * janela) / janela)
    const ehPonta = r.nivel === niveis - 1
    return {
      d: r.d,
      largura: r.largura,
      crescimento,
      ponta: ehPonta ? { cx: r.fim[0], cy: r.fim[1], visivel: crescimento >= 1 && !podado } : null,
    }
  })

  const yInicio = cfg.centroY + cfg.raio * 0.8
  const yFim = yInicio + cfg.axonio
  const crescimentoAxonio = limitar((p - INICIO_AXONIO) / (1 - INICIO_AXONIO))
  const axonio = {
    d: `M0 ${fmt(yInicio)}C4 ${fmt(yInicio + cfg.axonio * 0.4)} -4 ${fmt(yInicio + cfg.axonio * 0.7)} 0 ${fmt(yFim)}`,
    largura: cfg.largura * 0.8,
    crescimento: crescimentoAxonio,
    terminal: { cy: yFim + 3, visivel: crescimentoAxonio >= 1 },
  }

  const r = cfg.raio
  const cy = cfg.centroY
  const corpo = {
    forma: cfg.corpo,
    d:
      cfg.corpo === 'triangulo'
        ? `M0 ${fmt(cy - r * 1.25)}L${fmt(r * 1.05)} ${fmt(cy + r * 0.75)}L${fmt(-r * 1.05)} ${fmt(cy + r * 0.75)}Z`
        : '',
    cy,
    raio: r,
    escala: 0.4 + 0.6 * limitar(p / FIM_CORPO),
  }

  return { progresso: p, dendritos, axonio, corpo }
}
