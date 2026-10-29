import { beforeEach, describe, expect, it, vi } from 'vitest'
import CODIGO from '../public/sw.js?raw'

// O service worker (public/sw.js, issue #35) roda fora da página, então o jsdom não
// o executa. O teste carrega o arquivo de verdade com `self`, `caches` e `fetch`
// falsos e dispara os eventos que o navegador dispararia.
const ORIGEM = 'http://localhost:4173'

/** CacheStorage em memória, com a mesma interface usada pelo sw.js. */
function criarCaches(iniciais: string[] = []) {
  const caches = new Map<string, Map<string, Response>>(iniciais.map((nome) => [nome, new Map()]))
  const chave = (pedido: Request | string) =>
    typeof pedido === 'string' ? new URL(pedido, ORIGEM).href : pedido.url
  return {
    caches,
    api: {
      open: async (nome: string) => {
        if (!caches.has(nome)) caches.set(nome, new Map())
        const cache = caches.get(nome)!
        return {
          match: async (pedido: Request | string) => cache.get(chave(pedido))?.clone(),
          put: async (pedido: Request | string, resposta: Response) => {
            cache.set(chave(pedido), resposta)
          },
          addAll: async (urls: string[]) => {
            for (const url of urls) cache.set(chave(url), new Response(`conteúdo de ${url}`))
          },
        }
      },
      keys: async () => [...caches.keys()],
      delete: async (nome: string) => caches.delete(nome),
    },
  }
}

function carregarServiceWorker({ cachesIniciais = [] as string[] } = {}) {
  const ouvintes: Record<string, (evento: unknown) => void> = {}
  const self = {
    location: new URL(ORIGEM),
    addEventListener: (tipo: string, ouvinte: (evento: unknown) => void) => {
      ouvintes[tipo] = ouvinte
    },
    skipWaiting: vi.fn(async () => {}),
    clients: { claim: vi.fn(async () => {}) },
  }
  const { caches, api } = criarCaches(cachesIniciais)
  const rede = vi.fn(async (pedido: Request) => new Response(`da rede: ${pedido.url}`))
  new Function('self', 'caches', 'fetch', CODIGO)(self, api, rede)

  /** Dispara um evento com waitUntil/respondWith e espera o que ele prometeu. */
  async function disparar(tipo: string, pedido?: Request) {
    let promessa: Promise<unknown> | undefined
    let respondeu = false
    ouvintes[tipo]({
      request: pedido,
      waitUntil: (p: Promise<unknown>) => (promessa = p),
      respondWith: (p: Promise<unknown>) => {
        respondeu = true
        promessa = p
      },
    })
    return { resposta: (await promessa) as Response | undefined, respondeu }
  }

  return { self, caches, rede, disparar }
}

function navegacao(caminho: string) {
  // `mode` não pode ser 'navigate' num Request criado por código; o sw.js só lê.
  const pedido = new Request(ORIGEM + caminho)
  Object.defineProperty(pedido, 'mode', { value: 'navigate' })
  return pedido
}

describe('service worker', () => {
  let sw: ReturnType<typeof carregarServiceWorker>

  beforeEach(() => {
    sw = carregarServiceWorker({ cachesIniciais: ['synapse-v0-app', 'outra-coisa'] })
  })

  it('na instalação, guarda a casca do app e assume sem esperar', async () => {
    await sw.disparar('install')

    expect([...sw.caches.get('synapse-v1-app')!.keys()]).toEqual([
      `${ORIGEM}/`,
      `${ORIGEM}/manifest.webmanifest`,
      `${ORIGEM}/favicon.svg`,
      `${ORIGEM}/icones/icone-192.png`,
    ])
    expect(sw.self.skipWaiting).toHaveBeenCalled()
  })

  it('na ativação, apaga os caches de outras versões e controla as páginas abertas', async () => {
    await sw.disparar('install')
    await sw.disparar('activate')

    expect([...sw.caches.keys()]).toEqual(['synapse-v1-app'])
    expect(sw.self.clients.claim).toHaveBeenCalled()
  })

  it('páginas: busca na rede e guarda a última versão do app', async () => {
    const { resposta } = await sw.disparar('fetch', navegacao('/rede'))

    expect(await resposta!.text()).toBe(`da rede: ${ORIGEM}/rede`)
    expect(sw.caches.get('synapse-v1-app')!.has(`${ORIGEM}/`)).toBe(true)
  })

  it('critério: sem rede, qualquer página abre a última versão guardada do app', async () => {
    await sw.disparar('install')
    sw.rede.mockRejectedValue(new TypeError('Failed to fetch'))

    const { resposta } = await sw.disparar('fetch', navegacao('/historico'))

    expect(await resposta!.text()).toBe('conteúdo de /')
  })

  it('arquivos do build: usa o guardado e atualiza em segundo plano', async () => {
    const pedido = new Request(`${ORIGEM}/assets/index-abc123.js`)

    const primeira = await sw.disparar('fetch', pedido)
    expect(await primeira.resposta!.text()).toBe(`da rede: ${ORIGEM}/assets/index-abc123.js`)

    sw.rede.mockRejectedValue(new TypeError('Failed to fetch'))
    const segunda = await sw.disparar('fetch', pedido)
    expect(await segunda.resposta!.text()).toBe(`da rede: ${ORIGEM}/assets/index-abc123.js`)
  })

  it('guarda as fontes do Google para abrir sem rede', async () => {
    const pedido = new Request('https://fonts.gstatic.com/s/inter/v1/inter.woff2')

    await sw.disparar('fetch', pedido)

    expect(sw.caches.get('synapse-v1-fontes')!.has(pedido.url)).toBe(true)
  })

  it('a API e os envios nunca passam pelo cache', async () => {
    const api = await sw.disparar('fetch', new Request('http://localhost:8000/sessoes'))
    const envio = await sw.disparar(
      'fetch',
      new Request(`${ORIGEM}/qualquer`, { method: 'POST', body: '{}' }),
    )

    expect(api.respondeu).toBe(false)
    expect(envio.respondeu).toBe(false)
  })
})
