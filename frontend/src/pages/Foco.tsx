import { useEffect, useRef, useState } from 'react'
import { AvisoSaida } from '../components/AvisoSaida'
import { DialogoDesistir } from '../components/DialogoDesistir'
import { NeuronioAnimado } from '../components/NeuronioAnimado'
import { ResultadoSessao } from '../components/ResultadoSessao'
import { SeletorDuracao } from '../components/SeletorDuracao'
import { SeletorMateria } from '../components/SeletorMateria'
import { SeletorModo } from '../components/SeletorModo'
import { useConquistas } from '../hooks/useConquistas'
import { useDeteccaoSaida } from '../hooks/useDeteccaoSaida'
import { useMaterias } from '../hooks/useMaterias'
import { PROPORCAO_TOLERANCIA, useSessaoFoco } from '../hooks/useSessaoFoco'
import { conquistasApi, type ConquistaApi } from '../services/conquistas'
import '../styles/foco.css'
import { amostraDaCor } from '../utils/efeitos'
import { tipoNeuronio } from '../utils/neuronio'
import { formatarTempo } from '../utils/tempo'

const MS_POR_MINUTO = 60_000

export function Foco() {
  const sessao = useSessaoFoco()
  const { materias } = useMaterias()
  const { conquistas, sequencia, recarregar: recarregarConquistas } = useConquistas()
  const [confirmandoDesistencia, setConfirmandoDesistencia] = useState(false)
  const [conquistasNovas, setConquistasNovas] = useState<ConquistaApi[]>([])
  const conquistasDesbloqueadasAntesRef = useRef<Set<string>>(new Set())
  const { foraDaTelaCheia } = useDeteccaoSaida(sessao.fase === 'em_andamento', {
    onSaida: sessao.sairDaTela,
    onRetorno: sessao.voltarParaTela,
  })

  // Registra as conquistas já desbloqueadas antes do término da sessão
  useEffect(() => {
    if (sessao.fase !== 'concluida' && conquistas.length > 0) {
      conquistasDesbloqueadasAntesRef.current = new Set(
        conquistas.filter((c) => c.desbloqueada).map((c) => c.codigo),
      )
    }
  }, [sessao.fase, conquistas])

  // Ao concluir a sessão, consulta as conquistas para detectar as recém-desbloqueadas
  useEffect(() => {
    if (sessao.fase !== 'concluida') return
    let ativo = true

    void conquistasApi
      .consultar()
      .then((resposta) => {
        if (!ativo) return
        const desbloqueadasAntes = conquistasDesbloqueadasAntesRef.current
        const novas = resposta.conquistas.filter((c) => {
          if (!c.desbloqueada) return false
          const eraBloqueada = !desbloqueadasAntes.has(c.codigo)
          const desbloqueadaNestaSessao = Boolean(
            sessao.conclusao?.sessao.encerrada_em &&
              c.desbloqueada_em &&
              c.desbloqueada_em === sessao.conclusao.sessao.encerrada_em,
          )
          return eraBloqueada || desbloqueadaNestaSessao
        })
        setConquistasNovas(novas)
      })
      .catch(() => {
        // Ignora falhas de rede ao buscar conquistas para não prejudicar a tela de sucesso
      })

    return () => {
      ativo = false
    }
  }, [sessao.fase, sessao.conclusao])

  const materiaAtual = materias.find((m) => m.id === sessao.materiaId)

  if (sessao.fase === 'configurando') {
    return (
      <section className="foco">
        <div className="cabecalho-foco">
          <h1>Focar</h1>
          {sequencia && sequencia.atual > 0 && (
            <span
              className="selo sequencia"
              title={`Recorde: ${sequencia.recorde} ${sequencia.recorde === 1 ? 'dia' : 'dias'}`}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true">
                <path
                  fill="currentColor"
                  d="M12.5 2.5c.5 3-1.6 4.6-3 6.4C8.2 10.6 7 12.3 7 14.6A5 5 0 0 0 12 20a5 5 0 0 0 5-5.2c0-2.3-1.2-3.7-2.1-4.9-.3 1.3-1 2.2-2 2.6.6-2.9.4-6.6-.4-10Z"
                />
              </svg>
              {sequencia.atual} {sequencia.atual === 1 ? 'dia seguido' : 'dias seguidos'}
            </span>
          )}
        </div>
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
      cor={materiaAtual?.cor}
      efeito={materiaAtual?.efeito}
      nomeMateria={materiaAtual?.nome}
      atp={sessao.conclusao?.atp}
      conquistasNovas={conquistasNovas}
      onFocarDeNovo={() => {
        setConfirmandoDesistencia(false)
        setConquistasNovas([])
        sessao.focarDeNovo()
        void recarregarConquistas()
      }}
    />
  )
}
