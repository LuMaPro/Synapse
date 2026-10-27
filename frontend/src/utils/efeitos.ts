import type { CSSProperties } from 'react'

/**
 * Animação das cores com efeito da loja (issue #34). O desenho de cada uma fica em
 * styles/efeitos.css; sem animação (`prefers-reduced-motion`), vale o hexadecimal.
 */
export type Efeito = 'pulsar' | 'aurora' | 'galaxia' | 'tempestade' | 'arco_iris'

/** As classes que ligam a animação do efeito num neurônio ou numa amostra de cor. */
export function classeDoEfeito(efeito?: Efeito | null): string {
  return efeito ? `com-efeito efeito-${efeito}` : ''
}

/**
 * Props de uma amostra de cor (bolinha ou quadradinho) já com o efeito, para usar em
 * qualquer elemento: `<i {...amostraDaCor(materia.cor, materia.efeito)} />`.
 */
export function amostraDaCor(
  cor: string,
  efeito?: Efeito | null,
  classe = '',
): { className: string; style: CSSProperties } {
  return {
    className: ['amostra', classe, classeDoEfeito(efeito)].filter(Boolean).join(' '),
    style: { background: cor, color: cor, '--cor-neuronio': cor } as CSSProperties,
  }
}
