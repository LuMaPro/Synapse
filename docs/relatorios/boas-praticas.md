# Boas Práticas de Programação e Orientação a Objetos

> Enunciado, seção 2.5.1: para cada prática citada, indicar a classe, o módulo ou o trecho de código em que foi aplicada.

Cada PR que aplicar uma prática registra aqui o caminho do arquivo e um trecho curto de código. A versão final é consolidada na issue #44.

## SOLID

### S: Responsabilidade única

### O: Aberto/fechado

### L: Substituição de Liskov

### I: Segregação de interfaces

### D: Inversão de dependência

## Separação em camadas

- **Domínio puro** (`backend/app/domain/`, issue #9): entidades, objetos de valor e exceções não dependem do Django nem do DRF, então as regras de negócio são testadas sem banco e sem servidor. A regra é verificada automaticamente por `backend/tests/unit/domain/test_dominio_puro.py`.

## Baixo acoplamento e alta coesão

## Nomenclatura

## Tratamento de erros nas bordas
