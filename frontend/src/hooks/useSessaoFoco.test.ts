import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { criarServidorFalso, type ServidorFalso } from '../test/servidorFalso'
import { DURACAO_MAXIMA, DURACAO_MINIMA, useSessaoFoco } from './useSessaoFoco'

const MINUTO = 60_000

/** Deixa as respostas do servidor falso chegarem. */
async function aguardarServidor() {
  await act(async () => {
    for (let i = 0; i < 20; i++) await Promise.resolve()
  })
}

function simularVoltaParaAba() {
  act(() => {
    document.dispatchEvent(new Event('visibilitychange'))
  })
}

describe('useSessaoFoco', () => {
  let servidor: ServidorFalso

  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-13T14:00:00Z'))
    localStorage.clear()
    servidor = criarServidorFalso()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
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

  it('conta o tempo regressivo depois de iniciar', async () => {
    const { result } = renderHook(() => useSessaoFoco())

    await act(() => result.current.iniciar())
    expect(result.current.fase).toBe('em_andamento')
    expect(result.current.restanteMs).toBe(25 * MINUTO)

    act(() => vi.advanceTimersByTime(10 * MINUTO))
    expect(result.current.restanteMs).toBe(15 * MINUTO)
    expect(result.current.progresso).toBeCloseTo(0.4)
  })

  it('conclui a sessão quando o tempo acaba', async () => {
    const { result } = renderHook(() => useSessaoFoco())
    await act(() => result.current.iniciar())

    act(() => vi.advanceTimersByTime(25 * MINUTO))
    await aguardarServidor()

    expect(result.current.fase).toBe('concluida')
    expect(result.current.restanteMs).toBe(0)
  })

  it('mantém o tempo certo mesmo com a aba em segundo plano', async () => {
    const { result } = renderHook(() => useSessaoFoco())
    await act(() => result.current.iniciar())

    // Aba escondida: o navegador para de disparar o intervalo, mas o relógio anda.
    vi.setSystemTime(Date.now() + 7_000)
    simularVoltaParaAba()

    expect(result.current.restanteMs).toBe(25 * MINUTO - 7_000)
  })

  it('conclui ao voltar para a aba se o tempo acabou enquanto ela estava escondida', async () => {
    const { result } = renderHook(() => useSessaoFoco())
    await act(() => result.current.iniciar())

    vi.setSystemTime(Date.now() + 26 * MINUTO)
    simularVoltaParaAba()
    await aguardarServidor()

    expect(result.current.fase).toBe('concluida')
  })

  it('desistir poda a sessão e congela o tempo decorrido', async () => {
    const { result } = renderHook(() => useSessaoFoco())
    await act(() => result.current.iniciar())
    act(() => vi.advanceTimersByTime(4 * MINUTO))

    act(() => result.current.desistir())
    act(() => vi.advanceTimersByTime(10 * MINUTO))

    expect(result.current.fase).toBe('podada')
    expect(result.current.decorridoMs).toBe(4 * MINUTO)
  })

  it('focar de novo volta para a configuração mantendo duração e modo', async () => {
    const { result } = renderHook(() => useSessaoFoco())
    act(() => result.current.aumentarDuracao())
    act(() => result.current.escolherModo('tolerante'))
    await act(() => result.current.iniciar())
    act(() => result.current.desistir())

    act(() => result.current.focarDeNovo())

    expect(result.current.fase).toBe('configurando')
    expect(result.current.duracaoMin).toBe(30)
    expect(result.current.modo).toBe('tolerante')
    expect(result.current.restanteMs).toBe(30 * MINUTO)
  })

  describe('saídas da tela', () => {
    const SEGUNDO = 1_000

    async function iniciarSessao(modo: 'estrito' | 'tolerante', minutos = 10) {
      const hook = renderHook(() => useSessaoFoco())
      act(() => hook.result.current.escolherModo(modo))
      for (let m = 25; m > minutos; m -= 5) act(() => hook.result.current.diminuirDuracao())
      await act(() => hook.result.current.iniciar())
      return hook
    }

    /** Simula o estudante saindo agora e voltando depois de `ms`, sem o timer disparar. */
    function sairPor(hook: Awaited<ReturnType<typeof iniciarSessao>>, ms: number) {
      const inicio = Date.now()
      act(() => hook.result.current.sairDaTela(inicio))
      vi.setSystemTime(inicio + ms)
      act(() => hook.result.current.voltarParaTela(inicio + ms))
    }

    it('no modo tolerante, o saldo é 10% da duração da sessão', async () => {
      const { result } = await iniciarSessao('tolerante', 10)

      expect(result.current.toleranciaMs).toBe(MINUTO)
      expect(result.current.toleranciaRestanteMs).toBe(MINUTO)
    })

    it('no modo estrito não há saldo', async () => {
      const { result } = await iniciarSessao('estrito')

      expect(result.current.toleranciaMs).toBe(0)
    })

    it('desconta o tempo fora do saldo, sem voltar ao valor inicial', async () => {
      const hook = await iniciarSessao('tolerante', 10)

      sairPor(hook, 10 * SEGUNDO)
      expect(hook.result.current.toleranciaRestanteMs).toBe(50 * SEGUNDO)

      act(() => vi.advanceTimersByTime(2 * MINUTO))
      sairPor(hook, 20 * SEGUNDO)
      expect(hook.result.current.toleranciaRestanteMs).toBe(30 * SEGUNDO)
      expect(hook.result.current.fase).toBe('em_andamento')
    })

    it('usar exatamente o saldo todo ainda mantém a sessão viva', async () => {
      const hook = await iniciarSessao('tolerante', 10)

      sairPor(hook, MINUTO)

      expect(hook.result.current.fase).toBe('em_andamento')
      expect(hook.result.current.toleranciaRestanteMs).toBe(0)
    })

    it('poda quando a saída passa do saldo, no instante em que ele acabou', async () => {
      const hook = await iniciarSessao('tolerante', 10)
      act(() => vi.advanceTimersByTime(2 * MINUTO))
      sairPor(hook, 40 * SEGUNDO)

      sairPor(hook, 30 * SEGUNDO)

      expect(hook.result.current.fase).toBe('podada')
      expect(hook.result.current.motivoPoda).toBe('saiu')
      // 2 min + 40 s da primeira saída + 20 s que restavam de saldo
      expect(hook.result.current.decorridoMs).toBe(3 * MINUTO)
    })

    it('no modo estrito, poda na hora em que ele sai, sem esperar a volta', async () => {
      const hook = await iniciarSessao('estrito')
      act(() => vi.advanceTimersByTime(MINUTO))

      act(() => hook.result.current.sairDaTela(Date.now()))

      expect(hook.result.current.fase).toBe('podada')
      expect(hook.result.current.motivoPoda).toBe('saiu')
      expect(hook.result.current.decorridoMs).toBe(MINUTO)
    })

    it('no modo tolerante, o saldo diminui ao vivo enquanto ele está fora', async () => {
      const hook = await iniciarSessao('tolerante', 10)
      act(() => hook.result.current.sairDaTela(Date.now()))

      act(() => vi.advanceTimersByTime(15 * SEGUNDO))

      expect(hook.result.current.foraDaTela).toBe(true)
      expect(hook.result.current.toleranciaRestanteMs).toBe(45 * SEGUNDO)
      expect(hook.result.current.fase).toBe('em_andamento')
    })

    it('no modo tolerante, poda quando o saldo acaba, mesmo que ele não volte', async () => {
      const hook = await iniciarSessao('tolerante', 10)
      act(() => vi.advanceTimersByTime(2 * MINUTO))
      act(() => hook.result.current.sairDaTela(Date.now()))

      act(() => vi.advanceTimersByTime(MINUTO + SEGUNDO))

      expect(hook.result.current.fase).toBe('podada')
      expect(hook.result.current.motivoPoda).toBe('saiu')
      expect(hook.result.current.decorridoMs).toBe(3 * MINUTO)
    })

    it('fora da tela, mas dentro do saldo, quando o tempo acaba: a sessão conclui', async () => {
      const hook = await iniciarSessao('tolerante', 10)
      act(() => vi.advanceTimersByTime(9.5 * MINUTO))
      act(() => hook.result.current.sairDaTela(Date.now()))

      act(() => vi.advanceTimersByTime(MINUTO))
      await aguardarServidor()

      expect(hook.result.current.fase).toBe('concluida')
    })

    it('uma nova sessão começa com o saldo cheio', async () => {
      const hook = await iniciarSessao('tolerante', 10)
      sairPor(hook, 30 * SEGUNDO)
      act(() => hook.result.current.desistir())

      act(() => hook.result.current.focarDeNovo())
      await act(() => hook.result.current.iniciar())

      expect(hook.result.current.toleranciaRestanteMs).toBe(MINUTO)
      expect(hook.result.current.motivoPoda).toBeNull()
    })

    it('ignora saídas fora de uma sessão em andamento', () => {
      const { result } = renderHook(() => useSessaoFoco())

      act(() => result.current.sairDaTela(Date.now()))
      act(() => result.current.voltarParaTela(Date.now() + 5 * SEGUNDO))

      expect(result.current.fase).toBe('configurando')
    })

    it('ignora a saída que vem logo depois de a sessão terminar', async () => {
      const hook = await iniciarSessao('estrito')
      act(() => hook.result.current.desistir())

      // Ex.: o fullscreenchange disparado pelo próprio fim da sessão.
      act(() => hook.result.current.sairDaTela(Date.now()))

      expect(hook.result.current.motivoPoda).toBe('desistiu')
    })
  })

  it('desistir registra o motivo da poda', async () => {
    const { result } = renderHook(() => useSessaoFoco())
    await act(() => result.current.iniciar())

    act(() => result.current.desistir())

    expect(result.current.motivoPoda).toBe('desistiu')
  })

  it('entra em tela cheia ao iniciar e sai ao terminar', async () => {
    const requestFullscreen = vi.fn().mockResolvedValue(undefined)
    const exitFullscreen = vi.fn().mockResolvedValue(undefined)
    Object.assign(document.documentElement, { requestFullscreen })
    Object.assign(document, { exitFullscreen })
    const { result } = renderHook(() => useSessaoFoco())

    await act(() => result.current.iniciar())
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

    await act(() => result.current.iniciar())
    await act(async () => {})

    expect(result.current.fase).toBe('em_andamento')
  })

  describe('integração com a API de sessões (issue #20)', () => {
    const SEGUNDO = 1_000

    async function comecar(modo: 'estrito' | 'tolerante' = 'estrito', minutos = 25) {
      const hook = renderHook(() => useSessaoFoco())
      await aguardarServidor()
      act(() => hook.result.current.escolherModo(modo))
      for (let m = 25; m > minutos; m -= 5) act(() => hook.result.current.diminuirDuracao())
      await act(() => hook.result.current.iniciar())
      return hook
    }

    const sessaoNoServidor = () => servidor.sessoes()[0]

    it('começar cria a sessão no servidor com a duração e o modo escolhidos', async () => {
      const { result } = await comecar('tolerante', 10)

      expect(servidor.chamadasPara('/sessoes')).toEqual([
        expect.objectContaining({
          metodo: 'POST',
          corpo: { duracao_minutos: 10, modo: 'tolerante' },
        }),
      ])
      expect(sessaoNoServidor().estado).toBe('em_andamento')
      expect(result.current.fase).toBe('em_andamento')
    })

    it('ao abrir, retoma a sessão em andamento com o tempo calculado pelo servidor', async () => {
      servidor.criarSessaoAtiva({
        duracaoMin: 25,
        modo: 'tolerante',
        inicio: Date.now() - 5 * MINUTO,
        foraMs: 30 * SEGUNDO,
      })

      const { result } = renderHook(() => useSessaoFoco())
      await aguardarServidor()

      expect(result.current.fase).toBe('em_andamento')
      expect(result.current.modo).toBe('tolerante')
      expect(result.current.restanteMs).toBe(20 * MINUTO)
      // Saldo de 150 s, com 30 s já gastos antes de fechar a página.
      expect(result.current.toleranciaRestanteMs).toBe(120 * SEGUNDO)
    })

    it('ao abrir sem sessão em andamento, fica na configuração', async () => {
      const { result } = renderHook(() => useSessaoFoco())
      await aguardarServidor()

      expect(servidor.chamadasPara('/sessoes/ativa')).toHaveLength(1)
      expect(result.current.fase).toBe('configurando')
    })

    it('no estrito, avisa a saída na hora (com keepalive) e o servidor poda', async () => {
      const hook = await comecar('estrito')
      act(() => vi.advanceTimersByTime(MINUTO))

      act(() => hook.result.current.sairDaTela(Date.now()))
      await aguardarServidor()

      const [aviso] = servidor.chamadasPara('/interrupcoes')
      expect(aviso).toMatchObject({ keepalive: true, corpo: { inicio: expect.any(String) } })
      expect(aviso.corpo).not.toHaveProperty('fim')
      expect(sessaoNoServidor().estado).toBe('podada')
      expect(sessaoNoServidor().encerradaEm).toBe(sessaoNoServidor().inicio + MINUTO)
    })

    it('envia os horários no relógio do servidor, mesmo com o do navegador atrasado', async () => {
      servidor.adiantarRelogio(90 * SEGUNDO)
      const hook = await comecar('estrito')
      act(() => vi.advanceTimersByTime(MINUTO))

      act(() => hook.result.current.sairDaTela(Date.now()))
      await aguardarServidor()

      // Sem a conversão, o servidor recusaria a saída por ser antes do início da sessão.
      expect(sessaoNoServidor().estado).toBe('podada')
      expect(sessaoNoServidor().encerradaEm).toBe(sessaoNoServidor().inicio + MINUTO)
    })

    it('no tolerante, a volta envia a saída com início e fim', async () => {
      const hook = await comecar('tolerante', 10)
      act(() => vi.advanceTimersByTime(MINUTO))

      act(() => hook.result.current.sairDaTela(Date.now()))
      vi.setSystemTime(Date.now() + 20 * SEGUNDO)
      act(() => hook.result.current.voltarParaTela(Date.now()))
      await aguardarServidor()

      expect(servidor.chamadasPara('/interrupcoes')).toHaveLength(1)
      expect(sessaoNoServidor().foraMs).toBe(20 * SEGUNDO)
      expect(hook.result.current.fase).toBe('em_andamento')
    })

    it('se o servidor podar a sessão, a tela mostra a poda', async () => {
      const hook = await comecar('tolerante', 10)
      act(() => vi.advanceTimersByTime(MINUTO))
      // O servidor sabe de 55 s fora que esta tela não viu (ex.: outra aba).
      sessaoNoServidor().foraMs = 55 * SEGUNDO

      act(() => hook.result.current.sairDaTela(Date.now()))
      vi.setSystemTime(Date.now() + 10 * SEGUNDO)
      act(() => hook.result.current.voltarParaTela(Date.now()))
      expect(hook.result.current.fase).toBe('em_andamento')
      await aguardarServidor()

      expect(hook.result.current.fase).toBe('podada')
      expect(hook.result.current.motivoPoda).toBe('saiu')
      // Podada quando os 5 s de saldo que o servidor contava acabaram.
      expect(hook.result.current.decorridoMs).toBe(MINUTO + 5 * SEGUNDO)
    })

    it('desistir avisa o servidor', async () => {
      const hook = await comecar()

      act(() => hook.result.current.desistir())
      await aguardarServidor()

      expect(servidor.chamadasPara('/desistir')).toHaveLength(1)
      expect(sessaoNoServidor().estado).toBe('podada')
    })

    it('o fim do timer conclui no servidor, e o neurônio só aparece depois', async () => {
      const hook = await comecar('estrito', 10)

      act(() => vi.advanceTimersByTime(10 * MINUTO))
      expect(hook.result.current.fase).toBe('concluindo')
      await aguardarServidor()

      expect(servidor.chamadasPara('/concluir')).toHaveLength(1)
      expect(sessaoNoServidor().estado).toBe('concluida')
      expect(hook.result.current.fase).toBe('concluida')
    })

    it('sem rede no fim, tenta concluir de novo sem perder a sessão', async () => {
      const hook = await comecar('estrito', 10)
      servidor.ficarSemRede()

      act(() => vi.advanceTimersByTime(10 * MINUTO))
      await aguardarServidor()
      expect(hook.result.current.fase).toBe('concluindo')
      expect(hook.result.current.semConexao).toBe(true)

      servidor.ficarSemRede(false)
      act(() => vi.advanceTimersByTime(2 * SEGUNDO))
      await aguardarServidor()

      expect(hook.result.current.fase).toBe('concluida')
      expect(sessaoNoServidor().estado).toBe('concluida')
    })

    it('se o servidor recusar a conclusão (sessão abandonada e podada), mostra a poda', async () => {
      const hook = await comecar('estrito', 10)
      sessaoNoServidor().estado = 'podada'

      act(() => vi.advanceTimersByTime(10 * MINUTO))
      await aguardarServidor()

      expect(hook.result.current.fase).toBe('podada')
    })

    it('uma saída que não chegou por falta de rede é enviada antes da próxima sessão', async () => {
      const hook = await comecar('estrito')
      servidor.ficarSemRede()
      act(() => hook.result.current.sairDaTela(Date.now()))
      await aguardarServidor()
      expect(sessaoNoServidor().estado).toBe('em_andamento')

      servidor.ficarSemRede(false)
      act(() => hook.result.current.focarDeNovo())
      await act(() => hook.result.current.iniciar())

      expect(servidor.sessoes().map((s) => s.estado)).toEqual(['podada', 'em_andamento'])
      expect(hook.result.current.fase).toBe('em_andamento')
    })

    it('ao reabrir a tela, entrega a saída pendente em vez de retomar a sessão', async () => {
      const hook = await comecar('estrito')
      servidor.ficarSemRede()
      act(() => hook.result.current.sairDaTela(Date.now()))
      await aguardarServidor()
      hook.unmount()

      servidor.ficarSemRede(false)
      const { result } = renderHook(() => useSessaoFoco())
      await aguardarServidor()

      expect(sessaoNoServidor().estado).toBe('podada')
      expect(result.current.fase).toBe('configurando')
    })

    it('com aviso pendente que o servidor não aceitou (erro 500), não retoma a sessão', async () => {
      const hook = await comecar('estrito')
      servidor.falharCom500('/interrupcoes')
      act(() => hook.result.current.sairDaTela(Date.now()))
      await aguardarServidor()
      hook.unmount()

      const { result } = renderHook(() => useSessaoFoco())
      await aguardarServidor()

      // A sessão segue em andamento no servidor, mas o estudante já saiu da tela.
      expect(sessaoNoServidor().estado).toBe('em_andamento')
      expect(result.current.fase).toBe('configurando')
    })

    it('no tolerante, a saída com a página fechada conta o tempo fora ao reabrir', async () => {
      const hook = await comecar('tolerante', 10)
      act(() => hook.result.current.sairDaTela(Date.now()))
      hook.unmount()

      vi.setSystemTime(Date.now() + 20 * SEGUNDO)
      const { result } = renderHook(() => useSessaoFoco())
      await aguardarServidor()

      expect(sessaoNoServidor().foraMs).toBe(20 * SEGUNDO)
      expect(result.current.fase).toBe('em_andamento')
      expect(result.current.toleranciaRestanteMs).toBe(40 * SEGUNDO)
    })

    it('sair da tela de foco no meio da sessão estrita poda a sessão', async () => {
      const hook = await comecar('estrito')

      hook.unmount()
      await aguardarServidor()

      expect(sessaoNoServidor().estado).toBe('podada')
    })

    it('se já houver uma sessão em andamento (ex.: outra aba), continua nela', async () => {
      const hook = renderHook(() => useSessaoFoco())
      await aguardarServidor()
      const existente = servidor.criarSessaoAtiva({
        duracaoMin: 40,
        modo: 'estrito',
        inicio: Date.now() - 10 * MINUTO,
      })

      await act(() => hook.result.current.iniciar())

      expect(servidor.sessoes()).toHaveLength(1)
      expect(existente.estado).toBe('em_andamento')
      expect(hook.result.current.duracaoMin).toBe(40)
      expect(hook.result.current.restanteMs).toBe(30 * MINUTO)
    })

    it('sem conexão ao começar, mostra o erro e continua na configuração', async () => {
      const hook = renderHook(() => useSessaoFoco())
      await aguardarServidor()
      servidor.ficarSemRede()

      await act(() => hook.result.current.iniciar())

      expect(hook.result.current.fase).toBe('configurando')
      expect(hook.result.current.erro).toMatch(/Não foi possível começar a sessão/)
      expect(hook.result.current.iniciando).toBe(false)
    })
  })
})
