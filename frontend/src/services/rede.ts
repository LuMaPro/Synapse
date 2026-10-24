import type { TipoNeuronio } from '../utils/neuronio'
import { api } from './api'

/** Neurônio como vem do `GET /rede` (issue #25). */
export interface NeuronioRede {
  id: string
  tipo: TipoNeuronio
  materia_id: string | null
  /** Cor do tipo; o podado vem sempre cinza. A tela troca pela cor da matéria. */
  cor: string
  criado_em: string
  duracao_minutos: number
  vivo: boolean
}

export interface SinapseRede {
  id: string
  /** Neurônio mais antigo. */
  origem_id: string
  /** Neurônio mais novo. */
  destino_id: string
  /** De 1 a 5: cresce a cada volta à mesma matéria. */
  peso: number
}

export interface RedeApi {
  neuronios: NeuronioRede[]
  sinapses: SinapseRede[]
}

export interface FiltrosRede {
  /** Só os neurônios criados a partir deste instante. */
  de?: Date
  materiaId?: string
}

/** A rede do estudante no formato de grafo, com os filtros de período e matéria. */
export function buscarRede({ de, materiaId }: FiltrosRede = {}): Promise<RedeApi> {
  const parametros = new URLSearchParams()
  // Em UTC (`Z`): o servidor compara instantes, e não precisa codificar o `+` do fuso.
  if (de) parametros.set('de', de.toISOString())
  if (materiaId) parametros.set('materia', materiaId)
  const consulta = parametros.toString()
  return api.get<RedeApi>(consulta ? `/rede?${consulta}` : '/rede')
}
