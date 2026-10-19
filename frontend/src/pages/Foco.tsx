import { useState } from 'react'
import { AvisoSaida } from '../components/AvisoSaida'
import { DialogoDesistir } from '../components/DialogoDesistir'
import { NeuronioAnimado } from '../components/NeuronioAnimado'
import { ResultadoSessao } from '../components/ResultadoSessao'
import { SeletorDuracao } from '../components/SeletorDuracao'
import { SeletorModo } from '../components/SeletorModo'
import { useDeteccaoSaida } from '../hooks/useDeteccaoSaida'
import { PROPORCAO_TOLERANCIA, useSessaoFoco } from '../hooks/useSessaoFoco'
import '../styles/foco.css'
import { tipoNeuronio } from '../utils/neuronio'
import { formatarTempo } from '../utils/tempo'

const MS_POR_MINUTO = 60_000

export function Foco() {
  const sessao = useSessaoFoco()
  const [confirmandoDesistencia, setConfirmandoDesistencia] = useState(false)
  const { foraDaTelaCheia } = useDeteccaoSaida(sessao.fase === 'em_andamento', {
    onSaida: sessao.sairDaTela,
    onRetorno: sessao.voltarParaTela,
  })

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
        <button
          type="button"
          className="botao primario"
          onClick={sessao.iniciar}
          disabled={sessao.iniciando}
        >
          {sessao.iniciando ? 'Começando…' : 'Começar a focar'}
        </button>
        {sessao.erro && (
          <p className="texto-perigo" role="alert">
            {sessao.erro}
          </p>
        )}
      </section>
    )
  }

  if (sessao.fase === 'em_andamento' || sessao.fase === 'concluindo') {
    const concluindo = sessao.fase === 'concluindo'
    return (
      <section className="tela-sessao" aria-label="Sessão de foco">
        <p className="selo">Modo {sessao.modo}</p>
        <NeuronioAnimado tipo={tipoNeuronio(sessao.duracaoMin)} progresso={sessao.progresso} />
        <div className="centro">
          <p className="timer numero" role="timer" aria-label="Tempo restante">
            {formatarTempo(sessao.restanteMs)}
          </p>
          <p className="texto-fraco">
            de {formatarTempo(sessao.duracaoMin * MS_POR_MINUTO)} · seu neurônio está crescendo
          </p>
        </div>
        {concluindo ? (
          <p className="texto-suave" role="status">
            {sessao.semConexao
              ? 'Sem conexão. Seu neurônio será salvo assim que a internet voltar.'
              : 'Salvando seu neurônio…'}
          </p>
        ) : (
          <>
            <AvisoSaida
              modo={sessao.modo}
              toleranciaRestanteMs={sessao.toleranciaRestanteMs}
              foraDaTelaCheia={foraDaTelaCheia}
              onVoltarParaTelaCheia={sessao.voltarParaTelaCheia}
            />
            <button
              type="button"
              className="botao fantasma"
              onClick={() => setConfirmandoDesistencia(true)}
            >
              Desistir
            </button>
          </>
        )}
        {!concluindo && confirmandoDesistencia && (
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
      progresso={sessao.progresso}
      onFocarDeNovo={() => {
        setConfirmandoDesistencia(false)
        sessao.focarDeNovo()
      }}
    />
  )
}
