import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router'
import { listarMaterias, type Materia } from '../services/materias'
import { buscarHistorico, type SessaoApi } from '../services/sessoes'
import '../styles/foco.css'
import '../styles/rede.css'
import '../styles/historico.css'
import { amostraDaCor } from '../utils/efeitos'
import { agruparPorDia, descreverResultado, horaDoInicio } from '../utils/historico'
import { COR_PADRAO_TIPO_NEURONIO, NOME_TIPO_NEURONIO, tipoNeuronio } from '../utils/neuronio'
import { inicioDoPeriodo, type Periodo } from '../utils/redeNeural'

/** Sessões por página: a primeira enche a tela, e "Carregar mais" traz as seguintes. */
export const TAMANHO_PAGINA = 20

type FiltroStatus = 'todas' | 'concluida' | 'podada'

const STATUS: { valor: FiltroStatus; rotulo: string }[] = [
  { valor: 'todas', rotulo: 'Todas' },
  { valor: 'concluida', rotulo: 'Concluídas' },
  { valor: 'podada', rotulo: 'Podadas' },
]

const PERIODOS: { valor: Periodo; rotulo: string }[] = [
  { valor: 'sempre', rotulo: 'Sempre' },
  { valor: '7', rotulo: '7 dias' },
  { valor: '30', rotulo: '30 dias' },
]

interface Resultado {
  /** Os filtros pedidos: se mudarem, o resultado fica velho até a nova resposta. */
  chave: string
  sessoes: SessaoApi[]
  total: number
  pagina: number
  paginas: number
  erro?: boolean
}

function plural(quantidade: number, singular: string, plural: string): string {
  return `${quantidade} ${quantidade === 1 ? singular : plural}`
}

function ItemSessao({ sessao, materia }: { sessao: SessaoApi; materia?: Materia }) {
  const tipo = tipoNeuronio(sessao.duracao_minutos)
  const podada = sessao.estado === 'podada'
  // A mesma cor do neurônio na rede: a da matéria (com o efeito, se for da loja) ou,
  // sem matéria, a do tipo; podada, cinza.
  const cor = podada ? 'var(--cor-podado)' : (materia?.cor ?? COR_PADRAO_TIPO_NEURONIO[tipo])
  const efeito = podada ? null : materia?.efeito

  return (
    <li className={`sessao-item ${sessao.estado}`}>
      <span {...amostraDaCor(cor, efeito, 'sessao-cor')} aria-hidden="true" />
      <div className="sessao-info">
        <span className="sessao-materia">{materia?.nome ?? 'Sem matéria'}</span>
        <span className="sessao-detalhes">
          <time dateTime={sessao.inicio}>{horaDoInicio(sessao)}</time> ·{' '}
          <span className="numero">{sessao.duracao_minutos} min</span> · {NOME_TIPO_NEURONIO[tipo]}
        </span>
      </div>
      <span className="sessao-resultado">{descreverResultado(sessao)}</span>
    </li>
  )
}

