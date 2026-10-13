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
- **Lógica separada da tela no frontend** (`frontend/src/hooks/useSessaoFoco.ts`, issue #17): o hook concentra o estado e as regras da sessão (limites da duração, timer, conclusão, desistência, tela cheia), e a página `frontend/src/pages/Foco.tsx` só desenha o que ele devolve. Assim o timer é testado sem renderizar a tela, e a integração com a API (issue #20) muda o hook sem mexer nos componentes.

## Baixo acoplamento e alta coesão

- **Neurônio em três partes** (issue #19): a geometria é uma função pura em `frontend/src/utils/geometriaNeuronio.ts` (recebe tipo, progresso e se está podado e devolve o que desenhar), o componente `frontend/src/components/NeuronioAnimado.tsx` só transforma esse resultado em SVG, e a animação fica no CSS (`frontend/src/styles/neuronio.css`). Cada parte muda sem afetar as outras: a #22 pode trocar as formas dos tipos sem tocar no componente, e o `prefers-reduced-motion` desliga as transições sem mexer em código.

## Nomenclatura

## Tratamento de erros nas bordas
