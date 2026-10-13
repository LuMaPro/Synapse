# Testes de Software

> Enunciado, seção 2.5.3: descrever a estratégia de testes adotada, as ferramentas utilizadas, o que foi coberto e o que ficou fora do escopo, e apresentar evidências de execução.

Cada PR que adicionar testes registra aqui o que foi testado e em qual nível. A versão final é consolidada na issue #47, com as evidências da #43 em `evidencias/`.

## Estratégia

### Testes unitários

- **Domínio** (`backend/tests/unit/domain/`, issue #9): um arquivo por classe (`Usuario`, `SessaoFoco`, `Neuronio`, `Duracao` e as exceções). Cobrem valores válidos e inválidos (com `pytest.mark.parametrize`), atributos somente leitura e igualdade por identidade. Não usam banco nem Django.
- **Arquitetura** (`backend/tests/unit/domain/test_dominio_puro.py`, issue #9): lê os imports de cada arquivo de `app/domain/` com o módulo `ast` e falha se algum importar `django` ou `rest_framework`.

### Testes de integração

### Testes de aceitação (E2E)

## Ferramentas

## O que foi coberto

## O que ficou fora do escopo

## Evidências de execução
