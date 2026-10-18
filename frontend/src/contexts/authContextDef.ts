import { createContext } from 'react'
import type { CredenciaisLogin, DadosCadastro, UsuarioAutenticado } from '../services/auth'

export interface AuthContextTipo {
  usuario: UsuarioAutenticado | null
  token: string | null
  autenticado: boolean
  estaCarregando: boolean
  login: (credenciais: CredenciaisLogin) => Promise<void>
  cadastro: (dados: DadosCadastro) => Promise<void>
  logout: () => void
}

export const AuthContext = createContext<AuthContextTipo | null>(null)
