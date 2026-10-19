import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError, configurarSessao, definirTokenApi, obterTokenApi } from './api'

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

  describe('postEmSegundoPlano', () => {
    it('envia com keepalive, para continuar mesmo com a aba escondida ou fechando', async () => {
      const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(respostaJson(201, {}))

      await expect(api.postEmSegundoPlano('/sessoes/1/interrupcoes', { inicio: 1 })).resolves.toBe(
        true,
      )
      const [url, opcoes] = fetchMock.mock.calls[0]
      expect(url).toBe('http://localhost:8000/sessoes/1/interrupcoes')
      expect(opcoes).toMatchObject({
        method: 'POST',
        keepalive: true,
        body: JSON.stringify({ inicio: 1 }),
      })
    })

    it('não lança erro se a rede falhar ou o servidor recusar', async () => {
      vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new TypeError('Failed to fetch'))
      await expect(api.postEmSegundoPlano('/x', {})).resolves.toBe(false)

      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(respostaJson(500, {}))
      await expect(api.postEmSegundoPlano('/x', {})).resolves.toBe(false)
    })

    it('injeta o token de autenticação nos cabeçalhos quando configurado', async () => {
      definirTokenApi('token-teste-123')
      const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(respostaJson(200, {}))

      await api.get('/me')
      const [, opcoes] = fetchMock.mock.calls[0]
      expect(opcoes?.headers).toMatchObject({ Authorization: 'Bearer token-teste-123' })

      definirTokenApi(null)
    })
  })
})

describe('renovação automática do token', () => {
  let renovar: ReturnType<typeof vi.fn<() => Promise<string | null>>>
  let aoExpirar: ReturnType<typeof vi.fn<() => void>>

  /** Servidor falso: aceita só o token "novo" e recusa o "velho" com 401. */
  function simularServidor() {
    return vi.spyOn(globalThis, 'fetch').mockImplementation(async (_url, opcoes) => {
      const autorizacao = (opcoes?.headers as Record<string, string> | undefined)?.Authorization
      if (autorizacao === 'Bearer novo') return respostaJson(200, { ok: true })
      return respostaJson(401, {
        erro: 'nao_autenticado',
        mensagem: 'Credenciais ausentes ou inválidas.',
      })
    })
  }

  beforeEach(() => {
    definirTokenApi('velho')
    renovar = vi.fn(async () => {
      definirTokenApi('novo')
      return 'novo'
    })
    aoExpirar = vi.fn()
    configurarSessao({ renovar, aoExpirar })
  })

  afterEach(() => {
    configurarSessao(null)
    definirTokenApi(null)
    vi.restoreAllMocks()
  })

  it('com o token expirado, renova e repete a chamada com o token novo', async () => {
    const fetchMock = simularServidor()

    await expect(api.get('/me')).resolves.toEqual({ ok: true })

    expect(renovar).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock.mock.calls[1][1]?.headers).toMatchObject({ Authorization: 'Bearer novo' })
    expect(obterTokenApi()).toBe('novo')
    expect(aoExpirar).not.toHaveBeenCalled()
  })

  it('chamadas simultâneas com 401 compartilham uma única renovação', async () => {
    simularServidor()

    await Promise.all([api.get('/me'), api.get('/me'), api.post('/sessoes', {})])

    expect(renovar).toHaveBeenCalledOnce()
  })

  it('se não der para renovar, encerra a sessão e repassa o 401', async () => {
    simularServidor()
    renovar.mockResolvedValueOnce(null)

    await expect(api.get('/me')).rejects.toMatchObject({ status: 401, codigo: 'nao_autenticado' })

    expect(aoExpirar).toHaveBeenCalledOnce()
  })

  it('tenta só uma vez: se o token novo também é recusado, encerra a sessão', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockImplementation(async () => respostaJson(401, { erro: 'nao_autenticado' }))

    await expect(api.get('/me')).rejects.toBeInstanceOf(ApiError)

    expect(renovar).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(aoExpirar).toHaveBeenCalledOnce()
  })

  it.each(['/auth/login', '/auth/cadastro', '/auth/renovar'])(
    'não tenta renovar em %s, onde 401 é senha errada ou token inválido',
    async (rota) => {
      simularServidor()

      await expect(api.post(rota, {})).rejects.toMatchObject({ status: 401 })

      expect(renovar).not.toHaveBeenCalled()
      expect(aoExpirar).not.toHaveBeenCalled()
    },
  )

  it('sem token salvo, um 401 não dispara renovação', async () => {
    definirTokenApi(null)
    simularServidor()

    await expect(api.get('/me')).rejects.toMatchObject({ status: 401 })

    expect(renovar).not.toHaveBeenCalled()
  })

  it.each(['/auth/login', '/auth/cadastro', '/auth/renovar'])(
    'não envia o token em %s (um token expirado derrubaria a requisição no backend)',
    async (rota) => {
      const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(respostaJson(200, {}))

      await api.post(rota, {})

      expect(fetchMock.mock.calls[0][1]?.headers).not.toHaveProperty('Authorization')
    },
  )

  it('o envio em segundo plano também renova e reenvia', async () => {
    const fetchMock = simularServidor()

    await expect(api.postEmSegundoPlano('/sessoes/1/interrupcoes', { inicio: 1 })).resolves.toBe(
      true,
    )

    expect(renovar).toHaveBeenCalledOnce()
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ keepalive: true })
  })
})
