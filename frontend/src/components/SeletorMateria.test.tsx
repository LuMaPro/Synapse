import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { Materia } from '../services/materias'
import { SeletorMateria } from './SeletorMateria'

describe('SeletorMateria', () => {
  const materias: Materia[] = [
    { id: 'mat-1', nome: 'Cálculo', cor: '#8B7BFF', criada_em: '' },
    { id: 'mat-2', nome: 'POO', cor: '#3EE6E0', criada_em: '' },
  ]

  it('exibe o rótulo e as opções de matérias com Sem matéria', () => {
    render(<SeletorMateria materias={materias} materiaId={null} onEscolher={vi.fn()} />)

    expect(screen.getByText('Matéria')).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: 'Cálculo' })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: 'POO' })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: 'Sem matéria' })).toBeInTheDocument()
  })

  it('marca a opção Sem matéria como selecionada quando materiaId é null', () => {
    render(<SeletorMateria materias={materias} materiaId={null} onEscolher={vi.fn()} />)

    const semMateria = screen.getByRole('radio', { name: 'Sem matéria' })
    expect(semMateria).toBeChecked()
    expect(semMateria).toHaveClass('ativo')

    const calculo = screen.getByRole('radio', { name: 'Cálculo' })
    expect(calculo).not.toBeChecked()
    expect(calculo).not.toHaveClass('ativo')
  })

  it('marca a matéria correspondente quando materiaId está definido', () => {
    render(<SeletorMateria materias={materias} materiaId="mat-2" onEscolher={vi.fn()} />)

    const poo = screen.getByRole('radio', { name: 'POO' })
    expect(poo).toBeChecked()
    expect(poo).toHaveClass('ativo')

    const semMateria = screen.getByRole('radio', { name: 'Sem matéria' })
    expect(semMateria).not.toBeChecked()
  })

  it('chama onEscolher com o id da matéria ao clicar', async () => {
    const usuario = userEvent.setup()
    const onEscolher = vi.fn()
    render(<SeletorMateria materias={materias} materiaId={null} onEscolher={onEscolher} />)

    await usuario.click(screen.getByRole('radio', { name: 'Cálculo' }))
    expect(onEscolher).toHaveBeenCalledWith('mat-1')
  })

  it('chama onEscolher com null ao clicar em Sem matéria', async () => {
    const usuario = userEvent.setup()
    const onEscolher = vi.fn()
    render(<SeletorMateria materias={materias} materiaId="mat-1" onEscolher={onEscolher} />)

    await usuario.click(screen.getByRole('radio', { name: 'Sem matéria' }))
    expect(onEscolher).toHaveBeenCalledWith(null)
  })

  it('desabilita os botões quando disabled é true', () => {
    render(<SeletorMateria materias={materias} materiaId={null} onEscolher={vi.fn()} disabled />)

    expect(screen.getByRole('radio', { name: 'Cálculo' })).toBeDisabled()
    expect(screen.getByRole('radio', { name: 'POO' })).toBeDisabled()
    expect(screen.getByRole('radio', { name: 'Sem matéria' })).toBeDisabled()
  })
})
