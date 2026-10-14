import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { DURACAO_MAXIMA, DURACAO_MINIMA, useSessaoFoco } from './useSessaoFoco'

const MINUTO = 60_000

function simularVoltaParaAba() {
  act(() => {
    document.dispatchEvent(new Event('visibilitychange'))
  })
}

describe('useSessaoFoco', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-13T14:00:00Z'))
    localStorage.clear()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
    // O jsdom não implementa a API de tela cheia; os testes que a simulam limpam aqui.
    for (const alvo of [document.documentElement, document]) {
      for (const prop of ['requestFullscreen', 'exitFullscreen', 'fullscreenElement']) {
        Reflect.deleteProperty(alvo, prop)
      }
    }
  })

  it('começa configurando, com 25 minutos no modo estrito', () => {
    const { result } = renderHook(() => useSessaoFoco())

    expect(result.current.fase).toBe('configurando')
    expect(result.current.duracaoMin).toBe(25)
    expect(result.current.modo).toBe('estrito')
    expect(result.current.restanteMs).toBe(25 * MINUTO)
  })

  it('muda a duração de 5 em 5, sem passar de 10 a 120 minutos', () => {
    const { result } = renderHook(() => useSessaoFoco())

    act(() => result.current.aumentarDuracao())
    expect(result.current.duracaoMin).toBe(30)

    for (let i = 0; i < 30; i++) act(() => result.current.aumentarDuracao())
    expect(result.current.duracaoMin).toBe(DURACAO_MAXIMA)
    expect(result.current.podeAumentar).toBe(false)

    for (let i = 0; i < 30; i++) act(() => result.current.diminuirDuracao())
    expect(result.current.duracaoMin).toBe(DURACAO_MINIMA)
    expect(result.current.podeDiminuir).toBe(false)
  })

  it('lembra o último modo escolhido', () => {
    const { result, unmount } = renderHook(() => useSessaoFoco())
    act(() => result.current.escolherModo('tolerante'))
    unmount()

    const { result: novo } = renderHook(() => useSessaoFoco())
    expect(novo.current.modo).toBe('tolerante')
  })

  it('funciona mesmo sem acesso ao armazenamento do navegador', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('bloqueado')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('bloqueado')
    })
    const { result } = renderHook(() => useSessaoFoco())

    expect(result.current.modo).toBe('estrito')
    act(() => result.current.escolherModo('tolerante'))
    expect(result.current.modo).toBe('tolerante')
  })

  it('conta o tempo regressivo depois de iniciar', () => {
    const { result } = renderHook(() => useSessaoFoco())

    act(() => result.current.iniciar())
    expect(result.current.fase).toBe('em_andamento')
    expect(result.current.restanteMs).toBe(25 * MINUTO)

    act(() => vi.advanceTimersByTime(10 * MINUTO))
    expect(result.current.restanteMs).toBe(15 * MINUTO)
    expect(result.current.progresso).toBeCloseTo(0.4)
  })

  it('conclui a sessão quando o tempo acaba', () => {
    const { result } = renderHook(() => useSessaoFoco())
    act(() => result.current.iniciar())

    act(() => vi.advanceTimersByTime(25 * MINUTO))

    expect(result.current.fase).toBe('concluida')
    expect(result.current.restanteMs).toBe(0)
  })

  it('mantém o tempo certo mesmo com a aba em segundo plano', () => {
    const { result } = renderHook(() => useSessaoFoco())
    act(() => result.current.iniciar())

    // Aba escondida: o navegador para de disparar o intervalo, mas o relógio anda.
    vi.setSystemTime(Date.now() + 7_000)
    simularVoltaParaAba()

    expect(result.current.restanteMs).toBe(25 * MINUTO - 7_000)
  })

  it('conclui ao voltar para a aba se o tempo acabou enquanto ela estava escondida', () => {
    const { result } = renderHook(() => useSessaoFoco())
    act(() => result.current.iniciar())

    vi.setSystemTime(Date.now() + 26 * MINUTO)
    simularVoltaParaAba()

    expect(result.current.fase).toBe('concluida')
  })

  it('desistir poda a sessão e congela o tempo decorrido', () => {
    const { result } = renderHook(() => useSessaoFoco())
    act(() => result.current.iniciar())
    act(() => vi.advanceTimersByTime(4 * MINUTO))

    act(() => result.current.desistir())
    act(() => vi.advanceTimersByTime(10 * MINUTO))

    expect(result.current.fase).toBe('podada')
    expect(result.current.decorridoMs).toBe(4 * MINUTO)
  })

  it('focar de novo volta para a configuração mantendo duração e modo', () => {
    const { result } = renderHook(() => useSessaoFoco())
    act(() => result.current.aumentarDuracao())
    act(() => result.current.escolherModo('tolerante'))
    act(() => result.current.iniciar())
    act(() => result.current.desistir())

    act(() => result.current.focarDeNovo())

    expect(result.current.fase).toBe('configurando')
    expect(result.current.duracaoMin).toBe(30)
    expect(result.current.modo).toBe('tolerante')
    expect(result.current.restanteMs).toBe(30 * MINUTO)
  })

  describe('saídas da tela', () => {
    const SEGUNDO = 1_000

    function iniciarSessao(modo: 'estrito' | 'tolerante', minutos = 10) {
      const hook = renderHook(() => useSessaoFoco())
      act(() => hook.result.current.escolherModo(modo))
      for (let m = 25; m > minutos; m -= 5) act(() => hook.result.current.diminuirDuracao())
      act(() => hook.result.current.iniciar())
      return hook
    }

    /** Simula o estudante saindo agora e voltando depois de `ms`, sem o timer disparar. */
    function sairPor(hook: ReturnType<typeof iniciarSessao>, ms: number) {
      const inicio = Date.now()
      act(() => hook.result.current.sairDaTela(inicio))
      vi.setSystemTime(inicio + ms)
      act(() => hook.result.current.voltarParaTela(inicio + ms))
    }

    it('no modo tolerante, o saldo é 10% da duração da sessão', () => {
      const { result } = iniciarSessao('tolerante', 10)

      expect(result.current.toleranciaMs).toBe(MINUTO)
      expect(result.current.toleranciaRestanteMs).toBe(MINUTO)
    })

    it('no modo estrito não há saldo', () => {
      const { result } = iniciarSessao('estrito')

      expect(result.current.toleranciaMs).toBe(0)
    })

    it('desconta o tempo fora do saldo, sem voltar ao valor inicial', () => {
      const hook = iniciarSessao('tolerante', 10)

      sairPor(hook, 10 * SEGUNDO)
      expect(hook.result.current.toleranciaRestanteMs).toBe(50 * SEGUNDO)

      act(() => vi.advanceTimersByTime(2 * MINUTO))
      sairPor(hook, 20 * SEGUNDO)
      expect(hook.result.current.toleranciaRestanteMs).toBe(30 * SEGUNDO)
      expect(hook.result.current.fase).toBe('em_andamento')
    })

    it('usar exatamente o saldo todo ainda mantém a sessão viva', () => {
      const hook = iniciarSessao('tolerante', 10)

      sairPor(hook, MINUTO)

      expect(hook.result.current.fase).toBe('em_andamento')
      expect(hook.result.current.toleranciaRestanteMs).toBe(0)
    })

    it('poda quando a saída passa do saldo, no instante em que ele acabou', () => {
      const hook = iniciarSessao('tolerante', 10)
      act(() => vi.advanceTimersByTime(2 * MINUTO))
      sairPor(hook, 40 * SEGUNDO)

      sairPor(hook, 30 * SEGUNDO)

      expect(hook.result.current.fase).toBe('podada')
      expect(hook.result.current.motivoPoda).toBe('saiu')
      // 2 min + 40 s da primeira saída + 20 s que restavam de saldo
      expect(hook.result.current.decorridoMs).toBe(3 * MINUTO)
    })

    it('no modo estrito, poda na hora em que ele sai, sem esperar a volta', () => {
      const hook = iniciarSessao('estrito')
      act(() => vi.advanceTimersByTime(MINUTO))

      act(() => hook.result.current.sairDaTela(Date.now()))

      expect(hook.result.current.fase).toBe('podada')
      expect(hook.result.current.motivoPoda).toBe('saiu')
      expect(hook.result.current.decorridoMs).toBe(MINUTO)
    })

    it('no modo tolerante, o saldo diminui ao vivo enquanto ele está fora', () => {
      const hook = iniciarSessao('tolerante', 10)
      act(() => hook.result.current.sairDaTela(Date.now()))

      act(() => vi.advanceTimersByTime(15 * SEGUNDO))

      expect(hook.result.current.foraDaTela).toBe(true)
      expect(hook.result.current.toleranciaRestanteMs).toBe(45 * SEGUNDO)
      expect(hook.result.current.fase).toBe('em_andamento')
    })

    it('no modo tolerante, poda quando o saldo acaba, mesmo que ele não volte', () => {
      const hook = iniciarSessao('tolerante', 10)
      act(() => vi.advanceTimersByTime(2 * MINUTO))
      act(() => hook.result.current.sairDaTela(Date.now()))

      act(() => vi.advanceTimersByTime(MINUTO + SEGUNDO))

      expect(hook.result.current.fase).toBe('podada')
      expect(hook.result.current.motivoPoda).toBe('saiu')
      expect(hook.result.current.decorridoMs).toBe(3 * MINUTO)
    })

    it('fora da tela, mas dentro do saldo, quando o tempo acaba: a sessão conclui', () => {
      const hook = iniciarSessao('tolerante', 10)
      act(() => vi.advanceTimersByTime(9.5 * MINUTO))
      act(() => hook.result.current.sairDaTela(Date.now()))

      act(() => vi.advanceTimersByTime(MINUTO))

      expect(hook.result.current.fase).toBe('concluida')
    })

    it('uma nova sessão começa com o saldo cheio', () => {
      const hook = iniciarSessao('tolerante', 10)
      sairPor(hook, 30 * SEGUNDO)
      act(() => hook.result.current.desistir())

      act(() => hook.result.current.focarDeNovo())
      act(() => hook.result.current.iniciar())

      expect(hook.result.current.toleranciaRestanteMs).toBe(MINUTO)
      expect(hook.result.current.motivoPoda).toBeNull()
    })

    it('ignora saídas fora de uma sessão em andamento', () => {
      const { result } = renderHook(() => useSessaoFoco())

      act(() => result.current.sairDaTela(Date.now()))
      act(() => result.current.voltarParaTela(Date.now() + 5 * SEGUNDO))

      expect(result.current.fase).toBe('configurando')
    })

    it('ignora a saída que vem logo depois de a sessão terminar', () => {
      const hook = iniciarSessao('estrito')
      act(() => hook.result.current.desistir())

      // Ex.: o fullscreenchange disparado pelo próprio fim da sessão.
      act(() => hook.result.current.sairDaTela(Date.now()))

      expect(hook.result.current.motivoPoda).toBe('desistiu')
    })
  })

  it('desistir registra o motivo da poda', () => {
    const { result } = renderHook(() => useSessaoFoco())
    act(() => result.current.iniciar())

    act(() => result.current.desistir())

    expect(result.current.motivoPoda).toBe('desistiu')
  })

  it('entra em tela cheia ao iniciar e sai ao terminar', () => {
    const requestFullscreen = vi.fn().mockResolvedValue(undefined)
    const exitFullscreen = vi.fn().mockResolvedValue(undefined)
    Object.assign(document.documentElement, { requestFullscreen })
    Object.assign(document, { exitFullscreen })
    const { result } = renderHook(() => useSessaoFoco())

    act(() => result.current.iniciar())
    expect(requestFullscreen).toHaveBeenCalledOnce()

    Object.defineProperty(document, 'fullscreenElement', {
      configurable: true,
      get: () => document.documentElement,
    })
    act(() => vi.advanceTimersByTime(25 * MINUTO))
    expect(exitFullscreen).toHaveBeenCalled()
  })

  it('segue sem tela cheia se o navegador recusar', async () => {
    const requestFullscreen = vi.fn().mockRejectedValue(new Error('recusado'))
    Object.assign(document.documentElement, { requestFullscreen })
    const { result } = renderHook(() => useSessaoFoco())

    act(() => result.current.iniciar())
    await act(async () => {})

    expect(result.current.fase).toBe('em_andamento')
  })
})
