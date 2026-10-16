# Padrões de Projeto e Trade-offs

> Enunciado, seção 2.5.2: para cada padrão efetivamente utilizado, explicar o problema que ele resolveu no projeto, as alternativas consideradas e descartadas, e o motivo da escolha.

Cada PR que introduzir um padrão adiciona uma linha na tabela e uma seção com o código correspondente. A versão final é consolidada na issue #45.

| Padrão | Problema no projeto | Alternativa considerada | Trade-off da escolha |
| ------ | ------------------- | ----------------------- | -------------------- |
| State | O ciclo de vida da sessão (Em Andamento, Concluída, Podada) exigia regras rígidas de transição, como impedir a conclusão de algo já podado. | Uso de `Enum` para status e blocos `if/elif` espalhados pela classe `SessaoFoco`. | Adiciona mais classes ao domínio e complexidade estrutural, mas isola completamente as regras de transição e elimina os `if`s, facilitando a adição de novos estados futuros. |
| Strategy | O que acontece quando o estudante sai da tela depende do modo escolhido: no estrito, qualquer saída poda; no tolerante, as saídas somadas são perdoadas até 10% da duração da sessão. As regras precisam ser trocadas por sessão e por usuário. | `if modo == "estrito" ... elif modo == "tolerante"` dentro de `SessaoFoco`. | Cria uma classe por regra (`PoliticaInterrupcao`, `ModoEstrito`, `ModoTolerante` em `backend/app/domain/politica_interrupcao.py`), mas `SessaoFoco` não muda quando surge uma política nova (aberto/fechado), e cada regra é testada isolada. A política também diz *quando* a sessão morreu (`instante_da_poda`): no estrito, na saída; no tolerante, quando o saldo acabou. |

## Padrões considerados e descartados
