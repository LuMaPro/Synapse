import { Navigate, Route, Routes } from 'react-router'
import { Layout } from './components/Layout'
import { RotaProtegida } from './components/RotaProtegida'
import { AuthProvider } from './contexts/AuthContext'
import { Cadastro } from './pages/Cadastro'
import { Estatisticas } from './pages/Estatisticas'
import { Foco } from './pages/Foco'
import { Login } from './pages/Login'
import { Materias } from './pages/Materias'
import { NaoEncontrada } from './pages/NaoEncontrada'
import { Rede } from './pages/Rede'

export function AppRoutes() {
  return (
    <AuthProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route path="login" element={<Login />} />
          <Route path="cadastro" element={<Cadastro />} />

          <Route element={<RotaProtegida />}>
            <Route index element={<Navigate to="/foco" replace />} />
            <Route path="foco" element={<Foco />} />
            <Route path="rede" element={<Rede />} />
            <Route path="materias" element={<Materias />} />
            <Route path="estatisticas" element={<Estatisticas />} />
          </Route>

          <Route path="*" element={<NaoEncontrada />} />
        </Route>
      </Routes>
    </AuthProvider>
  )
}
