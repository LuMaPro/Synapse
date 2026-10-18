/**
 * Fundo decorativo com rede neural bioluminescente interativa (docs/design/prototipo.html).
 * Ocupa todo o background da tela de autenticação:
 *  - Sinapses e neurônios cobrem toda a área da viewport
 *  - O texto e formulário ficam diretamente sobre o fundo
 *  - Nós e conexões acendem e reagem suavemente ao cursor em qualquer ponto da tela
 */

import { useEffect, useRef } from 'react'

// ─── Paleta (tokens de docs/design/README.md) ──────────────────────────────
const COR_SINAPSE_INATIVA = 'rgba(42, 47, 85, 0.55)'
const COR_CIANO = '#3ee6e0'
const COR_VIOLETA = '#8b7bff'
const COR_VERDE = '#5be49b'
const COR_AMBAR = '#ffc857'
const CORES_NO = [COR_CIANO, COR_VIOLETA, COR_VERDE, COR_AMBAR, COR_CIANO, COR_VIOLETA]

// ─── Configuração ───────────────────────────────────────────────────────────
const RAIO_CONEXAO = 180     // px — distância máxima para desenhar sinapse
const RAIO_MOUSE = 150       // px — raio de influência do cursor
const VELOCIDADE_BASE = 0.28 // px/frame — velocidade de deriva dos nós
const RAIO_NO_BASE = 4.5     // px — raio padrão dos nós
const RAIO_NO_MAX = 8.5      // px — raio máximo ao ser ativado pelo mouse
const PULSO_AMPLITUDE = 0.9  // px — amplitude de pulsação natural
const PULSO_VELOCIDADE = 0.012
const REPULSAO = 18          // px — magnitude máxima de repulsão pelo cursor

interface No {
  x: number
  y: number
  vx: number
  vy: number
  raio: number
  cor: string
  fase: number   // fase do pulso de brilho (0–2π)
  brilho: number // 0..1 — intensidade do glow atual
}

function criarNo(largura: number, altura: number, i: number): No {
  const angulo = Math.random() * Math.PI * 2
  const speed = VELOCIDADE_BASE * (0.6 + Math.random() * 0.8)
  return {
    x: Math.random() * largura,
    y: Math.random() * altura,
    vx: Math.cos(angulo) * speed,
    vy: Math.sin(angulo) * speed,
    raio: RAIO_NO_BASE + Math.random() * 2,
    cor: CORES_NO[i % CORES_NO.length],
    fase: Math.random() * Math.PI * 2,
    brilho: 0,
  }
}

function hexParaRgb(hex: string): [number, number, number] {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return [r, g, b]
}

