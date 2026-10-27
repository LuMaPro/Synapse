import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { criarServidorFalso, type ServidorFalso } from '../test/servidorFalso'
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
  let servidor: ServidorFalso

  beforeEach(() => {
    // Só o relógio e o setInterval do timer são falsos. O setTimeout fica real porque
    // a Testing Library depende dele para esperar as atualizações do React.
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
    localStorage.clear()
    servidor = criarServidorFalso()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
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
    expect(screen.getByRole('link', { name: 'Ver histórico' })).toHaveAttribute(
      'href',
      '/historico',
    )
    expect(screen.getByRole('img', { name: 'Neurônio Piramidal podado' })).toBeInTheDocument()

    await usuario.click(screen.getByRole('button', { name: 'Tentar de novo' }))
    expect(screen.getByRole('button', { name: 'Começar a focar' })).toBeInTheDocument()
  })

  it('mostra a tela de sucesso quando o tempo acaba', async () => {
    const usuario = renderizar()
    await usuario.click(screen.getByRole('button', { name: 'Diminuir 5 minutos' }))
    await usuario.click(screen.getByRole('button', { name: 'Começar a focar' }))

    act(() => vi.advanceTimersByTime(20 * MINUTO))

    expect(await screen.findByRole('heading', { name: 'Neurônio formado!' })).toBeInTheDocument()
    expect(screen.getByText('Granular · 20 min')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Neurônio Granular, 100% formado' })).toBeInTheDocument()
    // O ATP que o servidor creditou (#34): 1 por minuto.
    expect(screen.getByText('+20 ATP')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ver na minha rede' })).toHaveAttribute('href', '/rede')

    await usuario.click(screen.getByRole('button', { name: 'Focar de novo' }))
    expect(screen.getByRole('status')).toHaveTextContent('20 minutos')
  })

  it('permite escolher matéria antes de iniciar a sessão, exibindo-a no selo e no resultado', async () => {
    servidor.definirMaterias([
      { id: 'mat-calc', nome: 'Cálculo', cor: '#8B7BFF', criada_em: '' },
    ])
    const usuario = renderizar()

    const chipCalculo = await screen.findByRole('radio', { name: 'Cálculo' })
    await usuario.click(chipCalculo)
    expect(chipCalculo).toBeChecked()

    await usuario.click(screen.getByRole('button', { name: 'Começar a focar' }))

    const chamadaInicio = servidor.chamadasPara('/sessoes')[0]
    expect(chamadaInicio.corpo?.materia_id).toBe('mat-calc')

    expect(screen.getByText(/Cálculo · Modo estrito/)).toBeInTheDocument()

    const neuronioCrescendo = screen.getByRole('img', { name: /Neurônio Piramidal/ })
    expect(neuronioCrescendo).toHaveStyle({ '--cor-neuronio': '#8B7BFF' })

    act(() => vi.advanceTimersByTime(25 * MINUTO))

    expect(await screen.findByRole('heading', { name: 'Neurônio formado!' })).toBeInTheDocument()
    expect(screen.getByText('Piramidal · 25 min · Cálculo')).toBeInTheDocument()
  })

  it('usa a cor do tipo escolhido na loja, e a da matéria vale mais (issue #34)', async () => {
    const tipo = (
      codigo: string,
      forma: 'granular' | 'piramidal',
      cor: string,
      emUso: boolean,
    ) => ({
      codigo,
      nome: codigo,
      forma,
      cor,
      preco: emUso && codigo !== forma ? 250 : 0,
      duracao_minima: forma === 'granular' ? 10 : 25,
      duracao_maxima: forma === 'granular' ? 24 : 59,
      desbloqueado: true,
      em_uso: emUso,
    })
    servidor.definirLoja({
      saldo: 10,
      tipos: [
        tipo('granular', 'granular', '#3EE6E0', true),
        tipo('piramidal', 'piramidal', '#8B7BFF', false),
        tipo('piramidal_rosa', 'piramidal', '#FF6FB5', true),
      ],
    })
    servidor.definirMaterias([{ id: 'mat-fis', nome: 'Física', cor: '#FFC857', criada_em: '' }])
    const usuario = renderizar()
    await screen.findByRole('radio', { name: 'Física' })

    await usuario.click(screen.getByRole('button', { name: 'Começar a focar' }))
    const crescendo = screen.getByRole('img', { name: /Neurônio Piramidal/ })
    await waitFor(() => expect(crescendo).toHaveStyle({ '--cor-neuronio': '#FF6FB5' }))

    act(() => vi.advanceTimersByTime(25 * MINUTO))
    const formado = await screen.findByRole('img', { name: 'Neurônio Piramidal, 100% formado' })
    expect(formado).toHaveStyle({ '--cor-neuronio': '#FF6FB5' })
    expect(screen.getByText('+25 ATP')).toBeInTheDocument()

    // Com matéria, a cor da matéria vale mais que a da loja.
    await usuario.click(screen.getByRole('button', { name: 'Focar de novo' }))
    await usuario.click(screen.getByRole('radio', { name: 'Física' }))
    await usuario.click(screen.getByRole('button', { name: 'Começar a focar' }))
    expect(screen.getByRole('img', { name: /Neurônio Piramidal/ })).toHaveStyle({
      '--cor-neuronio': '#FFC857',
    })
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

  describe('integração com a API (issue #20)', () => {
    it('critério de aceite: iniciar → concluir cria o neurônio no servidor', async () => {
      const usuario = renderizar()
      await usuario.click(screen.getByRole('button', { name: 'Diminuir 5 minutos' }))
      await usuario.click(screen.getByRole('button', { name: 'Diminuir 5 minutos' }))
      await usuario.click(screen.getByRole('button', { name: 'Diminuir 5 minutos' }))
      await usuario.click(screen.getByRole('button', { name: 'Começar a focar' }))
      expect(servidor.sessoes()).toHaveLength(1)

      act(() => vi.advanceTimersByTime(10 * MINUTO))

      expect(await screen.findByRole('heading', { name: 'Neurônio formado!' })).toBeInTheDocument()
      expect(servidor.chamadasPara('/concluir')).toHaveLength(1)
      expect(servidor.sessoes()[0].estado).toBe('concluida')
    })

    it('enquanto o servidor não confirma, avisa que está salvando o neurônio', async () => {
      const usuario = renderizar()
      await usuario.click(screen.getByRole('button', { name: 'Começar a focar' }))
      servidor.ficarSemRede()

      act(() => vi.advanceTimersByTime(25 * MINUTO))

      expect(screen.getByRole('timer')).toHaveTextContent('00:00')
      expect(await screen.findByText(/Sem conexão. Seu neurônio será salvo/)).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Desistir' })).not.toBeInTheDocument()
      expect(screen.queryByRole('heading', { name: 'Neurônio formado!' })).not.toBeInTheDocument()
    })

    it('ao abrir a tela, retoma a sessão em andamento', async () => {
      servidor.criarSessaoAtiva({ duracaoMin: 30, modo: 'tolerante', inicio: Date.now() - MINUTO })

      renderizar()

      expect(await screen.findByRole('timer')).toHaveTextContent('29:00')
      expect(screen.getByText('Modo tolerante')).toBeInTheDocument()
    })

    it('critério de aceite: no estrito, trocar de aba poda a sessão também no servidor', async () => {
      vi.spyOn(document, 'hasFocus').mockReturnValue(true)
      const usuario = renderizar()
      await usuario.click(screen.getByRole('button', { name: 'Começar a focar' }))

      Object.defineProperty(document, 'visibilityState', {
        configurable: true,
        get: () => 'hidden',
      })
      act(() => {
        document.dispatchEvent(new Event('visibilitychange'))
      })
      Reflect.deleteProperty(document, 'visibilityState')

      expect(screen.getByRole('heading', { name: 'A conexão se perdeu' })).toBeInTheDocument()
      await waitFor(() => expect(servidor.sessoes()[0].estado).toBe('podada'))
      vi.restoreAllMocks()
    })

    it('sem conexão ao começar, mostra o erro e deixa tentar de novo', async () => {
      const usuario = renderizar()
      servidor.ficarSemRede()

      await usuario.click(screen.getByRole('button', { name: 'Começar a focar' }))

      expect(await screen.findByRole('alert')).toHaveTextContent(
        'Não foi possível começar a sessão. Verifique sua conexão e tente de novo.',
      )
      servidor.ficarSemRede(false)
      await usuario.click(screen.getByRole('button', { name: 'Começar a focar' }))
      expect(screen.getByRole('timer')).toBeInTheDocument()
      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    })
  })
})
