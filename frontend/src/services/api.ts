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

export const api = {
  get: <T>(caminho: string) => requisicao<T>('GET', caminho),
  post: <T>(caminho: string, corpo?: unknown) => requisicao<T>('POST', caminho, corpo),
  patch: <T>(caminho: string, corpo?: unknown) => requisicao<T>('PATCH', caminho, corpo),
  delete: <T>(caminho: string) => requisicao<T>('DELETE', caminho),
}
