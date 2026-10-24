import { api, ApiError } from './api'

/**
 * Chamadas da API de sessões de foco (issue #20).
 *
 * O servidor é a fonte da verdade: é ele que decide se uma saída da tela poda a
 * sessão e se ela foi concluída. A tela mostra o resultado na hora, mas os avisos
 * (saídas e desistência) precisam chegar ao servidor mesmo que a rede caia ou a página
 * feche. Por isso eles passam por uma fila guardada no navegador, enviada em ordem e
 * repetida até ser entregue.
 */

export type ModoSessaoApi = 'estrito' | 'tolerante'

export interface SessaoApi {
  id: string
  duracao_minutos: number
  modo: ModoSessaoApi
  materia_id?: string | null
  estado: 'em_andamento' | 'concluida' | 'podada'
  inicio: string
  fim_previsto: string
  encerrada_em: string | null
  restante_segundos: number
  tempo_fora_segundos: number
}

export interface NeuronioApi {
  id: string
  sessao_id: string
  duracao_minutos: number
  materia_id?: string | null
  criado_em: string
}

export interface ConclusaoApi {
  sessao: SessaoApi
  neuronio: NeuronioApi
}

export const sessoesApi = {
  iniciar: (duracaoMinutos: number, modo: ModoSessaoApi, materiaId?: string | null) =>
    api.post<SessaoApi>('/sessoes', {
      duracao_minutos: duracaoMinutos,
      modo,
      ...(materiaId ? { materia_id: materiaId } : {}),
    }),
  /** A sessão em andamento do estudante, ou `undefined` se não houver (204). */
  buscarAtiva: () => api.get<SessaoApi | undefined>('/sessoes/ativa'),
  concluir: (sessaoId: string) => api.post<ConclusaoApi>(`/sessoes/${sessaoId}/concluir`),
}

/**
 * Falha que vale tentar de novo: sem rede, erro no servidor ou token que não deu para
 * renovar. Os outros erros (ex.: 409, a sessão já não está em andamento) são a resposta
 * definitiva do servidor.
 */
export function ehFalhaTemporaria(erro: unknown): boolean {
  return !(erro instanceof ApiError) || erro.status >= 500 || erro.status === 401
}

/** Aviso para o servidor. Os horários já estão no relógio do servidor (ms). */
export type Aviso =
  | { tipo: 'interrupcao'; sessaoId: string; inicio: number; fim?: number }
  | { tipo: 'desistir'; sessaoId: string }

export interface RespostaAviso {
  aviso: Aviso
  /** Como a sessão ficou; `null` se o servidor recusou (ex.: ela já tinha terminado). */
  sessao: SessaoApi | null
}

const CHAVE_AVISOS = 'synapse:avisos-pendentes'

// Sem armazenamento (ex.: navegação privada), a fila vive só enquanto a página estiver aberta.
let avisosSemArmazenamento: Aviso[] = []

function lerAvisos(): Aviso[] {
  try {
    const salvos = localStorage.getItem(CHAVE_AVISOS)
    return salvos ? (JSON.parse(salvos) as Aviso[]) : []
  } catch {
    return avisosSemArmazenamento
  }
}

function salvarAvisos(avisos: Aviso[]) {
  avisosSemArmazenamento = avisos
  try {
    if (avisos.length > 0) localStorage.setItem(CHAVE_AVISOS, JSON.stringify(avisos))
    else localStorage.removeItem(CHAVE_AVISOS)
  } catch {
    // Fica só na memória (ver `avisosSemArmazenamento`).
  }
}

function removerAviso(aviso: Aviso) {
  const avisos = lerAvisos()
  const indice = avisos.findIndex((a) => JSON.stringify(a) === JSON.stringify(aviso))
  if (indice >= 0) salvarAvisos(avisos.filter((_, i) => i !== indice))
}

