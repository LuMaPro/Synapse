import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { Foco } from './Foco'

const MINUTO = 60_000

function renderizar() {
  const usuario = userEvent.setup()
  render(
    <MemoryRouter>
      <Foco />
    </MemoryRouter>,
  )
  return usuario
}

describe('tela de foco', () => {
  beforeEach(() => {
    // Só o relógio e o setInterval do timer são falsos. O setTimeout fica real porque
    // a Testing Library depende dele para esperar as atualizações do React.
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
    localStorage.clear()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('escolhe a duração com os botões de menos e mais', async () => {
    const usuario = renderizar()
    const duracao = screen.getByRole('status')

    expect(duracao).toHaveTextContent('25 minutos')
    await usuario.click(screen.getByRole('button', { name: 'Aumentar 5 minutos' }))
    expect(duracao).toHaveTextContent('30 minutos')
    await usuario.click(screen.getByRole('button', { name: 'Diminuir 5 minutos' }))
    await usuario.click(screen.getByRole('button', { name: 'Diminuir 5 minutos' }))
    expect(duracao).toHaveTextContent('20 minutos')
  })

  it('mostra o tipo de neurônio que a duração vai gerar', async () => {
    const usuario = renderizar()

    expect(screen.getByText(/gera um neurônio/)).toHaveTextContent('Piramidal')
    await usuario.click(screen.getByRole('button', { name: 'Diminuir 5 minutos' }))
    expect(screen.getByText(/gera um neurônio/)).toHaveTextContent('Granular')
  })

  it('escolhe o modo estrito ou tolerante', async () => {
    const usuario = renderizar()

    expect(screen.getByRole('radio', { name: /Estrito/ })).toBeChecked()
    await usuario.click(screen.getByRole('radio', { name: /Tolerante/ }))
    expect(screen.getByRole('radio', { name: /Tolerante/ })).toBeChecked()
  })

  it('o modo tolerante mostra 10% da duração escolhida como tempo fora permitido', async () => {
    const usuario = renderizar()
    const tolerante = screen.getByRole('radio', { name: /Tolerante/ })

    expect(tolerante).toHaveAccessibleName(/Até 02:30 fora/)
    await usuario.click(screen.getByRole('button', { name: 'Aumentar 5 minutos' }))
    expect(tolerante).toHaveAccessibleName(/Até 03:00 fora/)
  })

  it('durante a sessão, mostra o aviso de saída de cada modo', async () => {
    const usuario = renderizar()
    await usuario.click(screen.getByRole('button', { name: 'Começar a focar' }))
    expect(screen.getByText(/poda este neurônio/)).toBeInTheDocument()

    await usuario.click(screen.getByRole('button', { name: 'Desistir' }))
    await usuario.click(screen.getByRole('button', { name: 'Desistir e podar' }))
    await usuario.click(screen.getByRole('button', { name: 'Tentar de novo' }))
    await usuario.click(screen.getByRole('radio', { name: /Tolerante/ }))
    await usuario.click(screen.getByRole('button', { name: 'Começar a focar' }))

    expect(screen.getByText(/Você ainda pode ficar/)).toHaveTextContent(
      'Você ainda pode ficar 02:30 fora da tela',
    )
  })

  it('mostra o timer regressivo depois de começar', async () => {
    const usuario = renderizar()
    await usuario.click(screen.getByRole('radio', { name: /Tolerante/ }))

    await usuario.click(screen.getByRole('button', { name: 'Começar a focar' }))

    expect(screen.getByRole('timer', { name: 'Tempo restante' })).toHaveTextContent('25:00')
    expect(screen.getByText('Modo tolerante')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Neurônio Piramidal, 0% formado' })).toBeInTheDocument()
    act(() => vi.advanceTimersByTime(MINUTO + 1_000))
    expect(screen.getByRole('timer')).toHaveTextContent('23:59')
  })

  it('o neurônio cresce junto com o timer', async () => {
    const usuario = renderizar()
    await usuario.click(screen.getByRole('button', { name: 'Começar a focar' }))

    act(() => vi.advanceTimersByTime(12.5 * MINUTO))

    expect(screen.getByRole('img', { name: 'Neurônio Piramidal, 50% formado' })).toBeInTheDocument()
  })

  it('pede confirmação antes de desistir e permite continuar', async () => {
    const usuario = renderizar()
    await usuario.click(screen.getByRole('button', { name: 'Começar a focar' }))

    await usuario.click(screen.getByRole('button', { name: 'Desistir' }))
    const dialogo = screen.getByRole('alertdialog', { name: 'Desistir agora?' })
    expect(dialogo).toHaveTextContent('Seu neurônio vai morrer')
    expect(screen.getByRole('button', { name: 'Continuar focando' })).toHaveFocus()

    await usuario.click(screen.getByRole('button', { name: 'Continuar focando' }))
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    expect(screen.getByRole('timer')).toBeInTheDocument()
  })

  it('Esc fecha a confirmação sem desistir', async () => {
    const usuario = renderizar()
    await usuario.click(screen.getByRole('button', { name: 'Começar a focar' }))
    await usuario.click(screen.getByRole('button', { name: 'Desistir' }))

    await usuario.keyboard('{Escape}')

    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    expect(screen.getByRole('timer')).toBeInTheDocument()
  })

  it('desistir mostra a tela de poda e permite tentar de novo', async () => {
    const usuario = renderizar()
    await usuario.click(screen.getByRole('button', { name: 'Começar a focar' }))
    act(() => vi.advanceTimersByTime(3 * MINUTO))

    await usuario.click(screen.getByRole('button', { name: 'Desistir' }))
    await usuario.click(screen.getByRole('button', { name: 'Desistir e podar' }))

    expect(screen.getByRole('heading', { name: 'A conexão se perdeu' })).toBeInTheDocument()
    expect(screen.getByText(/Você desistiu aos/)).toHaveTextContent('Você desistiu aos 03:00.')
    expect(screen.getByRole('img', { name: 'Neurônio Piramidal podado' })).toBeInTheDocument()

    await usuario.click(screen.getByRole('button', { name: 'Tentar de novo' }))
    expect(screen.getByRole('button', { name: 'Começar a focar' })).toBeInTheDocument()
  })

  it('mostra a tela de sucesso quando o tempo acaba', async () => {
    const usuario = renderizar()
    await usuario.click(screen.getByRole('button', { name: 'Diminuir 5 minutos' }))
    await usuario.click(screen.getByRole('button', { name: 'Começar a focar' }))

    act(() => vi.advanceTimersByTime(20 * MINUTO))

    expect(screen.getByRole('heading', { name: 'Neurônio formado!' })).toBeInTheDocument()
    expect(screen.getByText('Granular · 20 min')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Neurônio Granular, 100% formado' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ver na minha rede' })).toHaveAttribute('href', '/rede')

    await usuario.click(screen.getByRole('button', { name: 'Focar de novo' }))
    expect(screen.getByRole('status')).toHaveTextContent('20 minutos')
  })

  describe('saída da tela (issue #18)', () => {
    const SEGUNDO = 1_000

    function definirAba(estado: 'visible' | 'hidden') {
      Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => estado })
      act(() => {
        document.dispatchEvent(new Event('visibilitychange'))
      })
    }

    function definirTelaCheia(emTelaCheia: boolean) {
      Object.defineProperty(document, 'fullscreenElement', {
        configurable: true,
        get: () => (emTelaCheia ? document.documentElement : null),
      })
      act(() => {
        document.dispatchEvent(new Event('fullscreenchange'))
      })
    }

    /** Esconde a aba por `ms` (o relógio anda, mas o timer não dispara) e volta. */
    function sairDaAbaPor(ms: number) {
      definirAba('hidden')
      vi.setSystemTime(Date.now() + ms)
      definirAba('visible')
    }

    async function comecarTolerante10Min(usuario: ReturnType<typeof renderizar>) {
      await usuario.click(screen.getByRole('radio', { name: /Tolerante/ }))
      for (let i = 0; i < 3; i++) {
        await usuario.click(screen.getByRole('button', { name: 'Diminuir 5 minutos' }))
      }
      await usuario.click(screen.getByRole('button', { name: 'Começar a focar' }))
    }

    beforeEach(() => {
      vi.spyOn(document, 'hasFocus').mockReturnValue(true)
    })

    afterEach(() => {
      vi.restoreAllMocks()
      Reflect.deleteProperty(document, 'visibilityState')
      Reflect.deleteProperty(document, 'fullscreenElement')
      Reflect.deleteProperty(document.documentElement, 'requestFullscreen')
    })

    it('critério de aceite: trocar de aba no modo estrito poda a sessão', async () => {
      const usuario = renderizar()
      await usuario.click(screen.getByRole('button', { name: 'Começar a focar' }))
      act(() => vi.advanceTimersByTime(2 * MINUTO))

      sairDaAbaPor(5 * SEGUNDO)

      expect(screen.getByRole('heading', { name: 'A conexão se perdeu' })).toBeInTheDocument()
      expect(screen.getByText(/Você saiu da tela aos/)).toHaveTextContent(
        'Você saiu da tela aos 02:00.',
      )
    })

    it('critério de aceite: no tolerante, saídas somando até 10% mantêm a sessão viva e o saldo aparece', async () => {
      const usuario = renderizar()
      await comecarTolerante10Min(usuario)
      expect(screen.getByText(/Você ainda pode ficar/)).toHaveTextContent('01:00')

      sairDaAbaPor(20 * SEGUNDO)
      expect(screen.getByRole('timer')).toBeInTheDocument()
      expect(screen.getByText(/Você ainda pode ficar/)).toHaveTextContent('00:40')

      sairDaAbaPor(30 * SEGUNDO)
      expect(screen.getByRole('timer')).toBeInTheDocument()
      expect(screen.getByText(/Você ainda pode ficar/)).toHaveTextContent('00:10')

      sairDaAbaPor(15 * SEGUNDO)
      expect(screen.getByRole('heading', { name: 'A conexão se perdeu' })).toBeInTheDocument()
    })

    it('no tolerante, fora da tela cheia, avisa o tempo contando e oferece voltar', async () => {
      const requestFullscreen = vi.fn().mockResolvedValue(undefined)
      Object.assign(document.documentElement, { requestFullscreen })
      const usuario = renderizar()
      await comecarTolerante10Min(usuario)
      definirTelaCheia(true)

      definirTelaCheia(false)
      act(() => vi.advanceTimersByTime(12 * SEGUNDO))

      expect(screen.getByText(/Você saiu da tela cheia/)).toHaveTextContent('restam 00:48')
      requestFullscreen.mockClear()
      await usuario.click(screen.getByRole('button', { name: 'Voltar para a tela cheia' }))
      expect(requestFullscreen).toHaveBeenCalledOnce()

      definirTelaCheia(true)
      expect(screen.queryByRole('button', { name: 'Voltar para a tela cheia' })).toBeNull()
      expect(screen.getByText(/Você ainda pode ficar/)).toHaveTextContent('00:48')
    })
  })
})
