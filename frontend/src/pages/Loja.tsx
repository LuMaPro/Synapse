import { useEffect, useState } from 'react'
import { NeuronioAnimado } from '../components/NeuronioAnimado'
import { ApiError } from '../services/api'
import { lojaApi, type LojaApi, type TipoLojaApi } from '../services/loja'
import '../styles/foco.css'
import '../styles/rede.css'
import '../styles/loja.css'
import { NOME_TIPO_NEURONIO, type TipoNeuronio } from '../utils/neuronio'

const FORMAS: TipoNeuronio[] = ['granular', 'piramidal', 'purkinje']

function faixa(tipo: TipoLojaApi): string {
  return tipo.duracao_maxima === null
    ? `${tipo.duracao_minima} min ou mais`
    : `${tipo.duracao_minima} a ${tipo.duracao_maxima} min`
}

function mensagemDeErro(erro: unknown): string {
  // O servidor explica o motivo (ex.: "Faltam 50 ATP..."); sem resposta, é a rede.
  if (erro instanceof ApiError && erro.status < 500) return erro.message
  return 'Não foi possível concluir. Verifique sua conexão e tente de novo.'
}

interface CartaoTipoProps {
  tipo: TipoLojaApi
  saldo: number
  confirmando: boolean
  ocupado: boolean
  onComprar: () => void
  onConfirmar: () => void
  onCancelar: () => void
  onUsar: () => void
}

function CartaoTipo({
  tipo,
  saldo,
  confirmando,
  ocupado,
  onComprar,
  onConfirmar,
  onCancelar,
  onUsar,
}: CartaoTipoProps) {
  const falta = tipo.preco - saldo

  let acao
  if (tipo.em_uso) {
    acao = <span className="selo loja-em-uso">Em uso</span>
  } else if (tipo.desbloqueado) {
    acao = (
      <button type="button" className="botao secundario" onClick={onUsar} disabled={ocupado}>
        Usar
      </button>
    )
  } else if (confirmando) {
    acao = (
      <div className="loja-confirmacao">
        <button
          type="button"
          className="botao primario"
          onClick={onConfirmar}
          disabled={ocupado}
          aria-label={`Confirmar a compra do ${tipo.nome} por ${tipo.preco} ATP`}
        >
          Confirmar
        </button>
        <button type="button" className="botao fantasma" onClick={onCancelar} disabled={ocupado}>
          Cancelar
        </button>
      </div>
    )
  } else if (falta > 0) {
    acao = (
      <button type="button" className="botao primario" disabled>
        Faltam {falta} ATP
      </button>
    )
  } else {
    // O preço já aparece acima do botão; o nome completo fica para leitores de tela.
    acao = (
      <button
        type="button"
        className="botao primario"
        onClick={onComprar}
        disabled={ocupado}
        aria-label={`Comprar o ${tipo.nome} por ${tipo.preco} ATP`}
      >
        Comprar
      </button>
    )
  }

  return (
    <li className={tipo.em_uso ? 'loja-cartao em-uso' : 'loja-cartao'}>
      <NeuronioAnimado
        tipo={tipo.forma}
        progresso={1}
        cor={tipo.cor}
        tamanho={96}
        rotulo={`Prévia do ${tipo.nome}`}
      />
      <div className="loja-info">
        <h3>{tipo.nome}</h3>
        <p>{tipo.preco === 0 ? 'Original' : `${tipo.preco} ATP`}</p>
      </div>
      {acao}
    </li>
  )
}

/** Loja de ATP (issue #34): troque o ATP das sessões por novas cores de neurônio. */
export function Loja() {
  const [loja, setLoja] = useState<LojaApi | null>(null)
  const [erroAoCarregar, setErroAoCarregar] = useState(false)
  const [tentativa, setTentativa] = useState(0)
  const [confirmando, setConfirmando] = useState<string | null>(null)
  const [ocupado, setOcupado] = useState(false)
  const [erroDaAcao, setErroDaAcao] = useState<string | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)

  useEffect(() => {
    let ativo = true
    lojaApi
      .buscar()
      .then((resposta) => {
        if (ativo) setLoja(resposta)
      })
      .catch(() => {
        if (ativo) setErroAoCarregar(true)
      })
    return () => {
      ativo = false
    }
  }, [tentativa])

  async function executar(acao: () => Promise<LojaApi>, sucesso: string) {
    setOcupado(true)
    setErroDaAcao(null)
    setAviso(null)
    try {
      setLoja(await acao())
      setConfirmando(null)
      setAviso(sucesso)
    } catch (erro) {
      setErroDaAcao(mensagemDeErro(erro))
    } finally {
      setOcupado(false)
    }
  }

  function tentarDeNovo() {
    setErroAoCarregar(false)
    setTentativa((t) => t + 1)
  }

  let conteudo
  if (erroAoCarregar) {
    conteudo = (
      <div className="rede-mensagem" role="alert">
        <p>Não foi possível carregar a loja. Verifique sua conexão.</p>
        <button type="button" className="botao secundario" onClick={tentarDeNovo}>
          Tentar de novo
        </button>
      </div>
    )
  } else if (!loja) {
    conteudo = (
      <p className="rede-mensagem" role="status">
        Carregando a loja…
      </p>
    )
  } else {
    conteudo = FORMAS.map((forma) => {
      const tipos = loja.tipos.filter((t) => t.forma === forma)
      if (tipos.length === 0) return null
      return (
        <section key={forma} className="loja-forma" aria-labelledby={`forma-${forma}`}>
          <h2 id={`forma-${forma}`}>
            {NOME_TIPO_NEURONIO[forma]} <span>· sessões de {faixa(tipos[0])}</span>
          </h2>
          <ul>
            {tipos.map((tipo) => (
              <CartaoTipo
                key={tipo.codigo}
                tipo={tipo}
                saldo={loja.saldo}
                confirmando={confirmando === tipo.codigo}
                ocupado={ocupado}
                onComprar={() => {
                  setErroDaAcao(null)
                  setConfirmando(tipo.codigo)
                }}
                onCancelar={() => setConfirmando(null)}
                onConfirmar={() =>
                  executar(
                    () => lojaApi.comprar(tipo.codigo),
                    `${tipo.nome} desbloqueado! Suas próximas sessões de ${faixa(tipo)} já nascem com ele.`,
                  )
                }
                onUsar={() =>
                  executar(
                    () => lojaApi.usar(tipo.codigo),
                    `Suas próximas sessões de ${faixa(tipo)} vão usar o ${tipo.nome}.`,
                  )
                }
              />
            ))}
          </ul>
        </section>
      )
    })
  }

  return (
    <section className="rede loja" aria-busy={!loja && !erroAoCarregar}>
      <div className="rede-cabecalho">
        <h1>Loja</h1>
        {loja && (
          <span className="selo atp loja-saldo" aria-label={`Saldo: ${loja.saldo} ATP`}>
            {loja.saldo} ATP
          </span>
        )}
      </div>
      <p className="loja-intro">
        Cada minuto de foco concluído rende 1 ATP. Troque por novas cores de neurônio: a forma
        continua mostrando quanto durou a sessão. Nas sessões com matéria, vale a cor da matéria.
      </p>
      {erroDaAcao && (
        <p className="loja-erro" role="alert">
          {erroDaAcao}
        </p>
      )}
      {aviso && (
        <p className="loja-aviso" role="status">
          {aviso}
        </p>
      )}
      {conteudo}
    </section>
  )
}
