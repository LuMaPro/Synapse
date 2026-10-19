import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '../hooks/useAuth'
import { api, obterTokenApi } from '../services/api'
import { CHAVE_REFRESH_TOKEN, limparSessao, salvarSessao } from '../services/auth'
import { AuthProvider } from './AuthContext'

const USUARIO = { id: 'usr-1', nome: 'Ana', email: 'ana@synapse.com' }

function respostaJson(status: number, corpo: unknown) {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

/**
 * Servidor falso: só aceita o token "novo". Como o backend (DRF), recusa qualquer
 * requisição que chegue com um token inválido no cabeçalho, mesmo em rota pública.
 */
function simularServidor(renovacaoAceita: boolean) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, opcoes) => {
    const autorizacao = (opcoes?.headers as Record<string, string> | undefined)?.Authorization
    if (String(url).endsWith('/auth/renovar')) {
      if (autorizacao && autorizacao !== 'Bearer novo') {
        return respostaJson(401, { erro: 'nao_autenticado', mensagem: 'Token inválido.' })
      }
      return renovacaoAceita
        ? respostaJson(200, { access: 'novo' })
        : respostaJson(401, { erro: 'nao_autenticado', mensagem: 'Token inválido.' })
    }
    return autorizacao === 'Bearer novo'
      ? respostaJson(200, USUARIO)
      : respostaJson(401, { erro: 'nao_autenticado', mensagem: 'Credenciais ausentes.' })
  })
}

function renderizarAuth() {
  return renderHook(() => useAuth(), {
    wrapper: ({ children }: { children: ReactNode }) => <AuthProvider>{children}</AuthProvider>,
  })
}

describe('AuthProvider: renovação do token de acesso', () => {
  beforeEach(() => {
    // Sessão salva com um token de acesso que já expirou.
    salvarSessao('velho', 'refresh-valido', USUARIO)
  })

  afterEach(() => {
    limparSessao()
    vi.restoreAllMocks()
  })

  it('renova o token expirado sem o usuário perceber', async () => {
    const fetchMock = simularServidor(true)
    const { result } = renderizarAuth()

    let resposta: unknown
    await act(async () => {
      resposta = await api.get('/me')
    })

    expect(resposta).toEqual(USUARIO)
    expect(result.current.autenticado).toBe(true)
    expect(result.current.token).toBe('novo')
    expect(obterTokenApi()).toBe('novo')
    const renovacao = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/auth/renovar'))
    expect(JSON.parse(String(renovacao?.[1]?.body))).toEqual({ refresh: 'refresh-valido' })
  })

  it('se a renovação é recusada, encerra a sessão', async () => {
    simularServidor(false)
    const { result } = renderizarAuth()
    expect(result.current.autenticado).toBe(true)

    await act(async () => {
      await expect(api.get('/me')).rejects.toMatchObject({ status: 401 })
    })

    await waitFor(() => expect(result.current.autenticado).toBe(false))
    expect(result.current.usuario).toBeNull()
    expect(obterTokenApi()).toBeNull()
    expect(localStorage.getItem(CHAVE_REFRESH_TOKEN)).toBeNull()
  })
})
