import { api } from './api'

/** Sequência de dias seguidos com sessão concluída (#32). */
export interface SequenciaApi {
  atual: number
  recorde: number
}

/** Uma conquista do catálogo do estudante (#32). */
export interface ConquistaApi {
  codigo: string
  nome: string
  descricao: string
  desbloqueada: boolean
  desbloqueada_em: string | null
  progresso: number
  meta: number
  unidade: string
}

/** Resposta do endpoint `GET /conquistas` (#32). */
export interface ConquistasRespostaApi {
  sequencia: SequenciaApi
  desbloqueadas: number
  total: number
  conquistas: ConquistaApi[]
}

export const conquistasApi = {
  /** Busca a sequência e todas as conquistas, com progresso e status de desbloqueio. */
  consultar: () => api.get<ConquistasRespostaApi>('/conquistas'),
}
