import { api } from './api'

export interface MateriaApi {
  id: string
  usuario_id: string
  nome: string
  cor: string
  criada_em: string
}

export interface CriarMateriaPayload {
  nome: string
  cor: string
}

export interface AtualizarMateriaPayload {
  nome?: string
  cor?: string
}

export interface CorMateria {
  nome: string
  hex: string
}

/**
 * 8 cores oficiais do design do Synapse (docs/design/README.md).
 * O estudante escolhe uma delas ao criar ou editar uma matéria.
 */
export const CORES_MATERIAS: readonly CorMateria[] = [
  { nome: 'Violeta', hex: '#8B7BFF' },
  { nome: 'Ciano', hex: '#3EE6E0' },
  { nome: 'Verde', hex: '#5BE49B' },
  { nome: 'Âmbar', hex: '#FFC857' },
  { nome: 'Laranja', hex: '#FF8A5C' },
  { nome: 'Rosa', hex: '#FF6FB5' },
  { nome: 'Azul', hex: '#6FA8FF' },
  { nome: 'Lima', hex: '#C3E86B' },
] as const

export const materiasApi = {
  listar: () => api.get<MateriaApi[]>('/materias'),
  criar: (payload: CriarMateriaPayload) => api.post<MateriaApi>('/materias', payload),
  buscar: (id: string) => api.get<MateriaApi>(`/materias/${id}`),
  atualizar: (id: string, payload: AtualizarMateriaPayload) =>
    api.patch<MateriaApi>(`/materias/${id}`, payload),
  remover: (id: string) => api.delete<void>(`/materias/${id}`),
}
