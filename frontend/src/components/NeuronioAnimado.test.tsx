import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { NeuronioAnimado } from './NeuronioAnimado'

describe('NeuronioAnimado', () => {
  it('descreve o tipo e o quanto já cresceu', () => {
    render(<NeuronioAnimado tipo="piramidal" progresso={0.55} />)

    expect(screen.getByRole('img', { name: 'Neurônio Piramidal, 55% formado' })).toBeInTheDocument()
  })

  it('desenha os traços proporcionais ao progresso', () => {
    const { container, rerender } = render(<NeuronioAnimado tipo="granular" progresso={0} />)
    const desenhados = () =>
      [...container.querySelectorAll<SVGPathElement>('path.neuronio-traco')].filter(
        (traco) => Number(traco.style.strokeDashoffset) < 1,
      ).length

    expect(desenhados()).toBe(0)
    rerender(<NeuronioAnimado tipo="granular" progresso={1} />)
    expect(desenhados()).toBe(13) // 12 dendritos + o axônio
  })

  it('a poda acontece depois do primeiro quadro, para a retração ser animada', async () => {
    render(<NeuronioAnimado tipo="piramidal" progresso={0.9} podado />)
    const svg = screen.getByRole('img', { name: 'Neurônio Piramidal podado' })

    expect(svg).not.toHaveClass('neuronio-podado')
    await waitFor(() => expect(svg).toHaveClass('neuronio-podado'))
  })

  it('o brilho forte também entra depois do primeiro quadro', async () => {
    render(<NeuronioAnimado tipo="purkinje" progresso={1} brilho="forte" />)
    const svg = screen.getByRole('img')

    expect(svg).not.toHaveClass('neuronio-brilho-forte')
    await waitFor(() => expect(svg).toHaveClass('neuronio-brilho-forte'))
  })

  const corDoNeuronio = () => screen.getByRole('img').style.getPropertyValue('--cor-neuronio')

  it.each([
    ['granular', 'var(--cor-impulso)'],
    ['piramidal', 'var(--cor-destaque)'],
    ['purkinje', 'var(--cor-atp)'],
  ] as const)('sem matéria, o neurônio %s usa a cor padrão do tipo', (tipo, cor) => {
    render(<NeuronioAnimado tipo={tipo} progresso={1} />)

    expect(corDoNeuronio()).toBe(cor)
  })

  it('a cor da matéria substitui a cor padrão do tipo', () => {
    render(<NeuronioAnimado tipo="granular" progresso={1} cor="#ff6fb5" />)

    expect(corDoNeuronio()).toBe('#ff6fb5')
  })

  it('podado, deixa o CSS aplicar o cinza, mesmo com cor de matéria', async () => {
    render(<NeuronioAnimado tipo="purkinje" progresso={1} cor="#ff6fb5" podado />)

    await waitFor(() => expect(screen.getByRole('img')).toHaveClass('neuronio-podado'))
    expect(corDoNeuronio()).toBe('')
  })

  it('a cor com efeito da loja anima o neurônio (issue #34)', () => {
    const { container, rerender } = render(
      <NeuronioAnimado tipo="piramidal" progresso={1} cor="#A8C8FF" efeito="tempestade" />,
    )
    const svg = screen.getByRole('img')

    expect(svg).toHaveClass('com-efeito', 'efeito-tempestade')
    expect(container.querySelectorAll('.neuronio-raio')).toHaveLength(5)
    expect(container.querySelector('.neuronio-orbita')).toBeNull()

    rerender(<NeuronioAnimado tipo="piramidal" progresso={1} cor="#B69CFF" efeito="galaxia" />)
    expect(svg).toHaveClass('efeito-galaxia')
    expect(container.querySelectorAll('.neuronio-orbita circle')).toHaveLength(6)
    expect(container.querySelector('.neuronio-raio')).toBeNull()

    rerender(<NeuronioAnimado tipo="piramidal" progresso={1} cor="#FF7AD9" efeito="arco_iris" />)
    expect(svg).toHaveClass('efeito-arco_iris')
    expect(container.querySelector('.neuronio-orbita, .neuronio-raio')).toBeNull()
  })

  it('o neurônio podado não tem efeito', () => {
    const { container } = render(
      <NeuronioAnimado tipo="piramidal" progresso={1} cor="#A8C8FF" efeito="tempestade" podado />,
    )

    expect(screen.getByRole('img')).not.toHaveClass('com-efeito')
    expect(container.querySelector('.neuronio-raio')).toBeNull()
  })

  it('o tamanho controla a largura e a altura', () => {
    render(<NeuronioAnimado tipo="granular" progresso={1} tamanho={120} />)

    expect(screen.getByRole('img')).toHaveAttribute('width', '120')
    expect(screen.getByRole('img')).toHaveAttribute('height', '120')
  })
})
