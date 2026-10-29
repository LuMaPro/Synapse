import type { KeyboardEvent } from 'react'

interface DialogoDesistirProps {
  /** Ainda não passou de 5 minutos: a sessão desistida não fica no histórico. */
  curta: boolean
  onContinuar: () => void
  onDesistir: () => void
}

/**
 * Confirmação antes de desistir. A ação recomendada (continuar) é o botão de
 * destaque e já vem com o foco; Esc também continua a sessão.
 */
export function DialogoDesistir({ curta, onContinuar, onDesistir }: DialogoDesistirProps) {
  function aoTeclar(evento: KeyboardEvent) {
    if (evento.key === 'Escape') onContinuar()
  }

  return (
    <div className="dialogo-fundo">
      <div
        className="dialogo"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="dialogo-desistir-titulo"
        aria-describedby="dialogo-desistir-texto"
        onKeyDown={aoTeclar}
      >
        <h2 id="dialogo-desistir-titulo">Desistir agora?</h2>
        <p id="dialogo-desistir-texto" className="texto-suave">
          Seu neurônio vai morrer.{' '}
          {curta
            ? 'Com menos de 5 minutos, a sessão não fica no histórico.'
            : 'A sessão conta como podada e não entra na sua rede.'}
        </p>
        <button type="button" className="botao primario" onClick={onContinuar} autoFocus>
          Continuar focando
        </button>
        <button type="button" className="botao secundario texto-perigo" onClick={onDesistir}>
          Desistir e podar
        </button>
      </div>
    </div>
  )
}
