import { describe, expect, it } from 'vitest'
import type { SessaoApi } from '../services/sessoes'
import { agruparPorDia, descreverResultado, horaDoInicio, rotuloDoDia } from './historico'

// Datas no fuso do navegador, como a tela agrupa: o teste vale em qualquer fuso.
const AGORA = new Date(2026, 9, 26, 15, 0)

function sessao(id: string, inicio: Date, extra: Partial<SessaoApi> = {}): SessaoApi {
  return {
    id,
    duracao_minutos: 25,
    modo: 'estrito',
    materia_id: null,
    estado: 'concluida',
    inicio: inicio.toISOString(),
    fim_previsto: new Date(inicio.getTime() + 25 * 60_000).toISOString(),
    encerrada_em: new Date(inicio.getTime() + 25 * 60_000).toISOString(),
    restante_segundos: 0,
    tempo_fora_segundos: 0,
    ...extra,
  }
}

describe('rotuloDoDia', () => {
  it('chama o dia atual de "Hoje" e o anterior de "Ontem"', () => {
    expect(rotuloDoDia(new Date(2026, 9, 26, 0, 5), AGORA)).toBe('Hoje')
    expect(rotuloDoDia(new Date(2026, 9, 25, 23, 59), AGORA)).toBe('Ontem')
  })

  it('escreve os outros dias por extenso, com o ano só se não for o atual', () => {
    expect(rotuloDoDia(new Date(2026, 9, 20, 9, 0), AGORA)).toMatch(/20 de out/)
    expect(rotuloDoDia(new Date(2026, 9, 20, 9, 0), AGORA)).not.toMatch(/2026/)
    expect(rotuloDoDia(new Date(2025, 11, 31, 9, 0), AGORA)).toMatch(/31 de dez.*2025/)
  })
})

describe('agruparPorDia', () => {
  it('junta as sessões de cada dia, na ordem em que vieram', () => {
    const dias = agruparPorDia(
      [
        sessao('c', new Date(2026, 9, 26, 14, 0)),
        sessao('b', new Date(2026, 9, 26, 9, 0)),
        sessao('a', new Date(2026, 9, 24, 22, 30)),
      ],
      AGORA,
    )

    expect(dias.map((d) => [d.rotulo, d.sessoes.map((s) => s.id)])).toEqual([
      ['Hoje', ['c', 'b']],
      [expect.stringMatching(/24 de out/), ['a']],
    ])
  })

  it('sem sessões, não tem dias', () => {
    expect(agruparPorDia([], AGORA)).toEqual([])
  })
})

describe('descrição da sessão', () => {
  it('mostra a hora do início', () => {
    expect(horaDoInicio(sessao('a', new Date(2026, 9, 26, 9, 5)))).toBe('09:05')
  })

  it('descreve o resultado, com o tempo até a poda', () => {
    const inicio = new Date(2026, 9, 26, 9, 0)
    const podada = sessao('p', inicio, {
      estado: 'podada',
      encerrada_em: new Date(inicio.getTime() + 180_000).toISOString(),
    })

    expect(descreverResultado(sessao('c', inicio))).toBe('Concluída')
    expect(descreverResultado(podada)).toBe('Podada aos 03:00')
    // Como na tela de poda, a fração de segundo arredonda para cima.
    expect(
      descreverResultado({
        ...podada,
        encerrada_em: new Date(inicio.getTime() + 10_300).toISOString(),
      }),
    ).toBe('Podada aos 00:11')
    expect(descreverResultado({ ...podada, encerrada_em: null })).toBe('Podada')
    expect(
      descreverResultado(sessao('e', inicio, { estado: 'em_andamento', encerrada_em: null })),
    ).toBe('Em andamento')
  })
})
