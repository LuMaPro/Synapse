import type { TipoNeuronio } from '../utils/neuronio'
import { api } from './api'

/** Um tipo de neurônio da loja de ATP, como vem do `GET /loja` (issue #34). */
export interface TipoLojaApi {
  codigo: string
  nome: string
  /** O desenho do neurônio, que continua ligado à duração da sessão. */
  forma: TipoNeuronio
  cor: string
  /** Em ATP; 0 é o tipo original, que todo estudante já tem. */
  preco: number
  duracao_minima: number
  duracao_maxima: number | null
  desbloqueado: boolean
  /** Se as próximas sessões desta faixa de duração criam neurônios deste tipo. */
  em_uso: boolean
}

export interface LojaApi {
  saldo: number
  tipos: TipoLojaApi[]
}

export const lojaApi = {
  buscar: () => api.get<LojaApi>('/loja'),
  /** Compra e já passa a usar o tipo. Devolve a loja atualizada. */
  comprar: (codigo: string) => api.post<LojaApi>(`/loja/${encodeURIComponent(codigo)}/comprar`),
  /** Escolhe o tipo das próximas sessões; o original volta ao padrão. */
  usar: (codigo: string) => api.post<LojaApi>(`/loja/${encodeURIComponent(codigo)}/usar`),
}

/** A cor do tipo em uso para cada forma, para desenhar o neurônio que vai nascer. */
export function coresEmUso(loja: LojaApi): Partial<Record<TipoNeuronio, string>> {
  return Object.fromEntries(loja.tipos.filter((t) => t.em_uso).map((t) => [t.forma, t.cor]))
}
