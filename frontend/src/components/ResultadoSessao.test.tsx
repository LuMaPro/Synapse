import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import { ResultadoSessao } from './ResultadoSessao'

describe('ResultadoSessao', () => {
  it('renderiza o resultado de sucesso com neurônio e ATP ganho', async () => {
    const onFocarDeNovo = vi.fn()
    render(
      <MemoryRouter>
        <ResultadoSessao
          sucesso={true}
          duracaoMin={25}
          motivoPoda={null}
          decorridoMs={25 * 60_000}
          progresso={1}
          atp={25}
          nomeMateria="Cálculo"
          onFocarDeNovo={onFocarDeNovo}
        />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: 'Neurônio formado!' })).toBeInTheDocument()
    expect(screen.getByText('Piramidal · 25 min · Cálculo')).toBeInTheDocument()
    expect(screen.getByText('+25 ATP')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ver na minha rede' })).toHaveAttribute('href', '/rede')
    expect(screen.queryByRole('status', { name: /Conquista desbloqueada/ })).not.toBeInTheDocument()

    const usuario = userEvent.setup()
    await usuario.click(screen.getByRole('button', { name: 'Focar de novo' }))
    expect(onFocarDeNovo).toHaveBeenCalledTimes(1)
  })

  it('renderiza toasts para cada conquista recém-desbloqueada', () => {
    const conquistasNovas = [
      { codigo: 'primeira_sessao', nome: 'Primeiro neurônio' },
      { codigo: 'sete_dias', nome: 'Constância neural' },
    ]

    render(
      <MemoryRouter>
        <ResultadoSessao
          sucesso={true}
          duracaoMin={45}
          motivoPoda={null}
          decorridoMs={45 * 60_000}
          progresso={1}
          atp={45}
          conquistasNovas={conquistasNovas}
          onFocarDeNovo={vi.fn()}
        />
      </MemoryRouter>,
    )

    const toasts = screen.getAllByRole('status', { name: /Conquista desbloqueada/ })
    expect(toasts).toHaveLength(2)
    expect(screen.getByText('Primeiro neurônio')).toBeInTheDocument()
    expect(screen.getByText('Constância neural')).toBeInTheDocument()
    expect(screen.getAllByText('Conquista desbloqueada')).toHaveLength(2)
  })

  it('renderiza o resultado de poda sináptica por desistência', async () => {
    const onFocarDeNovo = vi.fn()
    render(
      <MemoryRouter>
        <ResultadoSessao
          sucesso={false}
          duracaoMin={30}
          motivoPoda="desistiu"
          decorridoMs={10 * 60_000}
          progresso={0.33}
          onFocarDeNovo={onFocarDeNovo}
        />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: 'A conexão se perdeu' })).toBeInTheDocument()
    expect(screen.getByText(/Você desistiu aos/)).toHaveTextContent('Você desistiu aos 10:00.')
    expect(screen.getByRole('link', { name: 'Ver histórico' })).toHaveAttribute(
      'href',
      '/historico',
    )
    expect(screen.queryByRole('status', { name: /Conquista desbloqueada/ })).not.toBeInTheDocument()

    const usuario = userEvent.setup()
    await usuario.click(screen.getByRole('button', { name: 'Tentar de novo' }))
    expect(onFocarDeNovo).toHaveBeenCalledTimes(1)
  })

  it('renderiza o resultado de poda sináptica por saída da tela', () => {
    render(
      <MemoryRouter>
        <ResultadoSessao
          sucesso={false}
          duracaoMin={25}
          motivoPoda="saiu"
          decorridoMs={5 * 60_000}
          progresso={0.2}
          onFocarDeNovo={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(screen.getByText(/Você saiu da tela aos/)).toHaveTextContent(
      'Você saiu da tela aos 05:00.',
    )
  })
})
