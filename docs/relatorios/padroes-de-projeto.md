# Padrões de Projeto e Trade-offs

> Enunciado, seção 2.5.2: para cada padrão efetivamente utilizado, explicar o problema que ele resolveu no projeto, as alternativas consideradas e descartadas, e o motivo da escolha.

A tabela resume cada padrão usado de fato no Synapse. Depois dela, cada padrão tem uma seção com o código, o custo da escolha e os testes que garantem que ele continua funcionando. No fim estão os padrões que foram considerados e descartados.

Os padrões de 1 a 11 estão no backend; os de 12 a 15, no frontend (o 12 também tem uma parte no backend). Onde ficam e como se relacionam com as camadas está em [arquitetura.md](../arquitetura.md), e o diagrama de classes está em [uml/](../uml).

| Padrão | Problema no projeto | Alternativa considerada | Trade-off da escolha |
| ------ | ------------------- | ----------------------- | -------------------- |
| [1. State](#1-state) | A sessão tem três estados (em andamento, concluída, podada) e cinco operações (concluir, podar, desistir, registrar saída e expirar), e cada operação só vale em um estado. | Um `Enum` de status e um `if` por operação dentro de `SessaoFoco`. | Quatro classes a mais no domínio, e o estado gravado no banco como texto precisa virar a classe certa ao carregar. Em troca, a regra de cada estado fica num lugar só e `SessaoFoco` não tem `if` de status. |
| [2. Strategy (política de interrupção)](#2-strategy-política-de-interrupção) | Sair da tela tem efeito diferente conforme o modo escolhido: no estrito, qualquer saída poda; no tolerante, as saídas somadas são perdoadas até 10% da duração. | `if modo == "estrito" ... elif modo == "tolerante"` dentro de `SessaoFoco`. | Uma classe por modo e um mapa de código para classe (`politica_por_codigo`). A sessão não muda quando surge um modo novo, e cada regra é testada sozinha. |
| [3. Strategy (formação das sinapses)](#3-strategy-formação-das-sinapses) | A regra que decide a quem um neurônio novo se liga é uma escolha de design que pode mudar, e a issue #23 pede trocá-la sem mexer no `SessaoService`. | Escrever a regra dentro de `RedeNeural.adicionar` ou do `SessaoService`. | Uma interface a mais (`RegraFormacaoSinapses`). A regra só propõe as ligações; quem garante as invariantes é a rede, valha a regra que valer. |
| [4. Factory Method](#4-factory-method) | Cada faixa de duração gera uma espécie de neurônio (Granular, Piramidal, Purkinje), e quem encerra a sessão não deve conhecer as faixas nem as classes concretas. | `if/elif` comparando `duracao_minutos` no `SessaoService` e no endpoint `GET /rede`. | A classe abstrata `TipoNeuronio`, um tipo concreto por espécie e a `FabricaNeuronio`. Um tipo novo é só uma classe nova, sem mudar quem chama a fábrica. |
| [5. Template Method](#5-template-method) | Cada conquista mede uma coisa diferente, mas todas comparam a medida com uma meta e mostram o progresso do mesmo jeito. | Um `if/elif` por conquista no serviço, ou uma tabela de funções soltas. | A classe abstrata `RegraConquista` faz a parte comum, e cada subclasse só implementa `medir`. Uma conquista nova é uma subclasse no catálogo. |
| [6. Observer](#6-observer) | O fim de uma sessão dispara várias reações (o neurônio entra na rede, as conquistas são avaliadas, o ATP é creditado), e o `SessaoService` mudaria a cada funcionalidade nova se chamasse cada uma. | Chamar os serviços direto do `SessaoService.concluir`, ou usar os Django Signals. | Um publicador e três observadores, montados fora do serviço. A ordem de inscrição passa a importar e precisa de teste; tudo roda na mesma transação. |
| [7. Repository](#7-repository) | O domínio precisa gravar e consultar entidades sem depender do Django ORM, para ser testado sem banco. | **Active Record**, o padrão do Django: o model concentra dados, consultas e regras. | Sete interfaces no domínio, implementações Django na infraestrutura e conversão entre model e entidade. Em troca, os testes de unidade rodam com repositórios em memória. |
| [8. Agregado (DDD)](#8-agregado-ddd) | A rede e a carteira têm regras que envolvem vários objetos ao mesmo tempo: sinapse só entre neurônios vivos e sem repetição; saldo nunca negativo e cada cor comprada uma vez só. | Repositórios separados para `Neuronio` e `Sinapse`, e validação de saldo e posse no endpoint. | `RedeNeural` e `Carteira` são a única porta para mudar esses dados. A rede é carregada inteira a cada neurônio novo (duas consultas), e a carteira fica reservada no banco durante a compra. |
| [9. Objeto de valor (DDD)](#9-objeto-de-valor-ddd) | A duração de uma sessão (de 10 a 120 minutos, de 5 em 5) é usada pela sessão, pelo neurônio e pela fábrica, e a validação não pode ser repetida em cada lugar. | Guardar a duração como `int` e validar onde ela é usada. | `Duracao` é imutável e só existe válida. O custo é escrever `duracao.minutos` em vez do número direto. |
| [10. Injeção de dependência](#10-injeção-de-dependência) | Os serviços da aplicação usam repositórios, publicador e relógio, e os testes precisam trocar tudo isso por versões em memória e por um relógio controlado. | O serviço criar as próprias dependências (`RepositorioSessaoDjango()` dentro do construtor), ou uma biblioteca de contêiner de injeção. | Os serviços recebem tudo pelo construtor, e cada módulo da API monta o seu em `_servico()`. A montagem é escrita à mão, e a do publicador aparece em dois módulos. |
| [11. Adapter](#11-adapter) | O cadastro precisa validar a senha com os `AUTH_PASSWORD_VALIDATORS` e gravá-la com Argon2, que são do Django, mas o caso de uso não pode importar o Django. | Chamar `validate_password` e `set_password` direto no `CadastroUsuario`. | A interface `ServicoSenhas` na aplicação e o adaptador `ServicoSenhasDjango` na infraestrutura. Gravar o usuário e a senha viram duas escritas, protegidas por uma transação no endpoint. |
| [12. Fila de saída (Outbox) e receptor idempotente](#12-fila-de-saída-outbox-e-receptor-idempotente) | Os avisos de saída da tela e de desistência precisam chegar ao servidor, na ordem, mesmo se a rede cair ou a página fechar. | Enviar direto e descartar o aviso que falhar, ou repetir só enquanto a página estiver aberta. | Uma fila guardada no navegador, enviada em ordem e repetida até ser entregue. Como um aviso pode chegar duas vezes, o servidor precisa ignorar o repetido. |
| [13. Facade (cliente da API)](#13-facade-cliente-da-api) | Toda chamada à API precisa do token, de renovar o token vencido (15 min) e repetir a chamada, e de transformar o corpo de erro num erro do JavaScript. | `fetch` direto em cada serviço ou componente, ou uma biblioteca com interceptadores (ex.: axios). | Um único módulo (`api.ts`) esconde tudo isso atrás de `api.get`, `api.post` etc. O preço é um estado de sessão no próprio módulo, configurado pelo `AuthProvider`. |
| [14. Provider (Context do React)](#14-provider-context-do-react) | O usuário logado e as ações de login, cadastro e logout são usados pela rota protegida, pelo layout e por várias telas. | Passar o usuário de componente em componente por props, ou uma biblioteca de estado global (ex.: Redux). | Um `AuthProvider` no topo do app e o hook `useAuth`. Quem usa o contexto é redesenhado quando ele muda, o que é raro (só no login, no logout e na renovação). |
| [15. Estratégias de cache do service worker](#15-estratégias-de-cache-do-service-worker) | O app instalado precisa abrir sem rede, mas os dados das sessões não podem vir de um cache velho. | Guardar também as respostas da API, para abrir offline com os últimos dados. | Rede primeiro para as páginas, cache primeiro para os arquivos, e a API sempre pela rede. Sem rede, o app abre, mas não mostra dados. |

## 1. State

**Onde:** `EstadoSessao`, `EmAndamento`, `Concluida` e `Podada` em `backend/app/domain/entidades/sessao_foco.py` (issue #10).

`SessaoFoco` não decide sozinha se pode ser concluída ou podada: ela repassa a operação para o estado atual. A classe base lança `TransicaoInvalida` em todas as operações, e cada estado só sobrescreve o que é permitido nele. Por isso `Concluida` e `Podada` não sobrescrevem nenhuma operação: só têm `nome` e `codigo`.

```python
class EstadoSessao(ABC):
    def concluir(self, sessao: "SessaoFoco", relogio: Callable[[], datetime]) -> None:
        raise TransicaoInvalida(f"Não é possível concluir uma sessão {self.nome}.")

class EmAndamento(EstadoSessao):
    def concluir(self, sessao: "SessaoFoco", relogio: Callable[[], datetime]) -> None:
        instante = relogio()
        if instante < sessao.fim_previsto:
            raise TransicaoInvalida("A sessão ainda não atingiu a duração planejada.")
        sessao._mudar_estado(Concluida(), instante)

class SessaoFoco(Entidade):
    def concluir(self, relogio: Callable[[], datetime] = agora) -> None:
        self._estado.concluir(self, self._relogio_validado(relogio))
```

A expiração por abandono segue o mesmo caminho: `EmAndamento.expirar` poda a sessão que passou de duração + 5 min, e os estados finais devolvem `False`.

**Trade-off:** são quatro classes onde um `Enum` bastaria para guardar o status. O banco guarda o estado como texto (`codigo`), então `SessaoFocoModel.para_entidade` (`backend/app/infra/modelos/sessao_foco.py`) tem um mapa de texto para classe. E o estado muda a sessão por um método protegido (`_mudar_estado`), que só ele deve chamar; o Python não impede outro código de chamá-lo, então a regra é uma convenção. Em troca, as cinco operações não têm nenhum `if` de status, e um estado novo (ex.: pausada) seria uma classe nova.

**Testes:** `test_transicoes_invalidas_sessao_concluida` e `test_transicoes_invalidas_sessao_podada` em `backend/tests/unit/domain/test_sessao_foco.py`.

## 2. Strategy (política de interrupção)

**Onde:** `PoliticaInterrupcao`, `ModoEstrito` e `ModoTolerante` em `backend/app/domain/politica_interrupcao.py` (issue #11).

A sessão recebe a política na criação e pergunta a ela se a saída da tela poda. Não sabe qual modo está valendo.

```python
class ModoEstrito(PoliticaInterrupcao):
    def deve_podar(
        self,
        sessao: "SessaoFoco",
        nova_interrupcao: Interrupcao,
        historico: list[Interrupcao],
    ) -> bool:
        return True

class ModoTolerante(PoliticaInterrupcao):
    def deve_podar(
        ...
    ) -> bool:
        if nova_interrupcao.retorno is None:
            return False  # Se ainda não voltou, não temos como saber o tempo total fora

        return nova_interrupcao.segundos_fora > self._saldo_restante(sessao, historico)
```

A política também diz quando a sessão morreu (`instante_da_poda`). O padrão é o momento da saída, que o estrito herda; o tolerante sobrescreve para o instante em que o saldo acabou, no meio da saída que o estourou. A API e o banco trocam o modo como texto (`"estrito"`, `"tolerante"`), e `politica_por_codigo` é o único lugar com a lista de modos:

```python
def politica_por_codigo(codigo: str) -> PoliticaInterrupcao:
    """Cria a política a partir do código vindo da API ou do banco."""
    try:
        return _POLITICAS[codigo]()
```

**Trade-off:** uma classe por modo, e o tolerante precisa receber o histórico de saídas, porque o saldo é da sessão inteira. A tela também conhece a regra dos 10% (`PROPORCAO_TOLERANCIA` em `frontend/src/hooks/useSessaoFoco.ts`), para mostrar o saldo e podar na hora. As duas contas podem divergir (ex.: relógios diferentes), então a sessão só aparece concluída quando o servidor confirma, e se ele responder que a sessão foi podada, a tela poda também. Em troca, `SessaoFoco` não muda quando surge um modo novo (aberto/fechado), e cada regra é testada sem sessão real no banco.

**Testes:** `test_modo_estrito_sempre_poda`, `test_modo_tolerante_poda_somando_historico`, `test_modo_tolerante_poda_quando_o_saldo_acaba` e `test_politica_por_codigo_cria_a_politica_certa` em `backend/tests/unit/domain/test_politica_interrupcao.py`.

## 3. Strategy (formação das sinapses)

**Onde:** `RegraFormacaoSinapses` e `RegraRecentesEMesmaMateria` em `backend/app/domain/formacao_sinapses.py` (issue #23).

A regra atual liga o neurônio novo aos 2 vivos mais recentes e ao último vivo da mesma matéria, com peso maior a cada volta à matéria. A regra só propõe as ligações (`Conexao`), e a `RedeNeural` as transforma em sinapses depois de validá-las:

```python
class RegraFormacaoSinapses(ABC):
    @abstractmethod
    def conexoes(self, novo: Neuronio, rede: "RedeNeural") -> list[Conexao]:
        """Ligações do neurônio `novo`, que ainda não está na `rede`."""
        ...

# RedeNeural.adicionar (backend/app/domain/rede_neural.py)
for conexao in self._regra.conexoes(neuronio, self)
```

A regra é escolhida na montagem do `RedeNeuralService` (`backend/app/application/rede.py`), e o `SessaoService` não sabe qual está valendo.

**Trade-off:** uma interface a mais, e a regra recebe a rede inteira, então pode ler qualquer coisa dela. Por isso a rede valida de novo cada ligação proposta (sem autoconexão, sem repetição, só neurônios vivos) e recusa tudo se uma for inválida. Em troca, trocar a regra é passar outra classe ao serviço.

**Testes:** `test_criterio_regra_trocada_sem_mexer_no_servico_de_sessao` em `backend/tests/unit/application/test_sessoes.py` (uma regra sem ligações, trocada só na montagem) e `test_criterio_sem_sinapses_repetidas_mesmo_que_a_regra_proponha` em `backend/tests/unit/domain/test_rede_neural.py`.

## 4. Factory Method

**Onde:** `TipoNeuronio`, `Granular`, `Piramidal`, `Purkinje` e `FabricaNeuronio` em `backend/app/domain/entidades/neuronio.py` (issue #22).

O `SessaoService` entrega a sessão para a fábrica e recebe o neurônio pronto (`neuronio = self._fabrica.criar(sessao)`). A fábrica pergunta a cada tipo se ele aceita a duração:

```python
@_MetodoFabrica
def tipo_para(self, duracao_minutos: int) -> TipoNeuronio:
    """Escolhe o `TipoNeuronio` pela faixa de duração (em minutos)."""
    ...
    for tipo in self._tipos:
        if tipo.aceita(duracao_minutos):
            return tipo

@_MetodoFabrica
def criar(self, sessao: "SessaoFoco") -> Neuronio:
    """Cria o `Neuronio` correspondente à `sessao`."""
    tipo = self.tipo_para(sessao.duracao.minutos)
```

Na forma clássica do padrão, o método de criação é sobrescrito por subclasses do criador. Aqui a variação ficou nos produtos: cada `TipoNeuronio` declara a própria faixa (`duracao_minima` e `duracao_maxima`), e a fábrica recebe a lista de tipos no construtor (`FabricaNeuronio(tipos)`). Um tipo novo entra na lista sem subclasse da fábrica e sem mudar quem a chama. Os tipos com faixa mais específica são consultados primeiro, então um tipo novo pode ocupar uma parte da faixa de outro.

**Trade-off:** mais classes no domínio, e o `_MetodoFabrica` (um descritor que permite chamar `FabricaNeuronio.criar(sessao)` direto na classe ou numa instância com outros tipos) é menos óbvio de ler que um método comum. Em troca, as faixas de duração ficam num lugar só, e o endpoint `GET /rede` usa os atributos do tipo (`cor`, `numero_dendritos`, `raio`) sem saber qual é.

**Testes:** `test_criterio_adicionar_tipo_novo_nao_altera_quem_chama_a_fabrica` em `backend/tests/unit/domain/test_neuronio.py`.

## 5. Template Method

**Onde:** `RegraConquista` e as subclasses em `backend/app/domain/conquistas.py` (issue #32).

A classe abstrata implementa os passos comuns (`progresso` e `cumprida`), e cada subclasse só preenche o passo que muda (`medir`):

```python
@abstractmethod
def medir(self, resumo: ResumoFoco) -> int:
    """O valor que a regra acompanha, na mesma unidade da meta."""

def progresso(self, resumo: ResumoFoco) -> int:
    """Quanto já foi feito, de 0 até a meta (o que passa da meta não conta)."""
    return min(self.medir(resumo), self._meta)

def cumprida(self, resumo: ResumoFoco) -> bool:
    return self.medir(resumo) >= self._meta

class DiasSeguidos(RegraConquista):
    def medir(self, resumo: ResumoFoco) -> int:
        return resumo.sequencia.recorde
```

O `ConquistaService` (`backend/app/application/conquistas.py`) percorre o `CATALOGO_CONQUISTAS` sem saber qual regra é qual. As regras com meta no construtor (`HorasFocadas(10)`, `DiasSeguidos(7)`) geram várias conquistas com uma classe só.

**Trade-off:** toda regra precisa caber no formato "um número contra uma meta". Uma conquista com duas condições ao mesmo tempo (ex.: 10 horas focadas e 7 dias seguidos) precisaria de um `medir` que juntasse as duas num número só, ou de uma mudança na classe base. Como só o código da conquista vai para o banco, nome, dica e meta podem mudar sem migração.

**Testes:** `backend/tests/unit/domain/test_conquistas.py` (uma classe de teste por regra) e `backend/tests/unit/application/test_conquistas.py`.

## 6. Observer

**Onde:** `PublicadorEventos`, `ObservadorSessao`, `SessaoConcluida` e `SessaoPodada` em `backend/app/domain/eventos.py` (issue #24); os observadores `AtualizadorRede` (#23), `AvaliadorConquistas` (#32) e `CreditadorATP` (#34) em `backend/app/domain/observadores.py`.

O `SessaoService` só publica o evento. O publicador entrega o evento aos observadores inscritos naquele tipo de evento:

```python
def publicar(self, evento: Any) -> None:
    tipo_evento = type(evento)
    # Observadores recebem alerta quando o evento acontece
    for observador in self._observadores.get(tipo_evento, []):
        observador.processar(evento)
```

Quem inscreve os observadores é a montagem do serviço, em `backend/app/api/sessoes.py`:

```python
publicador = PublicadorEventos()
publicador.inscrever(SessaoConcluida, atualizador)
publicador.inscrever(SessaoPodada, atualizador)
publicador.inscrever(SessaoConcluida, avaliador)
```

O evento leva o neurônio que a fábrica criou, para os observadores não precisarem buscá-lo de novo. As conquistas e o ATP entraram depois da rede, e o `SessaoService` não mudou em nenhuma das duas vezes.

**Trade-off:** a ordem de inscrição importa. O avaliador de conquistas olha a rede, então precisa vir depois do atualizador da rede; isso está comentado onde eles são inscritos e coberto por um teste. Os observadores rodam na hora, dentro da mesma transação da conclusão: se creditar o ATP falhar, a conclusão inteira é desfeita, o que evita uma sessão concluída sem neurônio, mas deixa a resposta esperando todos eles. E a montagem do publicador é repetida em `backend/app/api/estatisticas.py`, porque as estatísticas também podem podar uma sessão abandonada, e em `backend/app/management/commands/podar_sessoes_orfas.py`, que só poda e por isso só inscreve o atualizador da rede; quem inscrever um observador novo precisa lembrar dos três lugares.

**Testes:** `test_o_avaliador_precisa_vir_depois_do_atualizador_da_rede` em `backend/tests/unit/application/test_conquistas.py` (inscreve na ordem errada e mostra que nada é desbloqueado) e `test_publicar_evento_ignora_observadores_de_outros_tipos` em `backend/tests/unit/domain/test_eventos.py`.

## 7. Repository

**Onde:** sete interfaces em `backend/app/domain/repositorios.py` (`RepositorioUsuario`, `RepositorioSessao`, `RepositorioNeuronio`, `RepositorioRedeNeural`, `RepositorioMateria`, `RepositorioConquista` e `RepositorioCarteira`), implementadas com o Django em `backend/app/infra/repositorios/` e em memória em `backend/tests/repositorios.py` (issue #13).

O domínio declara só o que precisa, e a infraestrutura converte entre o model do Django e a entidade:

```python
class RepositorioSessao(ABC):
    @abstractmethod
    def buscar_por_id(self, id: UUID) -> SessaoFoco | None:
        """Busca uma sessão de foco pelo seu identificador único (UUID)."""
        ...

class RepositorioSessaoDjango(RepositorioSessao):
    def buscar_por_id(self, id: UUID) -> SessaoFoco | None:
        """Busca uma sessão de foco pelo seu identificador único (UUID)."""
        sessao_model = SessaoFocoModel.objects.filter(id=id).first()
        if not sessao_model:
            return None
        return sessao_model.para_entidade()

class RepositorioSessaoMemoria(RepositorioSessao):
    def buscar_por_id(self, id: UUID) -> SessaoFoco | None:
        """Busca uma sessão de foco pelo seu UUID em memória."""
        return self._sessoes.get(id)
```

**Trade-off:** cada entidade tem um model separado e dois conversores (`para_entidade` e `de_entidade`), e cada consulta nova vira um método na interface e em duas implementações (ex.: `listar_historico`, com filtros e paginação). A implementação em memória pode divergir da real, então os repositórios Django têm testes de integração próprios. Em troca, o domínio não importa o Django, e os testes de unidade dos serviços rodam sem banco.

**Testes:** `test_dominio_nao_importa_django_nem_drf` em `backend/tests/unit/domain/test_dominio_puro.py` e os repositórios Django em `backend/tests/integration/test_repositorios_django.py`.

## 8. Agregado (DDD)

**Onde:** `RedeNeural` em `backend/app/domain/rede_neural.py` (issue #23) e `Carteira` em `backend/app/domain/carteira.py` (issue #34), cada uma com o próprio repositório.

A rede é a única porta para adicionar neurônios e sinapses. Tudo é validado antes de mudar a rede, então uma ligação inválida não deixa nada pela metade:

```python
def adicionar(self, neuronio: Neuronio) -> list[Sinapse]:
    """Coloca o neurônio na rede e devolve as sinapses que ele formou.

    Tudo é validado antes de mudar a rede: se a regra propuser uma ligação
    inválida, nada é adicionado.
    """
```

A carteira é a única porta para gastar ATP, e o repositório a carrega com a linha reservada no banco até o fim da transação, para duas compras ao mesmo tempo não gastarem o mesmo saldo:

```python
def comprar(self, cor: CorLoja, instante: datetime) -> None:
    """Desconta o preço e desbloqueia a cor para as matérias do estudante."""
    if self.possui(cor):
        raise CorJaDesbloqueada(f"A cor {cor.nome} já é sua.")
    if self._saldo < cor.preco:
        ...
    self._saldo -= cor.preco

# backend/app/infra/repositorios/carteira.py
modelo = CarteiraModel.objects.select_for_update().get(
```

**Trade-off:** a rede é carregada inteira a cada neurônio novo (duas consultas, neurônios e sinapses), mesmo que a regra só olhe os últimos. Como neurônios e sinapses não mudam depois de criados, o agregado guarda só o que foi adicionado (`neuronios_novos` e `sinapses_novas`), e o repositório grava em lote. A reserva da carteira faz uma compra esperar a outra do mesmo estudante. O banco repete as regras principais como última barreira: `UniqueConstraint` e `CheckConstraint` em `SinapseModel`, e saldo como `PositiveIntegerField`.

**Testes:** `test_criterio_sem_autoconexao_mesmo_que_a_regra_proponha` em `backend/tests/unit/domain/test_rede_neural.py`, `test_criterio_sem_saldo_a_compra_e_recusada_e_nada_muda` em `backend/tests/unit/domain/test_carteira.py` e `test_o_banco_recusa_a_mesma_cor_duas_vezes` em `backend/tests/integration/test_repositorios_django.py`.

## 9. Objeto de valor (DDD)

**Onde:** `Duracao` em `backend/app/domain/duracao.py` (issue #9). Seguem a mesma ideia, como `@dataclass(frozen=True)`, a `Interrupcao`, a `Conexao`, a `CorLoja`, o `ResumoFoco` e os eventos.

```python
@dataclass(frozen=True)
class Duracao:
    """Objeto de valor: duração planejada de uma sessão de foco, em minutos.

    É imutável e sempre válido: se o objeto existe, a duração respeita as regras.
    Assim SessaoFoco e Neuronio não repetem a validação.
    """
```

A `Interrupcao` ser um objeto de valor também resolve um problema do padrão 12: duas interrupções com os mesmos horários são iguais, então a sessão reconhece um aviso repetido com `interrupcao in self._historico_interrupcoes`.

**Trade-off:** o código escreve `sessao.duracao.minutos` em vez do número direto, e as bordas (API e banco) convertem de e para `int`. Em troca, uma duração inválida não chega a existir.

**Testes:** `backend/tests/unit/domain/test_duracao.py`.

## 10. Injeção de dependência

**Onde:** os construtores dos serviços em `backend/app/application/` e as funções `_servico()` em cada módulo de `backend/app/api/`, que são o único lugar onde as implementações concretas são escolhidas.

O `SessaoService` depende só de interfaces e de uma função que lê a hora:

```python
def __init__(
    self,
    sessoes: RepositorioSessao,
    publicador: PublicadorEventos,
    relogio: Callable[[], datetime] = agora,
    materias: RepositorioMateria | None = None,
    fabrica: FabricaNeuronio | type[FabricaNeuronio] = FabricaNeuronio,
):
```

A API entrega as versões com o Django (`backend/app/api/sessoes.py`), e os testes entregam as em memória e um relógio que eles avançam:

```python
return SessaoService(
    RepositorioSessaoDjango(),
    publicador,
    relogio=lambda: agora(),
    materias=RepositorioMateriaDjango(),
)

# backend/tests/unit/application/test_conquistas.py
return SessaoService(sessoes, publicador, relogio=relogio)
```

O relógio injetado é o que permite testar "concluir antes da hora", "abandonada depois de duração + 5 min" e a sequência de dias sem esperar o tempo passar.

**Trade-off:** a montagem é escrita à mão, e cada requisição monta o seu grafo de objetos (barato, porque os repositórios não guardam estado). Sem um contêiner, a montagem do publicador aparece em `api/sessoes.py`, em `api/estatisticas.py` e no comando `podar_sessoes_orfas`. Uma biblioteca de contêiner resolveria isso, mas seria mais uma dependência para seis funções curtas.

**Testes:** todos os testes de `backend/tests/unit/application/` montam os serviços com repositórios em memória, sem banco.

## 11. Adapter

**Onde:** a interface `ServicoSenhas` em `backend/app/application/cadastro.py` e o adaptador `ServicoSenhasDjango` em `backend/app/infra/senhas.py` (issue #14).

O `Usuario` do domínio não tem senha. O caso de uso `CadastroUsuario` pede a validação e a gravação a uma interface, e o adaptador traduz isso para as ferramentas do Django (os validadores do `settings` e o hash Argon2):

```python
class ServicoSenhasDjango(ServicoSenhas):
    def validar(self, senha: str, usuario: Usuario) -> None:
        ...
        try:
            # As mensagens dos validadores vêm em português, como o resto da API.
            with translation.override("pt-br"):
                validate_password(senha, candidato)
        except ValidationError as erro:
            raise SenhaInvalida(" ".join(erro.messages)) from erro
```

O adaptador também traduz o erro: a `ValidationError` do Django vira `SenhaInvalida`, um erro do domínio, que a API responde como os outros.

**Trade-off:** gravar o usuário e gravar a senha viram duas escritas, então o endpoint as faz dentro de uma transação (`backend/app/api/auth.py`). Em troca, o cadastro é testado com um serviço de senhas falso, sem banco.

**Testes:** `ServicoSenhasFalso` em `backend/tests/unit/application/test_cadastro.py`, e as regras reais de senha em `backend/tests/integration/test_auth_cadastro.py`.

## 12. Fila de saída (Outbox) e receptor idempotente

**Onde:** a fila de avisos em `frontend/src/services/sessoes.ts` (issue #20) e a checagem de aviso repetido em `SessaoFoco._aplicar_politica` (`backend/app/domain/entidades/sessao_foco.py`).

Todo aviso (saída da tela ou desistência) é guardado no navegador antes de ser enviado. A fila é enviada um aviso por vez, na ordem em que aconteceram, e para no primeiro que falhar por rede, que fica para a próxima tentativa:

```ts
export function avisar(
  aviso: Aviso,
  aoResponder?: (resposta: RespostaAviso) => void,
): Promise<boolean> {
  salvarAvisos([...lerAvisos(), aviso])
  return enviarAvisosPendentes(aoResponder)
}
```

Se a resposta se perder, o mesmo aviso é enviado de novo. O servidor reconhece a saída repetida e não desconta o saldo do modo tolerante duas vezes:

```python
if interrupcao in self._historico_interrupcoes:
    # Reenvio da mesma saída (ex.: a resposta se perdeu na rede e o app
    # tentou de novo): já foi contada e não pode descontar o saldo duas vezes.
    return
```

Uma desistência repetida chega a uma sessão que já foi encerrada ou apagada, e a fila descarta o aviso recusado em vez de repeti-lo para sempre. A saída que acontece com a página fechando vai na hora com `keepalive` (`avisarSaidaImediata`) e só fica na fila se não for entregue.

**Trade-off:** a fila vive no `localStorage` (na navegação privada, só na memória da página), e os avisos chegam atrasados quando a rede volta. Por isso a conclusão espera a fila: os avisos pendentes vão antes do pedido de conclusão, porque o servidor precisa deles para decidir (`frontend/src/hooks/useSessaoFoco.ts`). O servidor, por sua vez, precisa aceitar avisos repetidos e atrasados, e valida os horários de cada um (`SessaoService.registrar_interrupcao` recusa saída no futuro ou antes do início da sessão).

**Testes:** `sem rede, guarda o aviso no navegador e entrega na próxima tentativa` em `frontend/src/services/sessoes.test.ts`, `test_reenviar_a_mesma_saida_nao_conta_duas_vezes` em `backend/tests/unit/domain/test_sessao_foco.py` e `test_reenviar_a_mesma_interrupcao_nao_desconta_o_saldo_de_novo` em `backend/tests/integration/test_api_sessoes.py`.

## 13. Facade (cliente da API)

**Onde:** `frontend/src/services/api.ts` (issues #12, #14 e #15).

Os serviços do frontend (`sessoes.ts`, `materias.ts`, `loja.ts` etc.) chamam `api.get` e `api.post` sem saber do token, da renovação nem do formato de erro:

```ts
export const api = {
  get: <T>(caminho: string) => requisicao<T>('GET', caminho),
  post: <T>(caminho: string, corpo?: unknown) => requisicao<T>('POST', caminho, corpo),
```

Por trás, `requisicao` põe o token, transforma o corpo `{"erro", "mensagem"}` num `ApiError` e, num 401, renova o token e repete a chamada uma vez. Várias chamadas recebendo 401 ao mesmo tempo esperam a mesma renovação:

```ts
function renovarToken(): Promise<string | null> {
  if (!sessao) return Promise.resolve(null)
  renovacaoEmAndamento ??= sessao.renovar().finally(() => {
    renovacaoEmAndamento = null
  })
  return renovacaoEmAndamento
}
```

**Trade-off:** o módulo guarda um estado de sessão (`sessao` e `renovacaoEmAndamento`), um por aba. Para o `api.ts` não depender do React, quem diz como renovar e o que fazer quando a sessão acaba é o `AuthProvider`, por `configurarSessao`. Usar uma biblioteca com interceptadores daria o mesmo resultado, com uma dependência a mais.

**Testes:** `chamadas simultâneas com 401 compartilham uma única renovação` e `se não der para renovar, encerra a sessão e repassa o 401` em `frontend/src/services/api.test.ts`.

## 14. Provider (Context do React)

**Onde:** `AuthProvider` em `frontend/src/contexts/AuthContext.tsx`, o contexto em `frontend/src/contexts/authContextDef.ts` e o hook `useAuth` em `frontend/src/hooks/useAuth.ts` (issues #14 e #15).

O `App.tsx` envolve as rotas no `AuthProvider`, e qualquer componente lê o usuário e as ações pelo hook, que falha com uma mensagem clara se for usado fora do provider:

```ts
export function useAuth(): AuthContextTipo {
  const contexto = useContext(AuthContext)
  if (!contexto) {
    throw new Error('useAuth deve ser utilizado dentro de um AuthProvider')
  }
  return contexto
}
```

**Trade-off:** todo componente que usa o contexto é redesenhado quando ele muda. Como isso só acontece no login, no logout e na renovação do token, não pesa. Uma biblioteca de estado global seria mais do que o app precisa: o resto do estado (sessão de foco, matérias, conquistas) fica nos hooks de cada tela.

**Testes:** `frontend/src/contexts/AuthContext.test.tsx` (renovação e fim da sessão) e `frontend/src/hooks/useAuth.test.tsx`.

## 15. Estratégias de cache do service worker

**Onde:** `frontend/public/sw.js` (issue #35).

Cada tipo de pedido tem uma estratégia: páginas vêm da rede primeiro (sem rede, a última versão guardada do app); arquivos vêm do cache primeiro; a API nunca passa pelo cache.

```js
if (pedido.mode === 'navigate' && url.origin === self.location.origin) {
  evento.respondWith(redePrimeiro(evento))
} else if (url.origin === self.location.origin) {
  evento.respondWith(cachePrimeiro(pedido, CACHE_APP))
} else if (ORIGENS_DE_FONTES.includes(url.origin)) {
  evento.respondWith(cachePrimeiro(pedido, CACHE_FONTES))
}
// O resto (a API, em outra origem) vai direto para a rede.
```

**Trade-off:** sem rede, o app abre, mas não mostra sessões nem a rede neural. Foi de propósito: o servidor é a fonte da verdade, e um dado velho (ex.: uma sessão que parece em andamento mas já foi podada) seria pior que um erro. Trocar a versão (`VERSAO`) a cada mudança no service worker é manual.

**Testes:** `critério: sem rede, a página abre com o JS, o CSS e as fontes guardados` e `a API e os envios nunca passam pelo cache` em `frontend/src/sw.test.ts`.

## Padrões considerados e descartados

- **Active Record** (descartado para as entidades de domínio, issue #13): embora seja o padrão natural do Django (onde `UsuarioModel.objects.create()` ou `model.save()` misturam persistência e estado), adotá-lo no domínio acoplaria todas as regras de negócio ao framework e ao banco de dados relacional. Foi descartado em favor do padrão **Repository**, mantendo os models do Django restritos à camada de infraestrutura (`backend/app/infra/modelos/`).
- **Django Signals** (descartado para mensageria de domínio, issue #24): embora seja o mecanismo nativo do framework para desacoplar ações, utilizá-lo para a lógica de negócio principal acoplaria o domínio à infraestrutura, dificultando a testabilidade isolada e ocultando o fluxo lógico que agora é explícito no sistema. Foi descartado em favor do padrão **Observer** construído em puro Python.
- **Decorator para variações de cor por tipo de neurônio** (usado na primeira versão da loja, issue #34, e retirado): a `VarianteCor` envolvia um `TipoNeuronio` e trocava só o nome e a cor, e a fábrica criava os neurônios com a variação escolhida para cada faixa de duração. Funcionava, mas a cor da matéria sempre vencia a da loja, então comprar uma cor parecida com uma da paleta não fazia sentido. A loja passou a vender cores para as matérias (`backend/app/domain/loja.py`), o Decorator e a fábrica por estudante saíram, e quem tinha comprado uma variação recebeu o ATP de volta (`backend/app/migrations/0008_reembolsar_loja_anterior.py`).
- **State também no frontend**: a tela de foco tem fases parecidas com os estados da sessão, mas elas são um tipo de união (`FaseSessao`, em `frontend/src/hooks/useSessaoFoco.ts`), e não classes. A tela muda de fase pelo que vê (o tempo acabou, o saldo do tolerante acabou), mas a sessão só aparece concluída quando o servidor confirma, e uma resposta de poda do servidor leva a tela para `podada`. Quem guarda as regras de transição é o servidor; classes de estado no cliente repetiriam essas regras sem proteger nada, e o TypeScript já recusa uma fase que não existe.
