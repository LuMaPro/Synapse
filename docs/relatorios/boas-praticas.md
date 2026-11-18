# Boas Práticas de Programação e Orientação a Objetos

> Enunciado, seção 2.5.1: para cada prática citada, indicar a classe, o módulo ou o trecho de código em que foi aplicada.

Cada item cita o arquivo e a classe ou função onde a prática foi aplicada, com um trecho curto do código atual. `...` marca linhas omitidas do trecho. As notas foram registradas nos PRs de cada issue, indicada entre parênteses, e consolidadas aqui na issue #44.

## SOLID

### S: Responsabilidade única

- **Cada efeito do fim da sessão numa classe** (`backend/app/domain/observadores.py`, issues #24, #32 e #34): quando uma sessão termina, três coisas acontecem: o neurônio entra na rede, as conquistas são avaliadas e o ATP é creditado. Cada uma é um observador com um só motivo para mudar. O `SessaoFoco` cuida do ciclo de vida da sessão, o `SessaoService` orquestra e publica o evento, e nenhum dos dois sabe que a rede, as conquistas e a loja existem.

  ```python
  class CreditadorATP(ObservadorSessao):
      def __init__(self, loja):
          self.loja = loja

      def processar(self, evento):
          if isinstance(evento, SessaoConcluida):
              self.loja.creditar_sessao(evento.usuario_id, evento.duracao_minutos)
  ```

- **Um hook por tarefa na tela de foco** (`frontend/src/hooks/`, issues #17, #18 e #35): `useDeteccaoSaida` só percebe que o estudante saiu da tela, `useTelaLigada` só mantém a tela acesa e `useSessaoFoco` cuida do timer e da conversa com a API, usando os outros dois. Cada um é testado sozinho (`useDeteccaoSaida.test.ts`, `useTelaLigada.test.ts`, `useSessaoFoco.test.ts`).

  ```ts
  export function useDeteccaoSaida(ativo: boolean, { onSaida, onRetorno }: CallbacksSaida) {
  export function useTelaLigada(ativo: boolean): void {
  ```

### O: Aberto/fechado

- **Tipo de neurônio novo sem mudar quem chama a fábrica** (`backend/app/domain/entidades/neuronio.py`, classe `FabricaNeuronio`, issue #22): a fábrica percorre os tipos que recebeu e pergunta a cada um se aceita a duração. Um tipo novo é uma subclasse de `TipoNeuronio` passada para a fábrica; nem a fábrica nem o `SessaoService` mudam. O critério de aceite da issue é um teste que faz exatamente isso (`test_criterio_adicionar_tipo_novo_nao_altera_quem_chama_a_fabrica`, em `backend/tests/unit/domain/test_neuronio.py`, com um tipo `Estrelado` de 90 minutos ou mais).

  ```python
  @_MetodoFabrica
  def tipo_para(self, duracao_minutos: int) -> TipoNeuronio:
      ...
      for tipo in self._tipos:
          if tipo.aceita(duracao_minutos):
              return tipo
  ```

- **Conquista nova é uma classe e uma linha no catálogo** (`backend/app/domain/conquistas.py`, issue #32): o `ConquistaService` trata todas as regras do mesmo jeito. Uma conquista nova é uma subclasse de `RegraConquista`, que só implementa `medir`, mais uma entrada em `CATALOGO_CONQUISTAS`.

  ```python
  class PrimeiroNeuronio(RegraConquista):
      ...
      def medir(self, resumo: ResumoFoco) -> int:
          return resumo.neuronios_vivos
  ```

### L: Substituição de Liskov

- **Qualquer política serve para a sessão** (`backend/app/domain/politica_interrupcao.py` e `backend/app/domain/entidades/sessao_foco.py`, issue #11): `SessaoFoco` usa a política só pelo contrato da base: `deve_podar` diz se a saída poda, e `instante_da_poda` diz quando a sessão morreu. `ModoTolerante` sobrescreve `instante_da_poda` sem mudar o contrato: o instante continua dentro da saída que estourou o saldo, nunca antes dela. A sessão funciona igual com as duas políticas, e os testes de integração rodam os mesmos cenários nos dois modos (`@pytest.mark.parametrize("modo", ["estrito", "tolerante"])`, em `backend/tests/integration/test_api_sessoes.py`).

  ```python
  # SessaoFoco._aplicar_politica
  if self._politica.deve_podar(self, interrupcao, historico):
      instante = self._politica.instante_da_poda(self, interrupcao, historico)
      self.podar(relogio=lambda: instante)

  # ModoTolerante
  def instante_da_poda(
      self,
      sessao: "SessaoFoco",
      nova_interrupcao: Interrupcao,
      historico: list[Interrupcao],
  ) -> datetime:
      """A sessão morre quando o saldo acaba, no meio da saída que o estourou."""
      saldo = self._saldo_restante(sessao, historico)
      return nova_interrupcao.saida + timedelta(seconds=saldo)
  ```

- **Repositório em memória no lugar do Django** (`backend/tests/repositorios.py`, issue #13): cada interface de repositório tem duas implementações, a do Django (`backend/app/infra/repositorios/`) e uma em memória. Os serviços são testados com a de memória e rodam em produção com a do Django sem nenhuma mudança, porque as duas cumprem o mesmo contrato.

  ```python
  class RepositorioSessaoMemoria(RepositorioSessao):
  ```

### I: Segregação de interfaces

- **Um repositório pequeno por agregado** (`backend/app/domain/repositorios.py`, issues #13, #23, #32 e #34): em vez de um repositório genérico com todas as operações, cada agregado tem uma interface só com o que os casos de uso usam. `RepositorioConquista` tem dois métodos e `RepositorioCarteira` também. O `ConquistaService` depende só de `RepositorioConquista` e `RepositorioRedeNeural`, e não enxerga sessões nem carteiras.

  ```python
  class RepositorioConquista(ABC):
      """Persistência das conquistas desbloqueadas (Padrão Repository, #32)."""

      @abstractmethod
      def listar_por_usuario(self, usuario_id: UUID) -> list[ConquistaDesbloqueada]:
          """Lista as conquistas que o estudante já desbloqueou."""
          ...

      @abstractmethod
      def salvar(self, conquista: ConquistaDesbloqueada) -> None:
          """Persiste uma conquista recém-desbloqueada."""
          ...
  ```

- **Observador com um método só** (`backend/app/domain/eventos.py`, issue #24): `ObservadorSessao` exige apenas `processar(evento)`. Quem implementa não precisa saber como o publicador guarda as inscrições.

  ```python
  class ObservadorSessao(ABC):
      """Interface que todo observador de sessão deve implementar"""

      @abstractmethod
      def processar(self, evento: Any) -> None:
          pass
  ```

### D: Inversão de dependência

- **Serviços dependem de interfaces; a API monta as implementações** (`backend/app/application/sessoes.py` e `backend/app/api/sessoes.py`, issues #13 e #24): o domínio define os contratos (`backend/app/domain/repositorios.py`) e a infraestrutura se adapta a eles (`backend/app/infra/repositorios/`), e não o contrário. Os serviços recebem os repositórios, o publicador e até o relógio pelo construtor, tipados pelas interfaces. Quem escolhe as implementações do Django e inscreve os observadores é a função `_servico()` da API, o único lugar que conhece as duas pontas. Nos testes unitários, as mesmas classes recebem repositórios em memória e um relógio controlado.

  ```python
  # backend/app/application/sessoes.py
  def __init__(
      self,
      sessoes: RepositorioSessao,
      publicador: PublicadorEventos,
      relogio: Callable[[], datetime] = agora,
      materias: RepositorioMateria | None = None,
      fabrica: FabricaNeuronio | type[FabricaNeuronio] = FabricaNeuronio,
  ):

  # backend/app/api/sessoes.py, _servico()
  return SessaoService(
      RepositorioSessaoDjango(),
      publicador,
      relogio=lambda: agora(),
      materias=RepositorioMateriaDjango(),
  )
  ```

## Separação em camadas

- **Domínio puro** (`backend/app/domain/`, issue #9): entidades, objetos de valor, regras e exceções não dependem do Django nem do DRF, então as regras de negócio são testadas sem banco e sem servidor. Um teste lê os imports de cada arquivo do domínio e falha se algum importar o framework (`backend/tests/unit/domain/test_dominio_puro.py`).

  ```python
  PROIBIDOS = {"django", "rest_framework"}
  ...
  def test_dominio_nao_importa_django_nem_drf(arquivo):
      raizes = {modulo.split(".")[0] for modulo in _modulos_importados(arquivo)}

      assert not raizes & PROIBIDOS
  ```

- **Cadastro como caso de uso** (`backend/app/application/cadastro.py`, issue #14): a view `cadastro` (`backend/app/api/auth.py`) só lê a requisição, abre a transação e devolve a resposta. A regra fica em `CadastroUsuario`, que usa a entidade `Usuario` (validação de nome e e-mail), o `RepositorioUsuario` (e-mail único) e a interface `ServicoSenhas`, implementada na infraestrutura com os validadores e o hash Argon2 do Django (`backend/app/infra/senhas.py`). É testado com repositório em memória (`backend/tests/unit/application/test_cadastro.py`).

  ```python
  def executar(self, nome: str, email: str, senha: str) -> Usuario:
      # A entidade valida e normaliza nome e e-mail (NomeInvalido, EmailInvalido).
      usuario = Usuario(nome, email)
      if self._repositorio.existe_com_email(usuario.email):
          raise EmailJaCadastrado(
              "E-mail já cadastrado. Tente fazer login ou use outro e-mail."
          )
      self._senhas.validar(senha, usuario)

      self._repositorio.salvar(usuario)
      self._senhas.definir(usuario, senha)
      return usuario
  ```

- **Endpoint da rede sem regra de negócio** (`backend/app/api/rede.py`, issues #22 e #25): a view só valida os filtros, chama `RedeNeuralService.consultar` e monta o JSON. O recorte (período, matéria e só as sinapses entre os neurônios escolhidos) é do agregado, em `RedeNeural.recortar`, e o tipo e a cor vêm do próprio `Neuronio`, criado pela `FabricaNeuronio` no domínio.

  ```python
  filtros.is_valid(raise_exception=True)
  dados = filtros.validated_data
  recorte = _servico().consultar(
      request.user.id,
      de=dados.get("de"),
      ate=dados.get("ate"),
      materia_id=dados.get("materia"),
  )
  ```

- **Sessões de foco como casos de uso** (`backend/app/application/sessoes.py`, issue #16): `SessaoService` orquestra a entidade `SessaoFoco` (estados e políticas) e os repositórios, com o relógio do servidor injetado. As views em `backend/app/api/sessoes.py` só validam o formato da requisição e montam a resposta; a regra de tempo (o servidor como fonte da verdade, a tolerância de 2 s, a expiração de sessões abandonadas) não aparece nelas.

  ```python
  def concluir(
      self, usuario_id: UUID, sessao_id: UUID, *, forcar_conclusao: bool = False
  ) -> tuple[SessaoFoco, Neuronio]:
      sessao = self._carregar(usuario_id, sessao_id)
      instante = self._relogio()
  ```

- **Banco sem começos desistidos** (`backend/app/domain/entidades/sessao_foco.py` e `backend/app/application/sessoes.py`): a sessão podada com menos de 5 min de foco (desistência ou saída da tela, até 4:59) não fica registrada. A regra é do domínio (`SessaoFoco.curta_demais`, calculada com o instante da poda, e não com a hora em que o aviso chegou). O serviço apaga a sessão em vez de gravá-la e não publica o evento, então não sobra neurônio morto, linha no histórico nem conta nas estatísticas. A tela de foco avisa o estudante no diálogo de desistir e na tela de poda.

  ```python
  def _registrar_poda(self, sessao: SessaoFoco) -> None:
      """Grava a poda e publica o neurônio morto, ou apaga a sessão curta demais."""
      if sessao.curta_demais:
          self._sessoes.remover(sessao.id)
          return
      self._sessoes.salvar(sessao)
      self._publicar_poda(sessao)
  ```

- **Lógica separada da tela no frontend** (`frontend/src/hooks/useSessaoFoco.ts` e `frontend/src/pages/Foco.tsx`, issues #17 e #20): o hook concentra o estado e as regras da sessão (limites da duração, timer, conclusão, desistência, tela cheia e a conversa com a API), e a página só desenha o que ele devolve. Assim o timer é testado sem renderizar a tela, e a integração com a API (issue #20) mudou o hook sem mexer nos componentes.

  ```tsx
  // Foco.tsx
  const sessao = useSessaoFoco()
  ...
  <button
    type="button"
    className="botao primario"
    onClick={sessao.iniciar}
    disabled={sessao.iniciando}
  >
  ```

- **Cálculo das estatísticas puro no domínio** (`backend/app/domain/estatisticas.py`, `backend/app/application/estatisticas.py` e `backend/app/api/estatisticas.py`, issue #30): toda a conta do painel (janelas de dia, semana e mês no fuso de Brasília, minutos por dia e por matéria, taxa de sucesso e horário de pico) fica numa função pura, que devolve objetos de valor imutáveis (`EstatisticasFoco`, `TempoDia`, `TempoMateria`). O `EstatisticasService` só expira uma eventual sessão abandonada e carrega do banco o recorte do período e as matérias; a view só valida `periodo` e serializa a resposta.

  ```python
  def calcular_estatisticas(
      sessoes: Iterable[SessaoFoco],
      *,
      periodo: PeriodoEstatisticas | str,
      instante: datetime,
      materias: Iterable[Materia] = (),
      fuso: tzinfo = FUSO_DOS_DIAS,
  ) -> EstatisticasFoco:
  ```

## Baixo acoplamento e alta coesão

- **Neurônio em três partes** (issue #19): a geometria é uma função pura em `frontend/src/utils/geometriaNeuronio.ts` (recebe tipo, progresso e se está podado e devolve o que desenhar), o componente `frontend/src/components/NeuronioAnimado.tsx` só transforma esse resultado em SVG, e a animação fica no CSS (`frontend/src/styles/neuronio.css`). Cada parte muda sem afetar as outras: a #22 trocou as formas dos tipos sem tocar no componente, e o `prefers-reduced-motion` desliga as transições sem mexer em código.

  ```ts
  export function desenharNeuronio(
    tipo: TipoNeuronio,
    progresso: number,
    podado = false,
  ): DesenhoNeuronio {
  ```

- **Rede neural em três partes** (issue #26): as contas ficam em funções puras em `frontend/src/utils/redeNeural.ts` (posições por simulação de forças com `d3-force`, quem acende quando um neurônio é tocado, a forma dos dendritos e o início do período), testadas sem navegador. O componente `frontend/src/components/GrafoRede.tsx` só desenha e trata toque e zoom, e a página `frontend/src/pages/Rede.tsx` cuida dos filtros, da busca na API e dos estados (carregando, erro, vazio).

  ```ts
  export function posicionarRede(
  export function vizinhanca(id: string, sinapses: SinapseRede[]): Vizinhanca {
  export function dendritos(tipo: TipoNeuronio, raio: number): string {
  export function inicioDoPeriodo(periodo: Periodo, agora: Date = new Date()): Date | undefined {
  ```

- **Filtro de período reaproveitado** (`backend/app/api/periodo.py`, issue #29): o campo que aceita data ou data e hora com fuso, criado na #25 para `GET /rede`, saiu de `rede.py` para um módulo próprio. `GET /rede` e `GET /sessoes` herdam o mesmo serializer e só acrescentam os filtros que são deles (matéria; resultado e página), então as duas rotas tratam o período do mesmo jeito e com as mesmas mensagens de erro.

  ```python
  class FiltrosRedeSerializer(FiltroPeriodoSerializer):        # api/rede.py
  class FiltrosHistoricoSerializer(FiltroPeriodoSerializer):   # api/sessoes.py
  ```

- **Conquistas a partir da rede** (`backend/app/domain/conquistas.py`, issue #32): as regras olham um `ResumoFoco` montado da rede neural do estudante, e não das sessões: cada neurônio vivo é uma sessão concluída, com a duração dela e criado no instante da conclusão. Assim, a avaliação carrega só a rede (duas consultas: neurônios e sinapses), as regras são funções puras do resumo (testadas sem banco) e o `ConquistaService` não depende do `RepositorioSessao`. No banco fica só o código de cada conquista desbloqueada e a data; nome, descrição e meta ficam no domínio.

  ```python
  @classmethod
  def da_rede(
      cls, rede: RedeNeural, instante: datetime, fuso: tzinfo = FUSO_DOS_DIAS
  ) -> "ResumoFoco":
  ```

- **Loja sem mexer na sessão** (`backend/app/application/loja.py` e `backend/app/domain/carteira.py`, issue #34): o ATP de cada sessão concluída chega pelo observador `CreditadorATP`, então o `SessaoService` continua sem saber que a loja existe. A cor do neurônio vem só da matéria (#28): a loja vende cores para as matérias, e o `MateriaService` confere com o `LojaService` se a cor escolhida é gratuita ou já comprada. O valor do ATP fica numa função só, usada pelo `LojaService`, pela resposta de `POST /sessoes/{id}/concluir` (o "+25 ATP" da tela) e pela migração que criou as carteiras.

  ```python
  ATP_POR_MINUTO = 1


  def atp_da_sessao(duracao_minutos: int) -> int:
      ...
      return duracao_minutos * ATP_POR_MINUTO
  ```

- **Efeitos das cores no CSS** (`frontend/src/styles/efeitos.css` e `frontend/src/utils/efeitos.ts`, issue #34): o backend só diz o nome do efeito (`pulsar`, `aurora`, `galaxia`, `tempestade` ou `arco_iris`), e o desenho fica numa folha de estilo, que vale para o neurônio animado, o neurônio da rede e as amostras de cor. A cor é a variável `--cor-neuronio`, registrada como `<color>`: assim dá para animar a cor de um tom para outro sem JavaScript e sem redesenhar o React. Com `prefers-reduced-motion`, as animações param e fica a cor fixa.

  ```css
  @property --cor-neuronio {
    syntax: '<color>';
    inherits: true;
    initial-value: #8b7bff;
  }
  ```

- **App instalável sem dependência nova** (`frontend/public/sw.js`, `frontend/public/manifest.webmanifest` e `frontend/src/registrarServiceWorker.ts`, issue #35): o service worker é um arquivo pequeno escrito à mão, em vez de um plugin que gera o código. Ele faz só o que a issue pede: deixa o app instalável e abre a casca sem rede. Dois problemas apareceram na validação manual e foram corrigidos, com testes que os reproduzem:
  - no primeiro acesso, a página baixa o JS e o CSS antes de o service worker começar a responder; por isso ele lê o `index.html` e guarda esses arquivos já na instalação;
  - o servidor pode responder com `Vary: Origin`, e a página pede o JS e o CSS com o cabeçalho Origin, que o service worker não manda; sem ignorar o `Vary`, o cache não acharia os arquivos e o app abriria em branco offline.

  A API nunca passa pelo cache, porque o servidor é a fonte da verdade das sessões. O service worker só é registrado no build de produção, para o cache não esconder mudanças durante o desenvolvimento.

  ```js
  const BUSCA = { ignoreVary: true }
  ```

- **Celular com a navegação do design** (`frontend/src/components/AbasCelular.tsx`, `frontend/src/components/Layout.tsx` e `frontend/src/hooks/useMidia.ts`, issue #35): abaixo de 640 px, a navegação vira a barra de abas embaixo, ao alcance do polegar. A escolha é feita por `matchMedia` num hook, e não só no CSS, para cada link existir uma vez só na página (leitores de tela e testes não veem a navegação repetida). O conteúdo, a tela da sessão e o diálogo de desistir respeitam o entalhe e a barra de gestos (`env(safe-area-inset-*)`).

  ```tsx
  const comAbas = useMidia(CONSULTA_CELULAR) && autenticado
  ...
  {comAbas && <AbasCelular onSair={handleLogout} />}
  ```

## Desempenho

- **Rede fluida com centenas de neurônios** (`frontend/src/components/GrafoRede.tsx` e `frontend/src/styles/rede.css`, issue #26), com decisões medidas no navegador:
  - o zoom e o arrasto (`d3-zoom`) mudam só o `transform` de um grupo, direto no DOM, e o React não redesenha os neurônios a cada quadro;
  - a opacidade fica nas formas, e não no grupo de cada neurônio: opacidade num grupo SVG obriga o navegador a pintar cada um à parte, e o zoom caía para uns 45 quadros por segundo com 300 neurônios (depois da mudança, passou de 60);
  - neurônios e sinapses são componentes memorizados (`memo`), então um realce só redesenha o que mudou de estado: no build de produção, cerca de 3 ms com 300 neurônios e 4 ms com 500;
  - a simulação de forças roda de uma vez, partindo de posições sorteadas com semente fixa (o desenho é sempre o mesmo) e assentando em 135 passos em vez de 300, o que corta o cálculo pela metade (cerca de 0,2 s com 300 neurônios e 0,35 s com 500).

  ```tsx
  const NeuronioGrafo = memo(function NeuronioGrafo({
  const SinapseGrafo = memo(function SinapseGrafo({
  ```

- **Histórico sem consultas por sessão** (`backend/app/infra/repositorios/sessao_foco.py`, método `listar_historico`, issue #29): a página é cortada no banco (`LIMIT` e `OFFSET`), e as interrupções de todas as sessões da página vêm numa consulta só (`prefetch_related`). Sem isso, cada sessão faria uma consulta a mais para calcular o tempo fora (o problema N+1): 21 consultas com 15 sessões, contra 6 com o `prefetch_related`, número que não cresce com o tamanho do histórico.

  ```python
  pagina = qs.order_by("-inicio").prefetch_related("interrupcoes")[
  ```

## Nomenclatura

- **A língua do problema no código** (`backend/app/domain/`, `frontend/src/`): classes, métodos e rotas usam os mesmos nomes da tela e do escopo do problema, em português: `SessaoFoco`, `Neuronio`, `Sinapse`, `RedeNeural`, `podar`, `Carteira`. A palavra que o estudante vê é a que o código usa, então uma regra descrita na issue ("a sessão é podada") é encontrada pelo nome. Termos de framework e de linguagem (`ABC`, `property`, `useEffect`, `Serializer`) ficam em inglês, como são.

  ```python
  class SessaoFoco(Entidade):
      ...
      def podar(self, relogio: Callable[[], datetime] = agora) -> None:
  ```

- **O sufixo diz a camada** (`backend/app/`, nas pastas `domain/`, `infra/`, `application/` e `api/`): `Repositorio*` é a interface no domínio, `*Django` é a implementação na infraestrutura, `*Model` é a tabela do ORM, `*Service` é o caso de uso na aplicação e `*Serializer` é o formato na API. Basta o nome para saber de que camada uma classe é e do que ela pode depender.

  ```python
  RepositorioSessao          # domain/repositorios.py: interface
  RepositorioSessaoDjango    # infra/repositorios/sessao_foco.py: implementação
  SessaoFocoModel            # infra/modelos/sessao_foco.py: tabela
  SessaoService              # application/sessoes.py: caso de uso
  IniciarSessaoSerializer    # api/sessoes.py: formato da requisição
  ```

- **Exceções nomeadas pelo que aconteceu** (`backend/app/domain/excecoes.py`, issue #12): todas herdam de `ErroDominio` e o nome descreve o problema (`SessaoNaoEncontrada`, `SaldoInsuficiente`, `CorBloqueada`). O tratamento central de erros (`backend/app/api/erros.py`) gera o código da resposta a partir do próprio nome da classe, então o nome no código e o código que o frontend recebe são o mesmo.

  ```python
  def _codigo(exc: Exception) -> str:
      """Transforma o nome da classe em texto legível.

      Exemplo: SessaoNaoEncontrada -> sessao_nao_encontrada.
      """
      return re.sub(r"(?<!^)(?=[A-Z])", "_", type(exc).__name__).lower()
  ```

- **Perguntas soam como perguntas** (`backend/app/domain/carteira.py`, `backend/app/domain/entidades/neuronio.py`, `backend/app/domain/conquistas.py` e `backend/app/domain/entidades/sessao_foco.py`): métodos e propriedades que devolvem `bool` se leem como uma pergunta de sim ou não: `TipoNeuronio.aceita(duracao)`, `Carteira.possui(cor)`, `RegraConquista.cumprida(resumo)`, `SessaoFoco.curta_demais`, `RepositorioUsuario.existe_com_email(email)`.

  ```python
  if self.possui(cor):
      raise CorJaDesbloqueada(f"A cor {cor.nome} já é sua.")
  ```

- **Privado começa com `_`** (`backend/app/domain/entidades/materia.py` e as outras entidades): atributos internos são `self._x`, lidos de fora por propriedades; quando um deles pode mudar, a propriedade tem um setter que valida de novo. Métodos internos também começam com `_` (`_validar_nome`, `_aplicar_politica`, `_registrar_poda`). Quem lê sabe o que é contrato e o que é detalhe.

  ```python
  self._nome = self._validar_nome(nome)
  ...
  @property
  def nome(self) -> str:
      return self._nome

  @nome.setter
  def nome(self, valor: str) -> None:
      self._nome = self._validar_nome(valor)
  ```

- **Convenções do React e do TypeScript** (`frontend/src/`): componentes e páginas em PascalCase (`GrafoRede`, `Foco`), hooks com o prefixo `use` (`useSessaoFoco`, `useMaterias`), um objeto de serviço por recurso da API com o sufixo `Api` (`materiasApi`, `sessoesApi`) e o teste ao lado do arquivo, com o mesmo nome e `.test.ts(x)` (`useMaterias.ts` e `useMaterias.test.ts`).

  ```ts
  export const materiasApi = {
  export function useMaterias() {
  ```

## Tratamento de erros nas bordas

- **Erros traduzidos para HTTP num lugar só** (`backend/app/api/erros.py`, issue #12): as regras de negócio lançam exceções do domínio, e nenhuma view escolhe código HTTP para elas. A tabela `STATUS_POR_ERRO_DOMINIO` e a função `resposta_erro_dominio` decidem o status (404 para o que não existe, 409 para conflito, 422 para regra violada) e o corpo (`{"erro", "mensagem"}`, com o código tirado do nome da exceção) para todas as rotas. O tratador configurado no DRF (`EXCEPTION_HANDLER`) usa essa função. Um erro inesperado vira um 500 genérico, com o detalhe só no log, sem expor nada ao cliente. Campos ausentes ou em formato errado são recusados antes, pelos serializers, com 400.

  ```python
  STATUS_POR_ERRO_DOMINIO = {
      dominio.SessaoNaoEncontrada: status.HTTP_404_NOT_FOUND,
      dominio.SaldoInsuficiente: status.HTTP_409_CONFLICT,
      dominio.DuracaoInvalida: status.HTTP_422_UNPROCESSABLE_ENTITY,
      ...
  }

  def resposta_erro_dominio(erro: dominio.ErroDominio) -> Response:
      status_http = STATUS_POR_ERRO_DOMINIO.get(type(erro), status.HTTP_400_BAD_REQUEST)
      mensagem = str(erro) or "Erro de regra de negócio."
      return _resposta(status_http, _codigo(erro), mensagem)

  def exception_handler(exc, context):
      # Parte 1: erros de domínio
      if isinstance(exc, dominio.ErroDominio):
          return resposta_erro_dominio(exc)
      ...
      # Parte 3: erro inesperado -> 500 genérico, detalhe só no log
      logger.exception("Erro inesperado na view %s", context.get("view"))
  ```

- **Erro da sessão tratado dentro da transação** (`backend/app/api/sessoes.py`, função `_responder`, issue #16): nas rotas de sessão, o erro de domínio é tratado antes de sair da transação. É de propósito: carregar uma sessão abandonada já a poda e grava a poda, e se a exceção saísse da transação essa gravação seria desfeita. A tradução continua sendo a do tratador central, porque `_responder` chama a mesma `resposta_erro_dominio`; assim a mesma exceção tem o mesmo status em qualquer rota. Sessão de outro estudante responde 404, igual a uma inexistente, para não revelar que ela existe.

  ```python
  with transaction.atomic():
      try:
          corpo = acao()
      except ErroDominio as erro:
          return resposta_erro_dominio(erro)
  ```

- **Compra que não gasta o mesmo ATP duas vezes** (`backend/app/infra/repositorios/carteira.py`, `backend/app/domain/carteira.py` e `backend/app/api/loja.py`, issue #34): a compra roda numa transação, com a carteira reservada (`SELECT ... FOR UPDATE`) do carregamento até a gravação, e o saldo é um `PositiveIntegerField` (o banco recusa saldo negativo, a última barreira). As regras ficam no agregado `Carteira`, e os erros (`SaldoInsuficiente`, `CorJaDesbloqueada`) saem com a mensagem que a tela mostra.

  ```python
  # infra/repositorios/carteira.py
  modelo = CarteiraModel.objects.select_for_update().get(
      usuario_id=usuario_id
  )

  # domain/carteira.py
  if self._saldo < cor.preco:
      falta = cor.preco - self._saldo
      raise SaldoInsuficiente(
          f"Faltam {falta} ATP para comprar a cor {cor.nome}."
      )
  ```

- **ATP de quem já focava e reembolso da loja anterior** (`backend/app/migrations/0007_loja_atp.py` e `0008_reembolsar_loja_anterior.py`, issue #34): a 0007 cria as carteiras com o ATP das sessões já concluídas (1 por minuto de cada neurônio vivo). A 0008 devolve o ATP de quem comprou uma variação por tipo na primeira versão da loja, antes de a 0009 apagar aquelas tabelas. O reembolso fica numa migração separada da mudança de esquema: no PostgreSQL, atualizar linhas e alterar a mesma tabela na mesma transação pode falhar ("pending trigger events").

  ```python
  migrations.RunPython(
      reembolsar_variacoes_compradas, migrations.RunPython.noop
  ```

- **Filtros validados pelo tratamento central** (`backend/app/api/rede.py`, issue #25): os filtros de `GET /rede` passam por um serializer com `raise_exception=True`, e o erro sai no formato padrão, com o campo inválido em `detalhes`. O campo de período aceita data ou data e hora com fuso; uma data no `ate` vale até o fim do dia, para não deixar o próprio dia de fora.

  ```python
  filtros.is_valid(raise_exception=True)
  ```

- **Tela ligada só quando dá** (`frontend/src/hooks/useTelaLigada.ts`, issue #35): no celular, a tela apagar sozinha esconderia a página e podaria a sessão sem o estudante ter feito nada. A sessão pede a Wake Lock API e a pede de novo quando a página volta a aparecer (o navegador a solta ao esconder). Onde não há suporte, ou se o navegador recusar, a sessão segue igual, e o aviso da sessão explica que a tela apagar conta como saída.

  ```ts
  try {
    const nova = await navigator.wakeLock.request('screen')
    ...
  } catch {
    // Recusado (bateria fraca, página sem foco...): a sessão segue sem a trava.
  }
  ```

- **Tela da rede que não quebra por partes** (`frontend/src/pages/Rede.tsx`, issue #26): se as matérias não carregarem, a rede aparece com as cores dos tipos e sem o filtro de matéria; se a rede não carregar, a tela avisa e oferece tentar de novo. Uma resposta que chega depois de o estudante trocar de filtro é descartada, para não mostrar a rede do filtro anterior.

  ```tsx
  useEffect(() => {
    let ativo = true
    buscarRede({ de: inicioDoPeriodo(periodo), materiaId: materiaId ?? undefined })
      .then((rede) => {
        if (ativo) setResultado({ chave, rede })
      })
      ...
    return () => {
      ativo = false
    }
  }, [chave, periodo, materiaId])
  ```

- **Envio em segundo plano que nunca lança erro** (`frontend/src/services/api.ts`, função `postEmSegundoPlano`, issue #18): avisa o servidor de uma saída da tela com `fetch(..., { keepalive: true })`, que continua mesmo se a aba fechar. Como a página pode estar sumindo, falhas de rede ou recusas do servidor viram `false` em vez de exceção.

  ```ts
  try {
    const resposta = await fetch(`${API_URL}${caminho}`, {
      method: 'POST',
      ...
      keepalive: true,
    })
    ...
    return resposta.ok
  } catch {
    return false
  }
  ```

- **Avisos ao servidor que sobrevivem a falhas** (`frontend/src/services/sessoes.ts`, issue #20): saídas da tela e desistências entram numa fila guardada no `localStorage` e são enviadas uma de cada vez, na ordem em que aconteceram. Falha de rede (ou erro 5xx) deixa o aviso na fila para a próxima tentativa; uma recusa definitiva do servidor (ex.: 409, a sessão já terminou) tira o aviso da fila e é tratada como resposta. Do lado do servidor, registrar a mesma interrupção de novo não muda nada (`SessaoFoco._aplicar_politica`), para que o reenvio seja seguro.

  ```ts
  export function avisar(
    aviso: Aviso,
    aoResponder?: (resposta: RespostaAviso) => void,
  ): Promise<boolean> {
    salvarAvisos([...lerAvisos(), aviso])
    return enviarAvisosPendentes(aoResponder)
  }
  ```

- **Eventos do navegador que chegam fora de hora** (`frontend/src/hooks/useSessaoFoco.ts`, issue #18): o fim da sessão sai da tela cheia, e o `fullscreenchange` resultante pode chegar antes do próximo render. Um `ref` atualizado na hora (`emAndamentoRef`) faz a sessão ignorar saídas depois que ela terminou.

  ```ts
  const sairDaTela = useCallback(
    (inicio: number) => {
      const sessaoId = sessaoIdRef.current
      if (!emAndamentoRef.current || fimEm === null || sessaoId === null) return
  ```

- **Relógio do servidor como referência** (`frontend/src/hooks/useSessaoFoco.ts`, issue #20): o tempo restante vem do servidor (`restante_segundos`), e os horários de saída e volta são convertidos para o relógio dele antes do envio. Sem isso, um computador com o relógio adiantado ou atrasado teria as saídas recusadas ("no futuro" ou "antes do início").

  ```ts
  const instante = Date.now()
  const fim = instante + sessao.restante_segundos * 1000
  sessaoIdRef.current = sessao.id
  deslocamentoRef.current = Date.parse(sessao.fim_previsto) - fim
  ```
