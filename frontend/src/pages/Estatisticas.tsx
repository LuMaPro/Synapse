import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { conquistasApi } from '../services/conquistas'
import {
  buscarEstatisticas,
  type EstatisticasApi,
  type PeriodoEstatisticas,
} from '../services/estatisticas'
import '../styles/rede.css'
import '../styles/estatisticas.css'
import { amostraDaCor } from '../utils/efeitos'
import { formatarHoras } from '../utils/tempo'

const PERIODOS: { valor: PeriodoEstatisticas; rotulo: string }[] = [
  { valor: 'dia', rotulo: 'Hoje' },
  { valor: 'semana', rotulo: '7 dias' },
  { valor: 'mes', rotulo: '30 dias' },
]

// O SVG do gráfico recebe as cores como atributo: os mesmos valores dos tokens do CSS.
const COR_BARRA = '#8b7bff' // --cor-destaque
const COR_SEM_MATERIA = '#6b7097' // --cor-texto-fraco
const COR_EIXO = '#6b7097'
const COR_GRADE = '#2a2f55' // --cor-borda

const ESTILO_TOOLTIP = {
  contentStyle: {
    background: '#1c2042',
    border: '1px solid #2a2f55',
    borderRadius: 10,
    color: '#ecedf7',
  },
  itemStyle: { color: '#ecedf7' },
  labelStyle: { color: '#9ca1c6' },
}

interface Resultado {
  /** O período pedido: se mudar, o resultado fica velho até a nova resposta. */
  chave: string
  dados?: EstatisticasApi
  erro?: boolean
}

/** Rótulo de um dia do gráfico: o dia da semana, ou a data no período de 30 dias. */
function rotuloDoDia(data: string, periodo: PeriodoEstatisticas): string {
  const [ano, mes, dia] = data.split('-').map(Number)
  const dataLocal = new Date(ano, mes - 1, dia)
  if (periodo === 'mes') {
    return dataLocal.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
  }
  const semana = dataLocal.toLocaleDateString('pt-BR', { weekday: 'short' }).replace('.', '')
  return semana.charAt(0).toUpperCase() + semana.slice(1)
}

function Destaque({ rotulo, valor, classe }: { rotulo: string; valor: string; classe?: string }) {
  return (
    <div className="estatistica-destaque">
      <dt>{rotulo}</dt>
      <dd className={classe}>{valor}</dd>
    </div>
  )
}

