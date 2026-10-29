import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { conquistasApi, type ConquistasRespostaApi } from '../services/conquistas'
import { Conquistas } from './Conquistas'

function renderizar() {
  const usuario = userEvent.setup()
  render(
    <MemoryRouter>
      <Conquistas />
    </MemoryRouter>,
  )
  return usuario
}

describe('tela de conquistas (Conquistas)', () => {
  const dadosExemplo: ConquistasRespostaApi = {
    sequencia: { atual: 3, recorde: 7 },
    desbloqueadas: 1,
    total: 2,
    conquistas: [
      {
        codigo: 'primeiro_neuronio',
        nome: 'Primeiro neurônio',
        descricao: 'Conclua sua primeira sessão de foco.',
        desbloqueada: true,
        desbloqueada_em: '2026-10-20T14:25:00+00:00',
        progresso: 1,
        meta: 1,
        unidade: 'neurônios',
      },
      {
        codigo: 'horas_focadas_10',
        nome: '10 horas focadas',
        descricao: 'Acumule 10 horas de foco.',
        desbloqueada: false,
        desbloqueada_em: null,
        progresso: 120,
        meta: 600,
        unidade: 'minutos',
      },
    ],
  }

  beforeEach(() => {
    vi.spyOn(conquistasApi, 'consultar').mockResolvedValue(dadosExemplo)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('exibe o cabeçalho com contagem e sequência de dias', async () => {
    renderizar()

    expect(screen.getByRole('heading', { name: 'Conquistas' })).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('1 de 2 desbloqueadas')).toBeInTheDocument()
      expect(screen.getByText('3 dias seguidos')).toBeInTheDocument()
      expect(screen.getByText(/Recorde: 7 dias/)).toBeInTheDocument()
    })
  })

  it('exibe conquistas desbloqueadas com selo e data', async () => {
    renderizar()

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Primeiro neurônio' })).toBeInTheDocument()
    })

    const cartao = screen.getByRole('heading', { name: 'Primeiro neurônio' }).closest('li')!
    expect(cartao).toHaveClass('desbloqueada')
    expect(within(cartao).getByText('Desbloqueada')).toBeInTheDocument()
    expect(within(cartao).getByText('Conclua sua primeira sessão de foco.')).toBeInTheDocument()
    expect(within(cartao).getByText(/Desbloqueada em \d{2}\/\d{2}\/\d{4}/)).toBeInTheDocument()
  })

  it('exibe conquistas bloqueadas em cinza com dica e barra de progresso', async () => {
    renderizar()

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: '10 horas focadas' })).toBeInTheDocument()
    })

    const cartao = screen.getByRole('heading', { name: '10 horas focadas' }).closest('li')!
    expect(cartao).toHaveClass('bloqueada')
    expect(within(cartao).getByText('Acumule 10 horas de foco.')).toBeInTheDocument()
    expect(within(cartao).getByText('120 / 600 minutos')).toBeInTheDocument()

    const barra = within(cartao).getByRole('progressbar', {
      name: 'Progresso da conquista 10 horas focadas',
    })
    expect(barra).toHaveAttribute('aria-valuenow', '120')
    expect(barra).toHaveAttribute('aria-valuemax', '600')
  })

  it('mostra mensagem de erro e permite tentar novamente', async () => {
    vi.spyOn(conquistasApi, 'consultar').mockRejectedValueOnce(new Error('Erro de conexão'))

    const usuario = renderizar()

    await waitFor(() => {
      expect(screen.getByText('Não foi possível carregar as conquistas.')).toBeInTheDocument()
    })

    const botaoTentar = screen.getByRole('button', { name: 'Tentar de novo' })
    await usuario.click(botaoTentar)

    await waitFor(() => {
      expect(screen.getByText('Primeiro neurônio')).toBeInTheDocument()
    })
  })
})
