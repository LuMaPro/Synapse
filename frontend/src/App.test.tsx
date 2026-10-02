import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { AppRoutes } from './App'

function renderizarEm(rota: string) {
  return render(
    <MemoryRouter initialEntries={[rota]}>
      <AppRoutes />
    </MemoryRouter>,
  )
}

describe('rotas', () => {
  it('redireciona a raiz para a tela de foco', () => {
    renderizarEm('/')
    expect(screen.getByRole('heading', { name: 'Foco' })).toBeInTheDocument()
  })

  it('navega entre as telas pelo menu', async () => {
    const usuario = userEvent.setup()
    renderizarEm('/foco')

    await usuario.click(screen.getByRole('link', { name: 'Rede' }))
    expect(screen.getByRole('heading', { name: 'Rede neural' })).toBeInTheDocument()

    await usuario.click(screen.getByRole('link', { name: 'Cadastro' }))
    expect(screen.getByRole('heading', { name: 'Criar conta' })).toBeInTheDocument()
  })

  it.each([
    ['/login', 'Entrar'],
    ['/cadastro', 'Criar conta'],
    ['/foco', 'Foco'],
    ['/rede', 'Rede neural'],
    ['/estatisticas', 'Estatísticas'],
  ])('abre %s', (rota, titulo) => {
    renderizarEm(rota)
    expect(screen.getByRole('heading', { name: titulo })).toBeInTheDocument()
  })

  it('mostra uma página de erro para endereço inexistente', () => {
    renderizarEm('/nao-existe')
    expect(screen.getByRole('heading', { name: 'Página não encontrada' })).toBeInTheDocument()
  })
})
