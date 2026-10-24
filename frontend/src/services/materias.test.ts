import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from './api'
import { CORES_MATERIAS, materiasApi, type MateriaApi } from './materias'

describe('materiasApi', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  function respostaJson(status: number, dados: unknown) {
    return Promise.resolve(
      new Response(JSON.stringify(dados), {
        status,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
  }

  function respostaVazia(status: number) {
    return Promise.resolve(new Response(null, { status }))
  }

  const materiaExemplo: MateriaApi = {
    id: 'mat-1',
    usuario_id: 'usr-1',
    nome: 'Cálculo I',
    cor: '#8B7BFF',
    criada_em: '2026-10-24T12:00:00Z',
  }

  it('lista as matérias do estudante', async () => {
    fetchMock.mockReturnValueOnce(respostaJson(200, [materiaExemplo]))

    const materias = await materiasApi.listar()

    expect(materias).toEqual([materiaExemplo])
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/materias', {
      method: 'GET',
      headers: undefined,
      body: undefined,
    })
  })

  it('cria uma nova matéria com sucesso', async () => {
    fetchMock.mockReturnValueOnce(respostaJson(201, materiaExemplo))

    const materia = await materiasApi.criar({ nome: 'Cálculo I', cor: '#8B7BFF' })

    expect(materia).toEqual(materiaExemplo)
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/materias', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nome: 'Cálculo I', cor: '#8B7BFF' }),
    })
  })

  it('busca uma matéria por ID', async () => {
    fetchMock.mockReturnValueOnce(respostaJson(200, materiaExemplo))

    const materia = await materiasApi.buscar('mat-1')

    expect(materia).toEqual(materiaExemplo)
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/materias/mat-1', {
      method: 'GET',
      headers: undefined,
      body: undefined,
    })
  })

  it('atualiza nome e cor de uma matéria', async () => {
    const atualizada = { ...materiaExemplo, nome: 'Cálculo II', cor: '#3EE6E0' }
    fetchMock.mockReturnValueOnce(respostaJson(200, atualizada))

    const materia = await materiasApi.atualizar('mat-1', {
      nome: 'Cálculo II',
      cor: '#3EE6E0',
    })

    expect(materia).toEqual(atualizada)
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/materias/mat-1', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nome: 'Cálculo II', cor: '#3EE6E0' }),
    })
  })

  it('remove uma matéria e trata resposta 204 No Content', async () => {
    fetchMock.mockReturnValueOnce(respostaVazia(204))

    const resultado = await materiasApi.remover('mat-1')

    expect(resultado).toBeUndefined()
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/materias/mat-1', {
      method: 'DELETE',
      headers: undefined,
      body: undefined,
    })
  })

  it('lança ApiError com status 409 quando o nome já existe', async () => {
    fetchMock.mockReturnValueOnce(
      respostaJson(409, {
        erro: 'materia_ja_existe',
        mensagem: 'O estudante já tem uma matéria cadastrada com este nome.',
      }),
    )

    await expect(materiasApi.criar({ nome: 'Cálculo I', cor: '#8B7BFF' })).rejects.toThrow(
      ApiError,
    )
  })

  it('lança ApiError com status 404 quando a matéria não existe', async () => {
    fetchMock.mockReturnValueOnce(
      respostaJson(404, {
        erro: 'materia_nao_encontrada',
        mensagem: 'Matéria não encontrada.',
      }),
    )

    await expect(materiasApi.buscar('inexistente')).rejects.toThrow(ApiError)
  })

  it('exporta as 8 cores oficiais do design com formato hexadecimal válido', () => {
    expect(CORES_MATERIAS).toHaveLength(8)
    const hexPattern = /^#[0-9A-Fa-f]{6}$/
    for (const cor of CORES_MATERIAS) {
      expect(cor.hex).toMatch(hexPattern)
      expect(cor.nome).toBeTruthy()
    }
  })
})
