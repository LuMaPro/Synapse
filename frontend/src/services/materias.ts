import type { Efeito } from '../utils/efeitos'
import { api } from './api'

/** Matéria (etiqueta) do estudante (issues #27 e #28). */
export interface MateriaApi {
  id: string
  usuario_id?: string
  nome: string
  /** Hexadecimal `#RRGGBB`. */
  cor: string
  /** Animação da cor, se for uma cor com efeito da loja (issue #34). */
  efeito?: Efeito | null
  criada_em: string
}

/** Alias de conveniência para a entidade de matéria no frontend. */
export type Materia = MateriaApi

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
 * 8 cores oficiais do design do Synapse (docs/design/README.md), de todos. A paleta
 * completa, com as cores da loja (#34), vem do `GET /loja`; estas ficam para quando
 * ela não carregar.
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
  listar: () => api.get<Materia[]>('/materias'),
  criar: (payload: CriarMateriaPayload) => api.post<Materia>('/materias', payload),
  buscar: (id: string) => api.get<Materia>(`/materias/${id}`),
  atualizar: (id: string, payload: AtualizarMateriaPayload) =>
    api.patch<Materia>(`/materias/${id}`, payload),
  remover: (id: string) => api.delete<void>(`/materias/${id}`),
}

/** As matérias do estudante, em ordem alfabética. */
export function listarMaterias(): Promise<Materia[]> {
  return materiasApi.listar()
}
