Synapse
# Synapse

## Como executar

A forma mais simples é com Docker: um único comando sobe o backend, o frontend e o banco, sem instalar Python nem Node na sua máquina.

### Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e **aberto** (espere aparecer "Engine running").
- Git.

### Subir o ambiente

```bash
git clone https://github.com/LuMaPro/Synapse.git
cd Synapse
docker compose up --build
```

A primeira vez demora, porque o Docker baixa as imagens e instala as dependências. Nas próximas, é bem mais rápido (e o `--build` só é necessário quando as dependências mudam).

### Endereços

| Serviço | Endereço |
|---|---|
| Frontend (React) | http://localhost:5173 |
| API: health check | http://localhost:8000/health |
| API: documentação (Swagger) | http://localhost:8000/docs/ |
| PostgreSQL | `localhost:5432` |

### Hot reload

As pastas `backend/` e `frontend/` são montadas dentro dos contêineres. Ao salvar um arquivo, o servidor recarrega sozinho, sem precisar reiniciar o Docker.

### Comandos úteis

```bash
docker compose up -d            # sobe em segundo plano
docker compose logs -f backend  # acompanha os logs de um serviço
docker compose down             # para e remove os contêineres
docker compose down -v          # idem, e apaga os dados do banco
```

### Problemas comuns

- **`failed to connect to the docker API`**: o Docker Desktop não está aberto. Abra-o e espere o "Engine running".
- **Porta já em uso (5173, 8000 ou 5432)**: feche o programa que está usando a porta ou pare outro `docker compose` que esteja rodando.
- **Mudei dependências e nada mudou**: rode `docker compose up --build` de novo.

### Rodar sem Docker

Para rodar cada parte separadamente, veja o `backend/README.md` e o `frontend/README.md`.