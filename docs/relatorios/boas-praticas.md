# Boas Práticas de Programação e Orientação a Objetos

> Enunciado, seção 2.5.1: para cada prática citada, indicar a classe, o módulo ou o trecho de código em que foi aplicada.

Cada PR que aplicar uma prática registra aqui o caminho do arquivo e um trecho curto de código. A versão final é consolidada na issue #44.

## SOLID

### S: Responsabilidade única

### O: Aberto/fechado

### L: Substituição de Liskov

### I: Segregação de interfaces

### D: Inversão de dependência

- **Repositórios abstratos no domínio e implementações injetadas** (`backend/app/domain/repositorios.py`, issue #13): as regras de negócio e os serviços dependem exclusivamente de interfaces abstratas (`RepositorioUsuario` e `RepositorioSessao` herdando de `ABC`), e nunca de implementações concretas ou do ORM do Django. A infraestrutura (`backend/app/infra/repositorios/`) implementa essas interfaces para o PostgreSQL usando o Django ORM (`RepositorioUsuarioDjango`, `RepositorioSessaoDjango`), enquanto os testes unitários utilizam implementações em memória (`backend/tests/repositorios.py`). A dependência foi invertida: o domínio define os contratos e a infraestrutura se adapta a eles, e não o contrário.

## Separação em camadas

- **Domínio puro** (`backend/app/domain/`, issue #9): entidades, objetos de valor e exceções não dependem do Django nem do DRF, então as regras de negócio são testadas sem banco e sem servidor. A regra é verificada automaticamente por `backend/tests/unit/domain/test_dominio_puro.py`.
- **Cadastro como caso de uso** (`backend/app/application/cadastro.py`, issue #14): a view `cadastro` (`backend/app/api/auth.py`) só lê a requisição e traduz erros para HTTP. A regra de negócio fica em `CadastroUsuario`, que usa a entidade `Usuario` (validação de nome e e-mail), o `RepositorioUsuario` (e-mail único) e a interface `ServicoSenhas`, implementada na infraestrutura com os validadores e o hash Argon2 do Django (`backend/app/infra/senhas.py`). O caso de uso depende só de interfaces (princípio D do SOLID) e é testado com repositório em memória (`backend/tests/unit/application/test_cadastro.py`).
- **Rede neural separada da sessão** (`backend/app/application/rede.py`, issue #23): quando uma sessão termina, o `SessaoService` só cria o neurônio (vivo se foi concluída, morto se foi podada) e o entrega ao `RedeNeuralService`. Quem decide as ligações é a regra de formação, escolhida na montagem do serviço; o `SessaoService` não a conhece. A issue #24 vai trocar essa chamada direta por eventos (Observer).
- **Endpoint da rede sem regra de negócio** (`backend/app/api/rede.py`, issues #22 e #25): a view só valida os filtros, chama `RedeNeuralService.consultar` e monta o JSON. O recorte (período, matéria e as sinapses que ficam, só as que ligam dois neurônios escolhidos) é do agregado, em `RedeNeural.recortar`, e o tipo e a cor vêm do próprio `Neuronio` (`neuronio.tipo.codigo` e `neuronio.cor`), criados pela `FabricaNeuronio` no domínio.
- **Sessões de foco como casos de uso** (`backend/app/application/sessoes.py`, issue #16): `SessaoService` orquestra a entidade `SessaoFoco` (estados e políticas) e os repositórios, com o relógio do servidor injetado. As views em `backend/app/api/sessoes.py` só validam o formato da requisição e montam a resposta; a regra de tempo (o servidor como fonte da verdade, a tolerância de 2 s, a expiração de sessões abandonadas) não aparece nelas.
- **Lógica separada da tela no frontend** (`frontend/src/hooks/useSessaoFoco.ts`, issue #17): o hook concentra o estado e as regras da sessão (limites da duração, timer, conclusão, desistência, tela cheia), e a página `frontend/src/pages/Foco.tsx` só desenha o que ele devolve. Assim o timer é testado sem renderizar a tela, e a integração com a API (issue #20) muda o hook sem mexer nos componentes.

## Baixo acoplamento e alta coesão

- **Neurônio em três partes** (issue #19): a geometria é uma função pura em `frontend/src/utils/geometriaNeuronio.ts` (recebe tipo, progresso e se está podado e devolve o que desenhar), o componente `frontend/src/components/NeuronioAnimado.tsx` só transforma esse resultado em SVG, e a animação fica no CSS (`frontend/src/styles/neuronio.css`). Cada parte muda sem afetar as outras: a #22 pode trocar as formas dos tipos sem tocar no componente, e o `prefers-reduced-motion` desliga as transições sem mexer em código.
- **Rede neural em três partes** (issue #26): as contas ficam em funções puras em `frontend/src/utils/redeNeural.ts` (posições por simulação de forças com `d3-force`, quem acende quando um neurônio é tocado, a forma dos dendritos e o início do período), testadas sem navegador; o componente `frontend/src/components/GrafoRede.tsx` só desenha e trata toque e zoom; e a página `frontend/src/pages/Rede.tsx` cuida dos filtros, da busca na API e dos estados (carregando, erro, vazio).
- **Filtro de período reaproveitado** (`backend/app/api/periodo.py`, issue #29): o campo que aceita data ou data e hora com fuso, criado na #25 para `GET /rede`, saiu de `rede.py` para um módulo próprio. `GET /rede` e `GET /sessoes` herdam o mesmo `FiltroPeriodoSerializer` e só acrescentam os filtros que são deles (matéria; resultado e página), então as duas rotas tratam o período do mesmo jeito e com as mesmas mensagens de erro.
- **Conquistas a partir da rede** (`backend/app/domain/conquistas.py`, issue #32): as regras olham um `ResumoFoco` montado da rede neural do estudante, e não das sessões: cada neurônio vivo é uma sessão concluída, com a duração dela e criado no instante da conclusão. Assim a avaliação carrega só a rede (duas consultas: neurônios e sinapses), as regras são funções puras do resumo (testadas sem banco), e o `ConquistaService` não depende do `RepositorioSessao`. No banco fica só o código de cada conquista desbloqueada e a data; nome, dica e meta ficam no domínio.

## Desempenho

- **Rede fluida com centenas de neurônios** (`frontend/src/components/GrafoRede.tsx` e `frontend/src/styles/rede.css`, issue #26), com decisões medidas no navegador:
  - o zoom e o arrasto (`d3-zoom`) mudam só o `transform` de um grupo, direto no DOM, e o React não redesenha os neurônios a cada quadro;
  - a opacidade fica nas formas, e não no grupo de cada neurônio: opacidade num grupo SVG obriga o navegador a pintar cada um à parte, e o zoom caía para uns 45 quadros por segundo com 300 neurônios (depois da mudança, passou de 60);
  - neurônios e sinapses são componentes memorizados (`memo`), então um realce só redesenha o que mudou de estado: no build de produção, cerca de 3 ms com 300 neurônios e 4 ms com 500;
  - a simulação de forças roda de uma vez, partindo de posições sorteadas com semente fixa (o desenho é sempre o mesmo) e assentando em 135 passos em vez de 300, o que corta o cálculo pela metade (cerca de 0,2 s com 300 neurônios e 0,35 s com 500).
- **Histórico sem consultas por sessão** (`backend/app/infra/repositorios/sessao_foco.py`, método `listar_historico`, issue #29): a página é cortada no banco (`LIMIT` e `OFFSET`), e as interrupções de todas as sessões da página vêm numa consulta só (`prefetch_related`). Sem isso, cada sessão faria uma consulta a mais para calcular o tempo fora (o problema N+1): 21 consultas com 15 sessões, contra 6 com o `prefetch_related`, número que não cresce com o tamanho do histórico.

## Nomenclatura

## Tratamento de erros nas bordas

- **Tela da rede que não quebra por partes** (`frontend/src/pages/Rede.tsx`, issue #26): se as matérias não carregarem, a rede aparece com as cores dos tipos e sem o filtro de matéria; se a rede não carregar, a tela avisa e oferece tentar de novo. Uma resposta que chega depois de o estudante trocar de filtro é descartada, para não mostrar a rede do filtro anterior.
- **Filtros validados pelo tratamento central de erros** (`backend/app/api/rede.py`, issue #25): os filtros de `GET /rede` passam por um serializer com `raise_exception=True`, e o erro sai no formato padrão da #12 (`{"erro": "validacao", "mensagem", "detalhes"}`), com o campo inválido em `detalhes`. O campo de período aceita data ou data e hora com fuso; uma data no `ate` vale até o fim do dia, para não deixar o próprio dia de fora.
- **Erros de domínio traduzidos num único ponto** (`backend/app/api/sessoes.py`, função `_responder`, issue #16): os casos de uso lançam exceções de domínio (`SessaoNaoEncontrada`, `SessaoAtivaExistente`, `TransicaoInvalida`...), e uma tabela no módulo da API as converte para HTTP (404, 409 ou 400) no formato `{"erro", "mensagem"}`. Sessão de outro estudante responde 404, igual a inexistente, para não revelar que ela existe. É provisório até o tratamento central de erros da issue #12.
- **Envio em segundo plano que nunca lança erro** (`frontend/src/services/api.ts`, função `postEmSegundoPlano`, issue #18): avisa o servidor de uma saída da tela com `fetch(..., { keepalive: true })`, que continua mesmo se a aba fechar. Como a página pode estar sumindo, falhas de rede ou recusas do servidor viram `false` em vez de exceção.
- **Eventos do navegador que chegam fora de hora** (`frontend/src/hooks/useSessaoFoco.ts`, issue #18): o fim da sessão sai da tela cheia, e o `fullscreenchange` resultante pode chegar antes do próximo render. Um `ref` atualizado na hora (`emAndamentoRef`) faz a sessão ignorar saídas depois que ela terminou.
- **Avisos ao servidor que sobrevivem a falhas** (`frontend/src/services/sessoes.ts`, issue #20): saídas da tela e desistências entram numa fila guardada no `localStorage` e são enviadas uma de cada vez, na ordem em que aconteceram. Falha de rede (ou erro 5xx) deixa o aviso na fila para a próxima tentativa; uma recusa definitiva do servidor (ex.: 409, a sessão já terminou) tira o aviso da fila e é tratada como resposta. A conclusão só aparece na tela depois que o servidor confirma, com novas tentativas enquanto não há conexão. Do lado do servidor, registrar a mesma interrupção de novo não muda nada (`SessaoFoco._aplicar_politica`), para que o reenvio seja seguro.
- **Relógio do servidor como referência** (`frontend/src/hooks/useSessaoFoco.ts`, issue #20): o tempo restante vem do servidor (`restante_segundos`), e os horários de saída e volta são convertidos para o relógio dele antes do envio. Sem isso, um computador com o relógio adiantado ou atrasado teria as saídas recusadas ("no futuro" ou "antes do início").
