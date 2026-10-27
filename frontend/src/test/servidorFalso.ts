import { vi } from 'vitest'
import type { LojaApi } from '../services/loja'
import type { Materia } from '../services/materias'
import type { SessaoApi } from '../services/sessoes'
import { tipoNeuronio } from '../utils/neuronio'

/** Uma requisição recebida pelo servidor falso. */
export interface Chamada {
  metodo: string
  caminho: string
  corpo: Record<string, string> | undefined
  keepalive: boolean
}

interface SessaoFalsa {
  id: string
  duracaoMin: number
  modo: 'estrito' | 'tolerante'
  materiaId: string | null
  estado: SessaoApi['estado']
  inicio: number
  encerradaEm: number | null
  foraMs: number
}

const TOLERANCIA_RELOGIO_MS = 2_000

/** As cores dos tipos originais, como o backend manda. */
const COR_ORIGINAL = { granular: '#3EE6E0', piramidal: '#8B7BFF', purkinje: '#FFC857' }

function json(status: number, corpo?: unknown) {
  if (corpo === undefined) return new Response(null, { status })
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

/**
 * Substitui o `fetch` por uma API de sessões falsa, com as mesmas regras do backend
 * (issue #19): uma sessão ativa por vez, poda no estrito, saldo de 10% no tolerante,
 * conclusão só no fim previsto. Guarda as chamadas para os testes conferirem.
 */
export function criarServidorFalso() {
  const chamadas: Chamada[] = []
  let sessoes: SessaoFalsa[] = []
  let materias: Materia[] = []
  /** A loja de ATP (#34); sem ela, `GET /loja` responde 404. */
  let loja: LojaApi | null = null
  let proximoId = 1
  let semRede = false
  /** Rotas que respondem 500 (terminadas neste trecho). */
  let comErro: string | null = null
  /** Relógio do servidor adiantado em relação ao do navegador (ms). */
  let deslocamentoMs = 0

  const agora = () => Date.now() + deslocamentoMs
  const fimPrevisto = (s: SessaoFalsa) => s.inicio + s.duracaoMin * 60_000
  const ativa = () => sessoes.find((s) => s.estado === 'em_andamento')

  function comoJson(s: SessaoFalsa): SessaoApi {
    return {
      id: s.id,
      duracao_minutos: s.duracaoMin,
      modo: s.modo,
      materia_id: s.materiaId,
      estado: s.estado,
      inicio: new Date(s.inicio).toISOString(),
      fim_previsto: new Date(fimPrevisto(s)).toISOString(),
      encerrada_em: s.encerradaEm === null ? null : new Date(s.encerradaEm).toISOString(),
      restante_segundos: Math.max(0, fimPrevisto(s) - agora()) / 1000,
      tempo_fora_segundos: s.foraMs / 1000,
    }
  }

  const transicaoInvalida = () =>
    json(409, { erro: 'transicao_invalida', mensagem: 'A sessão não está em andamento.' })

  function registrarInterrupcao(s: SessaoFalsa, corpo: Record<string, string>) {
    const saida = Date.parse(corpo.inicio)
    const retorno = corpo.fim ? Date.parse(corpo.fim) : null
    if (saida > agora() + TOLERANCIA_RELOGIO_MS || saida < s.inicio) {
      return json(400, { erro: 'horario_invalido', mensagem: 'Horário inválido.' })
    }
    if (s.modo === 'estrito') {
      s.estado = 'podada'
      s.encerradaEm = saida
    } else if (retorno !== null) {
      const saldo = Math.max(0, s.duracaoMin * 60_000 * 0.1 - s.foraMs)
      if (retorno - saida > saldo) {
        s.estado = 'podada'
        s.encerradaEm = saida + saldo
      } else {
        s.foraMs += retorno - saida
      }
    }
    return json(200, comoJson(s))
  }

  function responder(metodo: string, caminho: string, corpo: Record<string, string> | undefined) {
    if (metodo === 'POST' && caminho === '/sessoes') {
      if (ativa()) {
        return json(409, { erro: 'sessao_ativa_existente', mensagem: 'Já existe uma sessão.' })
      }
      const sessao: SessaoFalsa = {
        id: `sessao-${proximoId++}`,
        duracaoMin: Number(corpo?.duracao_minutos),
        modo: corpo?.modo === 'tolerante' ? 'tolerante' : 'estrito',
        materiaId: corpo?.materia_id ? String(corpo.materia_id) : null,
        estado: 'em_andamento',
        inicio: agora(),
        encerradaEm: null,
        foraMs: 0,
      }
      sessoes.push(sessao)
      return json(201, comoJson(sessao))
    }
    if (metodo === 'GET' && caminho === '/sessoes/ativa') {
      const sessao = ativa()
      return sessao ? json(200, comoJson(sessao)) : json(204)
    }
    if (metodo === 'GET' && caminho === '/materias') {
      return json(200, materias)
    }
    if (metodo === 'GET' && caminho === '/loja') {
      return loja ? json(200, loja) : json(404, { erro: 'nao_encontrado', mensagem: 'Sem loja.' })
    }

    const [, , id, acao] = caminho.split('/')
    const sessao = sessoes.find((s) => s.id === id)
    if (!sessao) return json(404, { erro: 'sessao_nao_encontrada', mensagem: 'Não encontrada.' })
    if (sessao.estado !== 'em_andamento') return transicaoInvalida()

    if (acao === 'interrupcoes') return registrarInterrupcao(sessao, corpo ?? {})
    if (acao === 'desistir') {
      sessao.estado = 'podada'
      sessao.encerradaEm = agora()
      return json(200, comoJson(sessao))
    }
    if (acao === 'concluir') {
      if (agora() < fimPrevisto(sessao) - TOLERANCIA_RELOGIO_MS) return transicaoInvalida()
      sessao.estado = 'concluida'
      sessao.encerradaEm = fimPrevisto(sessao)
      const forma = tipoNeuronio(sessao.duracaoMin)
      const emUso = loja?.tipos.find((t) => t.forma === forma && t.em_uso)
      return json(200, {
        sessao: comoJson(sessao),
        neuronio: {
          id: `neuronio-${sessao.id}`,
          sessao_id: sessao.id,
          duracao_minutos: sessao.duracaoMin,
          materia_id: sessao.materiaId,
          criado_em: new Date(fimPrevisto(sessao)).toISOString(),
          tipo: forma,
          variante: emUso?.codigo ?? forma,
          cor: emUso?.cor ?? COR_ORIGINAL[forma],
        },
        // 1 ATP por minuto, como o backend (#34).
        atp: sessao.duracaoMin,
      })
    }
    return json(404, { erro: 'nao_encontrado', mensagem: 'Rota inexistente.' })
  }

  const fetchFalso = vi.fn(async (url: string | URL | Request, opcoes?: RequestInit) => {
    const caminho = new URL(String(url)).pathname
    const metodo = opcoes?.method ?? 'GET'
    const corpo = opcoes?.body ? JSON.parse(String(opcoes.body)) : undefined
    chamadas.push({ metodo, caminho, corpo, keepalive: Boolean(opcoes?.keepalive) })
    if (semRede) throw new TypeError('Failed to fetch')
    if (comErro !== null && caminho.endsWith(comErro)) return json(500)
    return responder(metodo, caminho, corpo)
  })
  vi.stubGlobal('fetch', fetchFalso)

  return {
    chamadas,
    /** Chamadas a um caminho (ex.: '/sessoes' ou 'interrupcoes', que casa com o fim). */
    chamadasPara: (trecho: string) => chamadas.filter((c) => c.caminho.endsWith(trecho)),
    sessoes: () => sessoes,
    ficarSemRede: (valor = true) => {
      semRede = valor
    },
    falharCom500: (trecho: string | null) => {
      comErro = trecho
    },
    adiantarRelogio: (ms: number) => {
      deslocamentoMs = ms
    },
    /** Cria uma sessão em andamento, como se tivesse sido começada antes. */
    criarSessaoAtiva: (
      dados: Pick<SessaoFalsa, 'duracaoMin' | 'modo' | 'inicio'> & {
        foraMs?: number
        materiaId?: string | null
      },
    ) => {
      const sessao: SessaoFalsa = {
        id: `sessao-${proximoId++}`,
        estado: 'em_andamento',
        encerradaEm: null,
        foraMs: 0,
        materiaId: null,
        ...dados,
      }
      sessoes.push(sessao)
      return sessao
    },
    definirMaterias: (novas: Materia[]) => {
      materias = [...novas]
    },
    definirLoja: (nova: LojaApi | null) => {
      loja = nova
    },
    limpar: () => {
      sessoes = []
      materias = []
      loja = null
      chamadas.length = 0
    },
  }
}

export type ServidorFalso = ReturnType<typeof criarServidorFalso>
