import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError, obterTokenApi } from './api'
import {
  AuthError,
  CHAVE_REFRESH_TOKEN,
  CHAVE_USUARIO,
  cadastroApi,
  cadastroMock,
  limparSessao,
  loginApi,
  loginMock,
  obterSessaoSalva,
  renovarTokenApi,
  salvarSessao,
} from './auth'

describe('serviço de autenticação (auth.ts) - casos de erro e exceções', () => {
  beforeEach(() => {
    limparSessao()
    localStorage.clear()
    vi.restoreAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('loginMock - casos de erro', () => {
    it('lança AuthError com credenciais inválidas para e-mail erro@email.com', async () => {
      await expect(
        loginMock({ email: 'erro@email.com', senha: '123456' }),
      ).rejects.toThrow(AuthError)

      await expect(
        loginMock({ email: 'erro@email.com', senha: '123456' }),
      ).rejects.toMatchObject({
        codigo: 'credenciais_invalidas',
        message: 'Credenciais inválidas. Verifique seu e-mail e senha.',
      })
    })

    it('lança AuthError com senha incorreta para senhaerrada', async () => {
      await expect(
        loginMock({ email: 'usuario@valido.com', senha: 'senhaerrada' }),
      ).rejects.toMatchObject({
        codigo: 'credenciais_invalidas',
      })
    })
  })

  describe('cadastroMock - casos de erro', () => {
    it('lança AuthError com código email_duplicado quando e-mail já existe', async () => {
      await expect(
        cadastroMock({
          nome: 'Usuário Teste',
          email: 'existe@email.com',
          senha: '123456',
        }),
      ).rejects.toMatchObject({
        codigo: 'email_duplicado',
        message: 'E-mail já cadastrado. Tente fazer login ou use outro e-mail.',
      })
    })
  })

  describe('loginApi - casos de erro', () => {
    it('propaga ApiError quando a chamada /auth/login é rejeitada pelo servidor', async () => {
      vi.spyOn(api, 'post').mockRejectedValueOnce(
        new ApiError(401, 'credenciais_invalidas', 'E-mail ou senha incorretos.'),
      )

      await expect(
        loginApi({ email: 'usuario@synapse.com', senha: 'senha-errada' }),
      ).rejects.toThrow('E-mail ou senha incorretos.')
    })

    it('propaga ApiError quando a chamada subsequente para /me falha', async () => {
      vi.spyOn(api, 'post').mockResolvedValueOnce({
        access: 'token-jwt-temporario',
        refresh: 'refresh-jwt-temporario',
      })
      vi.spyOn(api, 'get').mockRejectedValueOnce(
        new ApiError(401, 'token_invalido', 'Token inválido ou expirado.'),
      )

      await expect(
        loginApi({ email: 'usuario@synapse.com', senha: 'senha-valida' }),
      ).rejects.toMatchObject({
        status: 401,
        codigo: 'token_invalido',
      })
    })
  })

  describe('cadastroApi - casos de erro', () => {
    it('propaga ApiError quando /auth/cadastro rejeita a criação da conta', async () => {
      vi.spyOn(api, 'post').mockRejectedValueOnce(
        new ApiError(409, 'email_em_uso', 'Este e-mail já está em uso.'),
      )

      await expect(
        cadastroApi({
          nome: 'Mariana',
          email: 'mariana@duplicada.com',
          senha: 'senha123',
        }),
      ).rejects.toMatchObject({
        status: 409,
        codigo: 'email_em_uso',
        message: 'Este e-mail já está em uso.',
      })
    })
  })

  describe('renovarTokenApi - casos de erro', () => {
    it('retorna null e limpa a sessão quando não há refresh token salvo', async () => {
      const token = await renovarTokenApi()
      expect(token).toBeNull()
      expect(obterTokenApi()).toBeNull()
    })

    it('retorna null e limpa a sessão quando a chamada /auth/renovar falha na API', async () => {
      salvarSessao('token-antigo', 'refresh-invalido', {
        id: 'usr-1',
        nome: 'Teste',
        email: 'teste@synapse.com',
      })

      vi.spyOn(api, 'post').mockRejectedValueOnce(
        new ApiError(401, 'token_revogado', 'Refresh token expirado ou revogado.'),
      )

      const resultado = await renovarTokenApi()
      expect(resultado).toBeNull()
      expect(obterTokenApi()).toBeNull()
      expect(localStorage.getItem(CHAVE_REFRESH_TOKEN)).toBeNull()
    })
  })

  describe('obterSessaoSalva, salvarSessao e limparSessao - tratamento de falhas', () => {
    it('retorna usuario como null sem lançar exceção se o localStorage tiver JSON corrompido', () => {
      localStorage.setItem(CHAVE_USUARIO, 'JSON-INVALIDO-{{{')
      const sessao = obterSessaoSalva()

      expect(sessao.usuario).toBeNull()
    })

    it('salvarSessao não falha se localStorage.setItem lançar exceção de quota ou permissão', () => {
      vi.spyOn(Storage.prototype, 'setItem').mockImplementationOnce(() => {
        throw new DOMException('QuotaExceededError')
      })

      expect(() => {
        salvarSessao('token-qualquer', 'refresh-qualquer', {
          id: 'usr-1',
          nome: 'Teste',
          email: 'teste@synapse.com',
        })
      }).not.toThrow()
    })

    it('limparSessao não falha se localStorage.removeItem lançar exceção', () => {
      vi.spyOn(Storage.prototype, 'removeItem').mockImplementationOnce(() => {
        throw new DOMException('SecurityError')
      })

      expect(() => {
        limparSessao()
      }).not.toThrow()
    })
  })
})