function caminhoECorpo(aviso: Aviso): [string, unknown] {
  if (aviso.tipo === 'desistir') return [`/sessoes/${aviso.sessaoId}/desistir`, undefined]
  const corpo = {
    inicio: new Date(aviso.inicio).toISOString(),
    ...(aviso.fim !== undefined && { fim: new Date(aviso.fim).toISOString() }),
  }
  return [`/sessoes/${aviso.sessaoId}/interrupcoes`, corpo]
}

async function enviarEmOrdem(aoResponder?: (resposta: RespostaAviso) => void) {
  for (;;) {
    const [aviso] = lerAvisos()
    if (!aviso) return true

    let sessao: SessaoApi | null
    try {
      sessao = await api.post<SessaoApi>(...caminhoECorpo(aviso))
    } catch (erro) {
      if (ehFalhaTemporaria(erro)) return false
      sessao = null
    }
    removerAviso(aviso)
    aoResponder?.({ aviso, sessao })
  }
}

let envioAnterior: Promise<unknown> = Promise.resolve()

/**
 * Envia os avisos pendentes, um de cada vez e na ordem em que aconteceram (o servidor
 * precisa da saída antes da conclusão). Para no primeiro que falhar por rede, que fica
 * guardado para a próxima tentativa. Devolve true se a fila ficou vazia.
 */
export function enviarAvisosPendentes(
  aoResponder?: (resposta: RespostaAviso) => void,
): Promise<boolean> {
  const envio = envioAnterior.then(() => enviarEmOrdem(aoResponder))
  envioAnterior = envio.catch(() => {})
  return envio
}

/** Guarda o aviso na fila e tenta entregar a fila. */
export function avisar(
  aviso: Aviso,
  aoResponder?: (resposta: RespostaAviso) => void,
): Promise<boolean> {
  salvarAvisos([...lerAvisos(), aviso])
  return enviarAvisosPendentes(aoResponder)
}

/**
 * Aviso de saída que precisa chegar mesmo se a página estiver fechando (trocar de aba
 * no modo estrito, recarregar, fechar). Vai na hora com `keepalive`; se não for
 * entregue, continua na fila. Devolve true se o servidor recebeu.
 */
export async function avisarSaidaImediata(aviso: Aviso): Promise<boolean> {
  salvarAvisos([...lerAvisos(), aviso])
  const entregue = await api.postEmSegundoPlano(...caminhoECorpo(aviso))
  if (entregue) removerAviso(aviso)
  return entregue
}

/**
 * Saída em curso no modo tolerante. O tempo fora só é conhecido na volta; se a página
 * for fechada antes disso, a saída fica guardada e é fechada na próxima abertura da
 * tela de foco, contando o tempo fora até ali.
 */
interface SaidaEmCurso {
  sessaoId: string
  /** Instante da saída no relógio do servidor (ms). */
  inicio: number
  /** Fim previsto da sessão no relógio do servidor (ms): o tempo fora conta só até ali. */
  fimPrevisto: number
  /** Diferença entre o relógio do servidor e o do navegador (ms). */
  deslocamento: number
}

const CHAVE_SAIDA = 'synapse:saida-em-curso'

export function guardarSaidaEmCurso(saida: SaidaEmCurso | null) {
  try {
    if (saida) localStorage.setItem(CHAVE_SAIDA, JSON.stringify(saida))
    else localStorage.removeItem(CHAVE_SAIDA)
  } catch {
    // Sem armazenamento: a saída só não sobrevive ao fechamento da página.
  }
}

/** Transforma uma saída deixada em aberto num aviso com o tempo fora até agora. */
export function fecharSaidaEmCurso() {
  let saida: SaidaEmCurso | null
  try {
    const salva = localStorage.getItem(CHAVE_SAIDA)
    saida = salva ? (JSON.parse(salva) as SaidaEmCurso) : null
  } catch {
    return
  }
  if (!saida) return
  guardarSaidaEmCurso(null)
  salvarAvisos([
    ...lerAvisos(),
    {
      tipo: 'interrupcao',
      sessaoId: saida.sessaoId,
      inicio: saida.inicio,
      fim: Math.min(Date.now() + saida.deslocamento, saida.fimPrevisto),
    },
  ])
}
