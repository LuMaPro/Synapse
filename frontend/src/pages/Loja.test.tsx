import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { CorLojaApi, LojaApi } from '../services/loja'
import type { Efeito } from '../utils/efeitos'
import { Loja } from './Loja'

function cor(
  codigo: string,
  nome: string,
  hex: string,
  preco: number,
  efeito: Efeito | null = null,
): CorLojaApi {
  return { codigo, nome, cor: hex, efeito, preco, desbloqueada: preco === 0 }
}

function catalogo(): CorLojaApi[] {
  return [
    cor('violeta', 'Violeta', '#8B7BFF', 0),
    cor('rosa', 'Rosa', '#FF6FB5', 0),
    cor('lavanda', 'Lavanda', '#C9B3FF', 100),
    cor('magenta_neon', 'Magenta neon', '#FF3DF0', 250),
    cor('pulsar', 'Pulsar', '#7DF9FF', 500, 'pulsar'),
    cor('arco_iris', 'Arco-íris', '#FF7AD9', 1200, 'arco_iris'),
  ]
}

interface Opcoes {
  saldo?: number
  /** Faz o `GET /loja` falhar (sem rede) enquanto devolver true. */
  falharAoCarregar?: () => boolean
  /** Faz a compra falhar sem rede enquanto devolver true. */
  semRedeNaCompra?: () => boolean
}

/** API falsa da loja, com as mesmas regras do backend (issue #34). */
function simularApi({ saldo = 300, falharAoCarregar, semRedeNaCompra }: Opcoes = {}) {
  const loja: LojaApi = { saldo, cores: catalogo() }
  const pedidos: string[] = []
  const json = (corpo: unknown, status = 200) =>
    new Response(JSON.stringify(corpo), {
      status,
      headers: { 'Content-Type': 'application/json' },
    })
  vi.stubGlobal(
    'fetch',
    vi.fn(async (endereco: string | URL | Request, opcoes?: RequestInit) => {
      const caminho = new URL(String(endereco)).pathname
      pedidos.push(`${opcoes?.method ?? 'GET'} ${caminho}`)
      if (caminho === '/loja') {
        if (falharAoCarregar?.()) throw new TypeError('Failed to fetch')
        return json(loja)
      }
      if (semRedeNaCompra?.()) throw new TypeError('Failed to fetch')
      const [, , codigo] = caminho.split('/')
      const item = loja.cores.find((c) => c.codigo === codigo)
      if (!item) return json({ erro: 'cor_nao_encontrada', mensagem: 'Não está à venda.' }, 404)
      if (item.desbloqueada)
        return json({ erro: 'cor_ja_desbloqueada', mensagem: 'Já é sua.' }, 409)
      if (loja.saldo < item.preco) {
        const falta = item.preco - loja.saldo
        return json(
          {
            erro: 'saldo_insuficiente',
            mensagem: `Faltam ${falta} ATP para comprar a cor ${item.nome}.`,
          },
          409,
        )
      }
      loja.saldo -= item.preco
      item.desbloqueada = true
      return json(loja)
    }),
  )
  return { loja, pedidos }
}

function renderizar() {
  const usuario = userEvent.setup()
  render(
    <MemoryRouter>
      <Loja />
    </MemoryRouter>,
  )
  return usuario
}

const cartao = (nome: string) => screen.getByRole('heading', { name: nome }).closest('li')!

