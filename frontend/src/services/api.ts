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

async function requisicao<T>(metodo: Metodo, caminho: string, corpo?: unknown): Promise<T> {
  const temCorpo = corpo !== undefined
  const resposta = await fetch(`${API_URL}${caminho}`, {
    method: metodo,
    headers: temCorpo ? { 'Content-Type': 'application/json' } : undefined,
    body: temCorpo ? JSON.stringify(corpo) : undefined,
  })

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
async function postEmSegundoPlano(caminho: string, corpo: unknown): Promise<boolean> {
  try {
    const resposta = await fetch(`${API_URL}${caminho}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(corpo),
      keepalive: true,
    })
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
  postEmSegundoPlano,
}
