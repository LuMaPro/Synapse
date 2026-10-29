import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useDeteccaoSaida } from './useDeteccaoSaida'

// O jsdom não troca de aba nem tem tela cheia de verdade: os testes simulam o que o
// navegador informa (visibilityState, fullscreenElement, hasFocus) e disparam os eventos.

function definirAba(estado: 'visible' | 'hidden') {
  Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => estado })
  act(() => {
    document.dispatchEvent(new Event('visibilitychange'))
  })
}

function definirTelaCheia(emTelaCheia: boolean) {
  Object.defineProperty(document, 'fullscreenElement', {
    configurable: true,
    get: () => (emTelaCheia ? document.documentElement : null),
  })
  act(() => {
    document.dispatchEvent(new Event('fullscreenchange'))
  })
}

function dispararNaJanela(tipo: string) {
  act(() => {
    window.dispatchEvent(new Event(tipo))
  })
}

function renderizar(ativo = true) {
  const onSaida = vi.fn()
  const onRetorno = vi.fn()
  const hook = renderHook(({ ativo }) => useDeteccaoSaida(ativo, { onSaida, onRetorno }), {
    initialProps: { ativo },
  })
  return { ...hook, onSaida, onRetorno }
}

describe('useDeteccaoSaida', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date('2026-10-13T14:00:00Z'))
    vi.spyOn(document, 'hasFocus').mockReturnValue(true)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
    Reflect.deleteProperty(document, 'visibilityState')
    Reflect.deleteProperty(document, 'fullscreenElement')
  })

  it('trocar de aba é uma saída, e voltar é um retorno, com os horários', () => {
    const { onSaida, onRetorno } = renderizar()

    definirAba('hidden')
    expect(onSaida).toHaveBeenCalledExactlyOnceWith(Date.now())

    vi.setSystemTime(Date.now() + 7_000)
    definirAba('visible')
    expect(onRetorno).toHaveBeenCalledExactlyOnceWith(Date.now())
  })

  it('no celular, trocar de app ou bloquear a tela é uma saída (issue #35)', () => {
    const { onSaida, onRetorno } = renderizar()

    // Os dois casos chegam igual à página: ela fica escondida e, na volta, visível.
    // O navegador também tira o foco da janela, mas é a mesma saída.
    dispararNaJanela('blur')
    definirAba('hidden')
    expect(onSaida).toHaveBeenCalledOnce()

    vi.setSystemTime(Date.now() + 30_000)
    definirAba('visible')
    expect(onRetorno).toHaveBeenCalledExactlyOnceWith(Date.now())
  })

  it('outra janela ou app recebendo o foco também é uma saída', () => {
    const { onSaida, onRetorno } = renderizar()

    dispararNaJanela('blur')
    expect(onSaida).toHaveBeenCalledOnce()

    dispararNaJanela('focus')
    expect(onRetorno).toHaveBeenCalledOnce()
  })

  it('sinais que chegam juntos contam como uma saída só', () => {
    const { onSaida, onRetorno } = renderizar()
    vi.mocked(document.hasFocus).mockReturnValue(false)

    dispararNaJanela('blur')
    definirAba('hidden')
    expect(onSaida).toHaveBeenCalledOnce()

    definirAba('visible')
    expect(onRetorno).not.toHaveBeenCalled() // a janela ainda está sem foco

    dispararNaJanela('focus')
    expect(onRetorno).toHaveBeenCalledOnce()
  })

  it('ao voltar para a aba com a janela em foco, não espera o evento focus', () => {
    const { onRetorno } = renderizar()

    dispararNaJanela('blur')
    definirAba('hidden')
    definirAba('visible') // hasFocus() é true: comum no celular, onde o focus nem vem

    expect(onRetorno).toHaveBeenCalledOnce()
  })

  it('clicar na página prova que a janela tem o foco', () => {
    const { onRetorno } = renderizar()

    dispararNaJanela('blur')
    dispararNaJanela('pointerdown')

    expect(onRetorno).toHaveBeenCalledOnce()
  })

  it('sair da tela cheia é uma saída, e voltar para ela é um retorno', () => {
    const { result, onSaida, onRetorno } = renderizar()
    definirTelaCheia(true)

    definirTelaCheia(false)
    expect(onSaida).toHaveBeenCalledOnce()
    expect(result.current.foraDaTelaCheia).toBe(true)

    definirTelaCheia(true)
    expect(onRetorno).toHaveBeenCalledOnce()
    expect(result.current.foraDaTelaCheia).toBe(false)
  })

  it('sem nunca ter entrado em tela cheia (ex.: iPhone), não acusa saída por ela', () => {
    const { result, onSaida } = renderizar()

    definirTelaCheia(false)

    expect(onSaida).not.toHaveBeenCalled()
    expect(result.current.foraDaTelaCheia).toBe(false)
  })

  it('fechar ou recarregar a página pede o aviso nativo do navegador', () => {
    renderizar()
    const evento = new Event('beforeunload', { cancelable: true })

    window.dispatchEvent(evento)

    expect(evento.defaultPrevented).toBe(true)
  })

  it('fora de uma sessão, não observa nada nem bloqueia a saída da página', () => {
    const { onSaida } = renderizar(false)
    const evento = new Event('beforeunload', { cancelable: true })

    definirAba('hidden')
    dispararNaJanela('blur')
    window.dispatchEvent(evento)

    expect(onSaida).not.toHaveBeenCalled()
    expect(evento.defaultPrevented).toBe(false)
  })

  it('para de observar quando a sessão termina', () => {
    const { rerender, onSaida } = renderizar()

    rerender({ ativo: false })
    definirAba('hidden')

    expect(onSaida).not.toHaveBeenCalled()
  })

  it('usa sempre a versão mais recente dos callbacks', () => {
    const primeiro = vi.fn()
    const segundo = vi.fn()
    const { rerender } = renderHook(
      ({ onSaida }) => useDeteccaoSaida(true, { onSaida, onRetorno: () => {} }),
      { initialProps: { onSaida: primeiro } },
    )

    rerender({ onSaida: segundo })
    definirAba('hidden')

    expect(primeiro).not.toHaveBeenCalled()
    expect(segundo).toHaveBeenCalledOnce()
  })
})
