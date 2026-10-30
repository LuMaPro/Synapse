import { useSyncExternalStore } from 'react'

/**
 * Se a media query do CSS vale agora, acompanhando as mudanças (ex.: girar o celular).
 * Sem `matchMedia` (ex.: nos testes com jsdom), vale como falsa.
 */
export function useMidia(consulta: string): boolean {
  return useSyncExternalStore(
    (avisar) => {
      if (typeof window.matchMedia !== 'function') return () => {}
      const lista = window.matchMedia(consulta)
      lista.addEventListener('change', avisar)
      return () => lista.removeEventListener('change', avisar)
    },
    () => typeof window.matchMedia === 'function' && window.matchMedia(consulta).matches,
  )
}

/** Telas estreitas, de celular: a navegação vira a barra de abas embaixo (issue #35). */
export const CONSULTA_CELULAR = '(max-width: 640px)'
