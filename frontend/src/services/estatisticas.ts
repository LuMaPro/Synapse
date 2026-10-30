import { api } from './api'

// O backend usa snake_case, precisamos tipar exatamente como ele devolve
export interface TempoMateriaDiaApi {
  materia_id: string | null
  minutos: number
}

export interface TempoDiaApi {
  data: string
  minutos: number
  por_materia: TempoMateriaDiaApi[]
}

export interface TempoMateriaApi {
  materia_id: string | null
  nome: string | null
  cor: string | null
  efeito: string | null
  minutos: number
  percentual: number
}

export interface EstatisticasApi {
  periodo: 'dia' | 'semana' | 'mes'
  inicio: string
  fim: string
  tempo_total_minutos: number
  sessoes_concluidas: number
  sessoes_podadas: number
  total_sessoes: number
  taxa_sucesso: number // Já vem de 0.0 a 1.0
  melhor_horario: number | null
  por_dia: TempoDiaApi[]
  por_materia: TempoMateriaApi[]
}

export function buscarEstatisticas(periodo: 'dia' | 'semana' | 'mes'): Promise<EstatisticasApi> {
  return api.get<EstatisticasApi>(`/estatisticas?periodo=${periodo}`)
}