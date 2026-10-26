import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { criarServidorFalso, type ServidorFalso } from '../test/servidorFalso'
import {
  avisar,
  avisarSaidaImediata,
  buscarHistorico,
  enviarAvisosPendentes,
  fecharSaidaEmCurso,
  guardarSaidaEmCurso,
  sessoesApi,
  type RespostaAviso,
} from './sessoes'

const MINUTO = 60_000

describe('fila de avisos da sessão', () => {
  let servidor: ServidorFalso
  let sessaoId: string

  beforeEach(async () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date('2026-10-13T14:00:00Z'))
    localStorage.clear()
    servidor = criarServidorFalso()
    sessaoId = (await sessoesApi.iniciar(10, 'tolerante')).id
    vi.setSystemTime(Date.now() + 2 * MINUTO)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  const pendentes = () => JSON.parse(localStorage.getItem('synapse:avisos-pendentes') ?? '[]')

  it('envia os avisos em ordem e devolve a resposta do servidor', async () => {
    const respostas: RespostaAviso[] = []
    const inicio = Date.now() - MINUTO

    await avisar({ tipo: 'interrupcao', sessaoId, inicio, fim: inicio + 10_000 }, (r) =>
      respostas.push(r),
    )
    await avisar({ tipo: 'desistir', sessaoId }, (r) => respostas.push(r))

    expect(servidor.chamadas.slice(1).map((c) => c.caminho)).toEqual([
      `/sessoes/${sessaoId}/interrupcoes`,
      `/sessoes/${sessaoId}/desistir`,
    ])
    expect(servidor.chamadas[1].corpo).toEqual({
      inicio: new Date(inicio).toISOString(),
      fim: new Date(inicio + 10_000).toISOString(),
    })
    expect(respostas.map((r) => r.sessao?.estado)).toEqual(['em_andamento', 'podada'])
    expect(pendentes()).toEqual([])
  })

  it('sem rede, guarda o aviso no navegador e entrega na próxima tentativa', async () => {
    servidor.ficarSemRede()

    await expect(avisar({ tipo: 'desistir', sessaoId })).resolves.toBe(false)
    expect(pendentes()).toEqual([{ tipo: 'desistir', sessaoId }])

    servidor.ficarSemRede(false)
    await expect(enviarAvisosPendentes()).resolves.toBe(true)
    expect(pendentes()).toEqual([])
    expect(servidor.sessoes()[0].estado).toBe('podada')
  })

  it('descarta o aviso que o servidor recusa de vez e informa a recusa', async () => {
    servidor.sessoes()[0].estado = 'concluida'
    const aoResponder = vi.fn()

    await expect(avisar({ tipo: 'desistir', sessaoId }, aoResponder)).resolves.toBe(true)

    expect(aoResponder).toHaveBeenCalledWith({
      aviso: { tipo: 'desistir', sessaoId },
      sessao: null,
    })
    expect(pendentes()).toEqual([])
  })

  it('a saída imediata vai com keepalive e só fica na fila se não for entregue', async () => {
    const aviso = { tipo: 'interrupcao' as const, sessaoId, inicio: Date.now() }

    await expect(avisarSaidaImediata(aviso)).resolves.toBe(true)
    expect(servidor.chamadas.at(-1)?.keepalive).toBe(true)
    expect(pendentes()).toEqual([])

    servidor.ficarSemRede()
    await expect(avisarSaidaImediata({ ...aviso, inicio: aviso.inicio + 1 })).resolves.toBe(false)
    expect(pendentes()).toHaveLength(1)
  })

  it('fecha a saída deixada em aberto contando o tempo fora até o fim previsto', () => {
    const fimPrevisto = Date.now() + MINUTO
    guardarSaidaEmCurso({ sessaoId, inicio: Date.now(), fimPrevisto, deslocamento: 0 })
    vi.setSystemTime(Date.now() + 5 * MINUTO)

    fecharSaidaEmCurso()

    expect(pendentes()).toEqual([
      { tipo: 'interrupcao', sessaoId, inicio: fimPrevisto - MINUTO, fim: fimPrevisto },
    ])
    expect(localStorage.getItem('synapse:saida-em-curso')).toBeNull()
  })

  it('permite iniciar sessão com materia_id opcional', async () => {
    // encerra a sessão ativa anterior para poder iniciar outra
    await avisar({ tipo: 'desistir', sessaoId })
    const sessaoComMateria = await sessoesApi.iniciar(25, 'estrito', 'mat-abc')
    expect(sessaoComMateria.materia_id).toBe('mat-abc')
    expect(servidor.chamadas.at(-1)?.corpo).toEqual({
      duracao_minutos: 25,
      modo: 'estrito',
      materia_id: 'mat-abc',
    })
  })
})

describe('histórico de sessões', () => {
  const PAGINA_VAZIA = { total: 0, pagina: 1, tamanho: 20, paginas: 1, resultados: [] }

  function simularFetch() {
    return vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(PAGINA_VAZIA), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
  }

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('sem filtros, pede a primeira página com o tamanho padrão do servidor', async () => {
    const fetchMock = simularFetch()

    await expect(buscarHistorico()).resolves.toEqual(PAGINA_VAZIA)
    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/sessoes')
  })

  it('manda o início do período em UTC, o resultado e a página', async () => {
    const fetchMock = simularFetch()

    await buscarHistorico({
      de: new Date('2026-10-16T03:00:00Z'),
      status: 'podada',
      pagina: 3,
      tamanho: 10,
    })

    const url = new URL(String(fetchMock.mock.calls[0][0]))
    expect(url.pathname).toBe('/sessoes')
    expect(Object.fromEntries(url.searchParams)).toEqual({
      de: '2026-10-16T03:00:00.000Z',
      status: 'podada',
      pagina: '3',
      tamanho: '10',
    })
  })
})
