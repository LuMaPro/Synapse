# Padrões de Projeto e Trade-offs

> Enunciado, seção 2.5.2: para cada padrão efetivamente utilizado, explicar o problema que ele resolveu no projeto, as alternativas consideradas e descartadas, e o motivo da escolha.

Cada PR que introduzir um padrão adiciona uma linha na tabela e uma seção com o código correspondente. A versão final é consolidada na issue #45.

| Padrão | Problema no projeto | Alternativa considerada | Trade-off da escolha |
| ------ | ------------------- | ----------------------- | -------------------- |
| State | O ciclo de vida da sessão (Em Andamento, Concluída, Podada) exigia regras rígidas de transição, como impedir a conclusão de algo já podado. | Uso de `Enum` para status e blocos `if/elif` espalhados pela classe `SessaoFoco`. | Adiciona mais classes ao domínio e complexidade estrutural, mas isola completamente as regras de transição e elimina os `if`s, facilitando a adição de novos estados futuros. |

## Padrões considerados e descartados
