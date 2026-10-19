import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import { AuthContext, type AuthContextTipo } from '../contexts/authContextDef'
import { ApiError } from '../services/api'
import { Login } from './Login'

function renderizarLogin(authContext?: Partial<AuthContextTipo>) {
  const contextoPadrao: AuthContextTipo = {
    usuario: null,
    token: null,
    autenticado: false,
    estaCarregando: false,
    login: vi.fn(),
    cadastro: vi.fn(),
    logout: vi.fn(),
    ...authContext,
  }

  const elemento = (
    <MemoryRouter initialEntries={['/login']}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/foco" element={<div>Tela de Foco Redirecionada</div>} />
        <Route path="/cadastro" element={<div>Tela de Cadastro Redirecionada</div>} />
      </Routes>
    </MemoryRouter>
  )

  if (authContext) {
    return render(<AuthContext.Provider value={contextoPadrao}>{elemento}</AuthContext.Provider>)
  }

  return render(elemento)
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

  it('não aplica regra de tamanho no login: quem confere a senha é o servidor', async () => {
    const usuario = userEvent.setup()
    const login = vi.fn()
    renderizarLogin({ login })

    await usuario.type(screen.getByLabelText(/e-mail/i), 'usuario@synapse.com')
    await usuario.type(screen.getByLabelText(/^senha/i), '123')
    await usuario.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(login).toHaveBeenCalledWith(
      expect.objectContaining({ email: 'usuario@synapse.com', senha: '123' }),
    )
    expect(screen.queryByText(/no mínimo/)).not.toBeInTheDocument()
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

  it('exibe erro de validação quando o e-mail contém apenas espaços em branco', async () => {
    const usuario = userEvent.setup()
    renderizarLogin()

    await usuario.type(screen.getByLabelText(/e-mail/i), '     ')
    await usuario.type(screen.getByLabelText(/^senha/i), '123456')
    await usuario.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(screen.getByText('O e-mail é obrigatório.')).toBeInTheDocument()
  })

  it('limpa o erro inline do campo quando o usuário digita um novo valor', async () => {
    const usuario = userEvent.setup()
    renderizarLogin()

    await usuario.click(screen.getByRole('button', { name: 'Entrar' }))
    expect(screen.getByText('O e-mail é obrigatório.')).toBeInTheDocument()

    await usuario.type(screen.getByLabelText(/e-mail/i), 'a')
    expect(screen.queryByText('O e-mail é obrigatório.')).not.toBeInTheDocument()
  })

  it('exibe alerta de erro quando a API responde com ApiError', async () => {
    const loginMock = vi
      .fn()
      .mockRejectedValueOnce(
        new ApiError(401, 'credenciais_invalidas', 'E-mail ou senha incorretos na API.'),
      )
    const usuario = userEvent.setup()
    renderizarLogin({ login: loginMock })

    await usuario.type(screen.getByLabelText(/e-mail/i), 'usuario@synapse.com')
    await usuario.type(screen.getByLabelText(/^senha/i), 'senha123')
    await usuario.click(screen.getByRole('button', { name: 'Entrar' }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('E-mail ou senha incorretos na API.')
    })
  })

  it('exibe alerta com mensagem genérica quando ocorre erro inesperado de rede', async () => {
    const loginMock = vi.fn().mockRejectedValueOnce(new Error('Falha de conexão com o servidor'))
    const usuario = userEvent.setup()
    renderizarLogin({ login: loginMock })

    await usuario.type(screen.getByLabelText(/e-mail/i), 'usuario@synapse.com')
    await usuario.type(screen.getByLabelText(/^senha/i), 'senha123')
    await usuario.click(screen.getByRole('button', { name: 'Entrar' }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Falha de conexão com o servidor')
    })
  })

  it('exibe mensagem padrão quando o erro não é uma instância de Error', async () => {
    const loginMock = vi.fn().mockRejectedValueOnce('erro desconhecido string')
    const usuario = userEvent.setup()
    renderizarLogin({ login: loginMock })

    await usuario.type(screen.getByLabelText(/e-mail/i), 'usuario@synapse.com')
    await usuario.type(screen.getByLabelText(/^senha/i), 'senha123')
    await usuario.click(screen.getByRole('button', { name: 'Entrar' }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(
        'Ocorreu um erro ao tentar entrar. Tente novamente.',
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
