# Deploy (issue #38)

O Synapse fica no ar com três serviços gratuitos, sem cartão de crédito:

| Parte | Onde | Plano |
|---|---|---|
| Frontend (React, build do Vite) | Render, *Static Site* | gratuito, não dorme |
| API (Django + gunicorn) | Render, *Web Service* (Docker) | gratuito, dorme após 15 min ocioso |
| Banco PostgreSQL | Neon | gratuito, não expira |

A configuração do Render está no [`render.yaml`](../render.yaml) (Blueprint), e a imagem da API no [`backend/Dockerfile.prod`](../backend/Dockerfile.prod).

## Decisão

O único critério era usar ferramentas gratuitas, e o app precisa estar no ar até a entrega (01/12/2026) e na apresentação.

- **Render para a API e o frontend.** O plano gratuito aceita Docker (a mesma imagem testada localmente e no CI), dá HTTPS e um endereço `onrender.com` sem configuração, e faz deploy a cada push na `main`. O frontend vai como site estático, servido por CDN, e esse tipo de serviço não dorme.
- **Neon para o banco, e não o PostgreSQL do Render.** O PostgreSQL gratuito do Render expira 30 dias depois de criado, antes da entrega. O do Neon não expira. Ele desliga sozinho quando fica ocioso e volta na primeira consulta, em menos de um segundo.
- **Alternativas descartadas.** Railway e Fly.io não têm um plano gratuito permanente que sirva: dão só crédito de teste ou pedem cartão. Vercel e Netlify serviriam para o frontend, mas deixariam o projeto em duas plataformas sem ganho real.

### O ponto fraco: a API dorme

No plano gratuito, a API dorme depois de 15 minutos sem requisições. A primeira requisição depois disso espera cerca de 1 minuto, enquanto o serviço sobe. O frontend não é afetado.

Para não acontecer na apresentação:

1. O workflow [`manter-acordado.yml`](../.github/workflows/manter-acordado.yml) chama o `/health` a cada 10 minutos, das 7h à meia-noite (horário de Brasília). O `/health` não consulta o banco, então o Neon pode continuar dormindo e não gasta horas de computação.
2. O plano gratuito dá 750 horas por mês, e cerca de 17 horas por dia somam 530 horas. Sobra margem.
3. **No dia da apresentação**, uns 5 minutos antes, rode o workflow à mão (aba *Actions* > *Manter a API acordada* > *Run workflow*) ou abra `https://<api>/health` no navegador e espere o `{"status": "ok"}`. O agendamento do GitHub pode atrasar alguns minutos, então essa checagem final é o que garante a API acordada.

## Como foi preparado para produção

- **Variáveis de ambiente**: `DEBUG=False`, `SECRET_KEY` gerada pelo Render, `DATABASE_URL` do Neon, `CORS_ALLOWED_ORIGINS` com o endereço do frontend. O `ALLOWED_HOSTS` recebe sozinho o endereço público do serviço, que vem em `RENDER_EXTERNAL_HOSTNAME`.
- **gunicorn**: `gunicorn config.wsgi` com 2 workers (`WEB_CONCURRENCY`), na porta que o Render informa em `$PORT`.
- **Arquivos estáticos**: o `collectstatic` roda no build da imagem, e o WhiteNoise serve o CSS e o JS do Admin e da API navegável, comprimidos e com cache longo. O Swagger carrega a interface pela CDN do jsDelivr.
- **Migrações**: rodam a cada deploy, antes de o gunicorn subir (`migrate --noinput && gunicorn ...`). O plano gratuito não tem a etapa de *pre-deploy*.
- **HTTPS**: o Render termina o HTTPS e avisa pelo cabeçalho `X-Forwarded-Proto` (`SECURE_PROXY_SSL_HEADER`). O Django redireciona HTTP para HTTPS, manda HSTS e marca os cookies como seguros. O login da API não usa cookie (o token JWT vai no cabeçalho `Authorization`), então frontend e API em domínios diferentes não são problema.
- **Conexões com o banco**: reaproveitadas por 60 s (`CONN_MAX_AGE`) e testadas antes do reuso (`CONN_HEALTH_CHECKS`), porque o Neon fecha as conexões quando desliga.
- **CI**: o job `imagem-producao` monta a imagem de produção e roda `manage.py check --deploy` com `DEBUG=False` a cada PR.

