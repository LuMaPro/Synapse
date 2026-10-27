import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Materia } from '../services/materias'
import type { SessaoApi } from '../services/sessoes'
import { Historico, TAMANHO_PAGINA } from './Historico'

const CALCULO: Materia = { id: 'calc', nome: 'Cálculo', cor: '#FF00AA', criada_em: '' }

// Datas no fuso do navegador, como a tela agrupa: o teste vale em qualquer fuso.
const AGORA = new Date(2026, 9, 26, 15, 0)
const MINUTO = 60_000

function sessao(id: string, inicio: Date, extra: Partial<SessaoApi> = {}): SessaoApi {
  const duracao = extra.duracao_minutos ?? 25
  const fim = new Date(inicio.getTime() + duracao * MINUTO).toISOString()
  return {
    id,
    duracao_minutos: duracao,
    modo: 'estrito',
    materia_id: null,
    estado: 'concluida',
    inicio: inicio.toISOString(),
    fim_previsto: fim,
    encerrada_em: fim,
    restante_segundos: 0,
    tempo_fora_segundos: 0,
    ...extra,
  }
}

const HOJE_14H = new Date(2026, 9, 26, 14, 0)
// Da mais recente para a mais antiga, como a API manda.
const SESSOES: SessaoApi[] = [
  sessao('andamento', HOJE_14H, {
    duracao_minutos: 60,
    estado: 'em_andamento',
    encerrada_em: null,
    restante_segundos: 1800,
  }),
  sessao('podada', new Date(2026, 9, 26, 9, 5), {
    duracao_minutos: 15,
    estado: 'podada',
    encerrada_em: new Date(new Date(2026, 9, 26, 9, 5).getTime() + 3 * MINUTO).toISOString(),
  }),
  sessao('calculo', new Date(2026, 9, 25, 20, 30), { materia_id: 'calc' }),
  sessao('antiga', new Date(2026, 8, 1, 10, 0), { duracao_minutos: 10 }),
]

interface Opcoes {
  sessoes?: SessaoApi[]
  materias?: Materia[] | 'erro'
  /** Falha (sem rede) o pedido desta página do histórico. */
  falharPagina?: () => number | null
}

/** API falsa: filtra e pagina como o `GET /sessoes` do backend. */
function simularApi({ sessoes = SESSOES, materias = [CALCULO], falharPagina }: Opcoes = {}) {
  const pedidos: URL[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (endereco: string | URL | Request) => {
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
      const filtros = url.searchParams
      const pagina = Number(filtros.get('pagina') ?? 1)
      const tamanho = Number(filtros.get('tamanho') ?? 20)
      if (falharPagina?.() === pagina) throw new TypeError('Failed to fetch')
      const de = filtros.get('de')
      const filtradas = sessoes.filter(
        (s) =>
          (!filtros.get('status') || s.estado === filtros.get('status')) &&
          (!de || Date.parse(s.inicio) >= Date.parse(de)),
      )
      return json({
        total: filtradas.length,
        pagina,
        tamanho,
        paginas: Math.max(1, Math.ceil(filtradas.length / tamanho)),
        resultados: filtradas.slice((pagina - 1) * tamanho, pagina * tamanho),
      })
    }),
  )
  return { pedidosDoHistorico: () => pedidos.filter((u) => u.pathname === '/sessoes') }
}

function renderizar() {
  const usuario = userEvent.setup()
  render(
    <MemoryRouter>
      <Historico />
    </MemoryRouter>,
  )
  return usuario
}

const itens = () => screen.queryAllByRole('listitem')
const dia = (rotulo: string | RegExp) => screen.getByRole('region', { name: rotulo })

