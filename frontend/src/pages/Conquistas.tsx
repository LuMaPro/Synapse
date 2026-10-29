import { useConquistas } from '../hooks/useConquistas'
import type { ConquistaApi } from '../services/conquistas'
import '../styles/foco.css'
import '../styles/conquistas.css'

function formatarDataDesbloqueio(iso: string): string {
  const data = new Date(iso)
  return data.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

function CartaoConquista({ conquista }: { conquista: ConquistaApi }) {
  const porcentagem = Math.min(
    100,
    Math.max(0, Math.round((conquista.progresso / Math.max(1, conquista.meta)) * 100)),
  )

  return (
    <li
      className={`conquista-cartao ${conquista.desbloqueada ? 'desbloqueada' : 'bloqueada'}`}
      data-codigo={conquista.codigo}
    >
      <div className="conquista-icone" aria-hidden="true">
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M8 4h8v5a4 4 0 0 1-8 0V4ZM8 6H4.5a3.5 3.5 0 0 0 3.8 4M16 6h3.5a3.5 3.5 0 0 1-3.8 4M12 13v4M8.5 20h7" />
        </svg>
      </div>

      <div className="conquista-conteudo">
        <div className="conquista-topo">
          <h3>{conquista.nome}</h3>
          {conquista.desbloqueada && (
            <span className="selo conquista-selo-desbloqueada">Desbloqueada</span>
          )}
        </div>

        <p className="conquista-descricao">{conquista.descricao}</p>

        {conquista.desbloqueada ? (
          conquista.desbloqueada_em && (
            <p className="conquista-data texto-fraco">
              Desbloqueada em {formatarDataDesbloqueio(conquista.desbloqueada_em)}
            </p>
          )
        ) : (
          <div className="conquista-progresso-container">
            <div
              className="barra-progresso"
              role="progressbar"
              aria-valuenow={conquista.progresso}
              aria-valuemin={0}
              aria-valuemax={conquista.meta}
              aria-label={`Progresso da conquista ${conquista.nome}`}
            >
              <div className="progresso-preenchimento" style={{ width: `${porcentagem}%` }} />
            </div>
            <span className="conquista-progresso-texto texto-fraco">
              {conquista.progresso} / {conquista.meta} {conquista.unidade}
            </span>
          </div>
        )}
      </div>
    </li>
  )
}

export function Conquistas() {
  const { conquistas, sequencia, desbloqueadas, total, carregando, erro, recarregar } =
    useConquistas()

  return (
    <section className="conquistas-container" aria-labelledby="titulo-conquistas">
      <header className="conquistas-cabecalho">
        <div>
          <h1 id="titulo-conquistas">Conquistas</h1>
          <p className="conquistas-subtitulo texto-suave">
            {carregando
              ? 'Carregando suas conquistas…'
              : `${desbloqueadas} de ${total} desbloqueadas`}
          </p>
        </div>

        {sequencia && (
          <div className="conquistas-sequencia-painel">
            {sequencia.atual > 0 ? (
              <span className="selo sequencia" title={`Maior sequência: ${sequencia.recorde} dias`}>
                <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    fill="currentColor"
                    d="M12.5 2.5c.5 3-1.6 4.6-3 6.4C8.2 10.6 7 12.3 7 14.6A5 5 0 0 0 12 20a5 5 0 0 0 5-5.2c0-2.3-1.2-3.7-2.1-4.9-.3 1.3-1 2.2-2 2.6.6-2.9.4-6.6-.4-10Z"
                  />
                </svg>
                {sequencia.atual} {sequencia.atual === 1 ? 'dia seguido' : 'dias seguidos'}
              </span>
            ) : null}
            <span className="texto-fraco">
              Recorde: {sequencia.recorde} {sequencia.recorde === 1 ? 'dia' : 'dias'}
            </span>
          </div>
        )}
      </header>

      {carregando && (
        <p className="conquistas-mensagem" role="status">
          Carregando suas conquistas…
        </p>
      )}

      {erro && (
        <div className="conquistas-mensagem" role="alert">
          <p className="texto-perigo">{erro}</p>
          <button type="button" className="botao secundario" onClick={recarregar}>
            Tentar de novo
          </button>
        </div>
      )}

      {!carregando && !erro && conquistas.length === 0 && (
        <p className="conquistas-mensagem texto-fraco">Nenhuma conquista disponível.</p>
      )}

      {!carregando && !erro && conquistas.length > 0 && (
        <ul className="conquistas-grid" aria-label="Lista de conquistas">
          {conquistas.map((conquista) => (
            <CartaoConquista key={conquista.codigo} conquista={conquista} />
          ))}
        </ul>
      )}
    </section>
  )
}
