# Testes de Software

> Enunciado, seção 2.5.3: descrever a estratégia de testes adotada, as ferramentas utilizadas, o que foi coberto e o que ficou fora do escopo, e apresentar evidências de execução.

Cada PR que adicionar testes registra aqui o que foi testado e em qual nível. A versão final é consolidada na issue #47, com as evidências da #43 em `evidencias/`.

## Estratégia

### Testes unitários

- **Domínio** (`backend/tests/unit/domain/`, issue #9): um arquivo por classe (`Usuario`, `SessaoFoco`, `Neuronio`, `Duracao` e as exceções). Cobrem valores válidos e inválidos (com `pytest.mark.parametrize`), atributos somente leitura e igualdade por identidade. Não usam banco nem Django.
- **Arquitetura** (`backend/tests/unit/domain/test_dominio_puro.py`, issue #9): lê os imports de cada arquivo de `app/domain/` com o módulo `ast` e falha se algum importar `django` ou `rest_framework`.
- **Timer da sessão de foco** (`frontend/src/hooks/useSessaoFoco.test.ts`, issue #17): testa o hook isolado com `renderHook` e o relógio falso do Vitest (`vi.useFakeTimers`). Inclui o critério de aceite da issue: o relógio avança sem o intervalo disparar, como numa aba em segundo plano, e o tempo restante continua certo ao voltar para a aba. Também cobre a regra do modo tolerante: saldo de 10% da sessão para ficar fora da tela, descontado a cada saída sem voltar ao valor inicial, e poda quando a saída passa do saldo.
- **Neurônio animado** (`frontend/src/utils/geometriaNeuronio.test.ts` e `frontend/src/components/NeuronioAnimado.test.tsx`, issue #19): a geometria é testada como função pura (o desenho é sempre o mesmo para o mesmo tipo; o corpo celular cresce primeiro, os dendritos nível a nível e o axônio só depois de 80%; podado, recolhe até 42%, sem axônio nem pontas). No componente, verifica que a poda e o brilho forte só entram depois do primeiro quadro, para a transição acontecer na tela.
- **Tela de foco** (`frontend/src/pages/Foco.test.tsx`, issue #17): usa a Testing Library para clicar como o estudante faria (escolher duração e modo, começar, desistir com confirmação, ver as telas de sucesso e de poda), buscando os elementos pelo papel acessível (`getByRole`).

### Testes de integração

### Testes de aceitação (E2E)

## Ferramentas

## O que foi coberto

## O que ficou fora do escopo

- **Aparência e fluidez das animações** (issue #19): o jsdom não desenha nem roda transições CSS, então os testes automatizados conferem os valores (quanto de cada traço está desenhado, classes de poda e de brilho), não o resultado visual. A comparação com o protótipo e a fluidez num celular real são verificadas manualmente.

## Evidências de execução
