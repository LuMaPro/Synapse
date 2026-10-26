import type { SessaoApi } from '../services/sessoes'
import { formatarTempo } from './tempo'

export interface DiaHistorico {
  /** Ano, mês e dia no fuso do navegador (ex.: `2026-10-20`). */
  chave: string
  rotulo: string
  sessoes: SessaoApi[]
}

function chaveDoDia(data: Date): string {
  const mes = String(data.getMonth() + 1).padStart(2, '0')
  const dia = String(data.getDate()).padStart(2, '0')
  return `${data.getFullYear()}-${mes}-${dia}`
}

/** "Hoje", "Ontem" ou a data por extenso (com o ano, se não for o atual). */
export function rotuloDoDia(data: Date, agora: Date = new Date()): string {
  const ontem = new Date(agora)
  ontem.setDate(ontem.getDate() - 1)
  if (chaveDoDia(data) === chaveDoDia(agora)) return 'Hoje'
  if (chaveDoDia(data) === chaveDoDia(ontem)) return 'Ontem'
  return data.toLocaleDateString('pt-BR', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    ...(data.getFullYear() !== agora.getFullYear() && { year: 'numeric' }),
  })
}

/**
 * Agrupa as sessões pelo dia em que começaram, no fuso do navegador. Mantém a ordem
 * em que vieram (a API manda da mais recente para a mais antiga).
 */
export function agruparPorDia(sessoes: SessaoApi[], agora: Date = new Date()): DiaHistorico[] {
  const dias: DiaHistorico[] = []
  for (const sessao of sessoes) {
    const inicio = new Date(sessao.inicio)
    const chave = chaveDoDia(inicio)
    const ultimo = dias.at(-1)
    if (ultimo?.chave === chave) ultimo.sessoes.push(sessao)
    else dias.push({ chave, rotulo: rotuloDoDia(inicio, agora), sessoes: [sessao] })
  }
  return dias
}

/** Hora em que a sessão começou (ex.: `14:05`). */
export function horaDoInicio(sessao: SessaoApi): string {
  return new Date(sessao.inicio).toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** O resultado da sessão em palavras: "Concluída", "Podada aos 03:00" ou "Em andamento". */
export function descreverResultado(sessao: SessaoApi): string {
  if (sessao.estado === 'concluida') return 'Concluída'
  if (sessao.estado === 'em_andamento') return 'Em andamento'
  if (!sessao.encerrada_em) return 'Podada'
  // Arredonda como a tela de poda, para mostrar o mesmo tempo que ela mostrou.
  const decorridoMs = Date.parse(sessao.encerrada_em) - Date.parse(sessao.inicio)
  return `Podada aos ${formatarTempo(decorridoMs)}`
}
