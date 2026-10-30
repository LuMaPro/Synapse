/**
 * Formata uma duração em milissegundos como `mm:ss`.
 *
 * Arredonda os segundos para cima: o timer mostra 25:00 no início e só chega a
 * 00:00 quando o tempo acabou de verdade.
 */
export function formatarTempo(ms: number): string {
  const totalSegundos = Math.max(0, Math.ceil(ms / 1000))
  const minutos = Math.floor(totalSegundos / 60)
  const segundos = totalSegundos % 60
  return `${String(minutos).padStart(2, '0')}:${String(segundos).padStart(2, '0')}`
}

/** Minutos em horas, com uma casa (ex.: 115 → "1,9 h"); abaixo de 1 h, em minutos. */
export function formatarHoras(minutos: number): string {
  if (minutos < 60) return `${minutos} min`
  return `${(minutos / 60).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} h`
}
