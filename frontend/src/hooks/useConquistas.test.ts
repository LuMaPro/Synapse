import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { conquistasApi, type ConquistasRespostaApi } from '../services/conquistas'
import { useConquistas } from './useConquistas'

describe('useConquistas', () => {
  const dadosExemplo: ConquistasRespostaApi = {
    sequencia: { atual: 3, recorde: 7 },
    desbloqueadas: 1,
    total: 5,
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

  it('carrega as conquistas e a sequência ao montar o hook', async () => {
    const { result } = renderHook(() => useConquistas())

    expect(result.current.carregando).toBe(true)
    await waitFor(() => expect(result.current.carregando).toBe(false))

    expect(result.current.conquistas).toEqual(dadosExemplo.conquistas)
    expect(result.current.sequencia).toEqual(dadosExemplo.sequencia)
    expect(result.current.desbloqueadas).toBe(1)
    expect(result.current.total).toBe(5)
    expect(result.current.erro).toBeNull()
  })

  it('trata erro quando o carregamento inicial falha', async () => {
    vi.spyOn(conquistasApi, 'consultar').mockRejectedValueOnce(new Error('Falha de rede'))

    const { result } = renderHook(() => useConquistas())

    await waitFor(() => expect(result.current.carregando).toBe(false))

    expect(result.current.conquistas).toEqual([])
    expect(result.current.sequencia).toBeNull()
    expect(result.current.erro).toBe('Não foi possível carregar as conquistas.')
  })

  it('permite recarregar as conquistas manualmente', async () => {
    const { result } = renderHook(() => useConquistas())

    await waitFor(() => expect(result.current.carregando).toBe(false))

    const dadosAtualizados: ConquistasRespostaApi = {
      ...dadosExemplo,
      desbloqueadas: 2,
      sequencia: { atual: 4, recorde: 7 },
    }
    vi.spyOn(conquistasApi, 'consultar').mockResolvedValueOnce(dadosAtualizados)

    await act(async () => {
      await result.current.recarregar()
    })

    expect(result.current.desbloqueadas).toBe(2)
    expect(result.current.sequencia?.atual).toBe(4)
  })
})
