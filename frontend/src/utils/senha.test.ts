import { describe, expect, it } from 'vitest'
import { SENHA_TAMANHO_MINIMO, validarSenhaNova } from './senha'

describe('validarSenhaNova', () => {
  it('exige 8 caracteres, como o backend', () => {
    expect(SENHA_TAMANHO_MINIMO).toBe(8)
  })

  it.each([
    ['', 'A senha é obrigatória.'],
    ['abc1234', 'A senha deve ter no mínimo 8 caracteres.'],
    ['12345678', 'A senha não pode ter só números.'],
    ['20262026202620', 'A senha não pode ter só números.'],
  ])('recusa %j', (senha, mensagem) => {
    expect(validarSenhaNova(senha)).toBe(mensagem)
  })

  it.each(['foco1234', 'rede-neural-2026', 'Abcdefgh'])('aceita %j', (senha) => {
    expect(validarSenhaNova(senha)).toBeNull()
  })
})
