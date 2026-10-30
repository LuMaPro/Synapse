/**
 * Registra o service worker (public/sw.js, issue #35), que deixa o app instalável e
 * faz a casca abrir sem rede.
 *
 * Só no build de produção: no `npm run dev`, um cache guardaria versões velhas do
 * código e atrapalharia o desenvolvimento.
 */
export function registrarServiceWorker(producao = import.meta.env.PROD): void {
  if (!producao || !('serviceWorker' in navigator)) return
  window.addEventListener(
    'load',
    () => {
      navigator.serviceWorker.register('/sw.js').catch(() => {
        // Sem service worker, o app funciona igual; só não abre offline nem instala.
      })
    },
    { once: true },
  )
}
