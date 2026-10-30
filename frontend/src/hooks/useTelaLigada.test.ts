import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { telaLigadaSuportada, useTelaLigada } from './useTelaLigada'

/** Wake Lock falsa: guarda as travas pedidas e deixa o teste soltá-las. */
function simularWakeLock({ recusar = false } = {}) {
  const travas: { solta: boolean; soltar: () => void }[] = []
  const request = vi.fn(async () => {
    if (recusar) throw new DOMException('Bateria fraca', 'NotAllowedError')
    const ouvintes: (() => void)[] = []
    const trava = {
      solta: false,
      soltar() {
        trava.solta = true
        ouvintes.forEach((ouvinte) => ouvinte())
      },
      release: vi.fn(async () => trava.soltar()),
      addEventListener: (_: string, ouvinte: () => void) => ouvintes.push(ouvinte),
    }
    travas.push(trava)
    return trava
  })
  Object.defineProperty(navigator, 'wakeLock', { configurable: true, value: { request } })
  return { request, travas }
}

function definirVisibilidade(estado: 'visible' | 'hidden') {
  Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => estado })
  act(() => {
    document.dispatchEvent(new Event('visibilitychange'))
  })
}

describe('useTelaLigada', () => {
  beforeEach(() => {
    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      get: () => 'visible',
    })
  })

  afterEach(() => {
    Reflect.deleteProperty(navigator, 'wakeLock')
    Reflect.deleteProperty(document, 'visibilityState')
  })

  it('mantém a tela ligada só enquanto a sessão está ativa', async () => {
    const { request, travas } = simularWakeLock()
    const { rerender } = renderHook(({ ativo }) => useTelaLigada(ativo), {
      initialProps: { ativo: false },
    })
    expect(request).not.toHaveBeenCalled()

    rerender({ ativo: true })
    await waitFor(() => expect(request).toHaveBeenCalledWith('screen'))

    rerender({ ativo: false })
    expect(travas[0].solta).toBe(true)
  })

  it('pede a trava de novo quando o estudante volta para a página', async () => {
    const { request, travas } = simularWakeLock()
    renderHook(() => useTelaLigada(true))
    await waitFor(() => expect(request).toHaveBeenCalledTimes(1))

    // Trocar de app ou bloquear a tela: o navegador solta a trava sozinho.
    definirVisibilidade('hidden')
    act(() => travas[0].soltar())
    expect(request).toHaveBeenCalledTimes(1)

    definirVisibilidade('visible')
    await waitFor(() => expect(request).toHaveBeenCalledTimes(2))
  })

  it('não pede outra trava se a anterior continua valendo', async () => {
    const { request } = simularWakeLock()
    renderHook(() => useTelaLigada(true))
    await waitFor(() => expect(request).toHaveBeenCalledTimes(1))

    definirVisibilidade('visible')

    expect(request).toHaveBeenCalledTimes(1)
  })

  it('solta a trava ao sair da tela de foco', async () => {
    const { request, travas } = simularWakeLock()
    const { unmount } = renderHook(() => useTelaLigada(true))
    await waitFor(() => expect(request).toHaveBeenCalled())

    unmount()

    expect(travas[0].solta).toBe(true)
  })

  it('se o navegador recusar, a sessão segue sem a trava', async () => {
    const { request } = simularWakeLock({ recusar: true })

    renderHook(() => useTelaLigada(true))

    await waitFor(() => expect(request).toHaveBeenCalled())
  })

  it('sem suporte, não faz nada', () => {
    expect(telaLigadaSuportada()).toBe(false)
    expect(() => renderHook(() => useTelaLigada(true))).not.toThrow()
  })
})
