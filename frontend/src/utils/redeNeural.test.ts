import { describe, expect, it } from 'vitest'
import type { NeuronioRede, SinapseRede } from '../services/rede'
import {
  dendritos,
  ESCALA_PODADO,
  inicioDoPeriodo,
  posicionarRede,
  RAIO_TIPO,
  raioDoNeuronio,
  vizinhanca,
} from './redeNeural'

function neuronio(id: string, extra: Partial<NeuronioRede> = {}): NeuronioRede {
  return {
    id,
    tipo: 'piramidal',
    materia_id: null,
    cor: '#8B7BFF',
    criado_em: '2026-10-20T14:00:00+00:00',
    duracao_minutos: 25,
    vivo: true,
    ...extra,
  }
}

function sinapse(origem: string, destino: string, peso = 1): SinapseRede {
  return { id: `${origem}-${destino}`, origem_id: origem, destino_id: destino, peso }
}

/** Rede em corrente: cada neurônio ligado aos 2 anteriores, como a regra da #23. */
function corrente(tamanho: number) {
  const neuronios = Array.from({ length: tamanho }, (_, i) => neuronio(`n${i}`))
  const sinapses = neuronios.flatMap((_, i) =>
    [i - 2, i - 1].filter((j) => j >= 0).map((j) => sinapse(`n${j}`, `n${i}`)),
  )
  return { neuronios, sinapses }
}

describe('posicionarRede', () => {
  it('a mesma rede sempre fica com o mesmo desenho', () => {
    const { neuronios, sinapses } = corrente(30)

    const primeiro = posicionarRede(neuronios, sinapses)
    const segundo = posicionarRede(neuronios, sinapses)

    expect([...segundo.posicoes]).toEqual([...primeiro.posicoes])
  })

  it('posiciona todos os neurônios dentro da caixa, que vira o viewBox', () => {
    const { neuronios, sinapses } = corrente(40)
    neuronios.push(neuronio('podado', { vivo: false }))

    const { posicoes, caixa } = posicionarRede(neuronios, sinapses)

    expect(posicoes.size).toBe(41)
    for (const { x, y } of posicoes.values()) {
      expect(Number.isFinite(x) && Number.isFinite(y)).toBe(true)
      expect(x).toBeGreaterThan(caixa.x)
      expect(x).toBeLessThan(caixa.x + caixa.largura)
      expect(y).toBeGreaterThan(caixa.y)
      expect(y).toBeLessThan(caixa.y + caixa.altura)
    }
  })

  it('neurônios ligados ficam mais perto do que a média', () => {
    const { neuronios, sinapses } = corrente(40)
    const { posicoes } = posicionarRede(neuronios, sinapses)
    const distancia = (a: string, b: string) => {
      const [p, q] = [posicoes.get(a)!, posicoes.get(b)!]
      return Math.hypot(p.x - q.x, p.y - q.y)
    }

    const ligados = sinapses.map((s) => distancia(s.origem_id, s.destino_id))
    const todos = neuronios.flatMap((a, i) =>
      neuronios.slice(i + 1).map((b) => distancia(a.id, b.id)),
    )
    const media = (v: number[]) => v.reduce((x, y) => x + y) / v.length

    expect(media(ligados)).toBeLessThan(media(todos) / 2)
  })

  it('aceita a rede vazia', () => {
    const { posicoes, caixa } = posicionarRede([], [])

    expect(posicoes.size).toBe(0)
    expect(caixa.largura).toBeGreaterThan(0)
  })
})

describe('vizinhanca', () => {
  it('acende o neurônio, os vizinhos e, mais fraco, os vizinhos deles', () => {
    // a - b - c - d - e
    const sinapses = [sinapse('a', 'b'), sinapse('b', 'c'), sinapse('c', 'd'), sinapse('d', 'e')]

    const { vizinhos, segundoNivel } = vizinhanca('c', sinapses)

    expect([...vizinhos].sort()).toEqual(['b', 'c', 'd'])
    expect([...segundoNivel].sort()).toEqual(['a', 'e'])
  })

  it('neurônio sem sinapses (como o podado) acende sozinho', () => {
    const { vizinhos, segundoNivel } = vizinhanca('sozinho', [sinapse('a', 'b')])

    expect([...vizinhos]).toEqual(['sozinho'])
    expect(segundoNivel.size).toBe(0)
  })
})

describe('forma dos neurônios no grafo', () => {
  it('o tamanho segue o tipo, e o podado fica recolhido', () => {
    expect(raioDoNeuronio({ tipo: 'granular', vivo: true })).toBe(RAIO_TIPO.granular)
    expect(RAIO_TIPO.granular).toBeLessThan(RAIO_TIPO.piramidal)
    expect(RAIO_TIPO.piramidal).toBeLessThan(RAIO_TIPO.purkinje)
    expect(raioDoNeuronio({ tipo: 'purkinje', vivo: false })).toBe(
      RAIO_TIPO.purkinje * ESCALA_PODADO,
    )
  })

  it.each([
    ['granular', 5],
    ['piramidal', 3],
    ['purkinje', 5],
  ] as const)('o %s tem %i dendritos', (tipo, quantidade) => {
    const caminho = dendritos(tipo, RAIO_TIPO[tipo])

    expect(caminho.match(/M/g)).toHaveLength(quantidade)
  })

  it('o dendrito longo do piramidal aponta para cima', () => {
    const [primeiro] = dendritos('piramidal', 10).split('M').filter(Boolean)
    const [, fim] = primeiro.split('L')
    const [x, y] = fim.split(' ').map(Number)

    expect(Math.abs(x)).toBeLessThan(0.01)
    expect(y).toBeCloseTo(-22)
  })
})

describe('inicioDoPeriodo', () => {
  const agora = new Date(2026, 9, 22, 15, 30)

  it('sem período, não filtra', () => {
    expect(inicioDoPeriodo('sempre', agora)).toBeUndefined()
  })

  it('os últimos 7 dias começam à meia-noite de 6 dias atrás, no horário local', () => {
    expect(inicioDoPeriodo('7', agora)).toEqual(new Date(2026, 9, 16, 0, 0))
  })

  it('os últimos 30 dias atravessam o mês', () => {
    expect(inicioDoPeriodo('30', agora)).toEqual(new Date(2026, 8, 23, 0, 0))
  })
})
