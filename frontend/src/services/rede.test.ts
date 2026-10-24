import { afterEach, describe, expect, it, vi } from 'vitest'
import { listarMaterias } from './materias'
import { buscarRede } from './rede'

function respostaJson(corpo: unknown) {
  return new Response(JSON.stringify(corpo), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('serviços da rede', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('sem filtros, pede a rede inteira', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(respostaJson({ neuronios: [], sinapses: [] }))

    await expect(buscarRede()).resolves.toEqual({ neuronios: [], sinapses: [] })
    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/rede')
  })

  it('manda o início do período em UTC e o id da matéria', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(respostaJson({ neuronios: [], sinapses: [] }))

    await buscarRede({ de: new Date('2026-10-16T03:00:00Z'), materiaId: 'abc' })

    const url = new URL(String(fetchMock.mock.calls[0][0]))
    expect(url.pathname).toBe('/rede')
    expect(url.searchParams.get('de')).toBe('2026-10-16T03:00:00.000Z')
    expect(url.searchParams.get('materia')).toBe('abc')
  })

  it('lista as matérias do estudante', async () => {
    const materias = [{ id: '1', nome: 'Cálculo', cor: '#8B7BFF', criada_em: '' }]
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(respostaJson(materias))

    await expect(listarMaterias()).resolves.toEqual(materias)
    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/materias')
  })
})
