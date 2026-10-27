import { afterEach, describe, expect, it, vi } from 'vitest'
import { lojaApi, type LojaApi } from './loja'

const LOJA: LojaApi = { saldo: 120, cores: [] }

function respostaJson(corpo: unknown) {
  return new Response(JSON.stringify(corpo), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
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

  it('compra a cor com um POST', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(respostaJson(LOJA))

    await expect(lojaApi.comprar('arco_iris')).resolves.toEqual(LOJA)
    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/loja/arco_iris/comprar')
    expect(fetchMock.mock.calls[0][1]?.method).toBe('POST')
  })
})
