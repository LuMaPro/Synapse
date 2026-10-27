import { useEffect, useState, type FormEvent } from 'react'
import { PaletaCores } from '../components/PaletaCores'
import { useMaterias } from '../hooks/useMaterias'
import { lojaApi, PALETA_GRATUITA, type CorLojaApi } from '../services/loja'
import { CORES_MATERIAS, type Materia } from '../services/materias'
import '../styles/materias.css'
import { amostraDaCor } from '../utils/efeitos'

export function Materias() {
  const { materias, carregando, erro: erroListagem, criar, atualizar, remover } = useMaterias()
  // A paleta completa, com as cores da loja (#34); sem ela, as 8 gratuitas.
  const [paleta, setPaleta] = useState<CorLojaApi[]>(PALETA_GRATUITA)

  useEffect(() => {
    lojaApi
      .buscar()
      .then((loja) => setPaleta(loja.cores))
      .catch(() => {})
  }, [])

  // Estado do formulário de criação
  const [nomeNovo, setNomeNovo] = useState('')
  const [corNova, setCorNova] = useState<string>(CORES_MATERIAS[0].hex)
  const [salvandoNovo, setSalvandoNovo] = useState(false)
  const [erroCriacao, setErroCriacao] = useState<string | null>(null)

  // Estado de edição
  const [editandoId, setEditandoId] = useState<string | null>(null)
  const [nomeEdicao, setNomeEdicao] = useState('')
  const [corEdicao, setCorEdicao] = useState('')
  const [salvandoEdicao, setSalvandoEdicao] = useState(false)
  const [erroEdicao, setErroEdicao] = useState<string | null>(null)

  // Estado de exclusão
  const [excluindoId, setExcluindoId] = useState<string | null>(null)
  const [removendo, setRemovendo] = useState(false)
  const [erroExclusao, setErroExclusao] = useState<string | null>(null)

  async function handleCriar(e: FormEvent) {
    e.preventDefault()
    if (!nomeNovo.trim()) return

    setSalvandoNovo(true)
    setErroCriacao(null)
    try {
      await criar(nomeNovo, corNova)
      setNomeNovo('')
      setCorNova(CORES_MATERIAS[0].hex)
    } catch (err) {
      setErroCriacao(err instanceof Error ? err.message : 'Erro ao criar matéria.')
    } finally {
      setSalvandoNovo(false)
    }
  }

  function iniciarEdicao(materia: Materia) {
    setEditandoId(materia.id)
    setNomeEdicao(materia.nome)
    setCorEdicao(materia.cor)
    setErroEdicao(null)
    setExcluindoId(null)
  }

  function cancelarEdicao() {
    setEditandoId(null)
    setNomeEdicao('')
    setCorEdicao('')
    setErroEdicao(null)
  }

  async function handleSalvarEdicao(e: FormEvent) {
    e.preventDefault()
    if (!editandoId || !nomeEdicao.trim()) return

    setSalvandoEdicao(true)
    setErroEdicao(null)
    try {
      await atualizar(editandoId, { nome: nomeEdicao, cor: corEdicao })
      setEditandoId(null)
    } catch (err) {
      setErroEdicao(err instanceof Error ? err.message : 'Erro ao atualizar matéria.')
    } finally {
      setSalvandoEdicao(false)
    }
  }

  async function handleConfirmarExclusao(id: string) {
    setRemovendo(true)
    setErroExclusao(null)
    try {
      await remover(id)
      setExcluindoId(null)
    } catch (err) {
      setErroExclusao(err instanceof Error ? err.message : 'Erro ao excluir matéria.')
    } finally {
      setRemovendo(false)
    }
  }

  return (
    <section className="materias-container" aria-labelledby="titulo-materias">
      <div className="materias-cabecalho">
        <h1 id="titulo-materias">Matérias</h1>
        <p>Organize suas sessões de foco e a cor dos seus neurônios por disciplina.</p>
      </div>

      <form className="materia-form" onSubmit={handleCriar} aria-label="Cadastrar nova matéria">
        <h2>Nova matéria</h2>

        <div className="campo-grupo">
          <label htmlFor="nome-materia">Nome da matéria</label>
          <input
            id="nome-materia"
            type="text"
            className="entrada-texto"
            placeholder="Ex.: Cálculo I, POO, Física..."
            value={nomeNovo}
            onChange={(e) => setNomeNovo(e.target.value)}
            maxLength={100}
            required
            disabled={salvandoNovo}
          />
        </div>

        <div className="campo-grupo">
          <span className="rotulo-paleta" id="rotulo-cor-nova">
            Cor
          </span>
          <PaletaCores
            cores={paleta}
            valor={corNova}
            onEscolher={setCorNova}
            rotuloId="rotulo-cor-nova"
            desabilitada={salvandoNovo}
          />
        </div>

        {erroCriacao && (
          <p className="texto-perigo" role="alert">
            {erroCriacao}
          </p>
        )}

        <button
          type="submit"
          className="botao primario botao-pequeno"
          disabled={salvandoNovo || !nomeNovo.trim()}
        >
          {salvandoNovo ? 'Adicionando…' : 'Adicionar matéria'}
        </button>
      </form>

      <div className="materias-secao">
        <h2>Suas matérias</h2>

        {carregando && <p role="status">Carregando matérias…</p>}
        {erroListagem && (
          <p className="texto-perigo" role="alert">
            {erroListagem}
          </p>
        )}

        {!carregando && materias.length === 0 && (
          <div className="materias-vazia">
            <p>Você ainda não tem matérias cadastradas.</p>
            <p className="texto-fraco">
              Crie sua primeira matéria para associar às suas sessões de foco.
            </p>
          </div>
        )}

        {!carregando && materias.length > 0 && (
          <ul className="materias-lista">
            {materias.map((materia) => {
              const estaEditando = editandoId === materia.id
              const estaExcluindo = excluindoId === materia.id

              if (estaEditando) {
                return (
                  <li key={materia.id} className="materia-item">
                    <form
                      className="materia-edicao-form"
                      onSubmit={handleSalvarEdicao}
                      aria-label={`Editar matéria ${materia.nome}`}
                    >
                      <div className="campo-grupo">
                        <label htmlFor={`editar-nome-${materia.id}`}>Nome</label>
                        <input
                          id={`editar-nome-${materia.id}`}
                          type="text"
                          className="entrada-texto"
                          value={nomeEdicao}
                          onChange={(e) => setNomeEdicao(e.target.value)}
                          maxLength={100}
                          required
                          disabled={salvandoEdicao}
                        />
                      </div>

                      <div className="campo-grupo">
                        <span className="rotulo-paleta" id={`rotulo-cor-${materia.id}`}>
                          Cor
                        </span>
                        <PaletaCores
                          cores={paleta}
                          valor={corEdicao}
                          onEscolher={setCorEdicao}
                          rotuloId={`rotulo-cor-${materia.id}`}
                          desabilitada={salvandoEdicao}
                        />
                      </div>

                      {erroEdicao && (
                        <p className="texto-perigo" role="alert">
                          {erroEdicao}
                        </p>
                      )}

                      <div className="botoes-edicao">
                        <button
                          type="submit"
                          className="botao primario botao-pequeno"
                          disabled={salvandoEdicao || !nomeEdicao.trim()}
                        >
                          {salvandoEdicao ? 'Salvando…' : 'Salvar'}
                        </button>
                        <button
                          type="button"
                          className="botao secundario botao-pequeno"
                          onClick={cancelarEdicao}
                          disabled={salvandoEdicao}
                        >
                          Cancelar
                        </button>
                      </div>
                    </form>
                  </li>
                )
              }

              return (
                <li key={materia.id} className="materia-item">
                  <div className="materia-linha">
                    <div className="materia-info">
                      <i
                        {...amostraDaCor(materia.cor, materia.efeito, 'indicador-cor')}
                        aria-hidden="true"
                      />
                      <span>{materia.nome}</span>
                    </div>

                    <div className="materia-acoes">
                      <button
                        type="button"
                        className="botao-acao"
                        aria-label={`Editar ${materia.nome}`}
                        onClick={() => iniciarEdicao(materia)}
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        className="botao-acao texto-perigo"
                        aria-label={`Excluir ${materia.nome}`}
                        onClick={() => {
                          setExcluindoId(materia.id)
                          setErroExclusao(null)
                          setEditandoId(null)
                        }}
                      >
                        Excluir
                      </button>
                    </div>
                  </div>

                  {estaExcluindo && (
                    <div
                      className="materia-confirmacao-exclusao"
                      role="region"
                      aria-label="Confirmar exclusão"
                    >
                      <p>
                        Deseja excluir a matéria <strong>{materia.nome}</strong>?
                      </p>
                      <p className="texto-fraco">
                        As sessões de foco e neurônios já concluídos continuarão existindo sem esta
                        etiqueta.
                      </p>

                      {erroExclusao && (
                        <p className="texto-perigo" role="alert">
                          {erroExclusao}
                        </p>
                      )}

                      <div className="botoes-confirmacao">
                        <button
                          type="button"
                          className="botao secundario texto-perigo botao-pequeno"
                          onClick={() => handleConfirmarExclusao(materia.id)}
                          disabled={removendo}
                        >
                          {removendo ? 'Excluindo…' : 'Sim, excluir'}
                        </button>
                        <button
                          type="button"
                          className="botao fantasma botao-pequeno"
                          onClick={() => setExcluindoId(null)}
                          disabled={removendo}
                        >
                          Cancelar
                        </button>
                      </div>
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </section>
  )
}
