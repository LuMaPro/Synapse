import { useCallback, useEffect, useState } from 'react'
import {
  conquistasApi,
  type ConquistaApi,
  type SequenciaApi,
} from '../services/conquistas'

export function useConquistas() {
  const [conquistas, setConquistas] = useState<ConquistaApi[]>([])
  const [sequencia, setSequencia] = useState<SequenciaApi | null>(null)
  const [desbloqueadas, setDesbloqueadas] = useState(0)
  const [total, setTotal] = useState(0)
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState<string | null>(null)

  const recarregar = useCallback(async () => {
    setCarregando(true)
    setErro(null)
    try {
      const dados = await conquistasApi.consultar()
      setConquistas(dados.conquistas)
      setSequencia(dados.sequencia)
      setDesbloqueadas(dados.desbloqueadas)
      setTotal(dados.total)
    } catch {
      setErro('Não foi possível carregar as conquistas.')
    } finally {
      setCarregando(false)
    }
  }, [])

  useEffect(() => {
    let ativo = true
    conquistasApi
      .consultar()
      .then((dados) => {
        if (ativo) {
          setConquistas(dados.conquistas)
          setSequencia(dados.sequencia)
          setDesbloqueadas(dados.desbloqueadas)
          setTotal(dados.total)
          setCarregando(false)
        }
      })
      .catch(() => {
        if (ativo) {
          setErro('Não foi possível carregar as conquistas.')
          setCarregando(false)
        }
      })
    return () => {
      ativo = false
    }
  }, [])

  return {
    conquistas,
    sequencia,
    desbloqueadas,
    total,
    carregando,
    erro,
    recarregar,
  }
}
