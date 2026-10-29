import { useEffect, useEffectEvent, useState } from 'react'

/** Por que o estudante está "fora": basta um motivo ativo para contar como saída. */
type MotivoSaida = 'aba_escondida' | 'janela_sem_foco' | 'fora_da_tela_cheia'

interface CallbacksSaida {
  /** Disparado quando o estudante sai da tela, com o horário da saída (ms). */
  onSaida: (inicio: number) => void
  /** Disparado quando ele volta de todos os motivos de saída, com o horário (ms). */
  onRetorno: (fim: number) => void
}

/**
 * Percebe quando o estudante sai da tela durante a sessão (issue #18).
 *
 * Um site não consegue impedir o uso de outros apps, mas consegue perceber a saída:
 * - troca de aba ou minimizar a janela (`visibilitychange`);
 * - outra janela ou app recebe o foco (`blur` / `focus`);
 * - saída da tela cheia (`fullscreenchange`), se a sessão chegou a entrar nela;
 * - fechar ou recarregar a página (`beforeunload`), que pede confirmação ao navegador.
 *
 * Vários sinais costumam chegar juntos (trocar de aba dispara `blur` e
 * `visibilitychange`), então eles viram motivos de um mesmo "estar fora": `onSaida`
 * dispara no primeiro motivo, e `onRetorno` só quando todos acabaram.
 *
 * No celular (issue #35), trocar de app, abrir o seletor de apps, atender uma ligação
 * e bloquear a tela escondem a página, e o `visibilitychange` cobre todos esses casos
 * no Android e no iPhone. Para a página, bloquear a tela de propósito é igual a trocar
 * de app, então conta como saída (o aviso da sessão diz isso). O que não pode contar é
 * a tela apagar sozinha por falta de toque: por isso a sessão mantém a tela ligada
 * (`useTelaLigada`). O iPhone não tem tela cheia para páginas, então lá só valem a
 * visibilidade e o foco.
 */
export function useDeteccaoSaida(ativo: boolean, { onSaida, onRetorno }: CallbacksSaida) {
  const [foraDaTelaCheia, setForaDaTelaCheia] = useState(false)
  const avisarSaida = useEffectEvent(onSaida)
  const avisarRetorno = useEffectEvent(onRetorno)

  useEffect(() => {
    if (!ativo) return

    const motivos = new Set<MotivoSaida>()
    let entrouEmTelaCheia = Boolean(document.fullscreenElement)

    function ativar(motivo: MotivoSaida) {
      if (motivos.has(motivo)) return
      motivos.add(motivo)
      if (motivos.size === 1) avisarSaida(Date.now())
    }

    function desativar(motivo: MotivoSaida) {
      if (!motivos.delete(motivo)) return
      if (motivos.size === 0) avisarRetorno(Date.now())
    }

    function aoMudarVisibilidade() {
      if (document.visibilityState === 'hidden') {
        ativar('aba_escondida')
      } else {
        desativar('aba_escondida')
        // No celular, voltar para o app nem sempre dispara `focus` depois do `blur`.
        if (document.hasFocus()) desativar('janela_sem_foco')
      }
    }

    const aoPerderFoco = () => ativar('janela_sem_foco')
    const aoGanharFoco = () => desativar('janela_sem_foco')

    function aoMudarTelaCheia() {
      if (document.fullscreenElement) {
        entrouEmTelaCheia = true
        setForaDaTelaCheia(false)
        desativar('fora_da_tela_cheia')
      } else if (entrouEmTelaCheia) {
        // Só conta se a sessão chegou a entrar: no iPhone, por exemplo, ela nunca entra.
        setForaDaTelaCheia(true)
        ativar('fora_da_tela_cheia')
      }
    }

    function aoSairDaPagina(evento: BeforeUnloadEvent) {
      // Pede ao navegador o aviso nativo de "sair do site?". O texto não é personalizável.
      evento.preventDefault()
      evento.returnValue = ''
    }

    document.addEventListener('visibilitychange', aoMudarVisibilidade)
    window.addEventListener('blur', aoPerderFoco)
    window.addEventListener('focus', aoGanharFoco)
    // Clicar ou teclar na página prova que a janela tem o foco.
    window.addEventListener('pointerdown', aoGanharFoco)
    window.addEventListener('keydown', aoGanharFoco)
    document.addEventListener('fullscreenchange', aoMudarTelaCheia)
    window.addEventListener('beforeunload', aoSairDaPagina)

    return () => {
      document.removeEventListener('visibilitychange', aoMudarVisibilidade)
      window.removeEventListener('blur', aoPerderFoco)
      window.removeEventListener('focus', aoGanharFoco)
      window.removeEventListener('pointerdown', aoGanharFoco)
      window.removeEventListener('keydown', aoGanharFoco)
      document.removeEventListener('fullscreenchange', aoMudarTelaCheia)
      window.removeEventListener('beforeunload', aoSairDaPagina)
      setForaDaTelaCheia(false)
    }
  }, [ativo])

  return { foraDaTelaCheia }
}
