import { NavLink, Outlet } from 'react-router'

const LINKS = [
  { para: '/foco', rotulo: 'Foco' },
  { para: '/rede', rotulo: 'Rede' },
  { para: '/estatisticas', rotulo: 'Estatísticas' },
  { para: '/login', rotulo: 'Entrar' },
  { para: '/cadastro', rotulo: 'Cadastro' },
]

export function Layout() {
  return (
    <div className="layout">
      <header className="cabecalho">
        <span className="marca">Synapse</span>
        <nav aria-label="Navegação principal">
          {LINKS.map(({ para, rotulo }) => (
            <NavLink key={para} to={para}>
              {rotulo}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="conteudo">
        <Outlet />
      </main>
    </div>
  )
}
