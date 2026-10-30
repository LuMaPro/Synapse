import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { EstatisticasApi } from '../services/estatisticas'
import { Estatisticas } from './Estatisticas'

const SEMANA: EstatisticasApi = {
  periodo: 'semana',
  inicio: '2026-10-24',
  fim: '2026-10-30',
  tempo_total_minutos: 115,
  sessoes_concluidas: 4,
  sessoes_podadas: 1,
  total_sessoes: 5,
  taxa_sucesso: 0.8,
  melhor_horario: 20,
  por_dia: [
    { data: '2026-10-29', minutos: 0, por_materia: [] },
    { data: '2026-10-30', minutos: 115, por_materia: [] },
  ],
  por_materia: [
    {
      materia_id: 'calc',
      nome: 'Cálculo',
      cor: '#8B7BFF',
      efeito: null,
      minutos: 75,
      percentual: 0.6522,
    },
    {
      materia_id: 'fis',
      nome: 'Física',
      cor: '#3EE6E0',
      efeito: 'aurora',
      minutos: 30,
      percentual: 0.2609,
    },
    {
      materia_id: null,
      nome: null,
      cor: null,
      efeito: null,
      minutos: 10,
      percentual: 0.087,
    },
  ],
}

const VAZIO: EstatisticasApi = {
  ...SEMANA,
  periodo: 'dia',
  tempo_total_minutos: 0,
  sessoes_concluidas: 0,
  sessoes_podadas: 0,
  total_sessoes: 0,
  taxa_sucesso: 0,
  melhor_horario: null,
  por_dia: [{ data: '2026-10-30', minutos: 0, por_materia: [] }],
  por_materia: [],
}

interface Opcoes {
  /** Resposta de cada período; `'erro'` simula a falta de rede. */
  periodos?: Partial<Record<EstatisticasApi['periodo'], EstatisticasApi | 'erro'>>
  sequencia?: number | 'erro'
}

/** API falsa: as estatísticas por período e a sequência, que vem das conquistas. */
function simularApi({ periodos = { semana: SEMANA }, sequencia = 3 }: Opcoes = {}) {
  const pedidos: URL[] = []
  const json = (corpo: unknown, status = 200) =>
    new Response(JSON.stringify(corpo), {
      status,
      headers: { 'Content-Type': 'application/json' },
    })
  vi.stubGlobal(
    'fetch',
    vi.fn(async (endereco: string | URL | Request) => {
      const url = new URL(String(endereco))
      pedidos.push(url)
      if (url.pathname === '/conquistas') {
        if (sequencia === 'erro') throw new TypeError('Failed to fetch')
        return json({
          sequencia: { atual: sequencia, recorde: sequencia },
          desbloqueadas: 0,
          total: 0,
          conquistas: [],
        })
      }
      const resposta = periodos[url.searchParams.get('periodo') as EstatisticasApi['periodo']]
      if (!resposta || resposta === 'erro') throw new TypeError('Failed to fetch')
      return json(resposta)
    }),
  )
  return {
    pedidosDePeriodo: () =>
      pedidos
        .filter((u) => u.pathname === '/estatisticas')
        .map((u) => u.searchParams.get('periodo')),
  }
}

function renderizar() {
  const usuario = userEvent.setup()
  render(
    <MemoryRouter>
      <Estatisticas />
    </MemoryRouter>,
  )
  return usuario
}

const destaque = (rotulo: string) => screen.getByText(rotulo).nextElementSibling

describe('tela de estatísticas', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('critério: mostra o total de horas, a taxa de sucesso e a sequência atual', async () => {
    simularApi()
    renderizar()

    expect(await screen.findByText('Tempo focado')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1, name: 'Estatísticas' })).toBeInTheDocument()
    expect(destaque('Tempo focado')).toHaveTextContent('1,9 h')
    expect(destaque('Taxa de sucesso')).toHaveTextContent('80%')
    await waitFor(() => expect(destaque('Sequência atual')).toHaveTextContent('3 dias'))
    expect(destaque('Melhor horário')).toHaveTextContent('20h')
  })

  it('critério: o seletor de período troca os dados', async () => {
    const api = simularApi({ periodos: { semana: SEMANA, dia: VAZIO } })
    const usuario = renderizar()
    await screen.findByText('Tempo focado')
    expect(screen.getByRole('button', { name: '7 dias' })).toHaveAttribute('aria-pressed', 'true')

    await usuario.click(screen.getByRole('button', { name: 'Hoje' }))

    expect(screen.getByRole('button', { name: 'Hoje' })).toHaveAttribute('aria-pressed', 'true')
    await waitFor(() => expect(destaque('Tempo focado')).toHaveTextContent('0 min'))
    expect(destaque('Melhor horário')).toHaveTextContent('—')
    expect(api.pedidosDePeriodo()).toEqual(['semana', 'dia'])
  })

  it('critério: o tempo por matéria tem a cor de cada matéria e as sem matéria juntas', async () => {
    simularApi()
    renderizar()

    const legenda = await screen.findByRole('list')
    const itens = within(legenda).getAllByRole('listitem')
    expect(itens.map((item) => item.textContent)).toEqual([
      'Cálculo1,3 h · 65%',
      'Física30 min · 26%',
      'Sem matéria10 min · 9%',
    ])
    const amostra = (indice: number) => itens[indice].querySelector('.amostra') as HTMLElement
    expect(amostra(0)).toHaveStyle({ background: '#8B7BFF' })
    // A cor com efeito da loja (#34) anima a amostra, como no resto do app.
    expect(amostra(1)).toHaveClass('efeito-aurora')
    // Sem matéria, uma cor neutra, que não se confunde com nenhuma matéria.
    expect(amostra(2)).toHaveStyle({ background: '#6b7097' })
  })

  it('período sem sessões convida a começar a focar', async () => {
    simularApi({ periodos: { semana: { ...VAZIO, periodo: 'semana' } } })
    renderizar()

    expect(await screen.findByText('Nenhuma sessão concluída neste período.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Começar a focar' })).toHaveAttribute('href', '/foco')
  })

  it('sem conexão, avisa e permite tentar de novo', async () => {
    const periodos: Opcoes['periodos'] = { semana: 'erro' }
    simularApi({ periodos })
    const usuario = renderizar()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Não foi possível carregar suas estatísticas',
    )
    periodos.semana = SEMANA
    await usuario.click(screen.getByRole('button', { name: 'Tentar de novo' }))

    expect(await screen.findByText('Tempo focado')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('sem a sequência, o resto da tela aparece mesmo assim', async () => {
    simularApi({ sequencia: 'erro' })
    renderizar()

    expect(await screen.findByText('Tempo focado')).toBeInTheDocument()
    expect(destaque('Sequência atual')).toHaveTextContent('—')
    expect(destaque('Tempo focado')).toHaveTextContent('1,9 h')
  })
})
