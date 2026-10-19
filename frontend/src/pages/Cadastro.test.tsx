import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import { AuthContext, type AuthContextTipo } from '../contexts/authContextDef'
import { ApiError } from '../services/api'
import { Cadastro } from './Cadastro'

function renderizarCadastro(authContext?: Partial<AuthContextTipo>) {
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
    <MemoryRouter initialEntries={['/cadastro']}>
      <Routes>
        <Route path="/cadastro" element={<Cadastro />} />
        <Route path="/foco" element={<div>Tela de Foco Redirecionada</div>} />
        <Route path="/login" element={<div>Tela de Login Redirecionada</div>} />
      </Routes>
    </MemoryRouter>
  )

  if (authContext) {
    return render(<AuthContext.Provider value={contextoPadrao}>{elemento}</AuthContext.Provider>)
  }

  return render(elemento)
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

  it('exibe erro para senha com menos de 8 caracteres, como exige o backend', async () => {
    const usuario = userEvent.setup()
    const cadastro = vi.fn()
    renderizarCadastro({ cadastro })

    await usuario.type(screen.getByLabelText(/nome/i), 'Ana Souza')
    await usuario.type(screen.getByLabelText(/e-mail/i), 'ana@email.com')
    await usuario.type(screen.getByLabelText(/^senha/i), 'abc1234')
    await usuario.click(screen.getByRole('button', { name: 'Criar conta' }))

    expect(screen.getByText('A senha deve ter no mínimo 8 caracteres.')).toBeInTheDocument()
    expect(cadastro).not.toHaveBeenCalled()
  })

  it('exibe erro para senha só com números', async () => {
    const usuario = userEvent.setup()
    const cadastro = vi.fn()
    renderizarCadastro({ cadastro })

    await usuario.type(screen.getByLabelText(/nome/i), 'Ana Souza')
    await usuario.type(screen.getByLabelText(/e-mail/i), 'ana@email.com')
    await usuario.type(screen.getByLabelText(/^senha/i), '12345678')
    await usuario.click(screen.getByRole('button', { name: 'Criar conta' }))

    expect(screen.getByText('A senha não pode ter só números.')).toBeInTheDocument()
    expect(cadastro).not.toHaveBeenCalled()
  })

  it('anuncia o tamanho mínimo da senha no campo', () => {
    renderizarCadastro()

    expect(screen.getByLabelText(/^senha/i)).toHaveAttribute(
      'placeholder',
      'Mínimo de 8 caracteres',
    )
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

  it('exibe erro de validação quando o nome contém apenas espaços em branco', async () => {
    const usuario = userEvent.setup()
    renderizarCadastro()

    await usuario.type(screen.getByLabelText(/nome/i), '    ')
    await usuario.type(screen.getByLabelText(/e-mail/i), 'ana@email.com')
    await usuario.type(screen.getByLabelText(/^senha/i), '123456')
    await usuario.click(screen.getByRole('button', { name: 'Criar conta' }))

    expect(screen.getByText('O nome é obrigatório.')).toBeInTheDocument()
  })

  it('exibe erro de validação quando o e-mail contém apenas espaços em branco', async () => {
    const usuario = userEvent.setup()
    renderizarCadastro()

    await usuario.type(screen.getByLabelText(/nome/i), 'Ana Souza')
    await usuario.type(screen.getByLabelText(/e-mail/i), '    ')
    await usuario.type(screen.getByLabelText(/^senha/i), '123456')
    await usuario.click(screen.getByRole('button', { name: 'Criar conta' }))

    expect(screen.getByText('O e-mail é obrigatório.')).toBeInTheDocument()
  })

  it('limpa o erro inline do campo quando o usuário digita um novo valor', async () => {
    const usuario = userEvent.setup()
    renderizarCadastro()

    await usuario.click(screen.getByRole('button', { name: 'Criar conta' }))
    expect(screen.getByText('O nome é obrigatório.')).toBeInTheDocument()

    await usuario.type(screen.getByLabelText(/nome/i), 'B')
    expect(screen.queryByText('O nome é obrigatório.')).not.toBeInTheDocument()
  })

  it('exibe alerta de erro quando a API responde com ApiError', async () => {
    const cadastroMockFn = vi
      .fn()
      .mockRejectedValueOnce(
        new ApiError(400, 'dados_invalidos', 'Dados cadastrais inválidos na API.'),
      )
    const usuario = userEvent.setup()
    renderizarCadastro({ cadastro: cadastroMockFn })

    await usuario.type(screen.getByLabelText(/nome/i), 'Carlos Silva')
    await usuario.type(screen.getByLabelText(/e-mail/i), 'carlos@email.com')
    await usuario.type(screen.getByLabelText(/^senha/i), 'senha123')
    await usuario.click(screen.getByRole('button', { name: 'Criar conta' }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Dados cadastrais inválidos na API.')
    })
  })

  it('exibe alerta com mensagem genérica quando ocorre erro inesperado de rede', async () => {
    const cadastroMockFn = vi
      .fn()
      .mockRejectedValueOnce(new Error('Servidor temporariamente inacessível'))
    const usuario = userEvent.setup()
    renderizarCadastro({ cadastro: cadastroMockFn })

    await usuario.type(screen.getByLabelText(/nome/i), 'Carlos Silva')
    await usuario.type(screen.getByLabelText(/e-mail/i), 'carlos@email.com')
    await usuario.type(screen.getByLabelText(/^senha/i), 'senha123')
    await usuario.click(screen.getByRole('button', { name: 'Criar conta' }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Servidor temporariamente inacessível')
    })
  })

  it('exibe mensagem padrão quando o erro não é uma instância de Error', async () => {
    const cadastroMockFn = vi.fn().mockRejectedValueOnce({ erro: 'desconhecido' })
    const usuario = userEvent.setup()
    renderizarCadastro({ cadastro: cadastroMockFn })

    await usuario.type(screen.getByLabelText(/nome/i), 'Carlos Silva')
    await usuario.type(screen.getByLabelText(/e-mail/i), 'carlos@email.com')
    await usuario.type(screen.getByLabelText(/^senha/i), 'senha123')
    await usuario.click(screen.getByRole('button', { name: 'Criar conta' }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(
        'Ocorreu um erro ao criar a conta. Tente novamente.',
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
