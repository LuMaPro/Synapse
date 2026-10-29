/* Service worker do Synapse (issue #35).
 *
 * Básico de propósito: deixa o app instalável e faz a "casca" (HTML, JS, CSS, ícones
 * e fontes) abrir mesmo sem rede ou com a rede lenta. A API nunca passa por cache: o
 * servidor é a fonte da verdade das sessões, e um dado velho seria pior que um erro.
 *
 * - Na instalação, e a cada página aberta com rede, guarda o index.html e os arquivos
 *   que ele usa (o JS e o CSS do build, a folha de estilo e os arquivos das fontes).
 *   Não dá para esperar a página pedir esses arquivos: no primeiro acesso, ela os
 *   baixa antes de o service worker começar a responder, e eles nunca seriam guardados.
 * - Páginas (navegação): rede primeiro; sem rede, a última versão do app guardada.
 * - Arquivos: cache primeiro. Os do build têm o hash no nome e nunca mudam; os
 *   outros (ícones, manifest) são atualizados em segundo plano.
 *
 * Trocar VERSAO descarta os caches antigos na ativação.
 */
const VERSAO = 'synapse-v3'
// O servidor pode responder com `Vary: Origin` (o `vite preview` responde), e a página
// pede o JS e o CSS com `crossorigin`, ou seja, com o cabeçalho Origin; o service
// worker, sem ele. Para o cache, seriam pedidos diferentes, e sem rede a página não
// acharia os arquivos guardados (abria em branco). São os mesmos arquivos estáticos
// para qualquer origem, então a busca ignora o Vary.
const BUSCA = { ignoreVary: true }
const CACHE_APP = `${VERSAO}-app`
const CACHE_FONTES = `${VERSAO}-fontes`
const CASCA = ['/manifest.webmanifest', '/favicon.svg', '/icones/icone-192.png']
const ORIGENS_DE_FONTES = ['https://fonts.googleapis.com', 'https://fonts.gstatic.com']

/** Os arquivos do build citados no HTML (`/assets/...`) e as folhas de fontes. */
function arquivosDoHtml(html) {
  const doBuild = [...html.matchAll(/(?:src|href)="(\/assets\/[^"]+)"/g)].map((m) => m[1])
  const fontes = [...html.matchAll(/href="(https:\/\/fonts\.googleapis\.com\/[^"]+)"/g)].map((m) =>
    m[1].replaceAll('&amp;', '&'),
  )
  return { doBuild, fontes }
}

/** Guarda o que ainda não está no cache, sem deixar uma falha derrubar o resto. */
async function guardarFaltantes(cache, urls) {
  await Promise.all(
    urls.map(async (url) => {
      if (await cache.match(url, BUSCA)) return
      try {
        const resposta = await fetch(url)
        if (resposta.ok) await cache.put(url, resposta)
      } catch {
        // Fica para a próxima vez que a página abrir com rede.
      }
    }),
  )
}

/** Guarda os arquivos que o index.html usa, incluindo os arquivos de fonte do CSS. */
async function guardarArquivosDa(html) {
  const { doBuild, fontes } = arquivosDoHtml(html)
  await guardarFaltantes(await caches.open(CACHE_APP), doBuild)
  const cacheFontes = await caches.open(CACHE_FONTES)
  await guardarFaltantes(cacheFontes, fontes)
  for (const folha of fontes) {
    const css = await cacheFontes.match(folha, BUSCA)
    if (!css) continue
    const arquivos = [
      ...(await css.text()).matchAll(/url\((https:\/\/fonts\.gstatic\.com[^)]+)\)/g),
    ]
    await guardarFaltantes(
      cacheFontes,
      arquivos.map((m) => m[1]),
    )
  }
}

self.addEventListener('install', (evento) => {
  evento.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE_APP)
      await cache.addAll(['/', ...CASCA])
      await guardarArquivosDa(await (await cache.match('/', BUSCA)).text())
      await self.skipWaiting()
    })(),
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

async function redePrimeiro(evento) {
  const cache = await caches.open(CACHE_APP)
  try {
    const resposta = await fetch(evento.request)
    if (resposta.ok) {
      // O app é uma página só: qualquer rota abre o mesmo index.html. Depois de uma
      // versão nova, os arquivos dela são guardados sem atrasar a página.
      await cache.put('/', resposta.clone())
      evento.waitUntil(
        resposta
          .clone()
          .text()
          .then(guardarArquivosDa)
          .catch(() => {}),
      )
    }
    return resposta
  } catch {
    const guardada = await cache.match('/', BUSCA)
    if (guardada) return guardada
    throw new Error('Sem rede e sem o app guardado.')
  }
}

async function cachePrimeiro(pedido, nomeDoCache) {
  const cache = await caches.open(nomeDoCache)
  const guardada = await cache.match(pedido, BUSCA)
  // Arquivo do build (hash no nome) nunca muda: guardado, não precisa da rede.
  if (guardada && new URL(pedido.url).pathname.startsWith('/assets/')) return guardada
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
    evento.respondWith(redePrimeiro(evento))
  } else if (url.origin === self.location.origin) {
    evento.respondWith(cachePrimeiro(pedido, CACHE_APP))
  } else if (ORIGENS_DE_FONTES.includes(url.origin)) {
    evento.respondWith(cachePrimeiro(pedido, CACHE_FONTES))
  }
  // O resto (a API, em outra origem) vai direto para a rede.
})
