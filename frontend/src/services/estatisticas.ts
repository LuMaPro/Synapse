import type { Efeito } from '../utils/efeitos'
import { api } from './api'

/** Janela das estatísticas: hoje, os últimos 7 dias ou os últimos 30 (#30). */
export type PeriodoEstatisticas = 'dia' | 'semana' | 'mes'

export interface TempoMateriaDiaApi {
  materia_id: string | null
  minutos: number
}

export interface TempoDiaApi {
  /** Data no fuso de Brasília, `AAAA-MM-DD`. */
  data: string
  minutos: number
  por_materia: TempoMateriaDiaApi[]
}

export interface TempoMateriaApi {
  /** `null` para as sessões sem matéria. */
  materia_id: string | null
  nome: string | null
  cor: string | null
  efeito: Efeito | null
  minutos: number
  percentual: number
}

/** Resposta do `GET /estatisticas` (#30). */
export interface EstatisticasApi {
  periodo: PeriodoEstatisticas
  inicio: string
  fim: string
  tempo_total_minutos: number
  sessoes_concluidas: number
  sessoes_podadas: number
  total_sessoes: number
  /** De 0 a 1. */
  taxa_sucesso: number
  /** Hora do dia (0 a 23) com mais minutos focados, ou `null` sem sessões. */
  melhor_horario: number | null
  por_dia: TempoDiaApi[]
  por_materia: TempoMateriaApi[]
}

export function buscarEstatisticas(periodo: PeriodoEstatisticas): Promise<EstatisticasApi> {
  return api.get<EstatisticasApi>(`/estatisticas?periodo=${periodo}`)
}
