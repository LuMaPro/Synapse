import { Navigate, Route, Routes } from 'react-router'
import { Layout } from './components/Layout'
import { Cadastro } from './pages/Cadastro'
import { Estatisticas } from './pages/Estatisticas'
import { Foco } from './pages/Foco'
import { Login } from './pages/Login'
import { NaoEncontrada } from './pages/NaoEncontrada'
import { Rede } from './pages/Rede'

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/foco" replace />} />
        <Route path="login" element={<Login />} />
        <Route path="cadastro" element={<Cadastro />} />
        <Route path="foco" element={<Foco />} />
        <Route path="rede" element={<Rede />} />
        <Route path="estatisticas" element={<Estatisticas />} />
        <Route path="*" element={<NaoEncontrada />} />
      </Route>
    </Routes>
  )
}
