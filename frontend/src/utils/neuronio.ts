export type TipoNeuronio = 'granular' | 'piramidal' | 'purkinje'

/** Faixas de duração de cada tipo, definidas no design (docs/design/README.md). */
export function tipoNeuronio(duracaoMin: number): TipoNeuronio {
  if (duracaoMin < 25) return 'granular'
  if (duracaoMin < 60) return 'piramidal'
  return 'purkinje'
}

export const NOME_TIPO_NEURONIO: Record<TipoNeuronio, string> = {
  granular: 'Granular',
  piramidal: 'Piramidal',
  purkinje: 'Purkinje',
}

/**
 * Cor padrão de cada tipo, a mesma do protótipo (docs/design). Quando a sessão tiver
 * uma matéria (#28), a cor da matéria substitui a padrão.
 */
export const COR_PADRAO_TIPO_NEURONIO: Record<TipoNeuronio, string> = {
  granular: 'var(--cor-impulso)',
  piramidal: 'var(--cor-destaque)',
  purkinje: 'var(--cor-atp)',
}