## Passo a passo

Faça isso depois que o PR da issue estiver na `main`.

### 1. Banco no Neon

1. Crie uma conta em <https://neon.tech> (dá para entrar com o GitHub).
2. Crie um projeto chamado `synapse`, com PostgreSQL 16 e região **AWS US East 1 (N. Virginia)**, a mesma da API no Render. Cada requisição faz várias consultas, então API e banco perto um do outro pesam mais que a distância até o Brasil.
3. Em *Connect*, desligue o *Connection pooling* e copie a *connection string*. Ela tem esta forma:
   `postgresql://usuario:senha@ep-xxxx.us-east-1.aws.neon.tech/neondb?sslmode=require`

### 2. API e frontend no Render

1. Crie uma conta em <https://render.com> com o GitHub e autorize o acesso ao repositório `LuMaPro/Synapse`.
2. *New* > *Blueprint*, escolha o repositório e a branch `main`. O Render lê o `render.yaml` e mostra os dois serviços, `synapse-api` e `synapse-web`.
3. Preencha as variáveis pedidas:
   - `DATABASE_URL`: a connection string do Neon.
   - `CORS_ALLOWED_ORIGINS` e `VITE_API_URL`: os endereços ainda não existem. Use `https://synapse-web.onrender.com` e `https://synapse-api.onrender.com` por enquanto; o passo 5 corrige se o Render der outro nome.
4. *Deploy Blueprint*. O primeiro deploy da API leva alguns minutos (build da imagem e migrações).
5. Confira os endereços reais no painel de cada serviço. Se forem diferentes (o Render acrescenta um sufixo quando o nome já existe, como `synapse-api-x1y2.onrender.com`):
   - em `synapse-api` > *Environment*, ajuste `CORS_ALLOWED_ORIGINS` para o endereço do frontend, sem barra no fim;
   - em `synapse-web` > *Environment*, ajuste `VITE_API_URL` para o endereço da API e faça *Manual Deploy* > *Clear build cache & deploy*. A variável entra no build, então só vale depois de um novo build.

### 3. Manter a API acordada

No GitHub, em *Settings* > *Secrets and variables* > *Actions* > *Variables*, crie a variável `API_URL` com o endereço da API (ex.: `https://synapse-api.onrender.com`, sem barra no fim). Depois, em *Actions* > *Manter a API acordada* > *Run workflow*, rode uma vez para conferir.

### 4. Conferir

- `https://<api>/health` responde `{"status": "ok"}`.
- `https://<api>/docs/` abre o Swagger, e `https://<api>/admin/` abre o Admin com o visual normal (CSS carregado).
- No endereço do frontend, crie uma conta, faça uma sessão de foco e veja o neurônio na rede.
- Atualize o endereço público no [README](../README.md#acesse-online).

### Superusuário do Admin (opcional)

O plano gratuito não tem terminal no servidor. Crie o superusuário do seu computador, apontando para o banco do Neon:

```bash
cd backend
DATABASE_URL="<connection string do Neon>" uv run python manage.py createsuperuser
```

No PowerShell: `$env:DATABASE_URL="<connection string do Neon>"; uv run python manage.py createsuperuser`.

## Testar a imagem de produção localmente

Com o banco do `docker compose` no ar:

```bash
docker build -f backend/Dockerfile.prod -t synapse-api-prod backend
docker run --rm -p 10000:10000 --network synapse_default -e PORT=10000 -e DEBUG=False -e SECURE_SSL_REDIRECT=False -e SECRET_KEY=uma-chave-local-qualquer-bem-longa -e DATABASE_URL=postgres://synapse:synapse@db:5432/synapse -e ALLOWED_HOSTS=localhost synapse-api-prod
```

`SECURE_SSL_REDIRECT=False` só porque localmente não há HTTPS. Para o frontend usar essa API, gere o build com `VITE_API_URL=http://localhost:10000` e abra com `npm run preview`.
