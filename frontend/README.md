# Synapse: frontend

SPA em **React 19 + TypeScript**, com **Vite**.

## Pré-requisitos

- [Node.js](https://nodejs.org/) 22 ou mais novo (LTS recomendado)

## Instalar

```bash
cd frontend
npm install
```

Para apontar para um backend diferente de `http://localhost:8000`, copie `.env.example` para `.env` e ajuste `VITE_API_URL`.

## Rodar

```bash
npm run dev
```

Abre em http://localhost:5173.

## Comandos

| Comando | O que faz |
| ------- | --------- |
| `npm run dev` | Servidor de desenvolvimento com recarregamento automático |
| `npm run build` | Checa os tipos e gera a versão de produção em `dist/` |
| `npm run preview` | Serve a versão de produção localmente |
| `npm run lint` | ESLint |
| `npm run format` | Formata o código com Prettier |
| `npm run format:check` | Só confere a formatação (usado no CI) |
| `npm test` | Roda os testes uma vez (Vitest) |
| `npm run test:watch` | Roda os testes de novo a cada alteração |

## Estrutura

```
src/
├── pages/        # uma tela por rota (Login, Cadastro, Foco, Rede, Estatisticas)
├── components/   # componentes reutilizáveis (Layout, ...)
├── hooks/        # hooks próprios (useAuth, useSessaoFoco, ...)
├── services/     # comunicação com a API (api.ts)
├── styles/       # CSS global
├── App.tsx       # definição das rotas
└── main.tsx      # ponto de entrada
```

## Rotas

| Rota | Tela |
| ---- | ---- |
| `/` | redireciona para `/foco` |
| `/login` | Entrar |
| `/cadastro` | Criar conta |
| `/foco` | Sessão de foco |
| `/rede` | Rede neural |
| `/estatisticas` | Estatísticas |

## Testes

Os testes ficam ao lado do código, com o sufixo `.test.ts` ou `.test.tsx`, e usam
Vitest + Testing Library. Para testar componentes com rotas, renderize dentro de um
`MemoryRouter` (veja `src/App.test.tsx`).
