import { describe, expect, it } from 'vitest'
import { tipoNeuronio } from './neuronio'

describe('tipoNeuronio', () => {
  it.each([
    [10, 'granular'],
    [20, 'granular'],
    [25, 'piramidal'],
    [55, 'piramidal'],
    [60, 'purkinje'],
    [120, 'purkinje'],
  ])('%i min gera um neurônio %s', (minutos, tipo) => {
    expect(tipoNeuronio(minutos)).toBe(tipo)
  })
})
