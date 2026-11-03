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

  it('carregar() busca a lista de novo e limpa o erro anterior', async () => {
    vi.spyOn(materiasApi, 'listar')
      .mockRejectedValueOnce(new Error('Falha de rede'))
      .mockResolvedValueOnce([...listaExemplo])

    const { result } = renderHook(() => useMaterias())
    await waitFor(() => expect(result.current.erro).not.toBeNull())

    await act(async () => {
      await result.current.carregar()
    })

    expect(result.current.erro).toBeNull()
    expect(result.current.carregando).toBe(false)
    expect(result.current.materias).toEqual(listaExemplo)
  })

  it('carregar() avisa quando a nova busca também falha', async () => {
    const { result } = renderHook(() => useMaterias())
    await waitFor(() => expect(result.current.carregando).toBe(false))
    vi.spyOn(materiasApi, 'listar').mockRejectedValueOnce(new Error('Falha de rede'))

    await act(async () => {
      await result.current.carregar()
    })

    expect(result.current.erro).toBe('Não foi possível carregar as matérias.')
    expect(result.current.carregando).toBe(false)
  })

  // Cada erro do servidor vira uma mensagem que o estudante entende.
  const errosDaApi: [string, unknown, string][] = [
    [
      'cor da loja ainda não comprada',
      new ApiError(409, 'cor_bloqueada', 'Compre a cor Aurora na loja.'),
      'Compre a cor Aurora na loja.',
    ],
    [
      'nome duplicado',
      new ApiError(409, 'materia_ja_existe', 'Conflito'),
      'Você já tem uma matéria com este nome.',
    ],
    ['dados inválidos (400)', new ApiError(400, 'nome_invalido', 'x'), 'Nome ou cor inválidos.'],
    ['dados inválidos (422)', new ApiError(422, 'cor_invalida', 'x'), 'Nome ou cor inválidos.'],
  ]

  it.each(errosDaApi)('criar: %s', async (_caso, erro, mensagem) => {
    vi.spyOn(materiasApi, 'criar').mockRejectedValueOnce(erro)
    const { result } = renderHook(() => useMaterias())
    await waitFor(() => expect(result.current.carregando).toBe(false))

    await expect(result.current.criar('Química', '#8B7BFF')).rejects.toThrow(mensagem)
  })

  it('criar: sem conexão, pede para tentar de novo', async () => {
    vi.spyOn(materiasApi, 'criar').mockRejectedValueOnce(new TypeError('Failed to fetch'))
    const { result } = renderHook(() => useMaterias())
    await waitFor(() => expect(result.current.carregando).toBe(false))

    await expect(result.current.criar('Química', '#8B7BFF')).rejects.toThrow(
      'Não foi possível criar a matéria. Tente novamente.',
    )
  })

  it.each(errosDaApi)('atualizar: %s', async (_caso, erro, mensagem) => {
    vi.spyOn(materiasApi, 'atualizar').mockRejectedValueOnce(erro)
    const { result } = renderHook(() => useMaterias())
    await waitFor(() => expect(result.current.carregando).toBe(false))

    await expect(result.current.atualizar('mat-1', { nome: 'Química' })).rejects.toThrow(mensagem)
    expect(result.current.materias).toEqual(listaExemplo)
  })

  it('atualizar: sem conexão, pede para tentar de novo', async () => {
    vi.spyOn(materiasApi, 'atualizar').mockRejectedValueOnce(new TypeError('Failed to fetch'))
    const { result } = renderHook(() => useMaterias())
    await waitFor(() => expect(result.current.carregando).toBe(false))

    await expect(result.current.atualizar('mat-1', { cor: '#5BE49B' })).rejects.toThrow(
      'Não foi possível atualizar a matéria. Tente novamente.',
    )
  })

  it('atualizar só a cor não manda o nome', async () => {
    const atualizada: Materia = { ...listaExemplo[1], cor: '#5BE49B' }
    vi.spyOn(materiasApi, 'atualizar').mockResolvedValueOnce(atualizada)
    const { result } = renderHook(() => useMaterias())
    await waitFor(() => expect(result.current.carregando).toBe(false))

    await act(async () => {
      await result.current.atualizar('mat-2', { cor: '#5BE49B' })
    })

    expect(materiasApi.atualizar).toHaveBeenCalledWith('mat-2', { cor: '#5BE49B' })
    expect(result.current.materias[1]).toEqual(atualizada)
  })

  it('remover: na falha, a matéria continua na lista', async () => {
    vi.spyOn(materiasApi, 'remover').mockRejectedValueOnce(new TypeError('Failed to fetch'))
    const { result } = renderHook(() => useMaterias())
    await waitFor(() => expect(result.current.carregando).toBe(false))

    await expect(result.current.remover('mat-1')).rejects.toThrow(
      'Não foi possível excluir a matéria. Tente novamente.',
    )
    expect(result.current.materias).toEqual(listaExemplo)
  })
})
