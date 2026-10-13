import { useCallback, useEffect, useState } from 'react'

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
  const [foraMs, setForaMs] = useState(0)
  const [motivoPoda, setMotivoPoda] = useState<MotivoPoda | null>(null)

  const duracaoMs = duracaoMin * MS_POR_MINUTO
  const restanteMs = fimEm === null ? duracaoMs : Math.max(0, fimEm - agora)
  const decorridoMs = duracaoMs - restanteMs
  const toleranciaMs = modo === 'tolerante' ? duracaoMs * PROPORCAO_TOLERANCIA : 0
  const toleranciaRestanteMs = Math.max(0, toleranciaMs - foraMs)

  useEffect(() => {
    if (fase !== 'em_andamento' || fimEm === null) return
    const fim = fimEm

    function tick() {
      const instante = Date.now()
      setAgora(instante)
      if (instante >= fim) {
        setFase('concluida')
        sairDaTelaCheia()
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
  }, [fase, fimEm])

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
    setMotivoPoda(null)
    setFase('em_andamento')
    entrarEmTelaCheia()
  }, [duracaoMin])

  const podar = useCallback((instante: number, motivo: MotivoPoda) => {
    setAgora(instante)
    setMotivoPoda(motivo)
    setFase('podada')
    sairDaTelaCheia()
  }, [])

  const desistir = useCallback(() => podar(Date.now(), 'desistiu'), [podar])

  /**
   * Registra que o estudante saiu da tela entre `inicio` e `fim` (horários em ms).
   * Quem detecta a saída é a issue #18; aqui fica só a regra de cada modo.
   *
   * - Estrito: qualquer saída poda, no instante em que ele saiu.
   * - Tolerante: o tempo fora vai sendo descontado de um saldo de 10% da sessão, que
   *   não volta ao valor inicial. Se a saída passar do saldo, poda no instante em que
   *   o saldo acabou.
   */
  const registrarSaida = useCallback(
    (inicio: number, fim: number) => {
      if (fase !== 'em_andamento' || fimEm === null) return
      const duracaoFora = Math.max(0, fim - inicio)

      if (modo === 'estrito') {
        podar(Math.min(inicio, fimEm), 'saiu')
      } else if (duracaoFora > toleranciaRestanteMs) {
        podar(Math.min(inicio + toleranciaRestanteMs, fimEm), 'saiu')
      } else {
        setForaMs((atual) => atual + duracaoFora)
      }
    },
    [fase, fimEm, modo, toleranciaRestanteMs, podar],
  )

  const focarDeNovo = useCallback(() => {
    setFimEm(null)
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
    podeDiminuir: duracaoMin > DURACAO_MINIMA,
    podeAumentar: duracaoMin < DURACAO_MAXIMA,
    diminuirDuracao,
    aumentarDuracao,
    escolherModo,
    iniciar,
    desistir,
    registrarSaida,
    focarDeNovo,
  }
}
