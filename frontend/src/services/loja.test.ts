import { afterEach, describe, expect, it, vi } from 'vitest'
import { coresEmUso, lojaApi, type LojaApi, type TipoLojaApi } from './loja'

const LOJA: LojaApi = { saldo: 120, tipos: [] }

function respostaJson(corpo: unknown) {
  return new Response(JSON.stringify(corpo), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

function tipo(codigo: string, forma: TipoLojaApi['forma'], cor: string, emUso: boolean) {
  return {
    codigo,
    nome: codigo,
    forma,
    cor,
    preco: 0,
    duracao_minima: 10,
    duracao_maxima: null,
    desbloqueado: true,
    em_uso: emUso,
  }
}

describe('serviços da loja', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('busca a loja', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(respostaJson(LOJA))

    await expect(lojaApi.buscar()).resolves.toEqual(LOJA)
    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/loja')
  })

  it.each([
    ['comprar', 'http://localhost:8000/loja/piramidal_rosa/comprar'],
    ['usar', 'http://localhost:8000/loja/piramidal_rosa/usar'],
  ] as const)('%s manda um POST para o tipo', async (acao, endereco) => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(respostaJson(LOJA))

    await expect(lojaApi[acao]('piramidal_rosa')).resolves.toEqual(LOJA)
    expect(fetchMock.mock.calls[0][0]).toBe(endereco)
    expect(fetchMock.mock.calls[0][1]?.method).toBe('POST')
  })

  it('pega a cor do tipo em uso de cada forma', () => {
    const loja: LojaApi = {
      saldo: 0,
      tipos: [
        tipo('granular', 'granular', '#3EE6E0', true),
        tipo('piramidal', 'piramidal', '#8B7BFF', false),
        tipo('piramidal_rosa', 'piramidal', '#FF6FB5', true),
      ],
    }

    expect(coresEmUso(loja)).toEqual({ granular: '#3EE6E0', piramidal: '#FF6FB5' })
  })
})
