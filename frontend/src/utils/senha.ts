/** Tamanho mínimo exigido pelo backend (MinimumLengthValidator do Django). */
export const SENHA_TAMANHO_MINIMO = 8

/**
 * Confere uma senha nova antes de enviar o cadastro. São as regras do backend
 * (AUTH_PASSWORD_VALIDATORS) que dá para verificar no navegador: tamanho mínimo e não
 * ser só números. Senhas comuns e parecidas com o e-mail dependem da lista e do
 * algoritmo do Django, então ficam com o servidor, cuja mensagem aparece na tela.
 *
 * Devolve a mensagem de erro, ou null se a senha passou.
 */
export function validarSenhaNova(senha: string): string | null {
  if (!senha) return 'A senha é obrigatória.'
  if (senha.length < SENHA_TAMANHO_MINIMO) {
    return `A senha deve ter no mínimo ${SENHA_TAMANHO_MINIMO} caracteres.`
  }
  if (/^\d+$/.test(senha)) return 'A senha não pode ter só números.'
  return null
}
