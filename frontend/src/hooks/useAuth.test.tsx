import { act, render, renderHook, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { AuthProvider } from '../contexts/AuthContext'
import { CHAVE_USUARIO, limparSessao, salvarSessao, type UsuarioAutenticado } from '../services/auth'
import { useAuth } from './useAuth'

describe('useAuth e AuthProvider', () => {
  beforeEach(() => {
    limparSessao()
    localStorage.clear()
  })

  it('lança erro descritivo ao ser utilizado fora de um AuthProvider', () => {
    expect(() => renderHook(() => useAuth())).toThrow(
      'useAuth deve ser utilizado dentro de um AuthProvider',
    )
  })

  it('inicia sem usuário nem token quando não há sessão prévia no localStorage', () => {
    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider usarMock>{children}</AuthProvider>,
    })

    expect(result.current.usuario).toBeNull()
    expect(result.current.token).toBeNull()
    expect(result.current.autenticado).toBe(false)
  })

  it('mantém o usuário logado recuperando a sessão do localStorage ao recarregar a página', () => {
    const usuarioSalvo: UsuarioAutenticado = {
      id: 'usr-123',
      nome: 'Mariana Silva',
      email: 'mariana@synapse.com',
    }
    salvarSessao('token-jwt-salvo', 'refresh-token-salvo', usuarioSalvo)

    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider usarMock>{children}</AuthProvider>,
    })

    expect(result.current.autenticado).toBe(true)
    expect(result.current.token).toBe('token-jwt-salvo')
    expect(result.current.usuario).toEqual(usuarioSalvo)
  })

  it('realiza login, atualiza estado e persiste dados no localStorage', async () => {
    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider usarMock>{children}</AuthProvider>,
    })

    await act(async () => {
      await result.current.login({
        email: 'aluno@synapse.com',
        senha: 'senha-correta-123',
      })
    })

    expect(result.current.autenticado).toBe(true)
    expect(result.current.token).toBeTruthy()
    expect(result.current.usuario?.email).toBe('aluno@synapse.com')

    // Confirma persistência no localStorage
    expect(localStorage.getItem('synapse_token')).toBe(result.current.token)
    expect(localStorage.getItem(CHAVE_USUARIO)).toContain('aluno@synapse.com')
  })

  it('realiza cadastro, atualiza estado e persiste dados no localStorage', async () => {
    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider usarMock>{children}</AuthProvider>,
    })

    await act(async () => {
      await result.current.cadastro({
        nome: 'Lucas Mendes',
        email: 'lucas@synapse.com',
        senha: 'senha-segura-123',
      })
    })

    expect(result.current.autenticado).toBe(true)
    expect(result.current.token).toBeTruthy()
    expect(result.current.usuario?.nome).toBe('Lucas Mendes')
    expect(result.current.usuario?.email).toBe('lucas@synapse.com')

    expect(localStorage.getItem('synapse_token')).toBe(result.current.token)
  })

  it('realiza logout, limpando o estado e o localStorage', async () => {
    salvarSessao('token-ativo', 'refresh-ativo', {
      id: 'usr-1',
      nome: 'Teste',
      email: 'teste@synapse.com',
    })

    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider usarMock>{children}</AuthProvider>,
    })

    expect(result.current.autenticado).toBe(true)

    act(() => {
      result.current.logout()
    })

    expect(result.current.autenticado).toBe(false)
    expect(result.current.usuario).toBeNull()
    expect(result.current.token).toBeNull()
    expect(localStorage.getItem('synapse_token')).toBeNull()
    expect(localStorage.getItem(CHAVE_USUARIO)).toBeNull()
  })

  it('disponibiliza dados de autenticação para componentes filhos', () => {
    function ComponenteConsumidor() {
      const { autenticado, usuario } = useAuth()
      return (
        <div>
          <span>{autenticado ? 'Logado' : 'Deslogado'}</span>
          {usuario && <span>{usuario.nome}</span>}
        </div>
      )
    }

    render(
      <AuthProvider usarMock>
        <ComponenteConsumidor />
      </AuthProvider>,
    )

    expect(screen.getByText('Deslogado')).toBeInTheDocument()
  })
})
