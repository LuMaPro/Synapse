import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
import { describe, expect, it } from 'vitest'
import { Login } from './Login'

function renderizarLogin() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/foco" element={<div>Tela de Foco Redirecionada</div>} />
        <Route path="/cadastro" element={<div>Tela de Cadastro Redirecionada</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Página de Login', () => {
  it('renderiza os elementos principais da página', () => {
    renderizarLogin()

    expect(screen.getByRole('heading', { name: 'Entrar' })).toBeInTheDocument()
    expect(screen.getByText('synapse')).toBeInTheDocument()
    expect(screen.getByLabelText(/e-mail/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^senha/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Entrar' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Cadastre-se' })).toHaveAttribute('href', '/cadastro')
  })

  it('exibe erros de validação para campos vazios', async () => {
    const usuario = userEvent.setup()
    renderizarLogin()

    await usuario.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(screen.getByText('O e-mail é obrigatório.')).toBeInTheDocument()
    expect(screen.getByText('A senha é obrigatória.')).toBeInTheDocument()
  })

  it('exibe erro para formato de e-mail inválido', async () => {
    const usuario = userEvent.setup()
    renderizarLogin()

    await usuario.type(screen.getByLabelText(/e-mail/i), 'emailinvalido')
    await usuario.type(screen.getByLabelText(/^senha/i), '123456')
    await usuario.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(screen.getByText('Digite um e-mail válido.')).toBeInTheDocument()
  })

  it('exibe erro para senha com menos de 6 caracteres', async () => {
    const usuario = userEvent.setup()
    renderizarLogin()

    await usuario.type(screen.getByLabelText(/e-mail/i), 'usuario@synapse.com')
    await usuario.type(screen.getByLabelText(/^senha/i), '123')
    await usuario.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(screen.getByText('A senha deve ter no mínimo 6 caracteres.')).toBeInTheDocument()
  })

  it('permite alternar a visibilidade da senha', async () => {
    const usuario = userEvent.setup()
    renderizarLogin()

    const campoSenha = screen.getByLabelText(/^senha/i)
    expect(campoSenha).toHaveAttribute('type', 'password')

    const botaoAlternar = screen.getByRole('button', { name: 'Mostrar senha' })
    await usuario.click(botaoAlternar)

    expect(campoSenha).toHaveAttribute('type', 'text')
    expect(screen.getByRole('button', { name: 'Ocultar senha' })).toBeInTheDocument()
  })

  it('exibe alerta de erro da API para credenciais inválidas', async () => {
    const usuario = userEvent.setup()
    renderizarLogin()

    await usuario.type(screen.getByLabelText(/e-mail/i), 'erro@email.com')
    await usuario.type(screen.getByLabelText(/^senha/i), 'senha123')
    await usuario.click(screen.getByRole('button', { name: 'Entrar' }))

    // Durante o envio, exibe estado de loading
    expect(screen.getByRole('button', { name: /carregando/i })).toBeDisabled()

    // Aguarda retorno com erro da API mock
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(
        'Credenciais inválidas. Verifique seu e-mail e senha.',
      )
    })
  })

  it('realiza login com sucesso e navega para /foco', async () => {
    const usuario = userEvent.setup()
    renderizarLogin()

    await usuario.type(screen.getByLabelText(/e-mail/i), 'aluno@faculdade.edu.br')
    await usuario.type(screen.getByLabelText(/^senha/i), 'minhasenha123')
    await usuario.click(screen.getByRole('button', { name: 'Entrar' }))

    await waitFor(() => {
      expect(screen.getByText('Tela de Foco Redirecionada')).toBeInTheDocument()
    })
  })
})
