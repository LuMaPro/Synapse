import { NavLink, Outlet, useNavigate } from 'react-router'
import { useAuth } from '../hooks/useAuth'

const LINKS_AUTENTICADOS = [
  { para: '/foco', rotulo: 'Foco' },
  { para: '/rede', rotulo: 'Rede' },
  { para: '/materias', rotulo: 'Matérias' },
  { para: '/estatisticas', rotulo: 'Estatísticas' },
]

const LINKS_PUBLICOS = [
  { para: '/login', rotulo: 'Entrar' },
  { para: '/cadastro', rotulo: 'Cadastro' },
]

export function Layout() {
  const { autenticado, usuario, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  const links = autenticado ? LINKS_AUTENTICADOS : LINKS_PUBLICOS

  return (
    <div className="layout">
      <header className="cabecalho">
        <span className="marca">Synapse</span>
        <nav aria-label="Navegação principal">
          {links.map(({ para, rotulo }) => (
            <NavLink key={para} to={para}>
              {rotulo}
            </NavLink>
          ))}
          {autenticado && (
            <div className="sessao-usuario">
              {usuario?.nome && (
                <div className="badge-usuario" title={usuario.email}>
                  <span className="avatar-usuario" aria-hidden="true">
                    {usuario.nome.trim().charAt(0).toUpperCase()}
                  </span>
                  <span className="nome-usuario">{usuario.nome}</span>
                </div>
              )}
              <button
                type="button"
                onClick={handleLogout}
                className="botao-sair"
                aria-label="Sair da conta"
              >
                Sair
              </button>
            </div>
          )}
        </nav>
      </header>
      <main className="conteudo">
        <Outlet />
      </main>
    </div>
  )
}
