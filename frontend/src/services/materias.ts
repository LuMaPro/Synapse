import { api } from './api'

/** Matéria (etiqueta) do estudante, como vem do `GET /materias` (issue #27). */
export interface Materia {
  id: string
  nome: string
  /** Hexadecimal `#RRGGBB`. */
  cor: string
  criada_em: string
}

/** As matérias do estudante, em ordem alfabética. O gerenciamento vem na #28. */
export function listarMaterias(): Promise<Materia[]> {
  return api.get<Materia[]>('/materias')
}
