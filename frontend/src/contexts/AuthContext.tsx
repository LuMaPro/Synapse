import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { configurarSessao } from '../services/api'
import {
  cadastroApi,
  cadastroMock,
  limparSessao,
  loginApi,
  loginMock,
  obterSessaoSalva,
  renovarTokenApi,
  type CredenciaisLogin,
  type DadosCadastro,
  type UsuarioAutenticado,
} from '../services/auth'
import { AuthContext, type AuthContextTipo } from './authContextDef'

export interface AuthProviderProps {
  children: ReactNode
  usarMock?: boolean
}

export function AuthProvider({ children, usarMock = false }: AuthProviderProps) {
  const [usuario, setUsuario] = useState<UsuarioAutenticado | null>(() => {
    return obterSessaoSalva().usuario
  })
  const [token, setToken] = useState<string | null>(() => {
    return obterSessaoSalva().token
  })
  const [estaCarregando, setEstaCarregando] = useState(false)

  const login = useCallback(
    async (credenciais: CredenciaisLogin) => {
      setEstaCarregando(true)
      try {
        const funcaoLogin = usarMock ? loginMock : loginApi
        const resposta = await funcaoLogin(credenciais)
        setToken(resposta.token)
        setUsuario(resposta.usuario)
      } finally {
        setEstaCarregando(false)
      }
    },
    [usarMock],
  )

  const cadastro = useCallback(
    async (dados: DadosCadastro) => {
      setEstaCarregando(true)
      try {
        const funcaoCadastro = usarMock ? cadastroMock : cadastroApi
        const resposta = await funcaoCadastro(dados)
        setToken(resposta.token)
        setUsuario(resposta.usuario)
      } finally {
        setEstaCarregando(false)
      }
    },
    [usarMock],
  )

  const logout = useCallback(() => {
    limparSessao()
    setUsuario(null)
    setToken(null)
  }, [])

  // Renovação automática do token de acesso (expira em 15 min): quando a API responde
  // 401, o api.ts renova e repete a chamada; se não der para renovar, a sessão acaba.
  useEffect(() => {
    configurarSessao({
      renovar: async () => {
        const novoToken = await renovarTokenApi()
        if (novoToken) setToken(novoToken)
        return novoToken
      },
      aoExpirar: logout,
    })
    return () => configurarSessao(null)
  }, [logout])

  const valor: AuthContextTipo = {
    usuario,
    token,
    autenticado: Boolean(token && usuario),
    estaCarregando,
    login,
    cadastro,
    logout,
  }

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>
}
