const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

type Metodo = 'GET' | 'POST' | 'PATCH' | 'DELETE'

/** Formato padrão de erro devolvido pela API (ver issue #12). */
interface CorpoErro {
  erro?: string
  mensagem?: string
}

export class ApiError extends Error {
  readonly status: number
  readonly codigo: string

  constructor(status: number, codigo: string, mensagem: string) {
    super(mensagem)
    this.name = 'ApiError'
    this.status = status
    this.codigo = codigo
  }
}

const CHAVE_TOKEN = 'synapse_token'

export function obterTokenApi(): string | null {
  try {
    return localStorage.getItem(CHAVE_TOKEN)
  } catch {
    return null
  }
}

export function definirTokenApi(token: string | null): void {
  try {
    if (token) {
      localStorage.setItem(CHAVE_TOKEN, token)
    } else {
      localStorage.removeItem(CHAVE_TOKEN)
    }
  } catch {
    // ignora erro em ambientes sem localStorage
  }
}

interface OpcoesSessao {
  /** Pede um token de acesso novo ao servidor; null se não der para renovar. */
  renovar: () => Promise<string | null>
  /** Chamado quando a sessão não pode mais ser renovada (o usuário precisa entrar de novo). */
  aoExpirar: () => void
}

let sessao: OpcoesSessao | null = null
let renovacaoEmAndamento: Promise<string | null> | null = null

/**
 * Rotas públicas de autenticação. Nelas o token não é enviado: o backend valida
 * qualquer token recebido antes da view, e um token expirado derrubaria até a própria
 * renovação. Também é onde 401 é a resposta esperada (senha errada, token de renovação
 * inválido), e não um sinal de que é preciso renovar.
 */
const ROTAS_PUBLICAS = ['/auth/login', '/auth/cadastro', '/auth/renovar']

/**
 * Liga a renovação automática do token (feito pelo AuthProvider). O token de acesso
 * dura 15 minutos: quando uma chamada autenticada recebe 401, o token é renovado e a
 * chamada é repetida uma vez.
 */
export function configurarSessao(opcoes: OpcoesSessao | null): void {
  sessao = opcoes
}

/** Várias chamadas recebendo 401 ao mesmo tempo compartilham uma única renovação. */
function renovarToken(): Promise<string | null> {
  if (!sessao) return Promise.resolve(null)
  renovacaoEmAndamento ??= sessao.renovar().finally(() => {
    renovacaoEmAndamento = null
  })
  return renovacaoEmAndamento
}

function cabecalhos(caminho: string, temCorpo: boolean): Record<string, string> {
  const headers: Record<string, string> = {}
  if (temCorpo) {
    headers['Content-Type'] = 'application/json'
  }
  const token = obterTokenApi()
  if (token && !ROTAS_PUBLICAS.includes(caminho)) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

/**
 * Decide o que fazer com um 401: true se o token foi renovado e a chamada deve ser
 * repetida. Na segunda tentativa, ou se não deu para renovar, encerra a sessão.
 */
async function deveRepetirApos401(caminho: string, jaRenovou: boolean): Promise<boolean> {
  if (!obterTokenApi() || ROTAS_PUBLICAS.includes(caminho)) return false
  if (!jaRenovou && (await renovarToken())) return true
  sessao?.aoExpirar()
  return false
}

async function requisicao<T>(
  metodo: Metodo,
  caminho: string,
  corpo?: unknown,
  jaRenovou = false,
): Promise<T> {
  const temCorpo = corpo !== undefined
  const headers = cabecalhos(caminho, temCorpo)

  const resposta = await fetch(`${API_URL}${caminho}`, {
    method: metodo,
    headers: Object.keys(headers).length > 0 ? headers : undefined,
    body: temCorpo ? JSON.stringify(corpo) : undefined,
  })

  if (resposta.status === 401 && (await deveRepetirApos401(caminho, jaRenovou))) {
    return requisicao<T>(metodo, caminho, corpo, true)
  }

  if (!resposta.ok) {
    const erro = (await resposta.json().catch(() => null)) as CorpoErro | null
    throw new ApiError(
      resposta.status,
      erro?.erro ?? 'erro_desconhecido',
      erro?.mensagem ?? `Erro ${resposta.status} ao acessar a API`,
    )
  }

  if (resposta.status === 204) {
    return undefined as T
  }
  return (await resposta.json()) as T
}

/**
 * POST que continua mesmo se a aba for escondida ou fechada logo em seguida, para
 * avisar o servidor de uma saída da tela (issues #18 e #20).
 *
 * Usa `fetch` com `keepalive` em vez de `navigator.sendBeacon` porque o beacon não
 * aceita cabeçalhos, e a API vai exigir o token de autenticação (#14). Não lança erro:
 * a página pode estar sumindo, então só devolve se o servidor aceitou.
 */
async function postEmSegundoPlano(
  caminho: string,
  corpo: unknown,
  jaRenovou = false,
): Promise<boolean> {
  try {
    const resposta = await fetch(`${API_URL}${caminho}`, {
      method: 'POST',
      headers: cabecalhos(caminho, true),
      body: JSON.stringify(corpo),
      keepalive: true,
    })
    // Aba só escondida (sem fechar) ainda roda JavaScript: dá para renovar e reenviar.
    if (resposta.status === 401 && (await deveRepetirApos401(caminho, jaRenovou))) {
      return postEmSegundoPlano(caminho, corpo, true)
    }
    return resposta.ok
  } catch {
    return false
  }
}

export const api = {
  get: <T>(caminho: string) => requisicao<T>('GET', caminho),
  post: <T>(caminho: string, corpo?: unknown) => requisicao<T>('POST', caminho, corpo),
  patch: <T>(caminho: string, corpo?: unknown) => requisicao<T>('PATCH', caminho, corpo),
  delete: <T>(caminho: string) => requisicao<T>('DELETE', caminho),
  postEmSegundoPlano: (caminho: string, corpo: unknown) => postEmSegundoPlano(caminho, corpo),
}