export function RedeFundo() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let nos: No[] = []
    let rafId = 0
    let pausado = false
    let mouseX = -9999
    let mouseY = -9999

    // ── Dimensionamento ──────────────────────────────────────────────────
    const dpr = Math.min(window.devicePixelRatio ?? 1, 2)

    function redimensionar() {
      if (!canvas || !ctx) return
      const rect = canvas.getBoundingClientRect()
      canvas.width = rect.width * dpr
      canvas.height = rect.height * dpr
      ctx.scale(dpr, dpr)

      // Número de nós proporcional à área para cobrir toda a tela
      const nAlvo = Math.min(Math.max(Math.round((rect.width * rect.height) / 22000), 24), 48)

      if (nos.length === 0) {
        nos = Array.from({ length: nAlvo }, (_, i) =>
          criarNo(rect.width, rect.height, i),
        )
      } else if (nos.length < nAlvo) {
        const adicionais = Array.from({ length: nAlvo - nos.length }, (_, i) =>
          criarNo(rect.width, rect.height, nos.length + i),
        )
        nos.push(...adicionais)
      } else if (nos.length > nAlvo) {
        nos.length = nAlvo
      }

      for (const no of nos) {
        if (no.x > rect.width) no.x = Math.random() * rect.width
        if (no.y > rect.height) no.y = Math.random() * rect.height
      }
    }

    const observer = new ResizeObserver(redimensionar)
    observer.observe(canvas)
    redimensionar()

    // ── Tracking global do mouse (janela inteira) ────────────────────────
    function onMouseMove(e: MouseEvent) {
      if (!canvas) return
      const rect = canvas.getBoundingClientRect()
      mouseX = e.clientX - rect.left
      mouseY = e.clientY - rect.top
    }
    function onMouseLeave() {
      mouseX = -9999
      mouseY = -9999
    }

    window.addEventListener('mousemove', onMouseMove, { passive: true })
    document.addEventListener('mouseleave', onMouseLeave)
    window.addEventListener('blur', onMouseLeave)

    // ── Visibilidade ─────────────────────────────────────────────────────
    function onVisibility() {
      pausado = document.hidden
      if (!pausado) tick()
    }
    document.addEventListener('visibilitychange', onVisibility)

    // ── Loop principal ───────────────────────────────────────────────────
    function tick() {
      if (pausado) return
      rafId = requestAnimationFrame(tick)

      const W = canvas!.getBoundingClientRect().width
      const H = canvas!.getBoundingClientRect().height

      // Limpa com fundo transparente
      ctx!.clearRect(0, 0, W, H)

      // ── Atualiza nós ──
      for (const no of nos) {
        no.fase += PULSO_VELOCIDADE

        // Distância ao cursor
        const dx = mouseX - no.x
        const dy = mouseY - no.y
        const dist = Math.sqrt(dx * dx + dy * dy)
        const influencia = dist < RAIO_MOUSE ? 1 - dist / RAIO_MOUSE : 0

        // Atualiza brilho com suavização
        const brilhoAlvo = influencia
        no.brilho += (brilhoAlvo - no.brilho) * 0.08

        // Repulsão suave — empurra para longe do cursor
        if (influencia > 0) {
          const forca = (influencia * REPULSAO) / Math.max(dist, 1)
          no.vx -= (dx / dist) * forca * 0.03
          no.vy -= (dy / dist) * forca * 0.03
        }

        // Amortecimento
        no.vx *= 0.985
        no.vy *= 0.985

        // Velocidade mínima para manter flutuação
        const speed = Math.sqrt(no.vx * no.vx + no.vy * no.vy)
        if (speed < VELOCIDADE_BASE * 0.4) {
          no.vx += (Math.random() - 0.5) * 0.08
          no.vy += (Math.random() - 0.5) * 0.08
        }

        // Move
        no.x += no.vx
        no.y += no.vy

        // Bounce suave nas bordas
        if (no.x < 10) { no.x = 10; no.vx = Math.abs(no.vx) }
        if (no.x > W - 10) { no.x = W - 10; no.vx = -Math.abs(no.vx) }
        if (no.y < 10) { no.y = 10; no.vy = Math.abs(no.vy) }
        if (no.y > H - 10) { no.y = H - 10; no.vy = -Math.abs(no.vy) }
      }

      // ── Desenha sinapses ──
      for (let i = 0; i < nos.length; i++) {
        for (let j = i + 1; j < nos.length; j++) {
          const a = nos[i]
          const b = nos[j]
          const dx = b.x - a.x
          const dy = b.y - a.y
          const dist = Math.sqrt(dx * dx + dy * dy)
          if (dist > RAIO_CONEXAO) continue

          const opacidadeDistancia = 1 - dist / RAIO_CONEXAO
          const ativacao = Math.max(a.brilho, b.brilho)

          const alphaInativo = opacidadeDistancia * 0.5
          const alphaAtivo = opacidadeDistancia * ativacao * 0.95

          // Fade sutil apenas nas margens externas da tela
          const cx = (a.x + b.x) / 2
          const cy = (a.y + b.y) / 2
          const margemX = Math.min(cx / 35, (W - cx) / 35, 1)
          const margemY = Math.min(cy / 35, (H - cy) / 35, 1)
          const fadeBorda = Math.max(0.15, Math.min(margemX, margemY, 1))

          // Sinapse inativa
          ctx!.beginPath()
          ctx!.moveTo(a.x, a.y)
          ctx!.lineTo(b.x, b.y)
          ctx!.strokeStyle = COR_SINAPSE_INATIVA
          ctx!.lineWidth = 1.1
          ctx!.globalAlpha = alphaInativo * fadeBorda
          ctx!.stroke()

          // Sinapse ativa (brilhante quando o mouse está próximo)
          if (ativacao > 0.05) {
            const [r, g, b2] = hexParaRgb(COR_CIANO)
            ctx!.beginPath()
            ctx!.moveTo(a.x, a.y)
            ctx!.lineTo(b.x, b.y)
            ctx!.strokeStyle = `rgba(${r},${g},${b2},1)`
            ctx!.lineWidth = 1.6
            ctx!.globalAlpha = alphaAtivo * fadeBorda
            ctx!.shadowBlur = 8
            ctx!.shadowColor = COR_CIANO
            ctx!.stroke()
            ctx!.shadowBlur = 0
          }

          ctx!.globalAlpha = 1
        }
      }

      // ── Desenha nós ──
      for (const no of nos) {
        const pulso = Math.sin(no.fase) * PULSO_AMPLITUDE
        const raioAtual = no.raio + pulso + no.brilho * (RAIO_NO_MAX - no.raio)

        // Fade sutil nas margens externas
        const margemX = Math.min(no.x / 30, (W - no.x) / 30, 1)
        const margemY = Math.min(no.y / 30, (H - no.y) / 30, 1)
        const fadeBorda = Math.max(0.2, Math.min(margemX, margemY, 1))

        const [r, g, b] = hexParaRgb(no.cor)
        const alphaBase = (0.55 + no.brilho * 0.45) * fadeBorda
        const glowSize = 12 + no.brilho * 20

        ctx!.globalAlpha = alphaBase

        // Glow externo bioluminescente
        if (no.brilho > 0.05 || Math.sin(no.fase) > 0.4) {
          const grad = ctx!.createRadialGradient(
            no.x, no.y, 0,
            no.x, no.y, raioAtual * 4,
          )
          grad.addColorStop(0, `rgba(${r},${g},${b},0.5)`)
          grad.addColorStop(1, `rgba(${r},${g},${b},0)`)
          ctx!.beginPath()
          ctx!.arc(no.x, no.y, raioAtual * 4, 0, Math.PI * 2)
          ctx!.fillStyle = grad
          ctx!.fill()
        }

        // Núcleo do nó
        ctx!.beginPath()
        ctx!.arc(no.x, no.y, raioAtual, 0, Math.PI * 2)
        ctx!.fillStyle = `rgba(${r},${g},${b},1)`
        ctx!.shadowBlur = glowSize
        ctx!.shadowColor = no.cor
        ctx!.fill()
        ctx!.shadowBlur = 0

        ctx!.globalAlpha = 1
      }
    }

    tick()

    return () => {
      cancelAnimationFrame(rafId)
      observer.disconnect()
      window.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseleave', onMouseLeave)
      window.removeEventListener('blur', onMouseLeave)
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="auth-fundo-rede"
      aria-hidden="true"
    />
  )
}
