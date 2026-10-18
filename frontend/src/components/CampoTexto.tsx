import { useId, useState, type InputHTMLAttributes } from 'react'

interface CampoTextoProps extends InputHTMLAttributes<HTMLInputElement> {
  rotulo: string
  erro?: string
}

export function CampoTexto({
  rotulo,
  erro,
  type = 'text',
  required,
  className = '',
  disabled,
  ...resto
}: CampoTextoProps) {
  const idGerado = useId()
  const id = resto.id ?? idGerado
  const idErro = `${id}-erro`

  const [mostrarSenha, setMostrarSenha] = useState(false)
  const ehCampoSenha = type === 'password'
  const tipoInputEfetivo = ehCampoSenha ? (mostrarSenha ? 'text' : 'password') : type

  return (
    <div className={`auth-campo ${className}`}>
      <label htmlFor={id} className="auth-rotulo">
        <span>
          {rotulo}
          {required && <span className="auth-rotulo-obrigatorio" aria-hidden="true">*</span>}
        </span>
      </label>

      <div className="auth-entrada-container">
        <input
          {...resto}
          id={id}
          type={tipoInputEfetivo}
          required={required}
          disabled={disabled}
          aria-invalid={Boolean(erro)}
          aria-describedby={erro ? idErro : undefined}
          className={`auth-entrada ${erro ? 'com-erro' : ''} ${ehCampoSenha ? 'com-icone-acao' : ''}`}
        />

        {ehCampoSenha && (
          <button
            type="button"
            className="auth-botao-visibilidade"
            onClick={() => setMostrarSenha((v) => !v)}
            disabled={disabled}
            aria-label={mostrarSenha ? 'Ocultar senha' : 'Mostrar senha'}
            title={mostrarSenha ? 'Ocultar senha' : 'Mostrar senha'}
          >
            {mostrarSenha ? (
              // Ícone Olho com traço
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
                <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" />
                <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" />
                <line x1="2" y1="2" x2="22" y2="22" />
              </svg>
            ) : (
              // Ícone Olho
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
                <circle cx="12" cy="12" r="3" />
              </svg>
            )}
          </button>
        )}
      </div>

      {erro && (
        <span id={idErro} role="alert" className="auth-erro-inline">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {erro}
        </span>
      )}
    </div>
  )
}
