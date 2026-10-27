import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router'
import { GrafoRede } from '../components/GrafoRede'
import { NeuronioAnimado } from '../components/NeuronioAnimado'
import { listarMaterias, type Materia } from '../services/materias'
import { buscarRede, type NeuronioRede, type RedeApi } from '../services/rede'
import '../styles/foco.css'
import '../styles/rede.css'
import { amostraDaCor } from '../utils/efeitos'
import { inicioDoPeriodo, type Periodo } from '../utils/redeNeural'

const PERIODOS: { valor: Periodo; rotulo: string }[] = [
  { valor: 'sempre', rotulo: 'Sempre' },
  { valor: '7', rotulo: '7 dias' },
  { valor: '30', rotulo: '30 dias' },
]

interface Resultado {
  /** Os filtros pedidos: se mudarem, o resultado fica velho até a nova resposta. */
  chave: string
  rede?: RedeApi
  erro?: boolean
}

function plural(quantidade: number, singular: string, plural: string): string {
  return `${quantidade} ${quantidade === 1 ? singular : plural}`
}

/** Tela da rede neural do estudante (issue #26), no desenho do protótipo (docs/design). */
export function Rede() {
  const [periodo, setPeriodo] = useState<Periodo>('sempre')
  const [materiaId, setMateriaId] = useState<string | null>(null)
  const [materias, setMaterias] = useState<Materia[]>([])
  const [tentativa, setTentativa] = useState(0)
  const [resultado, setResultado] = useState<Resultado | null>(null)
  const chave = `${periodo}|${materiaId ?? ''}|${tentativa}`

  useEffect(() => {
    // Sem as matérias, a rede aparece mesmo assim, com as cores dos tipos.
    listarMaterias()
      .then(setMaterias)
      .catch(() => {})
  }, [])

  useEffect(() => {
    let ativo = true
    buscarRede({ de: inicioDoPeriodo(periodo), materiaId: materiaId ?? undefined })
      .then((rede) => {
        if (ativo) setResultado({ chave, rede })
      })
      .catch(() => {
        if (ativo) setResultado({ chave, erro: true })
      })
    return () => {
      ativo = false
    }
  }, [chave, periodo, materiaId])

  const materiaPorId = useMemo(() => new Map(materias.map((m) => [m.id, m])), [materias])
  const corDe = useCallback(
    (n: NeuronioRede) => (n.materia_id && materiaPorId.get(n.materia_id)?.cor) || n.cor,
    [materiaPorId],
  )
  const efeitoDe = useCallback(
    (n: NeuronioRede) => (n.materia_id && materiaPorId.get(n.materia_id)?.efeito) || null,
    [materiaPorId],
  )
  const nomeDaMateria = useCallback(
    (n: NeuronioRede) => (n.materia_id ? (materiaPorId.get(n.materia_id)?.nome ?? null) : null),
    [materiaPorId],
  )

  const carregando = resultado?.chave !== chave
  const rede = resultado?.rede
  const comFiltro = periodo !== 'sempre' || materiaId !== null

  function verTudo() {
    setPeriodo('sempre')
    setMateriaId(null)
  }

  let conteudo
  if (resultado?.erro && !carregando) {
    conteudo = (
      <div className="rede-mensagem" role="alert">
        <p>Não foi possível carregar sua rede. Verifique sua conexão.</p>
        <button
          type="button"
          className="botao secundario"
          onClick={() => setTentativa((t) => t + 1)}
        >
          Tentar de novo
        </button>
      </div>
    )
  } else if (!rede) {
    conteudo = (
      <p className="rede-mensagem" role="status">
        Carregando sua rede…
      </p>
    )
  } else if (rede.neuronios.length === 0 && !comFiltro) {
    conteudo = (
      <div className="rede-vazia">
        <NeuronioAnimado tipo="piramidal" progresso={0.12} tamanho={150} />
        <h2>Seu primeiro neurônio está esperando</h2>
        <p>Cada sessão de foco concluída vira um neurônio, e eles se ligam formando sua rede.</p>
        <Link className="botao primario" to="/foco">
          Começar a focar
        </Link>
      </div>
    )
  } else if (rede.neuronios.length === 0) {
    conteudo = (
      <div className="rede-mensagem">
        <p>Nenhum neurônio neste filtro.</p>
        <button type="button" className="botao secundario" onClick={verTudo}>
          Ver a rede toda
        </button>
      </div>
    )
  } else {
    conteudo = (
      <>
        <div className={carregando ? 'rede-grafo atualizando' : 'rede-grafo'}>
          <GrafoRede
            // Filtro novo, rede nova: recomeça o zoom e o realce.
            key={resultado?.chave}
            neuronios={rede.neuronios}
            sinapses={rede.sinapses}
            corDe={corDe}
            efeitoDe={efeitoDe}
            nomeDaMateria={nomeDaMateria}
          />
        </div>
        <p className="rede-legenda">Toque num neurônio para acender suas conexões</p>
      </>
    )
  }

  return (
    <section className="rede" aria-busy={carregando}>
      <div className="rede-cabecalho">
        <h1>Sua rede</h1>
        {rede && rede.neuronios.length > 0 && (
          <span className="rede-resumo">
            {plural(rede.neuronios.length, 'neurônio', 'neurônios')} ·{' '}
            {plural(rede.sinapses.length, 'sinapse', 'sinapses')}
          </span>
        )}
      </div>

      <div className="filtros" role="group" aria-label="Período">
        {PERIODOS.map(({ valor, rotulo }) => (
          <button
            key={valor}
            type="button"
            className="chip"
            aria-pressed={periodo === valor}
            onClick={() => setPeriodo(valor)}
          >
            {rotulo}
          </button>
        ))}
      </div>
      {materias.length > 0 && (
        <div className="filtros" role="group" aria-label="Matéria">
          <button
            type="button"
            className="chip"
            aria-pressed={materiaId === null}
            onClick={() => setMateriaId(null)}
          >
            Tudo
          </button>
          {materias.map((materia) => (
            <button
              key={materia.id}
              type="button"
              className="chip"
              aria-pressed={materiaId === materia.id}
              onClick={() => setMateriaId(materia.id)}
            >
              <i {...amostraDaCor(materia.cor, materia.efeito)} aria-hidden="true" />
              {materia.nome}
            </button>
          ))}
        </div>
      )}

      {conteudo}
    </section>
  )
}
