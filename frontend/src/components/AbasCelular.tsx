import { useEffect, useState, type ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router'

/** Ícones das abas, os mesmos do protótipo (docs/design). */
function Icone({ children }: { children: ReactNode }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <g fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        {children}
      </g>
    </svg>
  )
}

const ABAS = [
  {
    para: '/foco',
    rotulo: 'Foco',
    icone: (
      <Icone>
        <circle cx="12" cy="13" r="8" />
        <path d="M12 9v4l2.5 2.5M9 2h6" />
      </Icone>
    ),
  },
  {
    para: '/rede',
    rotulo: 'Rede',
    icone: (
      <Icone>
        <circle cx="6" cy="7" r="2.5" />
        <circle cx="18" cy="6" r="2.5" />
        <circle cx="12" cy="18" r="2.5" />
        <path d="M8.3 8.2 10.8 15.7M15.9 7.7 13.2 15.8M8.5 6.8 15.5 6.2" />
      </Icone>
    ),
  },
  {
    para: '/historico',
    rotulo: 'Histórico',
    icone: (
      <Icone>
        <rect x="3.5" y="5" width="17" height="15" rx="2.5" />
        <path d="M3.5 10h17M8 3v4M16 3v4" />
      </Icone>
    ),
  },
  {
    para: '/estatisticas',
    rotulo: 'Estatísticas',
    icone: (
      <Icone>
        <path d="M5 20V12M12 20V5M19 20v-9" />
      </Icone>
    ),
  },
]

/** O que fica em "Mais", como no design: as telas usadas com menos frequência. */
const MAIS = [
  { para: '/materias', rotulo: 'Matérias' },
  { para: '/loja', rotulo: 'Loja' },
]

interface AbasCelularProps {
  onSair: () => void
}

/**
 * Navegação do celular (issue #35): a barra de abas embaixo do protótipo (docs/design),
 * ao alcance do polegar. Foco, Rede, Histórico e Estatísticas ficam sempre à mostra;
 * Matérias, Loja e Sair ficam em "Mais".
 */
export function AbasCelular({ onSair }: AbasCelularProps) {
  const [aberto, setAberto] = useState(false)
  const { pathname } = useLocation()
  const emMais = MAIS.some((link) => pathname.startsWith(link.para))

  useEffect(() => {
    if (!aberto) return
    const aoTeclar = (evento: KeyboardEvent) => {
      if (evento.key === 'Escape') setAberto(false)
    }
    document.addEventListener('keydown', aoTeclar)
    return () => document.removeEventListener('keydown', aoTeclar)
  }, [aberto])

  const fechar = () => setAberto(false)

  return (
    <>
      {aberto && (
        <>
          {/* Tocar fora fecha o menu. */}
          <div className="mais-fundo" onClick={fechar} aria-hidden="true" />
          <div className="mais-menu" id="menu-mais" role="menu" aria-label="Mais">
            {MAIS.map(({ para, rotulo }) => (
              <NavLink key={para} to={para} role="menuitem" onClick={fechar}>
                {rotulo}
              </NavLink>
            ))}
            <button
              type="button"
              role="menuitem"
              className="texto-perigo"
              onClick={() => {
                fechar()
                onSair()
              }}
            >
              Sair
            </button>
          </div>
        </>
      )}
      <nav className="abas" aria-label="Navegação principal">
        {ABAS.map(({ para, rotulo, icone }) => (
          <NavLink key={para} to={para} className="aba" onClick={fechar}>
            {icone}
            {rotulo}
          </NavLink>
        ))}
        <button
          type="button"
          className={emMais || aberto ? 'aba active' : 'aba'}
          aria-haspopup="menu"
          aria-expanded={aberto}
          aria-controls="menu-mais"
          onClick={() => setAberto((a) => !a)}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <g fill="currentColor">
              <circle cx="5" cy="12" r="1.8" />
              <circle cx="12" cy="12" r="1.8" />
              <circle cx="19" cy="12" r="1.8" />
            </g>
          </svg>
          Mais
        </button>
      </nav>
    </>
  )
}
