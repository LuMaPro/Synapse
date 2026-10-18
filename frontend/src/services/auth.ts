import { api, definirTokenApi, obterTokenApi } from './api'

/**
 * Serviço de autenticação para as telas de Login e Cadastro (issues #8, #14 e #15).
 * Gerencia tokens JWT, dados do usuário e persistência de sessão.
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

export const CHAVE_REFRESH_TOKEN = 'synapse_refresh_token'
export const CHAVE_USUARIO = 'synapse_usuario'

export function salvarSessao(
  token: string,
  refreshToken?: string,
  usuario?: UsuarioAutenticado,
): void {
  definirTokenApi(token)
  try {
    if (refreshToken) {
      localStorage.setItem(CHAVE_REFRESH_TOKEN, refreshToken)
    }
    if (usuario) {
      localStorage.setItem(CHAVE_USUARIO, JSON.stringify(usuario))
    }
  } catch {
    // ignora erro em ambientes sem localStorage
  }
}

export function obterSessaoSalva(): {
  token: string | null
  refreshToken: string | null
  usuario: UsuarioAutenticado | null
} {
  const token = obterTokenApi()
  let refreshToken: string | null = null
  let usuario: UsuarioAutenticado | null = null
  try {
    refreshToken = localStorage.getItem(CHAVE_REFRESH_TOKEN)
    const usuarioSalvo = localStorage.getItem(CHAVE_USUARIO)
    if (usuarioSalvo) {
      usuario = JSON.parse(usuarioSalvo) as UsuarioAutenticado
    }
  } catch {
    // ignora erro de parsing
  }
  return { token, refreshToken, usuario }
}

export function limparSessao(): void {
  definirTokenApi(null)
  try {
    localStorage.removeItem(CHAVE_REFRESH_TOKEN)
    localStorage.removeItem(CHAVE_USUARIO)
  } catch {
    // ignora erro
  }
}

interface RespostaLoginApi {
  access: string
  refresh: string
}

interface RespostaRenovarApi {
  access: string
  refresh?: string
}

export async function loginApi(credenciais: CredenciaisLogin): Promise<RespostaAuth> {
  const { access, refresh } = await api.post<RespostaLoginApi>('/auth/login', {
    email: credenciais.email.trim(),
    senha: credenciais.senha,
  })

  definirTokenApi(access)
  const usuario = await api.get<UsuarioAutenticado>('/me')

  salvarSessao(access, refresh, usuario)
  return { usuario, token: access }
}

export async function cadastroApi(dados: DadosCadastro): Promise<RespostaAuth> {
  await api.post<UsuarioAutenticado>('/auth/cadastro', {
    nome: dados.nome.trim(),
    email: dados.email.trim(),
    senha: dados.senha,
  })

  return loginApi({
    email: dados.email,
    senha: dados.senha,
  })
}

export async function renovarTokenApi(): Promise<string | null> {
  const { refreshToken } = obterSessaoSalva()
  if (!refreshToken) {
    limparSessao()
    return null
  }

  try {
    const { access, refresh } = await api.post<RespostaRenovarApi>('/auth/renovar', {
      refresh: refreshToken,
    })
    salvarSessao(access, refresh ?? refreshToken)
    return access
  } catch {
    limparSessao()
    return null
  }
}

export async function loginMock(credenciais: CredenciaisLogin): Promise<RespostaAuth> {
  await esperar(TEMPO_ESPERA_MS)

  const emailLimpo = credenciais.email.trim().toLowerCase()

  // Simulação de erro específico para testes de credenciais incorretas
  if (emailLimpo === 'erro@email.com' || credenciais.senha === 'senhaerrada') {
    throw new AuthError('credenciais_invalidas', 'Credenciais inválidas. Verifique seu e-mail e senha.')
  }

  const resposta: RespostaAuth = {
    usuario: {
      id: 'usr-mock-1',
      nome: 'Usuário Synapse',
      email: emailLimpo,
    },
    token: 'jwt-token-mock-synapse',
  }
  salvarSessao(resposta.token, 'jwt-refresh-mock-synapse', resposta.usuario)
  return resposta
}

export async function cadastroMock(dados: DadosCadastro): Promise<RespostaAuth> {
  await esperar(TEMPO_ESPERA_MS)

  const emailLimpo = dados.email.trim().toLowerCase()

  // Simulação de erro de e-mail duplicado
  if (emailLimpo === 'existe@email.com') {
    throw new AuthError('email_duplicado', 'E-mail já cadastrado. Tente fazer login ou use outro e-mail.')
  }

  const resposta: RespostaAuth = {
    usuario: {
      id: 'usr-mock-2',
      nome: dados.nome.trim(),
      email: emailLimpo,
    },
    token: 'jwt-token-mock-synapse',
  }
  salvarSessao(resposta.token, 'jwt-refresh-mock-synapse', resposta.usuario)
  return resposta
}
