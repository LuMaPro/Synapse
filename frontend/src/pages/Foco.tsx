import { useState } from 'react'
import { AvisoSaida } from '../components/AvisoSaida'
import { DialogoDesistir } from '../components/DialogoDesistir'
import { NeuronioAnimado } from '../components/NeuronioAnimado'
import { ResultadoSessao } from '../components/ResultadoSessao'
import { SeletorDuracao } from '../components/SeletorDuracao'
import { SeletorMateria } from '../components/SeletorMateria'
import { SeletorModo } from '../components/SeletorModo'
import { useDeteccaoSaida } from '../hooks/useDeteccaoSaida'
import { useMaterias } from '../hooks/useMaterias'
import {
  MINIMO_PARA_REGISTRO_MS,
  PROPORCAO_TOLERANCIA,
  useSessaoFoco,
} from '../hooks/useSessaoFoco'
import { telaLigadaSuportada, useTelaLigada } from '../hooks/useTelaLigada'
import '../styles/foco.css'
import { tipoNeuronio } from '../utils/neuronio'
import { amostraDaCor } from '../utils/efeitos'
import { formatarTempo } from '../utils/tempo'

const MS_POR_MINUTO = 60_000

export function Foco() {
  const sessao = useSessaoFoco()
  const { materias } = useMaterias()
  const [confirmandoDesistencia, setConfirmandoDesistencia] = useState(false)
  const { foraDaTelaCheia } = useDeteccaoSaida(sessao.fase === 'em_andamento', {
    onSaida: sessao.sairDaTela,
    onRetorno: sessao.voltarParaTela,
  })
  // No celular, a tela apagar sozinha contaria como saída (issue #35).
  useTelaLigada(sessao.fase === 'em_andamento')

  const materiaAtual = materias.find((m) => m.id === sessao.materiaId)

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
        <SeletorMateria
          materias={materias}
          materiaId={sessao.materiaId}
          onEscolher={sessao.escolherMateria}
          disabled={sessao.iniciando}
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
        <p className="selo">
          {materiaAtual && (
            <i {...amostraDaCor(materiaAtual.cor, materiaAtual.efeito)} aria-hidden="true" />
          )}
          {materiaAtual ? `${materiaAtual.nome} · Modo ${sessao.modo}` : `Modo ${sessao.modo}`}
        </p>
        <NeuronioAnimado
          tipo={tipoNeuronio(sessao.duracaoMin)}
          progresso={sessao.progresso}
          cor={materiaAtual?.cor}
          efeito={materiaAtual?.efeito}
        />
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
              telaSempreLigada={telaLigadaSuportada()}
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
            curta={sessao.decorridoMs < MINIMO_PARA_REGISTRO_MS}
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
      cor={materiaAtual?.cor}
      efeito={materiaAtual?.efeito}
      nomeMateria={materiaAtual?.nome}
      atp={sessao.conclusao?.atp}
      onFocarDeNovo={() => {
        setConfirmandoDesistencia(false)
        sessao.focarDeNovo()
      }}
    />
  )
}
