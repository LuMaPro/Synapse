import { useCallback, useEffect, useEffectEvent, useRef, useState } from 'react'
import { ApiError } from '../services/api'
import {
  avisar,
  avisarSaidaImediata,
  ehFalhaTemporaria,
  enviarAvisosPendentes,
  fecharSaidaEmCurso,
  guardarSaidaEmCurso,
  sessoesApi,
  type ConclusaoApi,
  type RespostaAviso,
  type SessaoApi,
} from '../services/sessoes'

export type ModoSessao = 'estrito' | 'tolerante'
export type FaseSessao = 'configurando' | 'em_andamento' | 'concluindo' | 'concluida' | 'podada'
export type MotivoPoda = 'desistiu' | 'saiu'

export const DURACAO_MINIMA = 10
export const DURACAO_MAXIMA = 120
export const PASSO_DURACAO = 5
const DURACAO_PADRAO = 25

/** No modo tolerante, o estudante pode passar até 10% da sessão fora da tela, somando as saídas. */
export const PROPORCAO_TOLERANCIA = 0.1

/** Frequência com que o timer é redesenhado. Não afeta a precisão (ver `tick`). */
const INTERVALO_ATUALIZACAO_MS = 250
const CHAVE_MODO = 'synapse:modo'

const MS_POR_MINUTO = 60_000

/** Esperas entre as tentativas de concluir quando a rede falha; a última se repete. */
export const ESPERAS_NOVA_TENTATIVA_MS = [2_000, 5_000, 10_000, 30_000]

function lerModoSalvo(): ModoSessao {
  try {
    return localStorage.getItem(CHAVE_MODO) === 'tolerante' ? 'tolerante' : 'estrito'
  } catch {
    return 'estrito'
  }
}

function salvarModo(modo: ModoSessao) {
  try {
    localStorage.setItem(CHAVE_MODO, modo)
  } catch {
    // Sem armazenamento (ex.: navegação privada): o app só não lembra a escolha.
  }
}

function entrarEmTelaCheia() {
  // O navegador pode recusar (ex.: iPhone fora de vídeo); a sessão segue sem tela cheia.
  document.documentElement.requestFullscreen?.()?.catch(() => {})
}

function sairDaTelaCheia() {
  if (document.fullscreenElement) {
    document.exitFullscreen?.()?.catch(() => {})
  }
}

/**
 * Estado e regras da sessão de foco no navegador: duração, modo, timer e resultado.
 *
 * O tempo restante é sempre calculado a partir do horário de término (`fimEm`), e
 * não somando intervalos: navegadores atrasam ou pausam o `setInterval` em abas em
 * segundo plano, mas o relógio (`Date.now()`) continua certo.
 *
 * A sessão existe no servidor (issue #20): começa e termina pela API, é retomada ao
 * abrir a tela e cada saída da tela é avisada ao servidor, que tem a palavra final
 * sobre a poda. A tela mostra a poda na hora, mas só mostra o neurônio formado
 * depois que o servidor confirma a conclusão.
 */
