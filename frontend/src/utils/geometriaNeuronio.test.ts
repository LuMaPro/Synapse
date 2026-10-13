import { describe, expect, it } from 'vitest'
import { desenharNeuronio, PROGRESSO_PODADO } from './geometriaNeuronio'
import type { TipoNeuronio } from './neuronio'

const TIPOS: TipoNeuronio[] = ['granular', 'piramidal', 'purkinje']

const crescidos = (desenho: ReturnType<typeof desenharNeuronio>) =>
  desenho.dendritos.filter((d) => d.crescimento > 0).length

describe('desenharNeuronio', () => {
  it('gera sempre o mesmo desenho para o mesmo tipo', () => {
    expect(desenharNeuronio('piramidal', 0.5)).toEqual(desenharNeuronio('piramidal', 0.5))
  })

  it.each([
    ['granular', 12],
    ['piramidal', 22],
    ['purkinje', 62],
  ] as const)('o tipo %s tem %i ramos de dendritos', (tipo, quantidade) => {
    expect(desenharNeuronio(tipo, 1).dendritos).toHaveLength(quantidade)
  })

  it.each(TIPOS)('%s: no início só aparece o corpo celular, ainda pequeno', (tipo) => {
    const desenho = desenharNeuronio(tipo, 0)

    expect(crescidos(desenho)).toBe(0)
    expect(desenho.axonio.crescimento).toBe(0)
    expect(desenho.corpo.escala).toBeCloseTo(0.4)
  })

  it.each(TIPOS)('%s: o corpo celular termina de crescer antes dos dendritos', (tipo) => {
    const desenho = desenharNeuronio(tipo, 0.12)

    expect(desenho.corpo.escala).toBe(1)
    expect(crescidos(desenho)).toBe(0)
  })

  it('os dendritos se ramificam conforme o progresso', () => {
    const contagens = [0.2, 0.4, 0.6, 0.78].map((p) => crescidos(desenharNeuronio('piramidal', p)))

    for (let i = 1; i < contagens.length; i++) {
      expect(contagens[i]).toBeGreaterThan(contagens[i - 1])
    }
  })

  it('o axônio só aparece no final, a partir de 80%', () => {
    expect(desenharNeuronio('piramidal', 0.79).axonio.crescimento).toBe(0)
    expect(desenharNeuronio('piramidal', 0.9).axonio.crescimento).toBeCloseTo(0.5)
    expect(desenharNeuronio('piramidal', 1).axonio.crescimento).toBe(1)
  })

  it.each(TIPOS)('%s: completo, com todos os ramos, pontas e axônio', (tipo) => {
    const desenho = desenharNeuronio(tipo, 1)

    expect(desenho.dendritos.every((d) => d.crescimento === 1)).toBe(true)
    expect(desenho.dendritos.filter((d) => d.ponta).every((d) => d.ponta!.visivel)).toBe(true)
    expect(desenho.axonio.terminal.visivel).toBe(true)
  })

  it('podado, recolhe até 42%: perde axônio, pontas e ramos finos', () => {
    const vivo = desenharNeuronio('piramidal', 1)
    const podado = desenharNeuronio('piramidal', 1, true)

    expect(podado.progresso).toBe(PROGRESSO_PODADO)
    expect(podado.axonio.crescimento).toBe(0)
    expect(podado.axonio.terminal.visivel).toBe(false)
    expect(podado.dendritos.some((d) => d.ponta?.visivel)).toBe(false)
    expect(crescidos(podado)).toBeLessThan(crescidos(vivo))
    expect(podado.corpo.escala).toBe(1)
  })

  it('podado cedo, não cresce além do que já tinha', () => {
    expect(desenharNeuronio('granular', 0.2, true)).toEqual(desenharNeuronio('granular', 0.2))
  })

  it('limita o progresso entre 0 e 1', () => {
    expect(desenharNeuronio('purkinje', 1.5)).toEqual(desenharNeuronio('purkinje', 1))
    expect(desenharNeuronio('purkinje', -1)).toEqual(desenharNeuronio('purkinje', 0))
  })
})
