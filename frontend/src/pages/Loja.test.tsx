import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { LojaApi, TipoLojaApi } from '../services/loja'
import { Loja } from './Loja'

type Forma = TipoLojaApi['forma']

const FAIXA: Record<Forma, [number, number | null]> = {
  granular: [10, 24],
  piramidal: [25, 59],
  purkinje: [60, null],
}

function tipo(codigo: string, nome: string, forma: Forma, cor: string, preco: number) {
  return {
    codigo,
    nome,
    forma,
    cor,
    preco,
    duracao_minima: FAIXA[forma][0],
    duracao_maxima: FAIXA[forma][1],
    desbloqueado: preco === 0,
    em_uso: preco === 0,
  }
}

function catalogo(): TipoLojaApi[] {
  return [
    tipo('granular', 'Granular', 'granular', '#3EE6E0', 0),
    tipo('granular_lima', 'Granular Lima', 'granular', '#C3E86B', 100),
    tipo('piramidal', 'Piramidal', 'piramidal', '#8B7BFF', 0),
    tipo('piramidal_rosa', 'Piramidal Rosa', 'piramidal', '#FF6FB5', 250),
    tipo('purkinje', 'Purkinje', 'purkinje', '#FFC857', 0),
    tipo('purkinje_lunar', 'Purkinje Lunar', 'purkinje', '#ECEDF7', 500),
  ]
}

interface Opcoes {
  saldo?: number
  /** Faz o `GET /loja` falhar (sem rede) enquanto devolver true. */
  falharAoCarregar?: () => boolean
  /** Faz a próxima compra ou uso falhar sem rede. */
  semRedeNaAcao?: () => boolean
}

