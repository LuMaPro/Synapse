import { Link } from 'react-router'
import type { MotivoPoda } from '../hooks/useSessaoFoco'
import { NOME_TIPO_NEURONIO, tipoNeuronio } from '../utils/neuronio'
import { formatarTempo } from '../utils/tempo'

interface ResultadoSessaoProps {
  sucesso: boolean
  duracaoMin: number
  motivoPoda: MotivoPoda | null
  decorridoMs: number
  onFocarDeNovo: () => void
}

/** Telas de fim de sessão: neurônio formado (sucesso) ou poda. */
export function ResultadoSessao({
  sucesso,
  duracaoMin,
  motivoPoda,
  decorridoMs,
  onFocarDeNovo,
}: ResultadoSessaoProps) {
  if (sucesso) {
    return (
      <section className="tela-sessao" aria-labelledby="resultado-titulo">
        <div className="centro">
          <p className="rotulo-campo texto-sucesso">Sessão concluída</p>
          <h1 id="resultado-titulo" className="titulo-resultado">
            Neurônio formado!
          </h1>
        </div>
        <p className="subtitulo-resultado">
          {NOME_TIPO_NEURONIO[tipoNeuronio(duracaoMin)]} · {duracaoMin} min
        </p>
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
      </div>
    </section>
  )
}
