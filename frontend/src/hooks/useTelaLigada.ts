import { useEffect } from 'react'

/** Se o navegador consegue manter a tela ligada (Wake Lock API). */
export function telaLigadaSuportada(): boolean {
  return typeof navigator !== 'undefined' && 'wakeLock' in navigator
}

/**
 * Mantém a tela ligada enquanto `ativo` (Wake Lock API, issue #35).
 *
 * No celular, a tela apaga sozinha depois de alguns segundos sem toque, e apagar a
 * tela esconde a página: para a detecção de saída (#18), é o mesmo que trocar de app,
 * e a sessão seria podada sem o estudante ter feito nada. A trava evita isso.
 *
 * O navegador solta a trava quando a página fica escondida (trocar de app, bloquear
 * a tela de propósito), então ela é pedida de novo na volta. Onde não há suporte, ou
 * se o navegador recusar (ex.: economia de bateria), a sessão segue sem ela.
 */
export function useTelaLigada(ativo: boolean): void {
  useEffect(() => {
    if (!ativo || !telaLigadaSuportada()) return

    let trava: WakeLockSentinel | null = null
    let pedindo = false
    let encerrado = false

    async function pedir() {
      if (trava || pedindo || document.visibilityState !== 'visible') return
      pedindo = true
      try {
        const nova = await navigator.wakeLock.request('screen')
        if (encerrado) {
          void nova.release()
          return
        }
        trava = nova
        nova.addEventListener('release', () => {
          if (trava === nova) trava = null
        })
      } catch {
        // Recusado (bateria fraca, página sem foco...): a sessão segue sem a trava.
      } finally {
        pedindo = false
      }
    }

    function aoMudarVisibilidade() {
      if (document.visibilityState === 'visible') void pedir()
    }

    void pedir()
    document.addEventListener('visibilitychange', aoMudarVisibilidade)
    return () => {
      encerrado = true
      document.removeEventListener('visibilitychange', aoMudarVisibilidade)
      void trava?.release()
      trava = null
    }
  }, [ativo])
}