describe('tela da loja', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('mostra o saldo e só as cores à venda, separando as que têm efeito', async () => {
    simularApi({ saldo: 120 })
    renderizar()

    expect(screen.getByRole('status')).toHaveTextContent('Carregando a loja')
    expect(await screen.findByLabelText('Saldo: 120 ATP')).toHaveTextContent('120 ATP')

    const titulos = (secao: RegExp) =>
      within(screen.getByRole('region', { name: secao }))
        .getAllByRole('heading', { level: 3 })
        .map((h) => h.textContent)
    expect(titulos(/Cores exclusivas/)).toEqual(['Lavanda', 'Magenta neon'])
    expect(titulos(/Cores com efeito/)).toEqual(['Pulsar', 'Arco-íris'])
    // As cores da paleta são de todos e não aparecem à venda.
    expect(screen.queryByRole('heading', { name: 'Violeta' })).not.toBeInTheDocument()
    // A prévia mostra a cor e o efeito.
    const previa = screen.getByRole('img', { name: 'Prévia da cor Arco-íris' })
    expect(previa).toHaveStyle({ '--cor-neuronio': '#FF7AD9' })
    expect(previa).toHaveClass('com-efeito', 'efeito-arco_iris')
    expect(screen.getByRole('img', { name: 'Prévia da cor Lavanda' })).not.toHaveClass('com-efeito')
  })

  it('critério: compra com confirmação, desconta o saldo e manda para as matérias', async () => {
    const api = simularApi({ saldo: 300 })
    const usuario = renderizar()
    await screen.findByLabelText('Saldo: 300 ATP')

    await usuario.click(
      screen.getByRole('button', { name: 'Comprar a cor Magenta neon por 250 ATP' }),
    )
    // Gastar ATP pede um segundo toque.
    expect(api.pedidos.filter((p) => p.startsWith('POST'))).toEqual([])
    await usuario.click(
      screen.getByRole('button', { name: 'Confirmar a compra da cor Magenta neon por 250 ATP' }),
    )

    expect(await screen.findByLabelText('Saldo: 50 ATP')).toBeInTheDocument()
    expect(api.pedidos).toContain('POST /loja/magenta_neon/comprar')
    expect(within(cartao('Magenta neon')).getByText('Sua')).toBeInTheDocument()
    const aviso = screen.getByRole('status')
    expect(aviso).toHaveTextContent(
      'Cor Magenta neon desbloqueada! Escolha-a para uma matéria em Matérias.',
    )
    expect(within(aviso).getByRole('link', { name: 'Matérias' })).toHaveAttribute(
      'href',
      '/materias',
    )
  })

  it('cancelar a confirmação não compra nada', async () => {
    const api = simularApi()
    const usuario = renderizar()
    await screen.findByLabelText('Saldo: 300 ATP')

    await usuario.click(screen.getByRole('button', { name: 'Comprar a cor Lavanda por 100 ATP' }))
    await usuario.click(screen.getByRole('button', { name: 'Cancelar' }))

    expect(screen.getByRole('button', { name: 'Comprar a cor Lavanda por 100 ATP' })).toBeEnabled()
    expect(api.pedidos.filter((p) => p.startsWith('POST'))).toEqual([])
  })

  it('critério: sem saldo, mostra quanto falta e não deixa comprar', async () => {
    simularApi({ saldo: 120 })
    renderizar()
    await screen.findByLabelText('Saldo: 120 ATP')

    expect(
      within(cartao('Magenta neon')).getByRole('button', { name: 'Faltam 130 ATP' }),
    ).toBeDisabled()
    expect(
      within(cartao('Arco-íris')).getByRole('button', { name: 'Faltam 1080 ATP' }),
    ).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Comprar a cor Lavanda por 100 ATP' })).toBeEnabled()
  })

  it('mostra o motivo quando o servidor recusa a compra', async () => {
    // O saldo da tela ficou velho: o servidor diz que falta ATP.
    const api = simularApi({ saldo: 300 })
    const usuario = renderizar()
    await screen.findByLabelText('Saldo: 300 ATP')
    api.loja.saldo = 200

    await usuario.click(
      screen.getByRole('button', { name: 'Comprar a cor Magenta neon por 250 ATP' }),
    )
    await usuario.click(
      screen.getByRole('button', { name: 'Confirmar a compra da cor Magenta neon por 250 ATP' }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Faltam 50 ATP para comprar a cor Magenta neon.',
    )
    expect(screen.getByLabelText('Saldo: 300 ATP')).toBeInTheDocument()
  })

  it('sem rede na compra, avisa e deixa tentar de novo', async () => {
    let semRede = true
    simularApi({ semRedeNaCompra: () => semRede })
    const usuario = renderizar()
    await screen.findByLabelText('Saldo: 300 ATP')

    await usuario.click(screen.getByRole('button', { name: 'Comprar a cor Lavanda por 100 ATP' }))
    const confirmar = { name: 'Confirmar a compra da cor Lavanda por 100 ATP' }
    await usuario.click(screen.getByRole('button', confirmar))
    expect(await screen.findByRole('alert')).toHaveTextContent('Verifique sua conexão')

    semRede = false
    await usuario.click(screen.getByRole('button', confirmar))
    expect(await screen.findByLabelText('Saldo: 200 ATP')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('sem conexão ao abrir, avisa e deixa tentar de novo', async () => {
    let falhar = true
    simularApi({ falharAoCarregar: () => falhar })
    const usuario = renderizar()

    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível carregar a loja')
    falhar = false
    await usuario.click(screen.getByRole('button', { name: 'Tentar de novo' }))

    expect(await screen.findByLabelText('Saldo: 300 ATP')).toBeInTheDocument()
  })
})
