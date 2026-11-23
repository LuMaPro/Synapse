# Conceitos de POO Aplicados

> Enunciado, seção 2.5.4: explicar, com exemplos retirados do próprio código, onde e por que os conceitos de encapsulamento, herança, polimorfismo e abstração foram utilizados e, quando for o caso, onde deliberadamente não foram aplicados.

Cada conceito tem uma seção com onde ele aparece, por que foi usado ali, um trecho do código e os testes que o garantem. A maior parte está no domínio do backend (`backend/app/domain/`), que é Python puro; o frontend aparece onde o conceito também foi aplicado lá. A última seção reúne os lugares onde cada conceito foi deixado de fora de propósito.

Os padrões de projeto que se apoiam nesses conceitos (State, Strategy, Factory Method e outros) estão em [padroes-de-projeto.md](padroes-de-projeto.md), e as classes, no diagrama em [uml/](../uml).

## Encapsulamento

**Onde:** as entidades em `backend/app/domain/entidades/` (`Usuario`, `Materia`, `SessaoFoco`, `Neuronio`, `Sinapse` e `ConquistaDesbloqueada`), o objeto de valor `Duracao` (`backend/app/domain/duracao.py`) e os agregados `RedeNeural` e `Carteira` (issues #9, #23 e #34).

**Por quê:** as regras de negócio do Synapse (duração de 10 a 120 minutos, e-mail único e válido, sessão que não termina antes de começar, saldo que nunca fica negativo) só valem se ninguém conseguir montar ou mudar um objeto sem passar por elas. Cada classe guarda o estado em atributos com prefixo `_`, expõe o que pode ser lido por propriedades e valida tudo no construtor. Um objeto inválido nunca chega a existir, então quem usa a classe não precisa lembrar de validar nada.

```python
class Usuario(Entidade):
    def __init__(
        self,
        nome: str,
        email: str,
        *,
        ...
    ):
        super().__init__(id)
        self._nome = self._validar_nome(nome)
        self._email = self._normalizar_email(email)
        ...

    @property
    def nome(self) -> str:
        return self._nome

    @nome.setter
    def nome(self, valor: str) -> None:
        self._nome = self._validar_nome(valor)

    @property
    def email(self) -> str:
        return self._email
```

- **Somente leitura quando faz sentido:** `id`, `email`, `criado_em`, `inicio`, `duracao` e os ids de relacionamento não têm setter. O `nome` do usuário e o `nome` e a `cor` da matéria têm, porque mudá-los é uma operação legítima, mas o setter passa pela mesma validação do construtor (`Materia.atualizar` usa os setters).
- **Regra num lugar só:** a duração de uma sessão fica em `Duracao`, um `@dataclass(frozen=True)` que valida em `__post_init__`. `SessaoFoco` e `Neuronio` recebem os minutos e guardam uma `Duracao`, sem repetir a regra.
- **Estado derivado em vez de guardado:** `SessaoFoco.fim_previsto` é calculado a partir de `inicio` e `duracao`, e `tempo_fora` soma o histórico de saídas. Não existe como esses valores ficarem inconsistentes com os dados de que dependem.
- **Coleções devolvidas como cópia:** `SessaoFoco.historico_interrupcoes`, `RedeNeural.neuronios` e `sinapses` e `Carteira.desbloqueadas` devolvem uma lista ou um dicionário novo. Quem lê não consegue mudar o objeto por fora.

  ```python
  @property
  def historico_interrupcoes(self) -> list[Interrupcao]:
      return list(self._historico_interrupcoes)
  ```

- **Agregados que protegem as próprias regras:** a única forma de mudar a rede é `RedeNeural.adicionar`, que valida tudo antes de alterar qualquer coisa; se a regra propuser uma ligação inválida, a rede fica como estava. O saldo da `Carteira` só muda por `creditar` e `comprar`, que garantem crédito de 1 em diante, saldo suficiente e cada cor comprada uma vez só. Até os dados que vêm do banco passam pelas mesmas validações ao montar os objetos.
- **No frontend, encapsulamento por módulo:** sem classes, o que fica escondido são as variáveis que o módulo não exporta. Em `frontend/src/services/api.ts`, o estado da renovação do token (`sessao` e `renovacaoEmAndamento`) só muda por `configurarSessao`. Em `frontend/src/services/sessoes.ts`, a fila de avisos só é lida e gravada por funções internas (`lerAvisos` e `salvarAvisos`), e o resto do app só usa `avisar` e `enviarAvisosPendentes`.
- **Limite do Python:** não há atributo privado de verdade; o `_` é uma convenção. O que garante o encapsulamento são as propriedades sem setter, que lançam `AttributeError` se alguém tentar atribuir. Um método protegido é usado fora da própria classe num caso só: os estados da sessão chamam `sessao._mudar_estado`, que fica no mesmo módulo e que só eles devem chamar.

**Testes:** `test_atributos_sao_somente_leitura` em `backend/tests/unit/domain/test_usuario.py`, `test_sessao_foco.py`, `test_neuronio.py` e `test_sinapse.py`; `test_recusa_atualizacao_invalida` em `backend/tests/unit/domain/test_materia.py`; `test_listas_devolvidas_sao_copias` em `backend/tests/unit/domain/test_rede_neural.py` e `test_a_lista_devolvida_e_uma_copia` em `backend/tests/unit/domain/test_carteira.py`.

## Herança

**Onde:** a base `Entidade` (`backend/app/domain/entidades/base.py`), os estados da sessão, as políticas de interrupção, os tipos de neurônio, as exceções de domínio, as regras de conquista e as interfaces (issues #9, #10, #11, #22 e #32).

**Por quê:** a herança foi usada quando as subclasses são de fato um caso da classe base e compartilham comportamento, não só para reaproveitar código. Em todas as hierarquias do projeto a classe base define o comportamento comum, e as subclasses só mudam o que é próprio delas. As hierarquias têm um nível só: nenhuma classe do projeto herda de uma subclasse de outra classe do projeto.

- **`Entidade`:** base de `Usuario`, `Materia`, `SessaoFoco`, `Neuronio`, `Sinapse` e `ConquistaDesbloqueada`. Concentra o que toda entidade tem: o `id` (UUID gerado no próprio domínio, sem depender do banco) e a igualdade por identidade. Duas entidades são iguais quando são do mesmo tipo e têm o mesmo `id`, mesmo que o resto seja diferente.

  ```python
  def __eq__(self, outro: object) -> bool:
      return type(self) is type(outro) and self._id == outro._id
  ```

- **Estados da sessão:** `EstadoSessao` implementa todas as operações (`concluir`, `podar`, `desistir`, `registrar_interrupcao`) lançando `TransicaoInvalida`, e `expirar` devolvendo `False`. `EmAndamento` sobrescreve todas, porque é o único estado em que a sessão ainda muda. `Concluida` e `Podada` não sobrescrevem nenhuma: herdam a recusa e só definem `nome` e `codigo`.
- **Políticas de interrupção:** `PoliticaInterrupcao` implementa `instante_da_poda` com o caso mais comum (a sessão morre no momento da saída). `ModoEstrito` herda esse comportamento; `ModoTolerante` sobrescreve, porque no tolerante a sessão morre quando o saldo de 10% acaba.
- **Tipos de neurônio:** `TipoNeuronio` define os atributos visuais como propriedades abstratas (`nome`, `cor`, `numero_dendritos`, `raio`) e implementa o que é comum: o `codigo` para a API, a verificação da faixa de duração (`aceita`) e a igualdade por tipo. `Granular`, `Piramidal` e `Purkinje` só declaram a faixa e os valores:

  ```python
  class Granular(TipoNeuronio):
      """Neurônio de sessões curtas (10 a 24 min): corpo pequeno e dendritos curtos."""

      duracao_minima = 10
      duracao_maxima = 24
  ```

- **Exceções de domínio:** `ErroDominio` (`backend/app/domain/excecoes.py`) é a base das 21 exceções de regra de negócio, como `DuracaoInvalida`, `TransicaoInvalida`, `SessaoNaoEncontrada`, `SaldoInsuficiente` e `CorBloqueada`. Os casos de uso lançam a exceção específica, e a API trata qualquer uma com um único `except ErroDominio` (issue #12), sem precisar conhecer cada exceção.
- **Regras de conquista:** `RegraConquista` (`backend/app/domain/conquistas.py`) guarda código, nome, dica, meta e unidade e implementa `cumprida` e `progresso`. As seis subclasses (`PrimeiroNeuronio`, `NeuroniosFormados`, `HorasFocadas`, `DiasSeguidos`, `SinapsesFormadas` e `SessaoLongaSemPoda`) só implementam `medir`.
- **Herança de interface:** as implementações herdam de uma classe abstrata sem herdar comportamento, só o contrato: os repositórios Django e em memória (`RepositorioSessaoDjango(RepositorioSessao)` e `RepositorioSessaoMemoria(RepositorioSessao)`), os três observadores (`ObservadorSessao`), o `ServicoSenhasDjango` (`ServicoSenhas`) e a regra das sinapses (`RegraFormacaoSinapses`).
- **No frontend:** as duas únicas classes, `ApiError` (`frontend/src/services/api.ts`) e `AuthError` (`frontend/src/services/auth.ts`), herdam de `Error`. Assim elas têm a mensagem e a pilha de um erro comum, e as telas as reconhecem com `instanceof` (ex.: `frontend/src/pages/Cadastro.tsx`).

**Testes:** `test_excecoes_herdam_de_erro_dominio` em `backend/tests/unit/domain/test_excecoes.py`, `test_transicoes_invalidas_sessao_concluida` e `test_transicoes_invalidas_sessao_podada` em `backend/tests/unit/domain/test_sessao_foco.py`, `test_modo_estrito_poda_no_instante_da_saida` e `test_modo_tolerante_poda_quando_o_saldo_acaba` em `backend/tests/unit/domain/test_politica_interrupcao.py`.

## Polimorfismo

**Onde:** `SessaoFoco` com as políticas e os estados (`backend/app/domain/entidades/sessao_foco.py`), a fábrica de neurônios, as regras de conquista, os observadores, os repositórios e o tratamento de erros da API (issues #10, #11, #22, #24 e #32).

**Por quê:** é o que permite acrescentar um modo, um estado, um tipo de neurônio ou uma conquista sem mexer em quem os usa. Quem chama trabalha com a classe base e não tem `if` perguntando qual é a classe concreta: a mesma chamada faz coisas diferentes conforme o objeto recebido.

`SessaoFoco` usa qualquer política e qualquer estado sem saber qual é:

```python
def concluir(self, relogio: Callable[[], datetime] = agora) -> None:
    self._estado.concluir(self, self._relogio_validado(relogio))

def _aplicar_politica(self, interrupcao: Interrupcao) -> None:
    ...
    historico = list(self._historico_interrupcoes)
    if self._politica.deve_podar(self, interrupcao, historico):
        instante = self._politica.instante_da_poda(self, interrupcao, historico)
        self.podar(relogio=lambda: instante)
    else:
        self._historico_interrupcoes.append(interrupcao)
```

- **Políticas:** `ModoEstrito.deve_podar` sempre responde que sim; `ModoTolerante.deve_podar` soma o tempo fora e compara com 10% da sessão. `instante_da_poda` também varia, como descrito na herança.
- **Estados:** `concluir`, `podar`, `desistir`, `registrar_interrupcao` e `expirar_se_abandonada` são repassados ao estado atual. A mesma chamada conclui a sessão em andamento e lança `TransicaoInvalida` na concluída ou na podada.
- **Tipos de neurônio:** `FabricaNeuronio.tipo_para` pergunta a cada tipo se ele aceita a duração, sem `if/elif` por classe concreta, e `Neuronio` repassa `cor`, `numero_dendritos` e `raio` ao seu `TipoNeuronio`. O `SessaoService` só chama `self._fabrica.criar(sessao)`, e o endpoint `GET /rede` lê `neuronio.tipo.codigo` sem saber se o neurônio é `Granular`, `Piramidal`, `Purkinje` ou um tipo novo.

  ```python
  for tipo in self._tipos:
      if tipo.aceita(duracao_minutos):
          return tipo
  ```

- **Conquistas e observadores:** o `ConquistaService` chama `regra.cumprida(resumo)` e `regra.progresso(resumo)` para cada regra do catálogo, e cada subclasse mede uma coisa diferente. O `PublicadorEventos` chama `observador.processar(evento)` sem saber se é o `AtualizadorRede`, o `AvaliadorConquistas` ou o `CreditadorATP`.
- **Repositórios:** o `SessaoService` roda igual com o `RepositorioSessaoDjango`, na API, e com o `RepositorioSessaoMemoria`, nos testes de unidade.
- **Exceções:** `resposta_erro_dominio` (`backend/app/api/erros.py`) responde qualquer `ErroDominio` com uma função só: o status vem de uma tabela pelo tipo da exceção, e o código do erro, do nome da classe (`SessaoNaoEncontrada` vira `sessao_nao_encontrada`).
- **Polimorfismo sem herança (duck typing):** o relógio que os serviços recebem é qualquer coisa que, chamada, devolve um `datetime` (`relogio: Callable[[], datetime]`). Na API é `lambda: agora()`; nos testes, um objeto `Relogio` com `__call__`, que o teste avança quando quer (`backend/tests/unit/application/test_sessoes.py`). Os dois não têm uma classe base em comum.

**Testes:** `test_criterio_adicionar_tipo_novo_nao_altera_quem_chama_a_fabrica` em `backend/tests/unit/domain/test_neuronio.py`, `test_criterio_regra_trocada_sem_mexer_no_servico_de_sessao` em `backend/tests/unit/application/test_sessoes.py` e `test_publicar_evento_notifica_observadores_inscritos` em `backend/tests/unit/domain/test_eventos.py`.

## Abstração

**Onde:** as interfaces de repositório (`backend/app/domain/repositorios.py`), `PoliticaInterrupcao`, `EstadoSessao`, `TipoNeuronio`, `RegraConquista`, `ObservadorSessao`, `RegraFormacaoSinapses` e `ServicoSenhas` (issues #10, #11, #13, #14, #22, #23, #24 e #32).

**Por quê:** cada abstração diz o que uma parte do sistema faz e esconde como. O domínio precisa gravar uma sessão, mas não deve saber que existe PostgreSQL; a sessão precisa saber se uma saída da tela a poda, mas não qual modo está valendo. Todas são classes abstratas (`ABC`) com métodos marcados com `@abstractmethod`, então o Python recusa criar uma subclasse que esqueceu de implementar parte do contrato.

- **Interfaces de repositório:** são sete (`RepositorioUsuario`, `RepositorioSessao`, `RepositorioNeuronio`, `RepositorioRedeNeural`, `RepositorioMateria`, `RepositorioConquista` e `RepositorioCarteira`). Cada uma tem só as operações de que os casos de uso precisam, com nomes do negócio (`buscar_ativa_por_usuario`, `listar_historico`, `carregar(usuario_id, para_alterar=True)`), e nenhuma menciona o ORM:

  ```python
  class RepositorioSessao(ABC):
      @abstractmethod
      def buscar_ativa_por_usuario(self, usuario_id: UUID) -> SessaoFoco | None:
          """
          Retorna a sessão de foco atualmente em andamento para o usuário, se houver.
          Garante a regra de que um usuário não pode ter mais de uma sessão ativa por vez.
          """
          ...
  ```

- **`PoliticaInterrupcao`:** o contrato de um modo é um código estável (`codigo`, gravado no banco e trocado com a API) e a decisão de podar (`deve_podar`). A sessão só conhece esse contrato.

  ```python
  class PoliticaInterrupcao(ABC):
      @property
      @abstractmethod
      def codigo(self) -> str:
          """Identificador estável do modo, para gravar no banco e trocar com a API."""

      @abstractmethod
      def deve_podar(
          self,
          sessao: "SessaoFoco",
          nova_interrupcao: Interrupcao,
          historico: list[Interrupcao],
      ) -> bool: ...
  ```

- **`EstadoSessao`:** cada estado precisa dizer o próprio `nome` (para as mensagens) e `codigo` (para o banco e a API). As transições têm uma implementação padrão, e por isso não são abstratas.
- **As outras:** `TipoNeuronio` abstrai a aparência de uma espécie de neurônio; `RegraConquista`, o que uma conquista mede (`medir`); `ObservadorSessao`, quem reage ao fim de uma sessão (`processar`); `RegraFormacaoSinapses`, a quem um neurônio novo se liga (`conexoes`); e `ServicoSenhas`, como uma senha é validada e guardada, para o cadastro não depender do Django.
- **Serviços como abstração dos casos de uso:** as views não conhecem as regras. `POST /sessoes/{id}/concluir` só chama `_servico().concluir(...)`, e tudo o que acontece depois (estado, neurônio, rede, conquistas, ATP) fica escondido atrás do `SessaoService`.
- **No frontend:** `frontend/src/services/api.ts` abstrai o `fetch`, o token e a renovação atrás de `api.get` e `api.post`, e as interfaces do TypeScript (ex.: `SessaoApi`, em `frontend/src/services/sessoes.ts`) descrevem o formato que a API devolve, sem dizer como ele é obtido.

**Testes:** `test_tipo_neuronio_e_abstrato` em `backend/tests/unit/domain/test_neuronio.py` e `test_regra_sem_medir_nao_pode_ser_criada` em `backend/tests/unit/domain/test_conquistas.py` (as classes incompletas lançam `TypeError` ao ser criadas), e os repositórios em memória de `backend/tests/repositorios.py`, que implementam as mesmas interfaces dos repositórios Django.

## Onde deliberadamente não aplicamos

- **Composição em vez de herança na sessão e no neurônio.** A sessão *tem* um estado e uma política, em vez de existirem subclasses como `SessaoEstrita` e `SessaoTolerante`. Com herança, cada combinação de modo e estado viraria uma classe, e mudar de estado exigiria trocar o objeto inteiro; com composição, concluir é só trocar o objeto `_estado`. Do mesmo jeito, o `Neuronio` *tem* um `TipoNeuronio`, em vez de existirem `NeuronioGranular` e `NeuronioPurkinje`: o neurônio é uma entidade só, gravado numa tabela só, e o tipo é decidido pela duração quando ele é criado.
- **`Duracao` não herda de `int`** (issue #9): usa composição (o atributo `minutos`). Herdar de `int` traria aritmética sem validação: `Duracao(25) + 3` resultaria no inteiro 28, que não é uma duração válida e escapa da regra.
- **Entidades não herdam dos models do Django** (issue #9): `Usuario` (domínio) e `UsuarioModel` (`backend/app/infra/modelos/usuario.py`) são classes separadas, e os repositórios convertem um no outro (`para_entidade` e `de_entidade`, issue #13). Assim as regras de negócio são testadas sem banco. O teste `test_dominio_nao_importa_django_nem_drf` (`backend/tests/unit/domain/test_dominio_puro.py`) falha se algum arquivo de `backend/app/domain/` importar `django` ou `rest_framework`. A única herança do framework fica na infraestrutura: `UsuarioModel` herda de `AbstractBaseUser` e `PermissionsMixin`, porque é isso que o login do Django exige.
- **Models e serializers sem regra de negócio:** os models de `backend/app/infra/modelos/` têm campos, restrições do banco (como última barreira, ex.: `UniqueConstraint` em `SinapseModel`) e os conversores para a entidade, e nenhuma regra do Synapse. Os serializers da API só conferem o formato: `IniciarSessaoSerializer` (`backend/app/api/sessoes.py`) aceita qualquer inteiro em `duracao_minutos`, e a regra de 10 a 120 minutos, de 5 em 5, continua só em `Duracao`. Se a regra estivesse nos dois lugares, uma mudança poderia esquecer um deles.
- **Funções puras nas estatísticas** (issue #30): o cálculo do painel é uma função, e não um objeto com estado. `calcular_estatisticas` (`backend/app/domain/estatisticas.py`) recebe as sessões, as matérias, o período e o instante e devolve um `EstatisticasFoco` imutável; o `EstatisticasService` só busca os dados e chama a função. Não há nada a encapsular: o resultado depende só da entrada, e os testes passam listas de sessões montadas na hora, sem repositório nem relógio. A sequência de dias das conquistas segue a mesma ideia (`calcular_sequencia`, em `backend/app/domain/conquistas.py`).
- **`RedeNeural` e `Carteira` não herdam de `Entidade`:** elas não têm um `id` próprio. Cada estudante tem uma rede e uma carteira, identificadas pelo `usuario_id`, então a igualdade por `id` da `Entidade` não faria sentido nelas.
- **Sem interface para o que só tem uma implementação:** `SessaoService`, `LojaService`, `PublicadorEventos` e `FabricaNeuronio` são classes concretas, e o `MateriaService` recebe o `LojaService` direto. As abstrações ficaram onde há mais de uma implementação (Django e memória; estrito e tolerante; as várias conquistas), onde trocar a implementação é o objetivo (a regra das sinapses) ou onde o domínio não pode conhecer a infraestrutura (`ServicoSenhas`). Uma interface com uma implementação só seria mais um arquivo para ler, sem nada para trocar.
- **Cores da loja como dados, e não como classes** (issue #34): as cores diferem só em nome, hexadecimal, preço e efeito, então cada uma é uma instância de `CorLoja` (um `@dataclass(frozen=True)`), e o efeito é um `Enum` (`Efeito`), em `backend/app/domain/loja.py`. Uma cor nova é uma linha no catálogo.
- **Frontend sem classes:** os componentes do React são funções, e o estado e o ciclo de vida ficam em hooks (`useSessaoFoco`, `useMaterias`, `useAuth` etc.). As contas da tela (geometria do neurônio, formatação de tempo, agrupamento do histórico) são funções puras em `frontend/src/utils/`, testadas sem montar componente. As únicas classes do frontend são os dois erros que herdam de `Error`.
