import { render } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { RedeFundo } from './RedeFundo'

// O jsdom não desenha em canvas: um contexto 2D falso registra o que seria desenhado.
function criarContextoFalso() {
  const tracos: string[] = []
  const contexto = {
    strokeStyle: '',
    fillStyle: '' as unknown,
    lineWidth: 1,
    globalAlpha: 1,
    shadowBlur: 0,
    shadowColor: '',
    scale: vi.fn(),
    clearRect: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    arc: vi.fn(),
    fill: vi.fn(),
    stroke: vi.fn(() => tracos.push(contexto.strokeStyle)),
    createRadialGradient: vi.fn(() => ({ addColorStop: vi.fn() })),
  }
  return { contexto, tracos }
}

const SINAPSE_ACESA = 'rgba(62,230,224,1)'

describe('RedeFundo', () => {
  let ctx: ReturnType<typeof criarContextoFalso>
  let quadros: FrameRequestCallback[]
  let tamanho: { width: number; height: number }
  let aoRedimensionar: () => void
  let desconectar: ReturnType<typeof vi.fn>
  let oculto: boolean

  /** Roda o próximo quadro da animação, como o navegador faria. */
  function proximoQuadro() {
    const quadro = quadros.shift()
    quadro?.(0)
  }

  /** Quantos neurônios o último quadro desenhou (o núcleo; o brilho em volta é maior). */
  function neuroniosDesenhados() {
    return ctx.contexto.arc.mock.calls.filter(([, , raio]) => raio < 12).length
  }

  beforeEach(() => {
    ctx = criarContextoFalso()
    quadros = []
    tamanho = { width: 800, height: 600 }
    oculto = false
    desconectar = vi.fn()
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(
      ctx.contexto as unknown as CanvasRenderingContext2D,
    )
    vi.spyOn(HTMLCanvasElement.prototype, 'getBoundingClientRect').mockImplementation(
      () => ({ ...tamanho, left: 0, top: 0 }) as DOMRect,
    )
    vi.stubGlobal('requestAnimationFrame', (quadro: FrameRequestCallback) => {
      quadros.push(quadro)
      return quadros.length
    })
    vi.stubGlobal('cancelAnimationFrame', vi.fn())
    vi.stubGlobal(
      'ResizeObserver',
      class {
        constructor(callback: () => void) {
          aoRedimensionar = callback
        }
        observe() {}
        disconnect = desconectar
      },
    )
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => oculto })
    // Todos os neurônios começam no centro, para o cursor ficar perto deles.
    vi.spyOn(Math, 'random').mockReturnValue(0.5)
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => false })
  })

  it('desenha os neurônios e as sinapses no canvas, sem ser lido por leitores de tela', () => {
    const { container } = render(<RedeFundo />)

    expect(container.querySelector('canvas')).toHaveAttribute('aria-hidden', 'true')
    expect(ctx.contexto.clearRect).toHaveBeenCalledWith(0, 0, 800, 600)
    // 800 x 600 pede o mínimo de 24 neurônios.
    expect(neuroniosDesenhados()).toBe(24)
    expect(ctx.tracos.length).toBeGreaterThan(0)
    expect(ctx.tracos).not.toContain(SINAPSE_ACESA)
  })

  it('o cursor perto dos neurônios acende as sinapses', () => {
    render(<RedeFundo />)

    window.dispatchEvent(new MouseEvent('mousemove', { clientX: 420, clientY: 300 }))
    ctx.tracos.length = 0
    proximoQuadro()

    expect(ctx.tracos).toContain(SINAPSE_ACESA)
  })

  it('o cursor saindo da janela apaga as sinapses aos poucos', () => {
    render(<RedeFundo />)
    window.dispatchEvent(new MouseEvent('mousemove', { clientX: 420, clientY: 300 }))
    proximoQuadro()

    window.dispatchEvent(new Event('blur'))
    for (let i = 0; i < 60; i++) proximoQuadro()
    ctx.tracos.length = 0
    proximoQuadro()

    expect(ctx.tracos.length).toBeGreaterThan(0)
    expect(ctx.tracos).not.toContain(SINAPSE_ACESA)
  })

  it('pausa com a aba escondida e volta quando ela reaparece', () => {
    render(<RedeFundo />)

    oculto = true
    document.dispatchEvent(new Event('visibilitychange'))
    ctx.contexto.clearRect.mockClear()
    proximoQuadro()
    expect(ctx.contexto.clearRect).not.toHaveBeenCalled()
    expect(quadros).toHaveLength(0)

    oculto = false
    document.dispatchEvent(new Event('visibilitychange'))
    expect(ctx.contexto.clearRect).toHaveBeenCalled()
    expect(quadros).toHaveLength(1)
  })

  it('ajusta o número de neurônios ao tamanho da tela', () => {
    render(<RedeFundo />)

    // Tela grande: o máximo de 48 neurônios.
    tamanho = { width: 1920, height: 1080 }
    aoRedimensionar()
    ctx.contexto.arc.mockClear()
    proximoQuadro()
    expect(neuroniosDesenhados()).toBe(48)

    // Volta para a tela pequena: os que sobram saem, e os de fora da tela voltam para dentro.
    tamanho = { width: 800, height: 600 }
    aoRedimensionar()
    ctx.contexto.arc.mockClear()
    proximoQuadro()
    expect(neuroniosDesenhados()).toBe(24)
    for (const [x, y] of ctx.contexto.arc.mock.calls) {
      expect(x).toBeLessThanOrEqual(800)
      expect(y).toBeLessThanOrEqual(600)
    }
  })

  it('para a animação e solta os eventos ao sair da tela', () => {
    const removerDaJanela = vi.spyOn(window, 'removeEventListener')
    const removerDoDocumento = vi.spyOn(document, 'removeEventListener')
    const { unmount } = render(<RedeFundo />)

    unmount()

    expect(cancelAnimationFrame).toHaveBeenCalled()
    expect(desconectar).toHaveBeenCalled()
    expect(removerDaJanela).toHaveBeenCalledWith('mousemove', expect.any(Function))
    expect(removerDaJanela).toHaveBeenCalledWith('blur', expect.any(Function))
    expect(removerDoDocumento).toHaveBeenCalledWith('visibilitychange', expect.any(Function))
  })
})
