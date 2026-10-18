import { Navigate, Outlet, useLocation } from 'react-router'
import { useAuth } from '../hooks/useAuth'

export function RotaProtegida() {
  const { autenticado, estaCarregando } = useAuth()
  const location = useLocation()

  if (estaCarregando) {
    return null
  }

  if (!autenticado) {
    return <Navigate to="/login" replace state={{ de: location.pathname }} />
  }

  return <Outlet />
}
