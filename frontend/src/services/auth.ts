/**
 * Serviço simulado de autenticação para as telas de Login e Cadastro (issues #8 e #15).
 * Simula requisições de rede, latência e respostas de erro da API.
 */

export interface CredenciaisLogin {
  email: string
  senha: string
}

export interface DadosCadastro {
  nome: string
  email: string
  senha: string
}

export interface UsuarioAutenticado {
  id: string
  nome: string
  email: string
}

export interface RespostaAuth {
  usuario: UsuarioAutenticado
  token: string
}

export class AuthError extends Error {
  readonly codigo: string

  constructor(codigo: string, mensagem: string) {
    super(mensagem)
    this.name = 'AuthError'
    this.codigo = codigo
  }
}

const TEMPO_ESPERA_MS = 600

function esperar(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export async function loginMock(credenciais: CredenciaisLogin): Promise<RespostaAuth> {
  await esperar(TEMPO_ESPERA_MS)

  const emailLimpo = credenciais.email.trim().toLowerCase()

  // Simulação de erro específico para testes de credenciais incorretas
  if (emailLimpo === 'erro@email.com' || credenciais.senha === 'senhaerrada') {
    throw new AuthError('credenciais_invalidas', 'Credenciais inválidas. Verifique seu e-mail e senha.')
  }

  return {
    usuario: {
      id: 'usr-mock-1',
      nome: 'Usuário Synapse',
      email: emailLimpo,
    },
    token: 'jwt-token-mock-synapse',
  }
}

export async function cadastroMock(dados: DadosCadastro): Promise<RespostaAuth> {
  await esperar(TEMPO_ESPERA_MS)

  const emailLimpo = dados.email.trim().toLowerCase()

  // Simulação de erro de e-mail duplicado
  if (emailLimpo === 'existe@email.com') {
    throw new AuthError('email_duplicado', 'E-mail já cadastrado. Tente fazer login ou use outro e-mail.')
  }

  return {
    usuario: {
      id: 'usr-mock-2',
      nome: dados.nome.trim(),
      email: emailLimpo,
    },
    token: 'jwt-token-mock-synapse',
  }
}
