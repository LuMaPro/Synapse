import { describe, expect, it } from 'vitest'
import { formatarHoras, formatarTempo } from './tempo'

describe('formatarTempo', () => {
  it.each([
    [25 * 60_000, '25:00'],
    [120 * 60_000, '120:00'],
    [61_000, '01:01'],
    [9_000, '00:09'],
    [0, '00:00'],
  ])('formata %i ms como %s', (ms, esperado) => {
    expect(formatarTempo(ms)).toBe(esperado)
  })

  it('arredonda os segundos para cima', () => {
    expect(formatarTempo(25 * 60_000 - 1)).toBe('25:00')
    expect(formatarTempo(1)).toBe('00:01')
  })

  it('nunca mostra tempo negativo', () => {
    expect(formatarTempo(-5_000)).toBe('00:00')
  })
})

describe('formatarHoras', () => {
  it.each([
    [45, '45 min'],
    [60, '1 h'],
    [115, '1,9 h'],
    [0, '0 min'],
  ])('formata %i minutos como %s', (minutos, esperado) => {
    expect(formatarHoras(minutos)).toBe(esperado)
  })
})
