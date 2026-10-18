import { useContext } from 'react'
import { AuthContext, type AuthContextTipo } from '../contexts/authContextDef'

export function useAuth(): AuthContextTipo {
  const contexto = useContext(AuthContext)
  if (!contexto) {
    throw new Error('useAuth deve ser utilizado dentro de um AuthProvider')
  }
  return contexto
}
