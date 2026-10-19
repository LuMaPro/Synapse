import { useContext, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { CampoTexto } from '../components/CampoTexto'
import { RedeFundo } from '../components/RedeFundo'
import { SimboloLogo } from '../components/SimboloLogo'
import { AuthContext } from '../contexts/authContextDef'
import { ApiError } from '../services/api'
import { AuthError, cadastroMock } from '../services/auth'
import { SENHA_TAMANHO_MINIMO, validarSenhaNova } from '../utils/senha'
import '../styles/auth.css'

interface ErrosFormulario {
  nome?: string
  email?: string
  senha?: string
}

export function Cadastro() {
  const navigate = useNavigate()
  const auth = useContext(AuthContext)

  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [erros, setErros] = useState<ErrosFormulario>({})
  const [erroApi, setErroApi] = useState<string | null>(null)
  const [carregando, setCarregando] = useState(false)

  function validar(): boolean {
    const novosErros: ErrosFormulario = {}
    const nomeLimpo = nome.trim()
    const emailLimpo = email.trim()

    if (!nomeLimpo) {
      novosErros.nome = 'O nome é obrigatório.'
    }

    if (!emailLimpo) {
      novosErros.email = 'O e-mail é obrigatório.'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailLimpo)) {
      novosErros.email = 'Digite um e-mail válido.'
    }

    const erroSenha = validarSenhaNova(senha)
    if (erroSenha) {
      novosErros.senha = erroSenha
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
        await auth.cadastro({ nome, email, senha })
      } else {
        await cadastroMock({ nome, email, senha })
      }
      navigate('/foco')
    } catch (erro) {
      if (erro instanceof AuthError || erro instanceof ApiError) {
        setErroApi(erro.message)
      } else if (erro instanceof Error) {
        setErroApi(erro.message)
      } else {
        setErroApi('Ocorreu um erro ao criar a conta. Tente novamente.')
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
          <p className="auth-subtitulo">Junte-se e transforme cada minuto em foco.</p>
          <h1 className="auth-titulo-pagina">Criar conta</h1>
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
            rotulo="Nome"
            type="text"
            placeholder="Seu nome completo"
            value={nome}
            onChange={(e) => {
              setNome(e.target.value)
              if (erros.nome) setErros((prev) => ({ ...prev, nome: undefined }))
            }}
            erro={erros.nome}
            disabled={carregando}
            autoComplete="name"
            required
          />

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
            placeholder={`Mínimo de ${SENHA_TAMANHO_MINIMO} caracteres`}
            value={senha}
            onChange={(e) => {
              setSenha(e.target.value)
              if (erros.senha) setErros((prev) => ({ ...prev, senha: undefined }))
            }}
            erro={erros.senha}
            disabled={carregando}
            autoComplete="new-password"
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
              'Criar conta'
            )}
          </button>
        </form>

        <footer className="auth-rodape">
          <span>Já tem uma conta?</span>
          <Link to="/login" className="auth-link">
            Faça login
          </Link>
        </footer>
      </div>
    </div>
  )
}
