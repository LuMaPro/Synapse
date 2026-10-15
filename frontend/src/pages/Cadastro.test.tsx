import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
import { describe, expect, it } from 'vitest'
import { Cadastro } from './Cadastro'

function renderizarCadastro() {
  return render(
    <MemoryRouter initialEntries={['/cadastro']}>
      <Routes>
        <Route path="/cadastro" element={<Cadastro />} />
        <Route path="/foco" element={<div>Tela de Foco Redirecionada</div>} />
        <Route path="/login" element={<div>Tela de Login Redirecionada</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Página de Cadastro', () => {
  it('renderiza os elementos principais da página', () => {
    renderizarCadastro()

    expect(screen.getByRole('heading', { name: 'Criar conta' })).toBeInTheDocument()
    expect(screen.getByText('synapse')).toBeInTheDocument()
    expect(screen.getByLabelText(/nome/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/e-mail/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^senha/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Criar conta' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Faça login' })).toHaveAttribute('href', '/login')
  })

  it('exibe erros de validação para campos vazios', async () => {
    const usuario = userEvent.setup()
    renderizarCadastro()

    await usuario.click(screen.getByRole('button', { name: 'Criar conta' }))

    expect(screen.getByText('O nome é obrigatório.')).toBeInTheDocument()
    expect(screen.getByText('O e-mail é obrigatório.')).toBeInTheDocument()
    expect(screen.getByText('A senha é obrigatória.')).toBeInTheDocument()
  })

  it('exibe erro para formato de e-mail inválido', async () => {
    const usuario = userEvent.setup()
    renderizarCadastro()

    await usuario.type(screen.getByLabelText(/nome/i), 'Ana Souza')
    await usuario.type(screen.getByLabelText(/e-mail/i), 'emailinvalido@')
    await usuario.type(screen.getByLabelText(/^senha/i), '123456')
    await usuario.click(screen.getByRole('button', { name: 'Criar conta' }))

    expect(screen.getByText('Digite um e-mail válido.')).toBeInTheDocument()
  })

  it('exibe erro para senha com menos de 6 caracteres', async () => {
    const usuario = userEvent.setup()
    renderizarCadastro()

    await usuario.type(screen.getByLabelText(/nome/i), 'Ana Souza')
    await usuario.type(screen.getByLabelText(/e-mail/i), 'ana@email.com')
    await usuario.type(screen.getByLabelText(/^senha/i), '12345')
    await usuario.click(screen.getByRole('button', { name: 'Criar conta' }))

    expect(screen.getByText('A senha deve ter no mínimo 6 caracteres.')).toBeInTheDocument()
  })

  it('exibe alerta de erro da API quando o e-mail já existe', async () => {
    const usuario = userEvent.setup()
    renderizarCadastro()

    await usuario.type(screen.getByLabelText(/nome/i), 'Carlos Silva')
    await usuario.type(screen.getByLabelText(/e-mail/i), 'existe@email.com')
    await usuario.type(screen.getByLabelText(/^senha/i), 'senha123')
    await usuario.click(screen.getByRole('button', { name: 'Criar conta' }))

    expect(screen.getByRole('button', { name: /carregando/i })).toBeDisabled()

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(
        'E-mail já cadastrado. Tente fazer login ou use outro e-mail.',
      )
    })
  })

  it('realiza cadastro com sucesso e navega para /foco', async () => {
    const usuario = userEvent.setup()
    renderizarCadastro()

    await usuario.type(screen.getByLabelText(/nome/i), 'Mariana Rios')
    await usuario.type(screen.getByLabelText(/e-mail/i), 'mariana@synapse.com')
    await usuario.type(screen.getByLabelText(/^senha/i), 'segredo123')
    await usuario.click(screen.getByRole('button', { name: 'Criar conta' }))

    await waitFor(() => {
      expect(screen.getByText('Tela de Foco Redirecionada')).toBeInTheDocument()
    })
  })
})
