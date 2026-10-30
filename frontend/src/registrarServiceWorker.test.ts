import { afterEach, describe, expect, it, vi } from 'vitest'
import { registrarServiceWorker } from './registrarServiceWorker'

describe('registrarServiceWorker', () => {
  afterEach(() => {
    Reflect.deleteProperty(navigator, 'serviceWorker')
  })

  function simularServiceWorker() {
    const register = vi.fn().mockResolvedValue({})
    Object.defineProperty(navigator, 'serviceWorker', { configurable: true, value: { register } })
    return register
  }

  it('no build de produção, registra o /sw.js quando a página termina de carregar', () => {
    const register = simularServiceWorker()

    registrarServiceWorker(true)
    expect(register).not.toHaveBeenCalled()
    window.dispatchEvent(new Event('load'))

    expect(register).toHaveBeenCalledWith('/sw.js')
  })

  it('em desenvolvimento, não registra (o cache atrapalharia)', () => {
    const register = simularServiceWorker()

    registrarServiceWorker(false)
    window.dispatchEvent(new Event('load'))

    expect(register).not.toHaveBeenCalled()
  })

  it('sem suporte a service worker, o app segue normal', () => {
    expect(() => registrarServiceWorker(true)).not.toThrow()
  })
})
