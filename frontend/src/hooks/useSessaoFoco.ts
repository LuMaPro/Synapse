import { useCallback, useEffect, useRef, useState } from 'react'

export type ModoSessao = 'estrito' | 'tolerante'
export type FaseSessao = 'configurando' | 'em_andamento' | 'concluida' | 'podada'
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

const API_URL = 'http://localhost:8000' 

/** Utilitário para tratar erros de rede sem perder a sessão (5 tentativas) */
async function fetchComRetry(url: string, options: RequestInit = {}, tentativas = 5): Promise<Response> {
  const token = localStorage.getItem('synapse_token') 

  const config: RequestInit = {
    ...options,
    credentials: 'include', 
    headers: {
      ...options.headers,
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    }
  }

  try {
    const res = await fetch(url, config)
    if (!res.ok && res.status >= 500 && tentativas > 1) throw new Error('Erro no servidor')
    return res
  } catch (erro) {
    if (tentativas <= 1) throw erro
    await new Promise((resolve) => setTimeout(resolve, 3000))
    return fetchComRetry(url, options, tentativas - 1)
  }
}

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
 */
export function useSessaoFoco() {
  const [fase, setFase] = useState<FaseSessao>('configurando')
  const [duracaoMin, setDuracaoMin] = useState(DURACAO_PADRAO)
  const [modo, setModo] = useState<ModoSessao>(lerModoSalvo)
  const [fimEm, setFimEm] = useState<number | null>(null)
  const [agora, setAgora] = useState(0)
  /** Tempo fora já descontado do saldo, somando as saídas que terminaram. */
  const [foraMs, setForaMs] = useState(0)
  /** Início da saída em curso (modo tolerante); null quando o estudante está na tela. */
  const [saidaEm, setSaidaEm] = useState<number | null>(null)
  const [motivoPoda, setMotivoPoda] = useState<MotivoPoda | null>(null)
  // Os eventos de saída chegam de fora do React (ex.: fullscreenchange disparado pelo
  // próprio fim da sessão) e podem vir antes do próximo render; o ref é atualizado na hora.
  const emAndamentoRef = useRef(false)

  const duracaoMs = duracaoMin * MS_POR_MINUTO
  const restanteMs = fimEm === null ? duracaoMs : Math.max(0, fimEm - agora)
  const decorridoMs = duracaoMs - restanteMs
  const toleranciaMs = modo === 'tolerante' ? duracaoMs * PROPORCAO_TOLERANCIA : 0
  const foraAgoraMs = saidaEm === null ? 0 : Math.max(0, agora - saidaEm)
  const toleranciaRestanteMs = Math.max(0, toleranciaMs - foraMs - foraAgoraMs)

  const sessaoIdRef = useRef<string | null>(null)

  // Ao abrir /foco, retomar a sessão ativa se houver
  useEffect(() => {
    let montado = true
    fetchComRetry(`${API_URL}/sessoes/ativa`, { method: 'GET' })
      .then(async (res) => {
        if (res.ok && montado) {
          const dados = await res.json()
          if (dados && dados.id) {
            sessaoIdRef.current = dados.id
            setDuracaoMin(dados.duracao_minutos)
            setModo(dados.modo)

            const restanteMs = (dados.restante_segundos || 0) * 1000
            setFimEm(Date.now() + restanteMs)
            
            setForaMs((dados.tempo_fora_segundos || 0) * 1000)
            setAgora(Date.now())
            setFase('em_andamento')
            emAndamentoRef.current = true
          }
        }
      })
      .catch(() => { /* Silencioso: se der erro na rede ao montar, mantém a tela de configuração normal */ })
    return () => { montado = false }
  }, [])

  const concluir = useCallback(() => {
    emAndamentoRef.current = false
    setSaidaEm(null)
    setFase('concluida')
    sairDaTelaCheia()

    if (sessaoIdRef.current) {
      fetchComRetry(`${API_URL}/sessoes/${sessaoIdRef.current}/concluir`, { method: 'POST' })
        .catch(console.error)
    }
  }, [])

  const podar = useCallback((instante: number, motivo: MotivoPoda) => {
    emAndamentoRef.current = false
    setAgora(instante)
    setSaidaEm(null)
    setMotivoPoda(motivo)
    setFase('podada')
    sairDaTelaCheia()

    if (sessaoIdRef.current) {
      fetchComRetry(`${API_URL}/sessoes/${sessaoIdRef.current}/desistir`, { method: 'POST' })
        .catch(console.error)
    }
  }, [])

  useEffect(() => {
    if (fase !== 'em_andamento' || fimEm === null) return
    const fim = fimEm
    // Fora da tela no modo tolerante: o saldo acaba neste instante, volte ele ou não.
    const saldoAcabaEm = saidaEm === null ? null : saidaEm + Math.max(0, toleranciaMs - foraMs)

    function tick() {
      const instante = Date.now()
      if (saldoAcabaEm !== null && instante > saldoAcabaEm && saldoAcabaEm < fim) {
        podar(saldoAcabaEm, 'saiu')
        return
      }
      setAgora(instante)
      if (instante >= fim) concluir()
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
  }, [fase, fimEm, saidaEm, foraMs, toleranciaMs, podar, concluir])

  // Saindo da tela de foco no meio da sessão, não deixa o navegador preso na tela cheia.
  useEffect(() => sairDaTelaCheia, [])

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

  const iniciar = useCallback(() => {
    const instante = Date.now()
    setAgora(instante)
    setFimEm(instante + duracaoMin * MS_POR_MINUTO)
    setForaMs(0)
    setSaidaEm(null)
    setMotivoPoda(null)
    setFase('em_andamento')
    emAndamentoRef.current = true
    entrarEmTelaCheia()

    fetchComRetry(`${API_URL}/sessoes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ duracao_minutos: duracaoMin, modo }),
    })
      .then(async (res) => {
        if (res.ok) {
          const dados = await res.json()
          sessaoIdRef.current = dados.id
        }
      })
      .catch(console.error)
  }, [duracaoMin, modo])

  const desistir = useCallback(() => {
    podar(Date.now(), 'desistiu')
  }, [podar])

  /** Botão para voltar à tela cheia: o navegador só aceita a partir de um clique. */
  const voltarParaTelaCheia = useCallback(() => entrarEmTelaCheia(), [])

  /**
   * O estudante saiu da tela no instante `inicio` (ms). Quem detecta é o
   * useDeteccaoSaida; aqui fica a regra de cada modo.
   *
   * - Estrito: poda na hora, no instante em que ele saiu.
   * - Tolerante: começa a descontar do saldo de 10% da sessão (ver `voltarParaTela`).
   */
  const sairDaTela = useCallback(
    (inicio: number) => {
      if (!emAndamentoRef.current || fimEm === null) return
      if (inicio >= fimEm) concluir()
      else if (modo === 'estrito') podar(inicio, 'saiu')
      else setSaidaEm((atual) => atual ?? inicio)

      // Notifica as saídas detectadas e escuta decisão do servidor
      if (sessaoIdRef.current) {
        fetchComRetry(`${API_URL}/sessoes/${sessaoIdRef.current}/interrupcoes`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          // Usando a chave "inicio" exigida pelo backend
          body: JSON.stringify({ inicio: new Date(inicio).toISOString() }),
        })
          .then(async (res) => {
            if (!res.ok) {
              const erro = await res.json().catch(() => ({}))
              if (erro.podada || res.status === 403 || res.status === 400) {
                podar(inicio, 'saiu')
              }
            }
          })
          .catch(console.error)
      }
    },
    [fimEm, modo, podar, concluir],
  )

  /**
   * O estudante voltou para a tela no instante `fim` (ms). O tempo fora é descontado
   * do saldo, que não volta ao valor inicial. Se passou do saldo, a poda vale a partir
   * do instante em que o saldo acabou.
   */
  const voltarParaTela = useCallback(
    (fim: number) => {
      if (!emAndamentoRef.current || saidaEm === null || fimEm === null) return
      
      const duracaoFora = Math.max(0, fim - saidaEm)
      const saldoAcabaEm = saidaEm + Math.max(0, toleranciaMs - foraMs)
      
      const inicioSaida = saidaEm

      setSaidaEm(null)
      
      if (fim > saldoAcabaEm && saldoAcabaEm < fimEm) {
        podar(saldoAcabaEm, 'saiu')
      } else if (fim >= fimEm) {
        concluir()
      } else {
        setForaMs((atual) => atual + duracaoFora)
        setAgora(fim)
      }

      if (sessaoIdRef.current) {
        fetchComRetry(`${API_URL}/sessoes/${sessaoIdRef.current}/interrupcoes`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            inicio: new Date(inicioSaida).toISOString(),
            fim: new Date(fim).toISOString() 
          }),
        }).catch(console.error)
      }
    },
    [saidaEm, fimEm, toleranciaMs, foraMs, podar, concluir],
  )

  const focarDeNovo = useCallback(() => {
    emAndamentoRef.current = false
    sessaoIdRef.current = null // Limpa o ID da sessão antiga
    setFimEm(null)
    setSaidaEm(null)
    setFase('configurando')
  }, [])

  return {
    fase,
    duracaoMin,
    modo,
    restanteMs,
    decorridoMs,
    progresso: decorridoMs / duracaoMs,
    toleranciaMs,
    toleranciaRestanteMs,
    motivoPoda,
    foraDaTela: saidaEm !== null,
    podeDiminuir: duracaoMin > DURACAO_MINIMA,
    podeAumentar: duracaoMin < DURACAO_MAXIMA,
    diminuirDuracao,
    aumentarDuracao,
    escolherModo,
    iniciar,
    desistir,
    sairDaTela,
    voltarParaTela,
    voltarParaTelaCheia,
    focarDeNovo,
  }
}