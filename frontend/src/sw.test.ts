import { beforeEach, describe, expect, it, vi } from 'vitest'
import CODIGO from '../public/sw.js?raw'

// O service worker (public/sw.js, issue #35) roda fora da página, então o jsdom não
// o executa. O teste carrega o arquivo de verdade com `self`, `caches` e `fetch`
// falsos e dispara os eventos que o navegador dispararia.
const ORIGEM = 'http://localhost:4173'
const FOLHA_FONTES = 'https://fonts.googleapis.com/css2?family=Inter:wght@400&display=swap'
const ARQUIVO_FONTE = 'https://fonts.gstatic.com/s/inter/v1/inter.woff2'

/** O index.html do build, como o Vite gera (com o `&amp;` na URL das fontes). */
function indexHtml(hash = 'abc123') {
  return `<!doctype html><html><head>
    <link href="${FOLHA_FONTES.replace('&', '&amp;')}" rel="stylesheet" />
    <script type="module" crossorigin src="/assets/index-${hash}.js"></script>
    <link rel="stylesheet" crossorigin href="/assets/index-${hash}.css">
  </head><body><div id="root"></div></body></html>`
}

/** A rede: o index.html, a folha de fontes (que cita um arquivo) e o resto. Como o
 * `vite preview`, responde tudo com `Vary: Origin`. */
function respostaDaRede(url: string, hash: string) {
  const { pathname, origin } = new URL(url)
  const vary = { headers: { Vary: 'Origin' } }
  if (origin === ORIGEM && !pathname.includes('.')) return new Response(indexHtml(hash), vary)
  if (url === FOLHA_FONTES) {
    return new Response(`@font-face { src: url(${ARQUIVO_FONTE}); }`, vary)
  }
  return new Response(`conteúdo de ${url}`, vary)
}

/** Pedido feito pela página com `crossorigin` (o JS e o CSS do Vite): leva o Origin. */
function daPagina(url: string) {
  const pedido = new Request(url)
  Object.defineProperty(pedido, 'origem', { value: ORIGEM })
  return pedido
}

const origemDo = (pedido: Request | string) =>
  typeof pedido === 'string' ? null : ((pedido as Request & { origem?: string }).origem ?? null)

/**
 * CacheStorage em memória, com a mesma interface usada pelo sw.js. Como no navegador,
 * uma resposta com `Vary: Origin` só serve para um pedido com o mesmo Origin, a não
 * ser com `ignoreVary`.
 */
