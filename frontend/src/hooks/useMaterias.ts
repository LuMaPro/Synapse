import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../services/api'
import { materiasApi, type Materia } from '../services/materias'

export function useMaterias() {
  const [materias, setMaterias] = useState<Materia[]>([])
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState<string | null>(null)

  const carregar = useCallback(async () => {
    setCarregando(true)
    setErro(null)
    try {
      const lista = await materiasApi.listar()
      setMaterias(lista)
    } catch {
      setErro('Não foi possível carregar as matérias.')
    } finally {
      setCarregando(false)
    }
  }, [])

  useEffect(() => {
    let ativo = true
    materiasApi
      .listar()
      .then((lista) => {
        if (ativo) {
          setMaterias(lista)
          setCarregando(false)
        }
      })
      .catch(() => {
        if (ativo) {
          setErro('Não foi possível carregar as matérias.')
          setCarregando(false)
        }
      })
    return () => {
      ativo = false
    }
  }, [])

  const criar = useCallback(async (nome: string, cor: string): Promise<Materia> => {
    setErro(null)
    try {
      const nova = await materiasApi.criar({ nome: nome.trim(), cor })
      setMaterias((atuais) => {
        const atualizadas = [...atuais, nova]
        return atualizadas.sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
      })
      return nova
    } catch (e) {
      if (e instanceof ApiError && (e.status === 409 || e.codigo === 'materia_ja_existe')) {
        throw new Error('Você já tem uma matéria com este nome.', { cause: e })
      }
      if (e instanceof ApiError && (e.status === 400 || e.status === 422)) {
        throw new Error('Nome ou cor inválidos.', { cause: e })
      }
      throw new Error('Não foi possível criar a matéria. Tente novamente.', { cause: e })
    }
  }, [])

  const atualizar = useCallback(
    async (id: string, dados: { nome?: string; cor?: string }): Promise<Materia> => {
      setErro(null)
      try {
        const payload = {
          ...(dados.nome !== undefined ? { nome: dados.nome.trim() } : {}),
          ...(dados.cor !== undefined ? { cor: dados.cor } : {}),
        }
        const atualizada = await materiasApi.atualizar(id, payload)
        setMaterias((atuais) => {
          const lista = atuais.map((m) => (m.id === id ? atualizada : m))
          return lista.sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
        })
        return atualizada
      } catch (e) {
        if (e instanceof ApiError && (e.status === 409 || e.codigo === 'materia_ja_existe')) {
          throw new Error('Você já tem uma matéria com este nome.', { cause: e })
        }
        if (e instanceof ApiError && (e.status === 400 || e.status === 422)) {
          throw new Error('Nome ou cor inválidos.', { cause: e })
        }
        throw new Error('Não foi possível atualizar a matéria. Tente novamente.', { cause: e })
      }
    },
    [],
  )

  const remover = useCallback(async (id: string): Promise<void> => {
    setErro(null)
    try {
      await materiasApi.remover(id)
      setMaterias((atuais) => atuais.filter((m) => m.id !== id))
    } catch (e) {
      throw new Error('Não foi possível excluir a matéria. Tente novamente.', { cause: e })
    }
  }, [])

  return {
    materias,
    carregando,
    erro,
    carregar,
    criar,
    atualizar,
    remover,
  }
}
