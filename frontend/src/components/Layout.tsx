import { NavLink, Outlet, useNavigate } from 'react-router'
import { useAuth } from '../hooks/useAuth'
import { CONSULTA_CELULAR, useMidia } from '../hooks/useMidia'
import { AbasCelular } from './AbasCelular'

const LINKS_AUTENTICADOS = [
  { para: '/foco', rotulo: 'Foco' },
  { para: '/rede', rotulo: 'Rede' },
  { para: '/historico', rotulo: 'Histórico' },
  { para: '/materias', rotulo: 'Matérias' },
  { para: '/conquistas', rotulo: 'Conquistas' },
  { para: '/loja', rotulo: 'Loja' },
  { para: '/estatisticas', rotulo: 'Estatísticas' },
]

const LINKS_PUBLICOS = [
  { para: '/login', rotulo: 'Entrar' },
  { para: '/cadastro', rotulo: 'Cadastro' },
]

export function Layout() {
  const { autenticado, usuario, logout } = useAuth()
  const navigate = useNavigate()
  // No celular, a navegação vira a barra de abas embaixo, como no design (#35).
  const comAbas = useMidia(CONSULTA_CELULAR) && autenticado

  function handleLogout() {
    logout()
    navigate('/login')
  }

  const links = autenticado ? LINKS_AUTENTICADOS : LINKS_PUBLICOS
  const badge = usuario?.nome && (
    <div className="badge-usuario" title={usuario.email}>
      <span className="avatar-usuario" aria-hidden="true">
        {usuario.nome.trim().charAt(0).toUpperCase()}
      </span>
      <span className="nome-usuario">{usuario.nome}</span>
    </div>
  )

  return (
    <div className={comAbas ? 'layout com-abas' : 'layout'}>
      <header className="cabecalho">
        <span className="marca">Synapse</span>
        {comAbas ? (
          <div className="sessao-usuario">{badge}</div>
        ) : (
          <nav aria-label="Navegação principal">
            {links.map(({ para, rotulo }) => (
              <NavLink key={para} to={para}>
                {rotulo}
              </NavLink>
            ))}
            {autenticado && (
              <div className="sessao-usuario">
                {badge}
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
        )}
      </header>
      <main className="conteudo">
        <Outlet />
      </main>
      {comAbas && <AbasCelular onSair={handleLogout} />}
    </div>
  )
}
