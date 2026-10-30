import { Link } from 'react-router'
import type { MotivoPoda } from '../hooks/useSessaoFoco'
import type { ConquistaApi } from '../services/conquistas'
import type { Efeito } from '../utils/efeitos'
import { NOME_TIPO_NEURONIO, tipoNeuronio } from '../utils/neuronio'
import { formatarTempo } from '../utils/tempo'
import { NeuronioAnimado } from './NeuronioAnimado'

interface ResultadoSessaoProps {
  sucesso: boolean
  duracaoMin: number
  motivoPoda: MotivoPoda | null
  decorridoMs: number
  /** Quanto o neurônio tinha crescido quando a sessão terminou. */
  progresso: number
  /** Cor da matéria selecionada na sessão (#28). */
  cor?: string
  /** Animação da cor da matéria, se for uma cor com efeito da loja (#34). */
  efeito?: Efeito | null
  /** Nome da matéria selecionada na sessão (#28). */
  nomeMateria?: string | null
  /** ATP ganho com a sessão concluída (#34). */
  atp?: number | null
  /** Conquistas desbloqueadas nesta sessão (#33). */
  conquistasNovas?: Array<Pick<ConquistaApi, 'codigo' | 'nome'>>
  onFocarDeNovo: () => void
}

/** Telas de fim de sessão: neurônio formado (sucesso) ou poda. */
export function ResultadoSessao({
  sucesso,
  duracaoMin,
  motivoPoda,
  decorridoMs,
  progresso,
  cor,
  efeito,
  nomeMateria,
  atp,
  conquistasNovas,
  onFocarDeNovo,
}: ResultadoSessaoProps) {
  const tipo = tipoNeuronio(duracaoMin)

  if (sucesso) {
    return (
      <section className="tela-sessao" aria-labelledby="resultado-titulo">
        <div className="centro">
          <p className="rotulo-campo texto-sucesso">Sessão concluída</p>
          <h1 id="resultado-titulo" className="titulo-resultado">
            Neurônio formado!
          </h1>
        </div>
        <NeuronioAnimado
          tipo={tipo}
          progresso={1}
          brilho="forte"
          tamanho={240}
          cor={cor}
          efeito={efeito}
        />
        <p className="subtitulo-resultado">
          {NOME_TIPO_NEURONIO[tipo]} · {duracaoMin} min
          {nomeMateria ? ` · ${nomeMateria}` : ''}
        </p>
        {atp ? <span className="selo atp">+{atp} ATP</span> : null}
        {conquistasNovas && conquistasNovas.length > 0 && (
          <div className="toasts-conquistas" aria-label="Conquistas desbloqueadas">
            {conquistasNovas.map((c) => (
              <div
                key={c.codigo}
                className="toast"
                role="status"
                aria-label={`Conquista desbloqueada: ${c.nome}`}
              >
                <span className="icone" aria-hidden="true">
                  <svg
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M8 4h8v5a4 4 0 0 1-8 0V4ZM8 6H4.5a3.5 3.5 0 0 0 3.8 4M16 6h3.5a3.5 3.5 0 0 1-3.8 4M12 13v4M8.5 20h7" />
                  </svg>
                </span>
                <div>
                  <b>Conquista desbloqueada</b>
                  <span>{c.nome}</span>
                </div>
              </div>
            ))}
          </div>
        )}
        <div className="acoes">
          <Link className="botao primario" to="/rede">
            Ver na minha rede
          </Link>
          <button type="button" className="botao fantasma" onClick={onFocarDeNovo}>
            Focar de novo
          </button>
        </div>
      </section>
    )
  }

  const acao = motivoPoda === 'saiu' ? 'saiu da tela' : 'desistiu'

  return (
    <section className="tela-sessao" aria-labelledby="resultado-titulo">
      <div className="centro">
        <p className="rotulo-campo texto-perigo">Poda sináptica</p>
        <h1 id="resultado-titulo" className="titulo-resultado">
          A conexão se perdeu
        </h1>
      </div>
      <NeuronioAnimado tipo={tipo} progresso={progresso} podado tamanho={240} cor={cor} />
      <div className="centro">
        <p className="texto-suave">
          Você {acao} aos <b className="numero texto-forte">{formatarTempo(decorridoMs)}</b>.
        </p>
        <p className="texto-fraco">Acontece, o importante é voltar.</p>
      </div>
      <div className="acoes">
        <button type="button" className="botao primario" onClick={onFocarDeNovo}>
          Tentar de novo
        </button>
        <Link className="botao fantasma" to="/historico">
          Ver histórico
        </Link>
      </div>
    </section>
  )
}
