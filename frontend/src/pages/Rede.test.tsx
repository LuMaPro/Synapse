import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Materia } from '../services/materias'
import type { NeuronioRede, RedeApi, SinapseRede } from '../services/rede'
import { Rede } from './Rede'

const CALCULO: Materia = { id: 'calc', nome: 'Cálculo', cor: '#FF00AA', criada_em: '' }
const FISICA: Materia = { id: 'fis', nome: 'Física', cor: '#FFC857', criada_em: '' }

function neuronio(id: string, extra: Partial<NeuronioRede> = {}): NeuronioRede {
  return {
    id,
    tipo: 'piramidal',
    materia_id: null,
    cor: '#8B7BFF',
    criado_em: '2026-10-20T14:00:00-03:00',
    duracao_minutos: 25,
    vivo: true,
    ...extra,
  }
}

function sinapse(origem: string, destino: string): SinapseRede {
  return { id: `${origem}-${destino}`, origem_id: origem, destino_id: destino, peso: 1 }
}

// a (Cálculo) - b (sem matéria) - c (Cálculo), e d podado, sem sinapses.
const REDE: RedeApi = {
  neuronios: [
    neuronio('a', { materia_id: 'calc', tipo: 'granular', duracao_minutos: 20 }),
    neuronio('b', { criado_em: '2026-10-21T09:00:00-03:00' }),
    neuronio('c', {
      materia_id: 'calc',
      tipo: 'purkinje',
      duracao_minutos: 60,
      cor: '#FFC857',
      criado_em: '2026-10-22T10:00:00-03:00',
    }),
    neuronio('d', {
      vivo: false,
      cor: '#4A4F6E',
      duracao_minutos: 15,
      tipo: 'granular',
      criado_em: '2026-10-22T11:00:00-03:00',
    }),
  ],
  sinapses: [sinapse('a', 'b'), sinapse('a', 'c'), sinapse('b', 'c')],
}

interface Respostas {
  rede?: RedeApi | (() => RedeApi | Promise<never>)
  materias?: Materia[] | 'erro'
}

function simularApi({ rede = REDE, materias = [CALCULO, FISICA] }: Respostas = {}) {
  const pedidos: URL[] = []
  const fetchFalso = vi.fn(async (endereco: string | URL | Request) => {
    const url = new URL(String(endereco))
    pedidos.push(url)
    const json = (corpo: unknown, status = 200) =>
      new Response(JSON.stringify(corpo), {
        status,
        headers: { 'Content-Type': 'application/json' },
      })
    if (url.pathname === '/materias') {
      return materias === 'erro' ? json({ erro: 'x', mensagem: 'x' }, 500) : json(materias)
    }
    const corpo = typeof rede === 'function' ? await rede() : rede
    return json(corpo)
  })
  vi.stubGlobal('fetch', fetchFalso)
  return {
    pedidos,
    pedidosDaRede: () => pedidos.filter((u) => u.pathname === '/rede'),
  }
}

function renderizar() {
  const usuario = userEvent.setup()
  render(
    <MemoryRouter>
      <Rede />
    </MemoryRouter>,
  )
  return usuario
}

const grafo = () => screen.getByRole('img', { name: /Rede com/ })
const doNeuronio = (id: string) => grafo().querySelector(`[data-id="${id}"]`) as SVGGElement

/**
 * Toque no grafo. Usa só o evento de clique: o `mousedown` do user-event no jsdom vem
 * sem `view`, e o d3-zoom precisa dele para começar um arrasto (no navegador, vem).
 */
function tocar(elemento: Element) {
  fireEvent.click(elemento)
}