describe('tela do histórico', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(AGORA)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('critério: lista as sessões com data, duração, matéria e resultado', async () => {
    simularApi()
    renderizar()

    expect(screen.getByRole('status')).toHaveTextContent('Carregando seu histórico')
    expect(await screen.findByText('4 sessões')).toBeInTheDocument()

    const hoje = within(dia('Hoje')).getAllByRole('listitem')
    expect(hoje.map((item) => item.textContent)).toEqual([
      'Sem matéria14:00 · 60 min · PurkinjeEm andamento',
      'Sem matéria09:05 · 15 min · GranularPodada aos 03:00',
    ])
    expect(within(dia('Ontem')).getByRole('listitem')).toHaveTextContent(
      'Cálculo20:30 · 25 min · PiramidalConcluída',
    )
    // Dias mais antigos aparecem com a data.
    expect(within(dia(/1 de set/)).getByRole('listitem')).toHaveTextContent('10 min')
    expect(within(hoje[0]).getByText('14:00')).toHaveAttribute('dateTime', HOJE_14H.toISOString())
  })

  it('pinta cada sessão com a cor da matéria, a do tipo sem matéria, e a podada de cinza', async () => {
    simularApi()
    renderizar()
    await screen.findByText('4 sessões')

    const cor = (item: HTMLElement) => (item.querySelector('.sessao-cor') as HTMLElement).style
    const [andamento, podada, calculo] = itens()
    expect(cor(calculo).background).toBe('rgb(255, 0, 170)')
    expect(cor(andamento).background).toBe('var(--cor-atp)')
    expect(cor(podada).background).toBe('var(--cor-podado)')
    expect(podada).toHaveClass('podada')
  })

  it('a bolinha da sessão anima com a cor de efeito da matéria (issue #34)', async () => {
    simularApi({ materias: [{ ...CALCULO, cor: '#5BFFB0', efeito: 'aurora' }] })
    renderizar()
    await screen.findByText('4 sessões')

    const bolinha = (item: HTMLElement) => item.querySelector('.sessao-cor') as HTMLElement
    const [andamento, , calculo] = itens()
    expect(bolinha(calculo)).toHaveClass('com-efeito', 'efeito-aurora')
    expect(bolinha(calculo)).toHaveStyle({ '--cor-neuronio': '#5BFFB0' })
    // Sem matéria: a cor padrão do tipo, sem efeito.
    expect(bolinha(andamento)).not.toHaveClass('com-efeito')
  })

  it('filtra pelo resultado e pelo período', async () => {
    const api = simularApi()
    const usuario = renderizar()
    await screen.findByText('4 sessões')

    await usuario.click(screen.getByRole('button', { name: 'Podadas' }))
    await waitFor(() => expect(itens()).toHaveLength(1))
    expect(itens()[0]).toHaveTextContent('Podada aos 03:00')
    expect(api.pedidosDoHistorico().at(-1)?.searchParams.get('status')).toBe('podada')
    expect(screen.getByRole('button', { name: 'Podadas' })).toHaveAttribute('aria-pressed', 'true')

    await usuario.click(screen.getByRole('button', { name: 'Todas' }))
    await usuario.click(screen.getByRole('button', { name: '7 dias' }))
    await waitFor(() => expect(itens()).toHaveLength(3))
    const pedido = api.pedidosDoHistorico().at(-1)!
    expect(pedido.searchParams.get('status')).toBeNull()
    // Desde a meia-noite de 6 dias atrás, no fuso do navegador.
    expect(pedido.searchParams.get('de')).toBe(new Date(2026, 9, 20).toISOString())
    expect(pedido.searchParams.get('tamanho')).toBe(String(TAMANHO_PAGINA))
  })

  it('critério: carrega as páginas seguintes ao pedir mais', async () => {
    const muitas = Array.from({ length: TAMANHO_PAGINA * 2 + 5 }, (_, i) =>
      sessao(`s${i}`, new Date(AGORA.getTime() - (i + 1) * 60 * MINUTO)),
    )
    const api = simularApi({ sessoes: muitas })
    const usuario = renderizar()

    expect(await screen.findByText('45 sessões')).toBeInTheDocument()
    expect(itens()).toHaveLength(TAMANHO_PAGINA)

    await usuario.click(screen.getByRole('button', { name: 'Carregar mais' }))
    await waitFor(() => expect(itens()).toHaveLength(TAMANHO_PAGINA * 2))
    await usuario.click(screen.getByRole('button', { name: 'Carregar mais' }))
    await waitFor(() => expect(itens()).toHaveLength(45))

    expect(screen.queryByRole('button', { name: 'Carregar mais' })).not.toBeInTheDocument()
    expect(api.pedidosDoHistorico().map((u) => u.searchParams.get('pagina'))).toEqual([
      null,
      '2',
      '3',
    ])
  })

  it('não repete a sessão que uma nova empurrou para a página seguinte', async () => {
    const muitas = Array.from({ length: TAMANHO_PAGINA + 1 }, (_, i) =>
      sessao(`s${i}`, new Date(AGORA.getTime() - (i + 1) * 60 * MINUTO)),
    )
    simularApi({ sessoes: muitas })
    const usuario = renderizar()
    await screen.findByText('21 sessões')

    // Uma sessão nova chega antes da segunda página: a última da primeira desce.
    muitas.unshift(sessao('nova', AGORA))
    await usuario.click(screen.getByRole('button', { name: 'Carregar mais' }))

    await waitFor(() => expect(screen.getByText('22 sessões')).toBeInTheDocument())
    expect(itens()).toHaveLength(21)
  })

  it('sem nenhuma sessão, convida a começar a focar', async () => {
    simularApi({ sessoes: [] })
    renderizar()

    expect(
      await screen.findByText('Você ainda não fez nenhuma sessão de foco.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Começar a focar' })).toHaveAttribute('href', '/foco')
  })

  it('num filtro sem sessões, deixa voltar a ver todas', async () => {
    simularApi({ sessoes: SESSOES.filter((s) => s.estado !== 'podada') })
    const usuario = renderizar()
    await screen.findByText('3 sessões')

    await usuario.click(screen.getByRole('button', { name: 'Podadas' }))
    expect(await screen.findByText('Nenhuma sessão neste filtro.')).toBeInTheDocument()
    await usuario.click(screen.getByRole('button', { name: 'Ver todas as sessões' }))

    await waitFor(() => expect(itens()).toHaveLength(3))
    expect(screen.getByRole('button', { name: 'Todas' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('sem conexão, avisa e deixa tentar de novo', async () => {
    let falhar = true
    simularApi({ falharPagina: () => (falhar ? 1 : null) })
    const usuario = renderizar()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Não foi possível carregar seu histórico',
    )
    falhar = false
    await usuario.click(screen.getByRole('button', { name: 'Tentar de novo' }))

    expect(await screen.findByText('4 sessões')).toBeInTheDocument()
  })

  it('se a página seguinte falhar, avisa e mantém as que já vieram', async () => {
    const muitas = Array.from({ length: TAMANHO_PAGINA + 3 }, (_, i) =>
      sessao(`s${i}`, new Date(AGORA.getTime() - (i + 1) * 60 * MINUTO)),
    )
    let falhar = true
    simularApi({ sessoes: muitas, falharPagina: () => (falhar ? 2 : null) })
    const usuario = renderizar()
    await screen.findByText('23 sessões')

    await usuario.click(screen.getByRole('button', { name: 'Carregar mais' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Não foi possível carregar mais sessões.',
    )
    expect(itens()).toHaveLength(TAMANHO_PAGINA)

    falhar = false
    await usuario.click(screen.getByRole('button', { name: 'Carregar mais' }))
    await waitFor(() => expect(itens()).toHaveLength(23))
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('se as matérias não carregarem, o histórico aparece mesmo assim', async () => {
    simularApi({ materias: 'erro' })
    renderizar()

    await screen.findByText('4 sessões')
    expect(within(dia('Ontem')).getByRole('listitem')).toHaveTextContent('Sem matéria')
  })
})
