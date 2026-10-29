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
├── utils/        # funções puras de apoio (formatarTempo, ...)
├── styles/       # CSS global e de cada tela (foco.css, ...)
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

## Celular e instalação como app (PWA)

O app pode ser instalado na tela inicial do celular (issue #35). Abaixo de 640 px de
largura, a navegação vira a barra de abas embaixo, como no design.

- `public/manifest.webmanifest` e `public/icones/`: nome, cores e ícones do app.
- `public/sw.js`: service worker básico. Deixa o app instalável e abre a casca sem
  rede; a API nunca passa por cache. Só é registrado no build de produção.
- Durante a sessão, a tela fica ligada (Wake Lock API, `src/hooks/useTelaLigada.ts`).

O service worker e a trava de tela só funcionam em contexto seguro (HTTPS ou
`localhost`). Para testar a instalação:

```bash
npm run build
npm run preview
```

- **Computador (Chrome ou Edge):** abra http://localhost:4173. O ícone de instalar
  aparece na barra de endereço; em DevTools > Application, veja o Manifest e o
  Service Worker.
- **Android:** ligue o celular no USB com a depuração ativada, abra
  `chrome://inspect/#devices` no computador e, em "Port forwarding", encaminhe as
  portas 4173 e 8000. No Chrome do celular, abra http://localhost:4173 e use
  "Instalar app".
- **iPhone:** o Safari não tem encaminhamento de porta. Pela rede local, rode
  `npm run preview -- --host` e acesse pelo IP do computador; o app funciona, mas sem
  HTTPS não instala o service worker. Para usar o backend, rode-o com
  `uv run python manage.py runserver 0.0.0.0:8000` e ponha o IP em `VITE_API_URL`
  (antes do build), em `ALLOWED_HOSTS` e em `CORS_ALLOWED_ORIGINS` (ver
  `backend/.env.example`).
