import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../services/api'
import { materiasApi, type Materia } from '../services/materias'
import { Materias } from './Materias'

function renderizar() {
  const usuario = userEvent.setup()
  render(
    <MemoryRouter>
      <Materias />
    </MemoryRouter>,
  )
  return usuario
}

describe('tela de gerenciamento de matérias (Materias)', () => {
  const listaExemplo: Materia[] = [
    {
      id: 'mat-1',
      nome: 'Cálculo I',
      cor: '#8B7BFF',
      criada_em: '2026-10-24T10:00:00Z',
    },
    {
      id: 'mat-2',
      nome: 'Física',
      cor: '#3EE6E0',
      criada_em: '2026-10-24T11:00:00Z',
    },
  ]

  beforeEach(() => {
    vi.spyOn(materiasApi, 'listar').mockResolvedValue([...listaExemplo])
    vi.spyOn(materiasApi, 'criar').mockResolvedValue({
      id: 'mat-nova',
      nome: 'Nova',
      cor: '#8B7BFF',
      criada_em: '2026-10-24T12:00:00Z',
    })
    vi.spyOn(materiasApi, 'atualizar').mockResolvedValue(listaExemplo[0])
    vi.spyOn(materiasApi, 'remover').mockResolvedValue(undefined)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('exibe o cabeçalho e a lista de matérias carregadas', async () => {
    renderizar()

    expect(screen.getByRole('heading', { name: 'Matérias' })).toBeInTheDocument()
    expect(
      screen.getByText('Organize suas sessões de foco e a cor dos seus neurônios por disciplina.'),
    ).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('Cálculo I')).toBeInTheDocument()
      expect(screen.getByText('Física')).toBeInTheDocument()
    })
  })

  it('exibe estado vazio quando o usuário não possui matérias', async () => {
    vi.spyOn(materiasApi, 'listar').mockResolvedValueOnce([])
    renderizar()

    await waitFor(() => {
      expect(screen.getByText('Você ainda não tem matérias cadastradas.')).toBeInTheDocument()
    })
  })

  it('exibe mensagem de erro quando o carregamento inicial falha', async () => {
    vi.spyOn(materiasApi, 'listar').mockRejectedValueOnce(new Error('Erro de conexão'))
    renderizar()

    await waitFor(() => {
      expect(screen.getByText('Não foi possível carregar as matérias.')).toBeInTheDocument()
    })
  })

  it('permite criar uma nova matéria escolhendo nome e cor', async () => {
    const nova: Materia = {
      id: 'mat-3',
      nome: 'Álgebra Linear',
      cor: '#5BE49B',
      criada_em: '2026-10-24T12:00:00Z',
    }
    vi.spyOn(materiasApi, 'criar').mockResolvedValueOnce(nova)

    const usuario = renderizar()

    await waitFor(() => {
      expect(screen.getByText('Cálculo I')).toBeInTheDocument()
    })

    const formCriacao = screen.getByRole('form', { name: 'Cadastrar nova matéria' })
    const inputNome = within(formCriacao).getByLabelText('Nome da matéria')
    await usuario.type(inputNome, 'Álgebra Linear')

    // Seleciona a cor Verde (#5BE49B) dentro do form de criação
    const botaoVerde = within(formCriacao).getByRole('radio', { name: 'Cor Verde' })
    await usuario.click(botaoVerde)
    expect(botaoVerde).toBeChecked()

    const botaoAdicionar = within(formCriacao).getByRole('button', { name: 'Adicionar matéria' })
    await usuario.click(botaoAdicionar)

    expect(materiasApi.criar).toHaveBeenCalledWith({
      nome: 'Álgebra Linear',
      cor: '#5BE49B',
    })

    await waitFor(() => {
      expect(screen.getByText('Álgebra Linear')).toBeInTheDocument()
    })
    expect(inputNome).toHaveValue('')
  })

  it('exibe mensagem de erro amigável ao falhar a criação por nome duplicado', async () => {
    vi.spyOn(materiasApi, 'criar').mockRejectedValueOnce(
      new ApiError(409, 'materia_ja_existe', 'Conflito'),
    )

    const usuario = renderizar()

    await waitFor(() => {
      expect(screen.getByText('Cálculo I')).toBeInTheDocument()
    })

    const formCriacao = screen.getByRole('form', { name: 'Cadastrar nova matéria' })
    const inputNome = within(formCriacao).getByLabelText('Nome da matéria')
    await usuario.type(inputNome, 'Cálculo I')

    const botaoAdicionar = within(formCriacao).getByRole('button', { name: 'Adicionar matéria' })
    await usuario.click(botaoAdicionar)

    await waitFor(() => {
      expect(screen.getByText('Você já tem uma matéria com este nome.')).toBeInTheDocument()
    })
  })

  it('permite editar o nome e a cor de uma matéria', async () => {
    const atualizada: Materia = {
      ...listaExemplo[0],
      nome: 'Cálculo Avançado',
      cor: '#FFC857',
    }
    vi.spyOn(materiasApi, 'atualizar').mockResolvedValueOnce(atualizada)

    const usuario = renderizar()

    await waitFor(() => {
      expect(screen.getByText('Cálculo I')).toBeInTheDocument()
    })

    const botaoEditar = screen.getByRole('button', { name: 'Editar Cálculo I' })
    await usuario.click(botaoEditar)

    // O formulário de edição substitui o item
    const formEdicao = screen.getByRole('form', { name: 'Editar matéria Cálculo I' })
    const inputEdicao = within(formEdicao).getByLabelText('Nome')
    await usuario.clear(inputEdicao)
    await usuario.type(inputEdicao, 'Cálculo Avançado')

    const botaoAmbar = within(formEdicao).getByRole('radio', { name: 'Cor Âmbar' })
    await usuario.click(botaoAmbar)

    const botaoSalvar = within(formEdicao).getByRole('button', { name: 'Salvar' })
    await usuario.click(botaoSalvar)

    expect(materiasApi.atualizar).toHaveBeenCalledWith('mat-1', {
      nome: 'Cálculo Avançado',
      cor: '#FFC857',
    })

    await waitFor(() => {
      expect(screen.getByText('Cálculo Avançado')).toBeInTheDocument()
      expect(screen.queryByText('Cálculo I')).not.toBeInTheDocument()
    })
  })

  it('permite cancelar a edição sem salvar', async () => {
    const usuario = renderizar()

    await waitFor(() => {
      expect(screen.getByText('Cálculo I')).toBeInTheDocument()
    })

    const botaoEditar = screen.getByRole('button', { name: 'Editar Cálculo I' })
    await usuario.click(botaoEditar)

    const formEdicao = screen.getByRole('form', { name: 'Editar matéria Cálculo I' })
    const inputEdicao = within(formEdicao).getByLabelText('Nome')
    await usuario.clear(inputEdicao)
    await usuario.type(inputEdicao, 'Texto Descartado')

    const botaoCancelar = within(formEdicao).getByRole('button', { name: 'Cancelar' })
    await usuario.click(botaoCancelar)

    expect(screen.getByText('Cálculo I')).toBeInTheDocument()
    expect(screen.queryByDisplayValue('Texto Descartado')).not.toBeInTheDocument()
    expect(materiasApi.atualizar).not.toHaveBeenCalled()
  })

  it('permite excluir uma matéria após confirmação', async () => {
    vi.spyOn(materiasApi, 'remover').mockResolvedValueOnce(undefined)

    const usuario = renderizar()

    await waitFor(() => {
      expect(screen.getByText('Cálculo I')).toBeInTheDocument()
    })

    const botaoExcluir = screen.getByRole('button', { name: 'Excluir Cálculo I' })
    await usuario.click(botaoExcluir)

    // Confirmação de exclusão aparece
    expect(screen.getByText(/Deseja excluir a matéria/)).toBeInTheDocument()
    expect(
      screen.getByText(/As sessões de foco e neurônios já concluídos continuarão existindo/),
    ).toBeInTheDocument()

    const botaoConfirmar = screen.getByRole('button', { name: 'Sim, excluir' })
    await usuario.click(botaoConfirmar)

    expect(materiasApi.remover).toHaveBeenCalledWith('mat-1')

    await waitFor(() => {
      expect(screen.queryByText('Cálculo I')).not.toBeInTheDocument()
      expect(screen.getByText('Física')).toBeInTheDocument()
    })
  })

  it('permite cancelar a exclusão', async () => {
    const usuario = renderizar()

    await waitFor(() => {
      expect(screen.getByText('Cálculo I')).toBeInTheDocument()
    })

    const botaoExcluir = screen.getByRole('button', { name: 'Excluir Cálculo I' })
    await usuario.click(botaoExcluir)

    expect(screen.getByText(/Deseja excluir a matéria/)).toBeInTheDocument()

    const botaoCancelar = screen.getByRole('button', { name: 'Cancelar' })
    await usuario.click(botaoCancelar)

    expect(screen.queryByText(/Deseja excluir a matéria/)).not.toBeInTheDocument()
    expect(screen.getByText('Cálculo I')).toBeInTheDocument()
    expect(materiasApi.remover).not.toHaveBeenCalled()
  })
})