/** Histórico de sessões do estudante (issue #29): a lista, dia a dia, com filtros. */
export function Historico() {
  const [status, setStatus] = useState<FiltroStatus>('todas')
  const [periodo, setPeriodo] = useState<Periodo>('sempre')
  const [materias, setMaterias] = useState<Materia[]>([])
  const [tentativa, setTentativa] = useState(0)
  const [resultado, setResultado] = useState<Resultado | null>(null)
  const [carregandoMais, setCarregandoMais] = useState(false)
  const chave = `${status}|${periodo}|${tentativa}`
  // Os filtros em que "Carregar mais" falhou: em outro filtro, o aviso some.
  const [falhouAoCarregarMaisEm, setFalhouAoCarregarMaisEm] = useState<string | null>(null)

  useEffect(() => {
    // Sem as matérias, o histórico aparece mesmo assim, com "Sem matéria".
    listarMaterias()
      .then(setMaterias)
      .catch(() => {})
  }, [])

  useEffect(() => {
    let ativo = true
    buscarHistorico({
      de: inicioDoPeriodo(periodo),
      status: status === 'todas' ? undefined : status,
      tamanho: TAMANHO_PAGINA,
    })
      .then(({ resultados, total, pagina, paginas }) => {
        if (ativo) setResultado({ chave, sessoes: resultados, total, pagina, paginas })
      })
      .catch(() => {
        if (ativo) setResultado({ chave, sessoes: [], total: 0, pagina: 0, paginas: 0, erro: true })
      })
    return () => {
      ativo = false
    }
  }, [chave, periodo, status])

  const materiaPorId = useMemo(() => new Map(materias.map((m) => [m.id, m])), [materias])
  const dias = useMemo(() => agruparPorDia(resultado?.sessoes ?? []), [resultado])

  const carregando = resultado?.chave !== chave
  const comFiltro = status !== 'todas' || periodo !== 'sempre'

  async function carregarMais() {
    if (!resultado) return
    const pedido = resultado
    setCarregandoMais(true)
    setFalhouAoCarregarMaisEm(null)
    try {
      const pagina = await buscarHistorico({
        de: inicioDoPeriodo(periodo),
        status: status === 'todas' ? undefined : status,
        pagina: pedido.pagina + 1,
        tamanho: TAMANHO_PAGINA,
      })
      setResultado((atual) => {
        // O filtro mudou enquanto a página vinha: ela já não serve.
        if (atual?.chave !== pedido.chave) return atual
        // Uma sessão nova empurra as outras para a página seguinte; sem repetir.
        const vistas = new Set(atual.sessoes.map((s) => s.id))
        return {
          ...atual,
          sessoes: [...atual.sessoes, ...pagina.resultados.filter((s) => !vistas.has(s.id))],
          total: pagina.total,
          pagina: pagina.pagina,
          paginas: pagina.paginas,
        }
      })
    } catch {
      setFalhouAoCarregarMaisEm(pedido.chave)
    } finally {
      setCarregandoMais(false)
    }
  }

  function verTudo() {
    setStatus('todas')
    setPeriodo('sempre')
  }

  let conteudo
  if (resultado?.erro && !carregando) {
    conteudo = (
      <div className="rede-mensagem" role="alert">
        <p>Não foi possível carregar seu histórico. Verifique sua conexão.</p>
        <button
          type="button"
          className="botao secundario"
          onClick={() => setTentativa((t) => t + 1)}
        >
          Tentar de novo
        </button>
      </div>
    )
  } else if (!resultado) {
    conteudo = (
      <p className="rede-mensagem" role="status">
        Carregando seu histórico…
      </p>
    )
  } else if (resultado.sessoes.length === 0 && !comFiltro) {
    conteudo = (
      <div className="rede-mensagem">
        <p>Você ainda não fez nenhuma sessão de foco.</p>
        <Link className="botao primario" to="/foco">
          Começar a focar
        </Link>
      </div>
    )
  } else if (resultado.sessoes.length === 0) {
    conteudo = (
      <div className="rede-mensagem">
        <p>Nenhuma sessão neste filtro.</p>
        <button type="button" className="botao secundario" onClick={verTudo}>
          Ver todas as sessões
        </button>
      </div>
    )
  } else {
    conteudo = (
      <div className={carregando ? 'historico-lista atualizando' : 'historico-lista'}>
        {dias.map((dia) => (
          <section key={dia.chave} className="historico-dia" aria-label={dia.rotulo}>
            <h2>{dia.rotulo}</h2>
            <ul>
              {dia.sessoes.map((sessao) => (
                <ItemSessao
                  key={sessao.id}
                  sessao={sessao}
                  materia={sessao.materia_id ? materiaPorId.get(sessao.materia_id) : undefined}
                />
              ))}
            </ul>
          </section>
        ))}
        {resultado.pagina < resultado.paginas && (
          <div className="historico-mais">
            {falhouAoCarregarMaisEm === chave && (
              <p role="alert">Não foi possível carregar mais sessões.</p>
            )}
            <button
              type="button"
              className="botao secundario"
              onClick={carregarMais}
              disabled={carregandoMais || carregando}
            >
              {carregandoMais ? 'Carregando…' : 'Carregar mais'}
            </button>
          </div>
        )}
      </div>
    )
  }

  return (
    <section className="rede historico" aria-busy={carregando || carregandoMais}>
      <div className="rede-cabecalho">
        <h1>Histórico</h1>
        {resultado && resultado.total > 0 && (
          <span className="rede-resumo">{plural(resultado.total, 'sessão', 'sessões')}</span>
        )}
      </div>

      <div className="filtros" role="group" aria-label="Resultado">
        {STATUS.map(({ valor, rotulo }) => (
          <button
            key={valor}
            type="button"
            className="chip"
            aria-pressed={status === valor}
            onClick={() => setStatus(valor)}
          >
            {rotulo}
          </button>
        ))}
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

      {conteudo}
    </section>
  )
}
