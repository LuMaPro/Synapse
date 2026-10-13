import { useState } from 'react'
import { AnelProgresso } from '../components/AnelProgresso'
import { AvisoSaida } from '../components/AvisoSaida'
import { DialogoDesistir } from '../components/DialogoDesistir'
import { ResultadoSessao } from '../components/ResultadoSessao'
import { SeletorDuracao } from '../components/SeletorDuracao'
import { SeletorModo } from '../components/SeletorModo'
import { PROPORCAO_TOLERANCIA, useSessaoFoco } from '../hooks/useSessaoFoco'
import '../styles/foco.css'
import { formatarTempo } from '../utils/tempo'

const MS_POR_MINUTO = 60_000

export function Foco() {
  const sessao = useSessaoFoco()
  const [confirmandoDesistencia, setConfirmandoDesistencia] = useState(false)

  if (sessao.fase === 'configurando') {
    return (
      <section className="foco">
        <h1>Focar</h1>
        <SeletorDuracao
          minutos={sessao.duracaoMin}
          podeDiminuir={sessao.podeDiminuir}
          podeAumentar={sessao.podeAumentar}
          onDiminuir={sessao.diminuirDuracao}
          onAumentar={sessao.aumentarDuracao}
        />
        <SeletorModo
          modo={sessao.modo}
          toleranciaMs={sessao.duracaoMin * MS_POR_MINUTO * PROPORCAO_TOLERANCIA}
          onEscolher={sessao.escolherModo}
        />
        <button type="button" className="botao primario" onClick={sessao.iniciar}>
          Começar a focar
        </button>
      </section>
    )
  }

  if (sessao.fase === 'em_andamento') {
    return (
      <section className="tela-sessao" aria-label="Sessão de foco">
        <p className="selo">Modo {sessao.modo}</p>
        {/* Lugar do neurônio crescendo (issue #19) */}
        <AnelProgresso progresso={sessao.progresso} tamanho={260} />
        <div className="centro">
          <p className="timer numero" role="timer" aria-label="Tempo restante">
            {formatarTempo(sessao.restanteMs)}
          </p>
          <p className="texto-fraco">
            de {formatarTempo(sessao.duracaoMin * MS_POR_MINUTO)} · seu neurônio está crescendo
          </p>
        </div>
        <AvisoSaida modo={sessao.modo} toleranciaRestanteMs={sessao.toleranciaRestanteMs} />
        <button
          type="button"
          className="botao fantasma"
          onClick={() => setConfirmandoDesistencia(true)}
        >
          Desistir
        </button>
        {confirmandoDesistencia && (
          <DialogoDesistir
            onContinuar={() => setConfirmandoDesistencia(false)}
            onDesistir={() => {
              setConfirmandoDesistencia(false)
              sessao.desistir()
            }}
          />
        )}
      </section>
    )
  }

  return (
    <ResultadoSessao
      sucesso={sessao.fase === 'concluida'}
      duracaoMin={sessao.duracaoMin}
      motivoPoda={sessao.motivoPoda}
      decorridoMs={sessao.decorridoMs}
      onFocarDeNovo={() => {
        setConfirmandoDesistencia(false)
        sessao.focarDeNovo()
      }}
    />
  )
}