describe('tela da rede neural', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('mostra a rede com o resumo e a descrição para leitores de tela', async () => {
    simularApi()
    renderizar()

    expect(screen.getByRole('status')).toHaveTextContent('Carregando sua rede')
    expect(await screen.findByText('4 neurônios · 3 sinapses')).toBeInTheDocument()
    expect(grafo()).toHaveAccessibleName('Rede com 3 neurônios vivos, 1 podados e 3 sinapses')
    expect(grafo().querySelectorAll('.rede-neuronio')).toHaveLength(4)
    expect(grafo().querySelectorAll('.rede-sinapse')).toHaveLength(3)
    expect(screen.getByText('Toque num neurônio para acender suas conexões')).toBeInTheDocument()
  })

  it('desenha cada neurônio conforme o tipo, com a cor da matéria, e o podado em cinza', async () => {
    simularApi()
    renderizar()
    await screen.findByText('4 neurônios · 3 sinapses')

    const corpo = (id: string) => doNeuronio(id).querySelector('.rede-corpo')
    // Com matéria, a cor é a dela; sem matéria, a do tipo, que vem da API.
    expect(corpo('a')).toHaveAttribute('fill', '#FF00AA')
    expect(corpo('b')).toHaveAttribute('fill', '#8B7BFF')
    // O tamanho segue o tipo: granular < Purkinje.
    expect(Number(corpo('a')?.getAttribute('r'))).toBeLessThan(
      Number(doNeuronio('b').querySelector('.rede-corpo')?.getAttribute('r')),
    )
    expect(doNeuronio('a').querySelector('.rede-dendritos')).toBeInTheDocument()
    // Podado: só o contorno, sem corpo nem dendritos.
    expect(doNeuronio('d')).toHaveClass('podado')
    expect(doNeuronio('d').querySelector('.rede-contorno-podado')).toBeInTheDocument()
    expect(doNeuronio('d').querySelector('.rede-corpo, .rede-dendritos')).toBeNull()
  })

  it('começa com o neurônio mais recente aceso e a dica dele', async () => {
    simularApi()
    renderizar()
    await screen.findByText('4 neurônios · 3 sinapses')

    // O mais recente é o podado (d); o aceso é o último vivo (c).
    expect(doNeuronio('c')).toHaveClass('foco')
    expect(screen.getByText('Cálculo · 60 min')).toBeInTheDocument()
    expect(screen.getByText(/Purkinje · 22\/10/)).toBeInTheDocument()
  })

  it('critério: tocar num neurônio acende ele, as sinapses e propaga o brilho aos vizinhos', async () => {
    simularApi({
      rede: {
        // e - a - b - c, com b tocado: a e c vizinhos, e no segundo nível.
        neuronios: [...REDE.neuronios.slice(0, 3), neuronio('e')],
        sinapses: [sinapse('e', 'a'), sinapse('a', 'b'), sinapse('b', 'c')],
      },
    })
    renderizar()
    await screen.findByText(/4 neurônios/)

    tocar(doNeuronio('b'))

    expect(doNeuronio('b')).toHaveClass('foco')
    expect(doNeuronio('a')).toHaveClass('vizinho')
    expect(doNeuronio('c')).toHaveClass('vizinho')
    expect(doNeuronio('e')).toHaveClass('segundo')
    const sinapses = Object.fromEntries(
      [...grafo().querySelectorAll('.rede-sinapse')].map((l, i) => [i, l.getAttribute('class')]),
    )
    expect(sinapses).toEqual({
      0: 'rede-sinapse indireta',
      1: 'rede-sinapse direta',
      2: 'rede-sinapse direta',
    })
    expect(screen.getByText('Sem matéria · 25 min')).toBeInTheDocument()
  })

  it('passar o mouse acende o neurônio', async () => {
    simularApi()
    const usuario = renderizar()
    await screen.findByText('4 neurônios · 3 sinapses')

    await usuario.hover(doNeuronio('a'))

    expect(doNeuronio('a')).toHaveClass('foco')
    expect(screen.getByText('Cálculo · 20 min')).toBeInTheDocument()
  })

  it('a dica do podado diz que ele foi podado', async () => {
    simularApi()
    renderizar()
    await screen.findByText('4 neurônios · 3 sinapses')

    tocar(doNeuronio('d'))

    expect(screen.getByText(/Granular podado · 22\/10/)).toBeInTheDocument()
  })

  it('tocar no fundo apaga o realce e a dica', async () => {
    simularApi()
    renderizar()
    await screen.findByText('4 neurônios · 3 sinapses')

    tocar(grafo())

    expect(grafo().querySelector('.foco')).toBeNull()
    expect(screen.queryByText(/ min$/)).not.toBeInTheDocument()
  })

  it('filtra por matéria, com os chips das matérias do estudante', async () => {
    const api = simularApi()
    const usuario = renderizar()
    await screen.findByText('4 neurônios · 3 sinapses')
    const materias = screen.getByRole('group', { name: 'Matéria' })
    expect(within(materias).getByRole('button', { name: 'Tudo' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )

    await usuario.click(within(materias).getByRole('button', { name: 'Física' }))

    await waitFor(() => expect(api.pedidosDaRede().at(-1)?.searchParams.get('materia')).toBe('fis'))
    expect(within(materias).getByRole('button', { name: 'Física' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })

  it('filtra por período a partir da meia-noite local', async () => {
    const api = simularApi()
    const usuario = renderizar()
    await screen.findByText('4 neurônios · 3 sinapses')

    await usuario.click(screen.getByRole('button', { name: '7 dias' }))

    await waitFor(() => expect(api.pedidosDaRede()).toHaveLength(2))
    const de = new Date(api.pedidosDaRede()[1].searchParams.get('de')!)
    expect([de.getHours(), de.getMinutes()]).toEqual([0, 0])
    const dias = (Date.now() - de.getTime()) / 86_400_000
    expect(dias).toBeGreaterThan(6)
    expect(dias).toBeLessThan(7)
  })

  it('estado vazio: convida a focar para criar o primeiro neurônio', async () => {
    simularApi({ rede: { neuronios: [], sinapses: [] } })
    renderizar()

    expect(
      await screen.findByRole('heading', { name: 'Seu primeiro neurônio está esperando' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Começar a focar' })).toHaveAttribute('href', '/foco')
    expect(screen.queryByRole('img', { name: /Rede com/ })).not.toBeInTheDocument()
  })

  it('filtro sem neurônios oferece voltar para a rede toda', async () => {
    let chamadas = 0
    simularApi({ rede: () => (chamadas++ === 1 ? { neuronios: [], sinapses: [] } : REDE) })
    const usuario = renderizar()
    await screen.findByText('4 neurônios · 3 sinapses')

    await usuario.click(screen.getByRole('button', { name: '30 dias' }))
    expect(await screen.findByText('Nenhum neurônio neste filtro.')).toBeInTheDocument()

    await usuario.click(screen.getByRole('button', { name: 'Ver a rede toda' }))
    expect(await screen.findByText('4 neurônios · 3 sinapses')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sempre' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('sem conexão, avisa e deixa tentar de novo', async () => {
    let falhar = true
    simularApi({
      rede: () => {
        if (falhar) return Promise.reject(new TypeError('Failed to fetch'))
        return REDE
      },
    })
    const usuario = renderizar()

    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível carregar sua rede')
    falhar = false
    await usuario.click(screen.getByRole('button', { name: 'Tentar de novo' }))

    expect(await screen.findByText('4 neurônios · 3 sinapses')).toBeInTheDocument()
  })

  it('se as matérias não carregarem, a rede aparece com as cores dos tipos', async () => {
    simularApi({ materias: 'erro' })
    renderizar()

    await screen.findByText('4 neurônios · 3 sinapses')
    expect(screen.queryByRole('group', { name: 'Matéria' })).not.toBeInTheDocument()
    expect(doNeuronio('c').querySelector('.rede-corpo')).toHaveAttribute('fill', '#FFC857')
    expect(screen.getByText('Sem matéria · 60 min')).toBeInTheDocument()
  })
})
