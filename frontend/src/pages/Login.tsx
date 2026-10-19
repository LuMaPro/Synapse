import { useContext, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { CampoTexto } from '../components/CampoTexto'
import { RedeFundo } from '../components/RedeFundo'
import { SimboloLogo } from '../components/SimboloLogo'
import { AuthContext } from '../contexts/authContextDef'
import { ApiError } from '../services/api'
import { AuthError, loginMock } from '../services/auth'
import '../styles/auth.css'

interface ErrosFormulario {
  email?: string
  senha?: string
}

export function Login() {
  const navigate = useNavigate()
  const auth = useContext(AuthContext)

  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [erros, setErros] = useState<ErrosFormulario>({})
  const [erroApi, setErroApi] = useState<string | null>(null)
  const [carregando, setCarregando] = useState(false)

  function validar(): boolean {
    const novosErros: ErrosFormulario = {}
    const emailLimpo = email.trim()

    if (!emailLimpo) {
      novosErros.email = 'O e-mail é obrigatório.'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailLimpo)) {
      novosErros.email = 'Digite um e-mail válido.'
    }

    // No login só se exige a senha: as regras de senha forte valem para criar senhas,
    // e quem confere se ela está certa é o servidor.
    if (!senha) {
      novosErros.senha = 'A senha é obrigatória.'
    }

    setErros(novosErros)
    return Object.keys(novosErros).length === 0
  }

  async function handleSubmit(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    setErroApi(null)

    if (!validar()) {
      return
    }

    setCarregando(true)

    try {
      if (auth) {
        await auth.login({ email, senha })
      } else {
        await loginMock({ email, senha })
      }
      navigate('/foco')
    } catch (erro) {
      if (erro instanceof AuthError || erro instanceof ApiError) {
        setErroApi(erro.message)
      } else if (erro instanceof Error) {
        setErroApi(erro.message)
      } else {
        setErroApi('Ocorreu um erro ao tentar entrar. Tente novamente.')
      }
    } finally {
      setCarregando(false)
    }
  }

  return (
    <div className="auth-container">
      <RedeFundo />

      <div className="auth-card">
        <header className="auth-cabecalho">
          <div className="auth-logo">
            <SimboloLogo tamanho={64} />
          </div>
          <div className="auth-titulo-marca">synapse</div>
          <p className="auth-subtitulo">Cada minuto de foco vira uma conexão.</p>
          <h1 className="auth-titulo-pagina">Entrar</h1>
        </header>

        {erroApi && (
          <div className="auth-alerta-erro" role="alert" aria-live="assertive">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>{erroApi}</span>
          </div>
        )}

        <form className="auth-formulario" onSubmit={handleSubmit} noValidate>
          <CampoTexto
            rotulo="E-mail"
            type="email"
            placeholder="seu@email.com"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value)
              if (erros.email) setErros((prev) => ({ ...prev, email: undefined }))
            }}
            erro={erros.email}
            disabled={carregando}
            autoComplete="email"
            required
          />

          <CampoTexto
            rotulo="Senha"
            type="password"
            placeholder="Sua senha secreta"
            value={senha}
            onChange={(e) => {
              setSenha(e.target.value)
              if (erros.senha) setErros((prev) => ({ ...prev, senha: undefined }))
            }}
            erro={erros.senha}
            disabled={carregando}
            autoComplete="current-password"
            required
          />

          <button
            type="submit"
            className="auth-botao-submit"
            disabled={carregando}
            aria-busy={carregando}
          >
            {carregando ? (
              <>
                <span className="auth-spinner" aria-hidden="true" />
                <span>Carregando...</span>
              </>
            ) : (
              'Entrar'
            )}
          </button>
        </form>

        <footer className="auth-rodape">
          <span>Não tem uma conta?</span>
          <Link to="/cadastro" className="auth-link">
            Cadastre-se
          </Link>
        </footer>
      </div>
    </div>
  )
}