/** Dashboard de estatísticas (issue #31): o tempo focado no período, por dia e por matéria. */
export function Estatisticas() {
  const [periodo, setPeriodo] = useState<PeriodoEstatisticas>('semana')
  const [tentativa, setTentativa] = useState(0)
  const [resultado, setResultado] = useState<Resultado | null>(null)
  const [sequencia, setSequencia] = useState<number | null>(null)
  const chave = `${periodo}|${tentativa}`

  useEffect(() => {
    // A sequência vem das conquistas (#32); sem ela, o resto da tela aparece mesmo assim.
    conquistasApi
      .consultar()
      .then((resposta) => setSequencia(resposta.sequencia.atual))
      .catch(() => {})
  }, [])

  useEffect(() => {
    let ativo = true
    buscarEstatisticas(periodo)
      .then((dados) => {
        if (ativo) setResultado({ chave, dados })
      })
      .catch(() => {
        if (ativo) setResultado({ chave, erro: true })
      })
    return () => {
      ativo = false
    }
  }, [chave, periodo])

  const carregando = resultado?.chave !== chave
  const dados = resultado?.dados

  let conteudo
  if (resultado?.erro && !carregando) {
    conteudo = (
      <div className="rede-mensagem" role="alert">
        <p>Não foi possível carregar suas estatísticas. Verifique sua conexão.</p>
        <button
          type="button"
          className="botao secundario"
          onClick={() => setTentativa((t) => t + 1)}
        >
          Tentar de novo
        </button>
      </div>
    )
  } else if (!dados) {
    conteudo = (
      <p className="rede-mensagem" role="status">
        Carregando suas estatísticas…
      </p>
    )
  } else {
    const barras = dados.por_dia.map((dia) => ({
      dia: rotuloDoDia(dia.data, dados.periodo),
      horas: Number((dia.minutos / 60).toFixed(1)),
    }))
    const fatias = dados.por_materia.map((materia) => ({
      chave: materia.materia_id ?? 'sem-materia',
      nome: materia.nome ?? 'Sem matéria',
      cor: materia.cor ?? COR_SEM_MATERIA,
      efeito: materia.efeito,
      minutos: materia.minutos,
      percentual: Math.round(materia.percentual * 100),
    }))

    conteudo = (
      <div className={carregando ? 'estatisticas-painel atualizando' : 'estatisticas-painel'}>
        <dl className="estatisticas-destaques">
          <Destaque rotulo="Tempo focado" valor={formatarHoras(dados.tempo_total_minutos)} />
          <Destaque
            rotulo="Taxa de sucesso"
            valor={`${Math.round(dados.taxa_sucesso * 100)}%`}
            classe="sucesso"
          />
          <Destaque
            rotulo="Sequência atual"
            valor={sequencia === null ? '—' : `${sequencia} ${sequencia === 1 ? 'dia' : 'dias'}`}
            classe="atp"
          />
          <Destaque
            rotulo="Melhor horário"
            valor={dados.melhor_horario === null ? '—' : `${dados.melhor_horario}h`}
          />
        </dl>

        <div className="estatisticas-graficos">
          <section className="estatisticas-cartao" aria-labelledby="titulo-por-dia">
            <h2 id="titulo-por-dia">Tempo focado por dia</h2>
            <div className="grafico-barras">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barras} margin={{ top: 8, right: 4, bottom: 0, left: -24 }}>
                  <CartesianGrid stroke={COR_GRADE} strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="dia"
                    stroke={COR_EIXO}
                    tickLine={false}
                    fontSize={12}
                    interval="preserveStartEnd"
                  />
                  <YAxis stroke={COR_EIXO} tickLine={false} fontSize={12} allowDecimals />
                  <Tooltip
                    {...ESTILO_TOOLTIP}
                    cursor={{ fill: 'rgb(139 123 255 / 8%)' }}
                    formatter={(valor) => [`${String(valor).replace('.', ',')} h`, 'Focado']}
                  />
                  <Bar dataKey="horas" fill={COR_BARRA} radius={[4, 4, 0, 0]} maxBarSize={48} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>

          <section className="estatisticas-cartao" aria-labelledby="titulo-por-materia">
            <h2 id="titulo-por-materia">Foco por matéria</h2>
            {fatias.length === 0 ? (
              <div className="rede-mensagem">
                <p>Nenhuma sessão concluída neste período.</p>
                <Link className="botao primario" to="/foco">
                  Começar a focar
                </Link>
              </div>
            ) : (
              <>
                <div className="grafico-rosca">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={fatias}
                        dataKey="minutos"
                        nameKey="nome"
                        innerRadius="60%"
                        outerRadius="95%"
                        paddingAngle={fatias.length > 1 ? 3 : 0}
                        stroke="none"
                      >
                        {fatias.map((fatia) => (
                          <Cell key={fatia.chave} fill={fatia.cor} />
                        ))}
                      </Pie>
                      <Tooltip
                        {...ESTILO_TOOLTIP}
                        formatter={(valor) => formatarHoras(Number(valor))}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <ul className="estatisticas-legenda">
                  {fatias.map((fatia) => (
                    <li key={fatia.chave}>
                      <i {...amostraDaCor(fatia.cor, fatia.efeito)} aria-hidden="true" />
                      <span className="legenda-nome">{fatia.nome}</span>
                      <span className="legenda-valor">
                        {formatarHoras(fatia.minutos)} · {fatia.percentual}%
                      </span>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </section>
        </div>
      </div>
    )
  }

  return (
    <section className="rede estatisticas" aria-busy={carregando}>
      <div className="rede-cabecalho">
        <h1>Estatísticas</h1>
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
