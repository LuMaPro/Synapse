import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { NeuronioAnimado } from '../components/NeuronioAnimado'
import { ApiError } from '../services/api'
import { lojaApi, type CorLojaApi, type LojaApi } from '../services/loja'
import '../styles/foco.css'
import '../styles/rede.css'
import '../styles/loja.css'

const SECOES: { titulo: string; descricao: string; comEfeito: boolean }[] = [
  { titulo: 'Cores exclusivas', descricao: 'Tons que não estão na paleta.', comEfeito: false },
  { titulo: 'Cores com efeito', descricao: 'Neurônios que se mexem.', comEfeito: true },
]

function mensagemDeErro(erro: unknown): string {
  // O servidor explica o motivo (ex.: "Faltam 50 ATP..."); sem resposta, é a rede.
  if (erro instanceof ApiError && erro.status < 500) return erro.message
  return 'Não foi possível concluir. Verifique sua conexão e tente de novo.'
}

interface CartaoCorProps {
  cor: CorLojaApi
  saldo: number
  confirmando: boolean
  ocupado: boolean
  onComprar: () => void
  onConfirmar: () => void
  onCancelar: () => void
}

function CartaoCor({
  cor,
  saldo,
  confirmando,
  ocupado,
  onComprar,
  onConfirmar,
  onCancelar,
}: CartaoCorProps) {
  const falta = cor.preco - saldo

  let acao
  if (cor.desbloqueada) {
    acao = <span className="selo loja-sua">Sua</span>
  } else if (confirmando) {
    acao = (
      <div className="loja-confirmacao">
        <button
          type="button"
          className="botao primario"
          onClick={onConfirmar}
          disabled={ocupado}
          aria-label={`Confirmar a compra da cor ${cor.nome} por ${cor.preco} ATP`}
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
        aria-label={`Comprar a cor ${cor.nome} por ${cor.preco} ATP`}
      >
        Comprar
      </button>
    )
  }

  return (
    <li className={cor.desbloqueada ? 'loja-cartao desbloqueada' : 'loja-cartao'}>
      <NeuronioAnimado
        tipo="piramidal"
        progresso={1}
        cor={cor.cor}
        efeito={cor.efeito}
        tamanho={96}
        rotulo={`Prévia da cor ${cor.nome}`}
      />
      <div className="loja-info">
        <h3>{cor.nome}</h3>
        <p>{cor.preco} ATP</p>
      </div>
      {acao}
    </li>
  )
}

/** Loja de ATP (issue #34): troque o ATP das sessões por cores para as matérias. */
export function Loja() {
  const [loja, setLoja] = useState<LojaApi | null>(null)
  const [erroAoCarregar, setErroAoCarregar] = useState(false)
  const [tentativa, setTentativa] = useState(0)
  const [confirmando, setConfirmando] = useState<string | null>(null)
  const [ocupado, setOcupado] = useState(false)
  const [erroDaCompra, setErroDaCompra] = useState<string | null>(null)
  const [comprada, setComprada] = useState<CorLojaApi | null>(null)

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

  async function comprar(cor: CorLojaApi) {
    setOcupado(true)
    setErroDaCompra(null)
    setComprada(null)
    try {
      setLoja(await lojaApi.comprar(cor.codigo))
      setConfirmando(null)
      setComprada(cor)
    } catch (erro) {
      setErroDaCompra(mensagemDeErro(erro))
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
    conteudo = SECOES.map(({ titulo, descricao, comEfeito }) => {
      // As 8 cores da paleta são de todos e não estão à venda.
      const cores = loja.cores.filter((c) => c.preco > 0 && Boolean(c.efeito) === comEfeito)
      if (cores.length === 0) return null
      const id = comEfeito ? 'secao-efeitos' : 'secao-exclusivas'
      return (
        <section key={id} className="loja-secao" aria-labelledby={id}>
          <h2 id={id}>
            {titulo} <span>· {descricao}</span>
          </h2>
          <ul>
            {cores.map((cor) => (
              <CartaoCor
                key={cor.codigo}
                cor={cor}
                saldo={loja.saldo}
                confirmando={confirmando === cor.codigo}
                ocupado={ocupado}
                onComprar={() => {
                  setErroDaCompra(null)
                  setConfirmando(cor.codigo)
                }}
                onCancelar={() => setConfirmando(null)}
                onConfirmar={() => comprar(cor)}
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
        Cada minuto de foco concluído rende 1 ATP. Troque por cores exclusivas para as suas
        matérias: os neurônios de cada matéria nascem na cor dela. As 8 cores da paleta são de
        todos.
      </p>
      {erroDaCompra && (
        <p className="loja-erro" role="alert">
          {erroDaCompra}
        </p>
      )}
      {comprada && (
        <p className="loja-aviso" role="status">
          Cor {comprada.nome} desbloqueada! Escolha-a para uma matéria em{' '}
          <Link to="/materias">Matérias</Link>.
        </p>
      )}
      {conteudo}
    </section>
  )
}