export function useSessaoFoco() {
  const [fase, setFase] = useState<FaseSessao>('configurando')
  const [duracaoMin, setDuracaoMin] = useState(DURACAO_PADRAO)
  const [modo, setModo] = useState<ModoSessao>(lerModoSalvo)
  const [materiaId, setMateriaId] = useState<string | null>(null)
  const [fimEm, setFimEm] = useState<number | null>(null)
  const [agora, setAgora] = useState(0)
  /** Tempo fora já descontado do saldo, somando as saídas que terminaram. */
  const [foraMs, setForaMs] = useState(0)
  /** Início da saída em curso (modo tolerante); null quando o estudante está na tela. */
  const [saidaEm, setSaidaEm] = useState<number | null>(null)
  const [motivoPoda, setMotivoPoda] = useState<MotivoPoda | null>(null)
  const [iniciando, setIniciando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  /** A conclusão não chegou ao servidor e está sendo tentada de novo. */
  const [semConexao, setSemConexao] = useState(false)
  /** A resposta do servidor ao concluir: o neurônio formado e o ATP ganho (#34). */
  const [conclusao, setConclusao] = useState<ConclusaoApi | null>(null)
  // Os eventos de saída chegam de fora do React (ex.: fullscreenchange disparado pelo
  // próprio fim da sessão) e podem vir antes do próximo render; o ref é atualizado na hora.
  const emAndamentoRef = useRef(false)
  const concluindoRef = useRef(false)
  const iniciandoRef = useRef(false)
  const sessaoIdRef = useRef<string | null>(null)
  const forcarConclusaoRef = useRef(false)
  /**
   * Diferença entre o relógio do servidor e o do navegador (ms). Os horários avisados
   * são convertidos para o relógio do servidor, que recusa uma saída "no futuro" ou
   * antes do início da sessão.
   */
  const deslocamentoRef = useRef(0)

  const duracaoMs = duracaoMin * MS_POR_MINUTO
  const terminou = fase === 'concluindo' || fase === 'concluida'
  const restanteMs = terminou ? 0 : fimEm === null ? duracaoMs : Math.max(0, fimEm - agora)
  const decorridoMs = duracaoMs - restanteMs
  const toleranciaMs = modo === 'tolerante' ? duracaoMs * PROPORCAO_TOLERANCIA : 0
  const foraAgoraMs = saidaEm === null ? 0 : Math.max(0, agora - saidaEm)
  const toleranciaRestanteMs = Math.max(0, toleranciaMs - foraMs - foraAgoraMs)

  const concluir = useCallback(() => {
    emAndamentoRef.current = false
    concluindoRef.current = true
    setSaidaEm(null)
    guardarSaidaEmCurso(null)
    setSemConexao(false)
    setFase('concluindo')
    sairDaTelaCheia()
  }, [])

  /** Conclui a sessão na hora em modo de desenvolvimento/debug. */
  const concluirDebug = useCallback(() => {
    forcarConclusaoRef.current = true
    concluir()
  }, [concluir])

  const podar = useCallback((instante: number, motivo: MotivoPoda) => {
    emAndamentoRef.current = false
    concluindoRef.current = false
    setAgora(instante)
    setSaidaEm(null)
    guardarSaidaEmCurso(null)
    setMotivoPoda(motivo)
    setFase('podada')
    sairDaTelaCheia()
  }, [])

  /** Mostra a sessão que veio do servidor (nova ou retomada). */
  const aplicarSessao = useCallback((sessao: SessaoApi) => {
    const instante = Date.now()
    const fim = instante + sessao.restante_segundos * 1000
    sessaoIdRef.current = sessao.id
    deslocamentoRef.current = Date.parse(sessao.fim_previsto) - fim
    setDuracaoMin(sessao.duracao_minutos)
    setModo(sessao.modo)
    setMateriaId(sessao.materia_id ?? null)
    setAgora(instante)
    setFimEm(fim)
    setForaMs(sessao.tempo_fora_segundos * 1000)
    setSaidaEm(null)
    setMotivoPoda(null)
    setFase('em_andamento')
    emAndamentoRef.current = true
  }, [])

  /** O servidor tem a palavra final: se ele podou a sessão, a tela mostra a poda. */
  const tratarResposta = useCallback(
    ({ aviso, sessao }: RespostaAviso) => {
      if (aviso.sessaoId !== sessaoIdRef.current) return
      if (!emAndamentoRef.current && !concluindoRef.current) return
      if (sessao !== null && sessao.estado !== 'podada') return
      // `null`: o servidor recusou o aviso porque a sessão já não estava em andamento.
      const instante = sessao?.encerrada_em
        ? Date.parse(sessao.encerrada_em) - deslocamentoRef.current
        : Date.now()
      podar(instante, 'saiu')
    },
    [podar],
  )

  /** Avisa ao servidor uma saída que já terminou (horários do navegador, em ms). */
  const avisarInterrupcao = useCallback(
    (inicio: number, fim: number) => {
      const sessaoId = sessaoIdRef.current
      if (sessaoId === null) return
      const deslocamento = deslocamentoRef.current
      void avisar(
        { tipo: 'interrupcao', sessaoId, inicio: inicio + deslocamento, fim: fim + deslocamento },
        tratarResposta,
      )
    },
    [tratarResposta],
  )

  useEffect(() => {
    if (fase !== 'em_andamento' || fimEm === null) return
    const fim = fimEm
    const saida = saidaEm
    // Fora da tela no modo tolerante: o saldo acaba neste instante, volte ele ou não.
    const saldoAcabaEm = saida === null ? null : saida + Math.max(0, toleranciaMs - foraMs)

    function tick() {
      if (!emAndamentoRef.current) return
      const instante = Date.now()
      if (saldoAcabaEm !== null && instante > saldoAcabaEm && saldoAcabaEm < fim) {
        podar(saldoAcabaEm, 'saiu')
        if (saida !== null) avisarInterrupcao(saida, instante)
        return
      }
      setAgora(instante)
      if (instante >= fim) {
        if (saida !== null) avisarInterrupcao(saida, fim)
        concluir()
      }
    }

    // Ao voltar para a aba, atualiza na hora em vez de esperar o próximo intervalo.
    function aoMudarVisibilidade() {
      if (document.visibilityState === 'visible') tick()
    }

    const intervalo = setInterval(tick, INTERVALO_ATUALIZACAO_MS)
    document.addEventListener('visibilitychange', aoMudarVisibilidade)
    return () => {
      clearInterval(intervalo)
      document.removeEventListener('visibilitychange', aoMudarVisibilidade)
    }
  }, [fase, fimEm, saidaEm, foraMs, toleranciaMs, podar, concluir, avisarInterrupcao])

  // O tempo acabou: o neurônio só aparece formado quando o servidor confirma. Sem rede,
  // tenta de novo (o servidor só poda por abandono 5 minutos depois do fim previsto).
  useEffect(() => {
    const sessaoId = sessaoIdRef.current
    if (fase !== 'concluindo' || sessaoId === null || fimEm === null) return
    const fim = fimEm
    let ativo = true
    let tentando = false
    let tentativas = 0
    let espera: ReturnType<typeof setTimeout> | undefined

    const tentar = async () => {
      if (tentando) return
      tentando = true
      clearTimeout(espera)
      try {
        // Os avisos pendentes vão antes: o servidor precisa deles para decidir a conclusão.
        if (!(await enviarAvisosPendentes(tratarResposta))) throw new Error('Sem conexão')
        if (!ativo || !concluindoRef.current) return
        const resposta = await sessoesApi.concluir(sessaoId, forcarConclusaoRef.current)
        if (!ativo) return
        concluindoRef.current = false
        setConclusao(resposta)
        setFase('concluida')
      } catch (erroConclusao) {
        if (!ativo) return
        if (!ehFalhaTemporaria(erroConclusao)) {
          // O servidor recusou: a sessão já tinha sido podada (ex.: ficou abandonada).
          podar(fim, 'saiu')
          return
        }
        setSemConexao(true)
        const indice = Math.min(tentativas++, ESPERAS_NOVA_TENTATIVA_MS.length - 1)
        espera = setTimeout(tentar, ESPERAS_NOVA_TENTATIVA_MS[indice])
      } finally {
        tentando = false
      }
    }

    void tentar()
    window.addEventListener('online', tentar)
    return () => {
      ativo = false
      clearTimeout(espera)
      window.removeEventListener('online', tentar)
    }
  }, [fase, fimEm, podar, tratarResposta])

  // Ao abrir a tela, entrega o que ficou pendente e retoma a sessão em andamento, se houver.
  useEffect(() => {
    let ativo = true
    fecharSaidaEmCurso()
    enviarAvisosPendentes(tratarResposta)
      // Com aviso pendente, a sessão no servidor ainda não reflete a saída: não retoma.
      .then((entregues) => (entregues ? sessoesApi.buscarAtiva() : undefined))
      .then((sessao) => {
        if (ativo && sessao && !emAndamentoRef.current) aplicarSessao(sessao)
      })
      .catch(() => {
        // Sem conexão: fica na configuração; ao começar, o servidor é consultado de novo.
      })
    return () => {
      ativo = false
    }
  }, [aplicarSessao, tratarResposta])

  const diminuirDuracao = useCallback(() => {
    setDuracaoMin((atual) => Math.max(DURACAO_MINIMA, atual - PASSO_DURACAO))
  }, [])

  const aumentarDuracao = useCallback(() => {
    setDuracaoMin((atual) => Math.min(DURACAO_MAXIMA, atual + PASSO_DURACAO))
  }, [])

  const escolherModo = useCallback((novoModo: ModoSessao) => {
    setModo(novoModo)
    salvarModo(novoModo)
  }, [])

  const escolherMateria = useCallback((novoId: string | null) => {
    setMateriaId(novoId)
  }, [])

  const iniciar = useCallback(async () => {
    if (iniciandoRef.current) return
    iniciandoRef.current = true
    setIniciando(true)
    setErro(null)
    // Ainda dentro do clique: o navegador só aceita a tela cheia a partir de um gesto.
    entrarEmTelaCheia()
    try {
      if (!(await enviarAvisosPendentes(tratarResposta))) throw new Error('Sem conexão')
      let sessao: SessaoApi | undefined
      try {
        sessao = await sessoesApi.iniciar(duracaoMin, modo, materiaId)
      } catch (erroInicio) {
        // Já existe uma sessão em andamento (ex.: aberta em outra aba): continua nela.
        if (!(erroInicio instanceof ApiError && erroInicio.status === 409)) throw erroInicio
        sessao = await sessoesApi.buscarAtiva()
        if (!sessao) throw erroInicio
      }
      aplicarSessao(sessao)
    } catch {
      sairDaTelaCheia()
      setErro('Não foi possível começar a sessão. Verifique sua conexão e tente de novo.')
    } finally {
      iniciandoRef.current = false
      setIniciando(false)
    }
  }, [duracaoMin, modo, materiaId, aplicarSessao, tratarResposta])

  const desistir = useCallback(() => {
    const sessaoId = sessaoIdRef.current
    podar(Date.now(), 'desistiu')
    if (sessaoId !== null) void avisar({ tipo: 'desistir', sessaoId }, tratarResposta)
  }, [podar, tratarResposta])

  /** Botão para voltar à tela cheia: o navegador só aceita a partir de um clique. */
  const voltarParaTelaCheia = useCallback(() => entrarEmTelaCheia(), [])

  /**
   * O estudante saiu da tela no instante `inicio` (ms). Quem detecta é o
   * useDeteccaoSaida; aqui fica a regra de cada modo.
   *
   * - Estrito: poda na hora, no instante em que ele saiu, e avisa o servidor.
   * - Tolerante: começa a descontar do saldo de 10% da sessão (ver `voltarParaTela`).
   *   A saída fica guardada até a volta, caso a página seja fechada antes.
   */
  const sairDaTela = useCallback(
    (inicio: number) => {
      const sessaoId = sessaoIdRef.current
      if (!emAndamentoRef.current || fimEm === null || sessaoId === null) return
      const deslocamento = deslocamentoRef.current
      if (inicio >= fimEm) {
        concluir()
      } else if (modo === 'estrito') {
        podar(inicio, 'saiu')
        // A página pode estar fechando: o aviso vai com keepalive e, se falhar, fica na fila.
        void avisarSaidaImediata({
          tipo: 'interrupcao',
          sessaoId,
          inicio: inicio + deslocamento,
        }).then((entregue) => entregue || enviarAvisosPendentes(tratarResposta))
      } else if (saidaEm === null) {
        setSaidaEm(inicio)
        guardarSaidaEmCurso({
          sessaoId,
          inicio: inicio + deslocamento,
          fimPrevisto: fimEm + deslocamento,
          deslocamento,
        })
      }
    },
    [fimEm, modo, saidaEm, podar, concluir, tratarResposta],
  )

  /**
   * O estudante voltou para a tela no instante `fim` (ms). O tempo fora é descontado
   * do saldo, que não volta ao valor inicial. Se passou do saldo, a poda vale a partir
   * do instante em que o saldo acabou. O servidor recebe a saída e decide pela mesma regra.
   */
  const voltarParaTela = useCallback(
    (fim: number) => {
      if (!emAndamentoRef.current || saidaEm === null || fimEm === null) return
      const duracaoFora = Math.max(0, fim - saidaEm)
      const saldoAcabaEm = saidaEm + Math.max(0, toleranciaMs - foraMs)

      setSaidaEm(null)
      guardarSaidaEmCurso(null)
      if (fim > saldoAcabaEm && saldoAcabaEm < fimEm) {
        podar(saldoAcabaEm, 'saiu')
      } else if (fim >= fimEm) {
        concluir()
      } else {
        setForaMs((atual) => atual + duracaoFora)
        setAgora(fim)
      }
      // Depois do fim previsto, o tempo fora não conta mais.
      avisarInterrupcao(saidaEm, Math.min(fim, fimEm))
    },
    [saidaEm, fimEm, toleranciaMs, foraMs, podar, concluir, avisarInterrupcao],
  )

  // Sair da tela de foco no meio da sessão (ex.: pelo menu) conta como sair da tela.
  const sairAoDesmontar = useEffectEvent(() => {
    if (emAndamentoRef.current) sairDaTela(Date.now())
  })

  useEffect(
    () => () => {
      sairAoDesmontar()
      // Não deixa o navegador preso na tela cheia.
      sairDaTelaCheia()
    },
    [],
  )

  const focarDeNovo = useCallback(() => {
    emAndamentoRef.current = false
    concluindoRef.current = false
    forcarConclusaoRef.current = false
    sessaoIdRef.current = null
    setFimEm(null)
    setSaidaEm(null)
    setErro(null)
    setConclusao(null)
    setFase('configurando')
  }, [])

  return {
    fase,
    duracaoMin,
    modo,
    materiaId,
    restanteMs,
    decorridoMs,
    progresso: decorridoMs / duracaoMs,
    toleranciaMs,
    toleranciaRestanteMs,
    motivoPoda,
    iniciando,
    erro,
    semConexao,
    conclusao,
    foraDaTela: saidaEm !== null,
    podeDiminuir: duracaoMin > DURACAO_MINIMA,
    podeAumentar: duracaoMin < DURACAO_MAXIMA,
    diminuirDuracao,
    aumentarDuracao,
    escolherModo,
    escolherMateria,
    iniciar,
    desistir,
    concluirDebug,
    sairDaTela,
    voltarParaTela,
    voltarParaTelaCheia,
    focarDeNovo,
  }
}
