# Documentação do Synapse

Mapa dos entregáveis do projeto: onde cada um está e em que issue foi feito. Para a visão geral, como executar e como rodar os testes, veja o [README principal](../README.md).

## Entregáveis

| Entregável | Onde está | Issues | Situação |
|---|---|---|---|
| Escopo do problema socioeconômico | [escopo-do-problema.md](escopo-do-problema.md) | #6, #39 | ✅ Pronto |
| Diagrama de casos de uso | [uml/casos-de-uso.puml](uml/casos-de-uso.puml) ([PNG](uml/casos-de-uso.png) e [SVG](uml/casos-de-uso.svg)) | #7, #41 | ✅ Pronto |
| Diagrama de classes | [uml/classes.puml](uml/classes.puml), com PNG e SVG de cada vista em [uml/](uml) | #40 | ✅ Pronto |
| Arquitetura | [arquitetura.md](arquitetura.md) | #39 | ✅ Pronto |
| Identidade visual e protótipo das telas | [design/](design/README.md) | #8 | ✅ Pronto |
| Prints do app | [prints/](prints) | #39 | ✅ Pronto |
| Código-fonte | [backend/](../backend/README.md) (Django) e [frontend/](../frontend/README.md) (React) | #1 a #35 | ✅ Pronto |
| Deploy com URL pública | [deploy.md](deploy.md); endereços no [README principal](../README.md#acesse-online) | #38 | ✅ Pronto |
| Cobertura de testes e evidências | [relatorios/evidencias/](relatorios/evidencias/README.md) | #43, #47 | ✅ Pronto |
| Boas práticas de programação e POO (seção 2.5.1) | [relatorios/boas-praticas.md](relatorios/boas-praticas.md) | #44 | ✅ Pronto |
| Padrões de projeto e trade-offs (seção 2.5.2) | [relatorios/padroes-de-projeto.md](relatorios/padroes-de-projeto.md) | #45 | ✅ Pronto |
| Testes de software (seção 2.5.3) | [relatorios/testes.md](relatorios/testes.md) | #47 | ✅ Pronto |
| Conceitos de POO aplicados (seção 2.5.4) | [relatorios/conceitos-poo.md](relatorios/conceitos-poo.md) | #46 | ✅ Pronto |
| Revisão final e release v1.0.0 | Tag `v1.0.0` e [Release no GitHub](https://github.com/LuMaPro/Synapse/releases/tag/v1.0.0) | #48 | ✅ Pronto |

## Diagramas UML

O [diagrama de casos de uso](uml/casos-de-uso.png) mostra o que a versão 1.0.0 faz, com três atores: o visitante (cadastro e login), o estudante (sessões de foco, rede, histórico, estatísticas, conquistas, matérias e loja) e o administrador (painel do Django e comando de poda das sessões abandonadas). Os `<<include>>` são os passos que sempre acontecem (concluir uma sessão forma o neurônio e rende ATP; desistir poda o neurônio), e os `<<extend>>`, os que dependem de uma condição, escrita entre colchetes (no modo estrito, qualquer saída da tela poda; no tolerante, só quando o tempo fora passa de 10% da sessão; a compra só sai com saldo suficiente).

O diagrama de classes tem várias vistas, para caber na página:

| Vista | Conteúdo |
|---|---|
| [Visão geral](uml/classes-visao-geral.png) | Todas as classes e relações, por camada, sem atributos nem métodos |
| [Sessão de foco](uml/classes-sessao.png) | `SessaoFoco` com os padrões State e Strategy |
| [Rede neural](uml/classes-rede.png) | `Neuronio`, Factory Method, `RedeNeural` e a regra das sinapses |
| [Eventos e conquistas](uml/classes-eventos.png) | Observer e Template Method |
| [Loja e estatísticas](uml/classes-loja-estatisticas.png) | `Carteira`, cores e os objetos das estatísticas |
| [Aplicação](uml/classes-aplicacao.png) | Os serviços e as dependências de cada um |
| [Repositórios](uml/classes-repositorios.png) | Interfaces do domínio e implementações com o Django |
| [Exceções](uml/classes-excecoes.png) | As exceções do domínio |

Para gerar as imagens de novo, veja o cabeçalho de [uml/casos-de-uso.puml](uml/casos-de-uso.puml) e de [uml/classes.puml](uml/classes.puml).

## Organização da pasta

```
docs/
├── README.md               # este mapa
├── escopo-do-problema.md   # problema, dados, público-alvo, personas e limitações
├── arquitetura.md          # camadas, fluxo da sessão, padrões, frontend e CI
├── deploy.md               # Render + Neon, passo a passo
├── design/                 # identidade visual e protótipo (HTML e PNGs)
├── prints/                 # telas do app pronto
├── uml/                    # diagramas de casos de uso e de classes
└── relatorios/             # relatórios das seções 2.5.1 a 2.5.4 e evidências
```
