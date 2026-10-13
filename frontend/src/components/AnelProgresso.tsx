import type { ReactNode } from 'react'

// Mesmas proporções do anel do protótipo (docs/design/prototipo.html, tela de foco).
const LADO = 168
const RAIO = 72
const CIRCUNFERENCIA = 2 * Math.PI * RAIO

interface AnelProgressoProps {
  /** De 0 (vazio) a 1 (completo). */
  progresso: number
  /** Largura e altura em px. */
  tamanho?: number
  children?: ReactNode
}

/** Anel que se preenche no sentido horário, com conteúdo no centro. */
export function AnelProgresso({ progresso, tamanho = LADO, children }: AnelProgressoProps) {
  const limitado = Math.min(1, Math.max(0, progresso))

  return (
    <div className="anel" style={{ width: tamanho, height: tamanho }}>
      <svg viewBox={`0 0 ${LADO} ${LADO}`} aria-hidden="true" focusable="false">
        <circle className="anel-trilho" cx={LADO / 2} cy={LADO / 2} r={RAIO} />
        <circle
          className="anel-preenchimento"
          cx={LADO / 2}
          cy={LADO / 2}
          r={RAIO}
          strokeDasharray={CIRCUNFERENCIA}
          strokeDashoffset={CIRCUNFERENCIA * (1 - limitado)}
        />
      </svg>
      <div className="anel-conteudo">{children}</div>
    </div>
  )
}
