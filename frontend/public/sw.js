/* Service worker do Synapse (issue #35).
 *
 * Básico de propósito: deixa o app instalável e faz a "casca" (HTML, JS, CSS, ícones
 * e fontes) abrir mesmo sem rede ou com a rede lenta. A API nunca passa por cache: o
 * servidor é a fonte da verdade das sessões, e um dado velho seria pior que um erro.
 *
 * - Páginas (navegação): rede primeiro; sem rede, a última versão do app guardada.
 * - Arquivos do build e fontes: cache primeiro, atualizando em segundo plano. Os
 *   arquivos do build têm o hash no nome, então uma versão nova nunca é confundida.
 *
 * Trocar VERSAO descarta os caches antigos na ativação.
 */
const VERSAO = 'synapse-v1'
const CACHE_APP = `${VERSAO}-app`
const CACHE_FONTES = `${VERSAO}-fontes`
const CASCA = ['/', '/manifest.webmanifest', '/favicon.svg', '/icones/icone-192.png']
const ORIGENS_DE_FONTES = ['https://fonts.googleapis.com', 'https://fonts.gstatic.com']

self.addEventListener('install', (evento) => {
  evento.waitUntil(
    caches
      .open(CACHE_APP)
      .then((cache) => cache.addAll(CASCA))
      .then(() => self.skipWaiting()),
  )
})

self.addEventListener('activate', (evento) => {
  evento.waitUntil(
    caches
      .keys()
      .then((nomes) =>
        Promise.all(
          nomes.filter((nome) => !nome.startsWith(VERSAO)).map((nome) => caches.delete(nome)),
        ),
      )
      .then(() => self.clients.claim()),
  )
})

async function redePrimeiro(pedido) {
  const cache = await caches.open(CACHE_APP)
  try {
    const resposta = await fetch(pedido)
    // O app é uma página só: qualquer rota abre o mesmo index.html.
    if (resposta.ok) await cache.put('/', resposta.clone())
    return resposta
  } catch {
    const guardada = await cache.match('/')
    if (guardada) return guardada
    throw new Error('Sem rede e sem o app guardado.')
  }
}

async function cachePrimeiro(pedido, nomeDoCache) {
  const cache = await caches.open(nomeDoCache)
  const guardada = await cache.match(pedido)
  const atualizada = fetch(pedido)
    .then((resposta) => {
      if (resposta.ok || resposta.type === 'opaque') cache.put(pedido, resposta.clone())
      return resposta
    })
    .catch(() => guardada)
  return guardada ?? atualizada
}

self.addEventListener('fetch', (evento) => {
  const pedido = evento.request
  if (pedido.method !== 'GET') return
  const url = new URL(pedido.url)

  if (pedido.mode === 'navigate' && url.origin === self.location.origin) {
    evento.respondWith(redePrimeiro(pedido))
  } else if (url.origin === self.location.origin) {
    evento.respondWith(cachePrimeiro(pedido, CACHE_APP))
  } else if (ORIGENS_DE_FONTES.includes(url.origin)) {
    evento.respondWith(cachePrimeiro(pedido, CACHE_FONTES))
  }
  // O resto (a API, em outra origem) vai direto para a rede.
})
