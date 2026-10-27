import type { Efeito } from '../utils/efeitos'
import { api } from './api'
import { CORES_MATERIAS } from './materias'

/** Uma cor das matérias, como vem do `GET /loja` (issue #34). */
export interface CorLojaApi {
  codigo: string
  nome: string
  /** Hexadecimal `#RRGGBB`: vai na matéria e é o que se vê sem animação. */
  cor: string
  efeito: Efeito | null
  /** Em ATP; 0 é uma das 8 cores da paleta, que todo estudante já tem. */
  preco: number
  /** Se o estudante pode dar esta cor a uma matéria. */
  desbloqueada: boolean
}

export interface LojaApi {
  saldo: number
  /** A paleta inteira: as gratuitas primeiro, depois as da loja. */
  cores: CorLojaApi[]
}

/** As 8 cores gratuitas, para quando a paleta completa (`GET /loja`) não carregar. */
export const PALETA_GRATUITA: CorLojaApi[] = CORES_MATERIAS.map((cor) => ({
  codigo: cor.nome.toLowerCase(),
  nome: cor.nome,
  cor: cor.hex,
  efeito: null,
  preco: 0,
  desbloqueada: true,
}))

export const lojaApi = {
  buscar: () => api.get<LojaApi>('/loja'),
  /** Compra a cor para as matérias. Devolve a loja atualizada. */
  comprar: (codigo: string) => api.post<LojaApi>(`/loja/${encodeURIComponent(codigo)}/comprar`),
}
