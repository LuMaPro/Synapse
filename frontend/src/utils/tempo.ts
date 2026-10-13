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
