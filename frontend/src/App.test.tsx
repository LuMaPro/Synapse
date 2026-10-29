import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AppRoutes } from './App'
import { limparSessao, salvarSessao } from './services/auth'

function renderizarEm(rota: string) {
  return render(
    <MemoryRouter initialEntries={[rota]}>
      <AppRoutes />
    </MemoryRouter>,
  )
}

describe('rotas e proteção de acesso', () => {
  beforeEach(() => {
    limparSessao()
    localStorage.clear()
  })

  describe('usuário não autenticado', () => {
    it('redireciona a raiz para /login', () => {
      renderizarEm('/')
      expect(screen.getByRole('heading', { name: 'Entrar' })).toBeInTheDocument()
    })

    it.each(['/foco', '/rede', '/historico', '/estatisticas', '/materias', '/loja'])(
      'redireciona rota protegida %s para /login',
      (rota) => {
        renderizarEm(rota)
        expect(screen.getByRole('heading', { name: 'Entrar' })).toBeInTheDocument()
      },
    )

    it('permite acessar páginas públicas normalmente', () => {
      renderizarEm('/login')
      expect(screen.getByRole('heading', { name: 'Entrar' })).toBeInTheDocument()

      renderizarEm('/cadastro')
      expect(screen.getByRole('heading', { name: 'Criar conta' })).toBeInTheDocument()
    })

    it('mostra uma página de erro para endereço inexistente', () => {
      renderizarEm('/nao-existe')
      expect(screen.getByRole('heading', { name: 'Página não encontrada' })).toBeInTheDocument()
    })
  })

  describe('usuário autenticado', () => {
    beforeEach(() => {
      salvarSessao('token-teste', 'refresh-teste', {
        id: 'usr-1',
        nome: 'Mariana Souza',
        email: 'mariana@synapse.com',
      })
      // As telas buscam dados ao abrir; sem isso, iriam a um backend de verdade, e um
      // 401 dele (o token é de teste) encerraria a sessão no meio do teste.
      vi.stubGlobal(
        'fetch',
        vi.fn(async (endereco: string | URL | Request) => {
          const { pathname } = new URL(String(endereco))
          const corpo = {
            '/rede': { neuronios: [], sinapses: [] },
            '/materias': [],
            '/sessoes': { total: 0, pagina: 1, tamanho: 20, paginas: 1, resultados: [] },
            '/loja': { saldo: 0, cores: [] },
          }[pathname]
          return corpo === undefined
            ? new Response(null, { status: 204 })
            : new Response(JSON.stringify(corpo), {
                headers: { 'Content-Type': 'application/json' },
              })
        }),
      )
    })

    afterEach(() => {
      vi.unstubAllGlobals()
    })

    it('redireciona a raiz para a tela de foco', () => {
      renderizarEm('/')
      expect(screen.getByRole('heading', { name: 'Focar' })).toBeInTheDocument()
    })

    it.each([
      ['/foco', 'Focar'],
      ['/rede', 'Sua rede'],
      ['/historico', 'Histórico'],
      ['/estatisticas', 'Estatísticas'],
      ['/materias', 'Matérias'],
      ['/loja', 'Loja'],
    ])('abre rota protegida %s diretamente', (rota, titulo) => {
      renderizarEm(rota)
      expect(screen.getByRole('heading', { name: titulo })).toBeInTheDocument()
    })

    it('exibe o nome do usuário e o botão Sair no cabeçalho', () => {
      renderizarEm('/foco')
      expect(screen.getByText('Mariana Souza')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /sair/i })).toBeInTheDocument()
    })

    it('permite deslogar através do botão Sair e redireciona para /login', async () => {
      const usuario = userEvent.setup()
      renderizarEm('/foco')

      const botaoSair = screen.getByRole('button', { name: /sair/i })
      await usuario.click(botaoSair)

      expect(screen.getByRole('heading', { name: 'Entrar' })).toBeInTheDocument()
      expect(localStorage.getItem('synapse_token')).toBeNull()
    })

    it('navega entre as telas protegidas pelo menu', async () => {
      const usuario = userEvent.setup()
      renderizarEm('/foco')

      await usuario.click(screen.getByRole('link', { name: 'Rede' }))
      expect(screen.getByRole('heading', { name: 'Sua rede' })).toBeInTheDocument()

      await usuario.click(screen.getByRole('link', { name: 'Histórico' }))
      expect(screen.getByRole('heading', { name: 'Histórico' })).toBeInTheDocument()

      await usuario.click(screen.getByRole('link', { name: 'Matérias' }))
      expect(screen.getByRole('heading', { name: 'Matérias' })).toBeInTheDocument()

      await usuario.click(screen.getByRole('link', { name: 'Loja' }))
      expect(screen.getByRole('heading', { name: 'Loja' })).toBeInTheDocument()

      await usuario.click(screen.getByRole('link', { name: 'Estatísticas' }))
      expect(screen.getByRole('heading', { name: 'Estatísticas' })).toBeInTheDocument()
    })

    describe('no celular (issue #35)', () => {
      beforeEach(() => {
        // Tela estreita: a media query do celular vale.
        vi.stubGlobal(
          'matchMedia',
          vi.fn((consulta: string) => ({
            matches: consulta === '(max-width: 640px)',
            addEventListener: vi.fn(),
            removeEventListener: vi.fn(),
          })),
        )
      })

      it('navega pela barra de abas embaixo, como no design', async () => {
        const usuario = userEvent.setup()
        renderizarEm('/foco')

        const abas = screen.getByRole('navigation', { name: 'Navegação principal' })
        expect(abas).toHaveClass('abas')
        expect([...abas.querySelectorAll('a, button')].map((item) => item.textContent)).toEqual([
          'Foco',
          'Rede',
          'Histórico',
          'Estatísticas',
          'Mais',
        ])
        expect(screen.getByRole('link', { name: 'Foco' })).toHaveClass('active')
        // O cabeçalho fica só com a marca e a inicial do estudante.
        expect(screen.queryByRole('button', { name: /sair/i })).not.toBeInTheDocument()

        await usuario.click(screen.getByRole('link', { name: 'Histórico' }))
        expect(screen.getByRole('heading', { name: 'Histórico' })).toBeInTheDocument()
      })

      it('"Mais" abre Matérias, Loja e Sair', async () => {
        const usuario = userEvent.setup()
        renderizarEm('/foco')
        const mais = screen.getByRole('button', { name: 'Mais' })

        await usuario.click(mais)
        expect(mais).toHaveAttribute('aria-expanded', 'true')
        const menu = screen.getByRole('menu', { name: 'Mais' })
        expect(
          [...menu.querySelectorAll('[role="menuitem"]')].map((item) => item.textContent),
        ).toEqual(['Matérias', 'Loja', 'Sair'])

        await usuario.click(screen.getByRole('menuitem', { name: 'Loja' }))
        expect(screen.getByRole('heading', { name: 'Loja' })).toBeInTheDocument()
        expect(screen.queryByRole('menu')).not.toBeInTheDocument()
        // Estando numa tela de "Mais", a aba Mais fica acesa.
        expect(mais).toHaveClass('active')

        await usuario.click(mais)
        await usuario.keyboard('{Escape}')
        expect(screen.queryByRole('menu')).not.toBeInTheDocument()

        await usuario.click(mais)
        await usuario.click(screen.getByRole('menuitem', { name: 'Sair' }))
        expect(screen.getByRole('heading', { name: 'Entrar' })).toBeInTheDocument()
        expect(screen.queryByRole('navigation', { name: 'Navegação principal' })).not.toHaveClass(
          'abas',
        )
      })
    })
  })
})
