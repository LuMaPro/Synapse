import { afterEach, describe, expect, it, vi } from 'vitest'
import { conquistasApi, type ConquistasRespostaApi } from './conquistas'

const RESPOSTA_EXEMPLO: ConquistasRespostaApi = {
  sequencia: { atual: 3, recorde: 5 },
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
      codigo: 'dias_seguidos_7',
      nome: '7 dias seguidos',
      descricao: 'Conclua pelo menos uma sessão por dia, 7 dias seguidos.',
      desbloqueada: false,
      desbloqueada_em: null,
      progresso: 3,
      meta: 7,
      unidade: 'dias',
    },
  ],
}

function respostaJson(corpo: unknown) {
  return new Response(JSON.stringify(corpo), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('serviço de conquistas', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('consulta as conquistas e a sequência no endpoint /conquistas', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(respostaJson(RESPOSTA_EXEMPLO))

    const resultado = await conquistasApi.consultar()

    expect(resultado).toEqual(RESPOSTA_EXEMPLO)
    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/conquistas')
    expect(fetchMock.mock.calls[0][1]?.method ?? 'GET').toBe('GET')
  })
})