function criarCaches(rede: (pedido: Request) => Promise<Response>, iniciais: string[]) {
  type Entrada = { resposta: Response; origem: string | null }
  const caches = new Map<string, Map<string, Entrada>>(iniciais.map((nome) => [nome, new Map()]))
  const chave = (pedido: Request | string) =>
    typeof pedido === 'string' ? new URL(pedido, ORIGEM).href : pedido.url
  const api = {
    open: async (nome: string) => {
      if (!caches.has(nome)) caches.set(nome, new Map())
      const cache = caches.get(nome)!
      return {
        match: async (pedido: Request | string, opcoes?: { ignoreVary?: boolean }) => {
          const entrada = cache.get(chave(pedido))
          if (!entrada) return undefined
          const variaPelaOrigem = entrada.resposta.headers.get('Vary')?.includes('Origin')
          if (variaPelaOrigem && !opcoes?.ignoreVary && entrada.origem !== origemDo(pedido)) {
            return undefined
          }
          return entrada.resposta.clone()
        },
        put: async (pedido: Request | string, resposta: Response) => {
          cache.set(chave(pedido), { resposta, origem: origemDo(pedido) })
        },
        addAll: async (urls: string[]) => {
          for (const url of urls) {
            cache.set(chave(url), { resposta: await rede(new Request(chave(url))), origem: null })
          }
        },
      }
    },
    keys: async () => [...caches.keys()],
    delete: async (nome: string) => caches.delete(nome),
  }
  return { caches, api }
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
  let hash = 'abc123'
  // Como no navegador, um caminho relativo vale a partir da origem do service worker.
  const rede = vi.fn(async (pedido: Request | string) =>
    respostaDaRede(typeof pedido === 'string' ? new URL(pedido, ORIGEM).href : pedido.url, hash),
  )
  const { caches, api } = criarCaches(rede, cachesIniciais)
  new Function('self', 'caches', 'fetch', CODIGO)(self, api, rede)

  /** Dispara um evento e espera a resposta e o trabalho em segundo plano. */
  async function disparar(tipo: string, pedido?: Request) {
    const pendentes: Promise<unknown>[] = []
    let resposta: Promise<unknown> | undefined
    ouvintes[tipo]({
      request: pedido,
      waitUntil: (p: Promise<unknown>) => pendentes.push(p),
      respondWith: (p: Promise<unknown>) => (resposta = p),
    })
    const valor = (await resposta) as Response | undefined
    // O que for agendado durante a resposta também entra na espera.
    for (let i = 0; i < pendentes.length; i++) await pendentes[i]
    return { resposta: valor, respondeu: resposta !== undefined }
  }

  const guardados = (nome: string) => [...(caches.get(nome)?.keys() ?? [])]

  return {
    self,
    caches,
    rede,
    disparar,
    guardados,
    novaVersao: (novo: string) => (hash = novo),
  }
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
    sw = carregarServiceWorker({ cachesIniciais: ['synapse-v2-app', 'outra-coisa'] })
  })

  it('critério: na instalação, guarda a casca e os arquivos que o index.html usa', async () => {
    await sw.disparar('install')

    expect(sw.guardados('synapse-v3-app').sort()).toEqual(
      [
        `${ORIGEM}/`,
        `${ORIGEM}/manifest.webmanifest`,
        `${ORIGEM}/favicon.svg`,
        `${ORIGEM}/icones/icone-192.png`,
        `${ORIGEM}/assets/index-abc123.js`,
        `${ORIGEM}/assets/index-abc123.css`,
      ].sort(),
    )
    // As fontes: a folha de estilo e o arquivo que ela cita.
    expect(sw.guardados('synapse-v3-fontes').sort()).toEqual([FOLHA_FONTES, ARQUIVO_FONTE].sort())
    expect(sw.self.skipWaiting).toHaveBeenCalled()
  })

  it('na ativação, apaga os caches de outras versões e controla as páginas abertas', async () => {
    await sw.disparar('install')
    await sw.disparar('activate')

    expect([...sw.caches.keys()].sort()).toEqual(['synapse-v3-app', 'synapse-v3-fontes'])
    expect(sw.self.clients.claim).toHaveBeenCalled()
  })

  it('critério: sem rede, a página abre com o JS, o CSS e as fontes guardados', async () => {
    await sw.disparar('install')
    sw.rede.mockRejectedValue(new TypeError('Failed to fetch'))

    const pagina = await sw.disparar('fetch', navegacao('/historico'))
    // A página pede o JS e o CSS com o Origin; o service worker os guardou sem ele.
    const css = await sw.disparar('fetch', daPagina(`${ORIGEM}/assets/index-abc123.css`))
    const js = await sw.disparar('fetch', daPagina(`${ORIGEM}/assets/index-abc123.js`))
    const fonte = await sw.disparar('fetch', new Request(ARQUIVO_FONTE))

    expect(await pagina.resposta!.text()).toContain('/assets/index-abc123.css')
    expect(await css.resposta!.text()).toBe(`conteúdo de ${ORIGEM}/assets/index-abc123.css`)
    expect(await js.resposta!.text()).toBe(`conteúdo de ${ORIGEM}/assets/index-abc123.js`)
    expect(await fonte.resposta!.text()).toBe(`conteúdo de ${ARQUIVO_FONTE}`)
  })

  it('arquivos do build guardados não vão à rede (o hash no nome garante a versão)', async () => {
    await sw.disparar('install')
    sw.rede.mockClear()

    await sw.disparar('fetch', daPagina(`${ORIGEM}/assets/index-abc123.js`))

    expect(sw.rede).not.toHaveBeenCalled()
  })

  it('páginas vêm da rede, e uma versão nova do app tem os arquivos guardados', async () => {
    await sw.disparar('install')
    sw.novaVersao('def456')

    const { resposta } = await sw.disparar('fetch', navegacao('/rede'))

    expect(await resposta!.text()).toContain('/assets/index-def456.js')
    expect(sw.guardados('synapse-v3-app')).toEqual(
      expect.arrayContaining([
        `${ORIGEM}/assets/index-def456.js`,
        `${ORIGEM}/assets/index-def456.css`,
      ]),
    )
  })

  it('outros arquivos da casca são atualizados em segundo plano', async () => {
    await sw.disparar('install')
    sw.rede.mockClear()

    const { resposta } = await sw.disparar('fetch', new Request(`${ORIGEM}/favicon.svg`))

    expect(await resposta!.text()).toBe(`conteúdo de ${ORIGEM}/favicon.svg`)
    expect(sw.rede).toHaveBeenCalledOnce()
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
