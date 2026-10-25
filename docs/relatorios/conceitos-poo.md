# Conceitos de POO Aplicados

> Enunciado, seção 2.5.4: explicar, com exemplos retirados do próprio código, onde e por que os conceitos de encapsulamento, herança, polimorfismo e abstração foram utilizados e, quando for o caso, onde deliberadamente não foram aplicados.

Cada PR que aplicar um desses conceitos registra aqui a classe, o motivo e um trecho curto de código. A versão final é consolidada na issue #46.

## Encapsulamento

**Onde:** entidades de domínio em `backend/app/domain/entidades/` (`Usuario`, `SessaoFoco`, `Neuronio`) e o objeto de valor `Duracao` em `backend/app/domain/duracao.py` (issue #9).

As entidades guardam o estado em atributos com prefixo `_` e o expõem por propriedades. Toda validação acontece no construtor, então um objeto inválido nunca chega a existir: quem usa a classe não precisa lembrar de validar nada.

```python
# backend/app/domain/entidades/usuario.py
class Usuario(Entidade):
    def __init__(self, nome: str, email: str, *, id=None, criado_em=None):
        super().__init__(id)
        self._nome = self._validar_nome(nome)
        self._email = self._normalizar_email(email)
        ...

    @property
    def email(self) -> str:  # sem setter: o e-mail não muda depois de criado
        return self._email

    @nome.setter
    def nome(self, valor: str) -> None:  # pode mudar, mas passa pela mesma validação
        self._nome = self._validar_nome(valor)
```

- **Somente leitura quando faz sentido:** `id`, `email`, `criado_em`, `inicio`, `duracao` e os ids de relacionamento não têm setter. O `nome` do usuário tem, porque trocar de nome é uma operação legítima; mesmo assim, o setter reaproveita a validação do construtor.
- **Regra num lugar só:** a duração de uma sessão (de 10 a 120 minutos, de 5 em 5) fica encapsulada em `Duracao`, um `@dataclass(frozen=True)` que valida em `__post_init__`. `SessaoFoco` e `Neuronio` recebem os minutos e guardam uma `Duracao`, sem repetir a regra.
- **Estado derivado em vez de guardado:** `SessaoFoco.fim_previsto` é calculado a partir de `inicio` e `duracao`, então não existe como os dois ficarem inconsistentes.
- **Agregado que protege as próprias regras** (`backend/app/domain/rede_neural.py`, issue #23): `RedeNeural` não expõe as listas internas. `neuronios`, `sinapses` e `sinapses_de` devolvem cópias, e a única forma de mudar a rede é `adicionar`, que valida tudo antes de alterar qualquer coisa: se a regra propuser uma ligação inválida, a rede fica como estava. Até os dados que vêm do banco passam pelas mesmas validações ao montar o agregado.
- **Limite do Python:** não há atributo privado de verdade; o `_` é uma convenção. O que garante o encapsulamento são as propriedades sem setter, e os testes em `backend/tests/unit/domain/` verificam que atribuir a elas lança `AttributeError`.

## Herança

**Onde:** `backend/app/domain/entidades/base.py`, `backend/app/domain/excecoes.py` (issue #9) e `backend/app/domain/entidades/neuronio.py` (issue #22).

- **`Entidade`**: classe base de `Usuario`, `SessaoFoco` e `Neuronio`. Concentra o que toda entidade tem em comum: o `id` (UUID gerado no próprio domínio) e a igualdade por identidade (`__eq__` e `__hash__` comparam tipo e `id`, não os outros atributos). É uma relação "é um" de verdade, e o comportamento herdado é idêntico nas três classes.
- **Exceções de domínio**: `ErroDominio` é a base de `DuracaoInvalida`, `NomeInvalido`, `EmailInvalido` e `HorarioInvalido`. A camada de API pode tratar qualquer erro de regra de negócio com um único `except ErroDominio` (issue #12), sem conhecer cada exceção.
- **`TipoNeuronio` (`Granular`, `Piramidal` e `Purkinje`)**: a classe abstrata `TipoNeuronio` define o contrato visual de toda espécie de neurônio (`nome`, `cor`, `numero_dendritos` e `raio` como propriedades abstratas) e fornece o comportamento comum herdado pelas subclasses: o `codigo` em minúsculas para a API, a verificação de faixa de duração em `aceita(duracao_minutos)` (a partir de `duracao_minima` e `duracao_maxima` de cada classe) e a igualdade por tipo (`__eq__` e `__hash__`).

## Polimorfismo

**Onde:** políticas de interrupção em `backend/app/domain/politica_interrupcao.py` (issue #11), estados da sessão em `backend/app/domain/entidades/sessao_foco.py` (issue #10) e tipos de neurônio em `backend/app/domain/entidades/neuronio.py` (issue #22).

`SessaoFoco` chama a política e o estado sem saber qual é a classe concreta. A mesma chamada tem comportamentos diferentes conforme o objeto recebido:

```python
# backend/app/domain/entidades/sessao_foco.py
def _aplicar_politica(self, interrupcao: Interrupcao) -> None:
    historico = list(self._historico_interrupcoes)
    if self._politica.deve_podar(self, interrupcao, historico):  # estrito ou tolerante?
        instante = self._politica.instante_da_poda(self, interrupcao, historico)
        self.podar(relogio=lambda: instante)
    else:
        self._historico_interrupcoes.append(interrupcao)
```

- **Políticas:** `ModoEstrito.deve_podar` sempre responde que sim; `ModoTolerante.deve_podar` soma o tempo fora e compara com 10% da sessão. `instante_da_poda` também varia: o estrito herda o padrão da classe base (o momento da saída), e o tolerante sobrescreve com o momento em que o saldo acabou.
- **Estados:** `registrar_interrupcao`, `concluir`, `podar` e `desistir` são delegados ao estado atual. `EmAndamento` aceita; `Concluida` e `Podada` herdam o comportamento padrão, que lança `TransicaoInvalida`.
- **Regra de formação das sinapses** (`backend/app/domain/formacao_sinapses.py`, issue #23): `RedeNeural.adicionar` chama `self._regra.conexoes(neuronio, self)` sem saber qual regra está valendo. Nos testes, uma regra que não liga nada, ou que propõe ligações inválidas, entra no lugar da padrão sem mudar a rede nem o `SessaoService`.
- **Tipos de neurônio e fábrica** (`backend/app/domain/entidades/neuronio.py`, issue #22): `FabricaNeuronio.tipo_para` percorre os objetos `TipoNeuronio` chamando `tipo.aceita(duracao_minutos)` sem `if/elif` por classe concreta, e `Neuronio` delega `cor`, `numero_dendritos` e `raio` ao seu `TipoNeuronio`. Da mesma forma, o `SessaoService` só chama `self._fabrica.criar(sessao)` e o endpoint `GET /rede` lê `neuronio.tipo.codigo` e `neuronio.cor` sem saber se o neurônio é `Granular`, `Piramidal`, `Purkinje` ou um tipo novo adicionado depois:

```python
# backend/app/domain/entidades/neuronio.py
for tipo in self._tipos:
    if tipo.aceita(duracao_minutos):  # Granular, Piramidal, Purkinje ou novo tipo?
        return tipo
```

- **Por quê:** uma política, um estado ou um tipo de neurônio novo é só uma classe nova. Quem chama (`SessaoFoco`, `SessaoService`, `GET /rede`) não muda e não tem `if` perguntando qual é o modo, o estado ou o tipo.

## Abstração

## Onde deliberadamente não aplicamos

- **Entidades não herdam dos models do Django** (issue #9). `Usuario` (domínio) e `UsuarioModel` (`backend/app/infra/modelos/usuario.py`) são classes separadas: o model só cuida da persistência e os repositórios convertem um no outro (issue #13). Assim as regras de negócio são testadas sem banco. O teste `backend/tests/unit/domain/test_dominio_puro.py` falha se algum arquivo de `app/domain/` importar `django` ou `rest_framework`.
- **`Duracao` não herda de `int`** (issue #9): usa composição (o atributo `minutos`). Herdar de `int` traria aritmética sem validação: `Duracao(25) + 3` resultaria no inteiro 28, que não é uma duração válida e escapa da regra.