/** API falsa da loja, com as mesmas regras do backend (issue #34). */
function simularApi({ saldo = 300, falharAoCarregar, semRedeNaAcao }: Opcoes = {}) {
  const loja: LojaApi = { saldo, tipos: catalogo() }
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
      if (semRedeNaAcao?.()) throw new TypeError('Failed to fetch')
      const [, , codigo, acao] = caminho.split('/')
      const item = loja.tipos.find((t) => t.codigo === codigo)
      if (!item) return json({ erro: 'tipo_nao_encontrado', mensagem: 'Não está à venda.' }, 404)
      if (acao === 'comprar') {
        if (item.desbloqueado)
          return json({ erro: 'tipo_ja_desbloqueado', mensagem: 'Já tem.' }, 409)
        if (loja.saldo < item.preco) {
          const falta = item.preco - loja.saldo
          return json(
            {
              erro: 'saldo_insuficiente',
              mensagem: `Faltam ${falta} ATP para comprar o ${item.nome}.`,
            },
            409,
          )
        }
        loja.saldo -= item.preco
        item.desbloqueado = true
      } else if (!item.desbloqueado) {
        return json({ erro: 'tipo_bloqueado', mensagem: 'Compre antes.' }, 409)
      }
      for (const outro of loja.tipos) {
        if (outro.forma === item.forma) outro.em_uso = outro.codigo === item.codigo
      }
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

  it('mostra o saldo e os tipos agrupados pela forma, com prévia na cor de cada um', async () => {
    simularApi({ saldo: 120 })
    renderizar()

    expect(screen.getByRole('status')).toHaveTextContent('Carregando a loja')
    expect(await screen.findByLabelText('Saldo: 120 ATP')).toHaveTextContent('120 ATP')

    const granular = screen.getByRole('region', { name: /Granular · sessões de 10 a 24 min/ })
    expect(
      within(granular)
        .getAllByRole('heading', { level: 3 })
        .map((h) => h.textContent),
    ).toEqual(['Granular', 'Granular Lima'])
    expect(
      screen.getByRole('region', { name: /Purkinje · sessões de 60 min ou mais/ }),
    ).toBeVisible()
    expect(screen.getByRole('img', { name: 'Prévia do Piramidal Rosa' })).toHaveStyle({
      '--cor-neuronio': '#FF6FB5',
    })
    // Os originais já são do estudante e estão em uso.
    expect(within(cartao('Piramidal')).getByText('Em uso')).toBeInTheDocument()
    expect(within(cartao('Piramidal')).getByText('Original')).toBeInTheDocument()
    expect(within(cartao('Piramidal Rosa')).getByText('250 ATP')).toBeInTheDocument()
  })

  it('critério: compra com confirmação, desconta o saldo e passa a usar o tipo', async () => {
    const api = simularApi({ saldo: 300 })
    const usuario = renderizar()
    await screen.findByLabelText('Saldo: 300 ATP')

    await usuario.click(
      within(cartao('Piramidal Rosa')).getByRole('button', {
        name: 'Comprar o Piramidal Rosa por 250 ATP',
      }),
    )
    // Gastar ATP pede um segundo toque.
    expect(api.pedidos.filter((p) => p.startsWith('POST'))).toEqual([])
    await usuario.click(
      within(cartao('Piramidal Rosa')).getByRole('button', {
        name: 'Confirmar a compra do Piramidal Rosa por 250 ATP',
      }),
    )

    expect(await screen.findByLabelText('Saldo: 50 ATP')).toBeInTheDocument()
    expect(api.pedidos).toContain('POST /loja/piramidal_rosa/comprar')
    expect(within(cartao('Piramidal Rosa')).getByText('Em uso')).toBeInTheDocument()
    expect(within(cartao('Piramidal')).getByRole('button', { name: 'Usar' })).toBeEnabled()
    expect(screen.getByRole('status')).toHaveTextContent(
      'Piramidal Rosa desbloqueado! Suas próximas sessões de 25 a 59 min já nascem com ele.',
    )
  })

  it('cancelar a confirmação não compra nada', async () => {
    const api = simularApi()
    const usuario = renderizar()
    await screen.findByLabelText('Saldo: 300 ATP')

    await usuario.click(screen.getByRole('button', { name: 'Comprar o Granular Lima por 100 ATP' }))
    await usuario.click(screen.getByRole('button', { name: 'Cancelar' }))

    expect(
      screen.getByRole('button', { name: 'Comprar o Granular Lima por 100 ATP' }),
    ).toBeEnabled()
    expect(api.pedidos.filter((p) => p.startsWith('POST'))).toEqual([])
  })

  it('critério: sem saldo, mostra quanto falta e não deixa comprar', async () => {
    simularApi({ saldo: 120 })
    renderizar()
    await screen.findByLabelText('Saldo: 120 ATP')

    expect(screen.getByRole('button', { name: 'Faltam 130 ATP' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Faltam 380 ATP' })).toBeDisabled()
    expect(
      screen.getByRole('button', { name: 'Comprar o Granular Lima por 100 ATP' }),
    ).toBeEnabled()
  })

  it('mostra o motivo quando o servidor recusa a compra', async () => {
    // O saldo da tela ficou velho: o servidor diz que falta ATP.
    const api = simularApi({ saldo: 300 })
    const usuario = renderizar()
    await screen.findByLabelText('Saldo: 300 ATP')
    api.loja.saldo = 200

    await usuario.click(
      screen.getByRole('button', { name: 'Comprar o Piramidal Rosa por 250 ATP' }),
    )
    await usuario.click(
      screen.getByRole('button', { name: 'Confirmar a compra do Piramidal Rosa por 250 ATP' }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Faltam 50 ATP para comprar o Piramidal Rosa.',
    )
    expect(screen.getByLabelText('Saldo: 300 ATP')).toBeInTheDocument()
  })

  it('sem rede na compra, avisa e deixa tentar de novo', async () => {
    let semRede = true
    simularApi({ semRedeNaAcao: () => semRede })
    const usuario = renderizar()
    await screen.findByLabelText('Saldo: 300 ATP')

    await usuario.click(screen.getByRole('button', { name: 'Comprar o Granular Lima por 100 ATP' }))
    await usuario.click(
      screen.getByRole('button', { name: 'Confirmar a compra do Granular Lima por 100 ATP' }),
    )
    expect(await screen.findByRole('alert')).toHaveTextContent('Verifique sua conexão')

    semRede = false
    await usuario.click(
      screen.getByRole('button', { name: 'Confirmar a compra do Granular Lima por 100 ATP' }),
    )
    expect(await screen.findByLabelText('Saldo: 200 ATP')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('troca entre a variação comprada e o original', async () => {
    simularApi({ saldo: 300 })
    const usuario = renderizar()
    await screen.findByLabelText('Saldo: 300 ATP')
    await usuario.click(
      screen.getByRole('button', { name: 'Comprar o Piramidal Rosa por 250 ATP' }),
    )
    await usuario.click(
      screen.getByRole('button', { name: 'Confirmar a compra do Piramidal Rosa por 250 ATP' }),
    )
    await screen.findByLabelText('Saldo: 50 ATP')

    await usuario.click(within(cartao('Piramidal')).getByRole('button', { name: 'Usar' }))

    await waitFor(() => expect(within(cartao('Piramidal')).getByText('Em uso')).toBeInTheDocument())
    expect(within(cartao('Piramidal Rosa')).getByRole('button', { name: 'Usar' })).toBeEnabled()
    expect(screen.getByRole('status')).toHaveTextContent(
      'Suas próximas sessões de 25 a 59 min vão usar o Piramidal.',
    )
    // Voltar a usar não cobra de novo.
    expect(screen.getByLabelText('Saldo: 50 ATP')).toBeInTheDocument()
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
