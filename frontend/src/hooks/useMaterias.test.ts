import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../services/api'
import { materiasApi, type Materia } from '../services/materias'
import { useMaterias } from './useMaterias'

describe('useMaterias', () => {
  const listaExemplo: Materia[] = [
    {
      id: 'mat-1',
      nome: 'Cálculo I',
      cor: '#8B7BFF',
      criada_em: '2026-10-24T10:00:00Z',
    },
    {
      id: 'mat-2',
      nome: 'Física',
      cor: '#3EE6E0',
      criada_em: '2026-10-24T11:00:00Z',
    },
  ]

  beforeEach(() => {
    vi.spyOn(materiasApi, 'listar').mockResolvedValue([...listaExemplo])
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('carrega a lista de matérias ao montar o hook', async () => {
    const { result } = renderHook(() => useMaterias())

    expect(result.current.carregando).toBe(true)
    await waitFor(() => expect(result.current.carregando).toBe(false))

    expect(result.current.materias).toEqual(listaExemplo)
    expect(result.current.erro).toBeNull()
  })

  it('define mensagem de erro quando a listagem falha', async () => {
    vi.spyOn(materiasApi, 'listar').mockRejectedValueOnce(new Error('Falha de rede'))

    const { result } = renderHook(() => useMaterias())
    await waitFor(() => expect(result.current.carregando).toBe(false))

    expect(result.current.materias).toEqual([])
    expect(result.current.erro).toBe('Não foi possível carregar as matérias.')
  })

  it('cria uma matéria e adiciona à lista ordenada', async () => {
    const nova: Materia = {
      id: 'mat-3',
      nome: 'Álgebra Linear',
      cor: '#5BE49B',
      criada_em: '2026-10-24T12:00:00Z',
    }
    vi.spyOn(materiasApi, 'criar').mockResolvedValueOnce(nova)

    const { result } = renderHook(() => useMaterias())
    await waitFor(() => expect(result.current.carregando).toBe(false))

    await act(async () => {
      const criada = await result.current.criar('Álgebra Linear', '#5BE49B')
      expect(criada).toEqual(nova)
    })

    expect(materiasApi.criar).toHaveBeenCalledWith({
      nome: 'Álgebra Linear',
      cor: '#5BE49B',
    })
    // Deve vir em primeiro porque 'Á' vem antes de 'C'
    expect(result.current.materias[0].nome).toBe('Álgebra Linear')
    expect(result.current.materias).toHaveLength(3)
  })

  it('trata erro de nome duplicado (409) na criação', async () => {
    vi.spyOn(materiasApi, 'criar').mockRejectedValueOnce(
      new ApiError(409, 'materia_ja_existe', 'Conflito'),
    )

    const { result } = renderHook(() => useMaterias())
    await waitFor(() => expect(result.current.carregando).toBe(false))

    await expect(result.current.criar('Cálculo I', '#8B7BFF')).rejects.toThrow(
      'Você já tem uma matéria com este nome.',
    )
  })

  it('atualiza uma matéria existente na lista', async () => {
    const atualizada: Materia = {
      ...listaExemplo[0],
      nome: 'Cálculo Avançado',
      cor: '#FFC857',
    }
    vi.spyOn(materiasApi, 'atualizar').mockResolvedValueOnce(atualizada)

    const { result } = renderHook(() => useMaterias())
    await waitFor(() => expect(result.current.carregando).toBe(false))

    await act(async () => {
      const res = await result.current.atualizar('mat-1', {
        nome: 'Cálculo Avançado',
        cor: '#FFC857',
      })
      expect(res).toEqual(atualizada)
    })

    expect(result.current.materias.find((m) => m.id === 'mat-1')?.nome).toBe(
      'Cálculo Avançado',
    )
    expect(result.current.materias.find((m) => m.id === 'mat-1')?.cor).toBe(
      '#FFC857',
    )
  })

  it('remove uma matéria da lista', async () => {
    vi.spyOn(materiasApi, 'remover').mockResolvedValueOnce(undefined)

    const { result } = renderHook(() => useMaterias())
    await waitFor(() => expect(result.current.carregando).toBe(false))

    await act(async () => {
      await result.current.remover('mat-1')
    })

    expect(materiasApi.remover).toHaveBeenCalledWith('mat-1')
    expect(result.current.materias).toEqual([listaExemplo[1]])
  })
})
