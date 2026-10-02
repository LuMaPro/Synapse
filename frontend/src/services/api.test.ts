import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError } from './api'

function respostaJson(status: number, corpo: unknown) {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('api', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('faz GET na URL base da API e devolve o JSON', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(respostaJson(200, { status: 'ok' }))

    await expect(api.get('/health')).resolves.toEqual({ status: 'ok' })
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/health',
      expect.objectContaining({ method: 'GET' }),
    )
  })

  it('envia o corpo como JSON no POST', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(respostaJson(201, {}))

    await api.post('/sessoes', { duracao: 25 })

    const [, opcoes] = fetchMock.mock.calls[0]
    expect(opcoes?.body).toBe(JSON.stringify({ duracao: 25 }))
    expect(opcoes?.headers).toEqual({ 'Content-Type': 'application/json' })
  })

  it('transforma o erro padrão da API em ApiError', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      respostaJson(409, { erro: 'sessao_ativa', mensagem: 'Já existe uma sessão em andamento' }),
    )

    const erro = await api.post('/sessoes').catch((e: unknown) => e)
    expect(erro).toBeInstanceOf(ApiError)
    expect(erro).toMatchObject({
      status: 409,
      codigo: 'sessao_ativa',
      message: 'Já existe uma sessão em andamento',
    })
  })

  it('usa uma mensagem genérica quando o erro não vem no formato padrão', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('falhou', { status: 500 }))

    await expect(api.get('/qualquer')).rejects.toMatchObject({
      status: 500,
      codigo: 'erro_desconhecido',
    })
  })
})
