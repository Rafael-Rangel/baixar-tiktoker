# Content Orchestrator

API de orquestração de conteúdo para **n8n**: busca vídeos em fontes (YouTube Shorts, etc.), faz download e organiza por grupo/fonte. Pensado para rodar em **Docker na VPS** e ser chamado pelos workflows do n8n.

## Deploy (GitHub → VPS → Docker)

### 1. Clone na VPS

```bash
git clone https://github.com/Rafael-Rangel/orquestrador.git
cd orquestrador
```

### 2. Diretórios e (opcional) variáveis de ambiente

```bash
mkdir -p data downloads
cp .env.example .env   # opcional; edite LOCAL_STORAGE_PATH, DATA_PATH se precisar
```

### 3. Subir com Docker

```bash
docker compose up -d
```

- API: `http://localhost:8000`
- Health: `http://localhost:8000/v1/n8n/health`
- Docs: `http://localhost:8000/docs`

### 4. Integração com n8n

O n8n precisa alcançar o container pelo nome `content-orchestrator` na porta 8000.

**Opção A – Mesmo `docker-compose` do n8n**

Adicione o serviço `content-orchestrator` ao `docker-compose` do n8n (ou use o `docker-compose.n8n.example.yml` como referência) e use a mesma rede. Assim o n8n chama `http://content-orchestrator:8000`.

**Opção B – Rede externa compartilhada**

Se o n8n usa a rede `root_default`:

```bash
docker compose -f docker-compose.yml -f docker-compose.n8n.example.yml up -d
```

Ajuste o exemplo se sua rede tiver outro nome.

**Volume compartilhado com n8n**

O workflow do n8n usa `rm -rf /content-downloads/<grupo>`. Os downloads ficam em `/content-downloads` (mapeado de `./downloads` no host). Monte o **mesmo** diretório do host em `/content-downloads` no container do n8n para que o comando e os arquivos batam.

---

## Endpoints usados pelo n8n

| Método | Endpoint | Uso |
|--------|----------|-----|
| `GET` | `/v1/n8n/health` | Health check antes do fluxo |
| `POST` | `/v1/n8n/process-sources` | Buscar vídeos nas fontes (YouTube Shorts, etc.) |
| `POST` | `/v1/download` | Baixar vídeo (aguarda término; retorna sucesso ou erro) |

### `POST /v1/n8n/process-sources`

Corpo (exemplo):

```json
{
  "sources": [
    {
      "platform": "youtube",
      "external_id": "@canal",
      "group_name": "PodCasts",
      "video_type": "shorts"
    }
  ],
  "limit": 1
}
```

Resposta: `{ "status": "completed", "videos_found": N, "videos": [...], "errors": [] }`.  
Cada vídeo tem `url`, `platform`, `external_video_id`, `group_name`, `external_id`, `view_count`, etc.

### `POST /v1/download`

Corpo (exemplo):

```json
{
  "video_url": "https://www.youtube.com/shorts/VIDEO_ID",
  "platform": "youtube",
  "external_video_id": "VIDEO_ID",
  "group_name": "PodCasts",
  "source_name": "@canal"
}
```

- Sucesso: `200` e `{ "status": "completed", "path": "...", "message": "Vídeo baixado com sucesso" }`
- Falha: `422` e `{ "detail": "mensagem de erro" }`

O request só termina quando o download conclui (ou falha).

---

## Fluxo do workflow n8n (resumo)

1. **Health** → `GET /v1/n8n/health`
2. **Limpar pasta** → `rm -rf /content-downloads/<grupo>` (ex.: podcasts)
3. **Fontes** → Google Sheets “Fontes” filtrado por `group_name`
4. **Processar fontes** → `POST /v1/n8n/process-sources` com cada fonte (`platform`, `external_id`, `group_name`, `video_type`: shorts)
5. **Vídeos já usados** → Google Sheets “Vídeos Encontrados” por `video_id`
6. **Filtrar** → Code: pegar vídeos que **não** estão na planilha, escolher o de maior `view_count`
7. **Download** → `POST /v1/download` com `url`, `platform`, `external_video_id`, `group_name`, `source_name` (external_id)

Arquivos em `./downloads` (no host) → `/content-downloads/<grupo>/<fonte>/` no container.

---

## Estrutura do projeto

```
.
├── app/
│   ├── main.py
│   ├── api/routes/     # n8n, download, health, fetch, confirm, select
│   ├── core/           # config, logging
│   └── services/
│       ├── fetcher/    # busca vídeos (yt-dlp)
│       └── downloader/ # download (yt-dlp)
├── docker-compose.yml
├── docker-compose.n8n.example.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## Cookies (opcional)

Para YouTube com restrições, coloque `cookies.txt` em `./data/`. No Docker, `./data` é montado em `/app/data` e o app usa `DATA_PATH=/app/data`.

---

## Tecnologias

- **FastAPI** – API REST  
- **yt-dlp** – extração e download de vídeos (YouTube Shorts, etc.)  
- **Docker / Docker Compose** – deploy na VPS  
- **n8n** – orquestração dos workflows  

---

---

## Como testar localmente

### Opção A: Docker (recomendado)

```bash
mkdir -p data downloads
docker compose up -d
# Aguarde subir, depois:
./scripts/test-local.sh http://localhost:8000
```

### Opção B: Python (uvicorn)

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
mkdir -p data downloads
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Em outro terminal:

```bash
./scripts/test-local.sh http://localhost:8000
```

### Testar download de um Shorts

O script `test-local.sh` testa **health** e **process-sources**. Para testar **download**:

1. Edite `scripts/test-local.sh` e descomente o bloco **3** (curl do `/v1/download`).
2. Rode de novo: `./scripts/test-local.sh http://localhost:8000`.

Ou direto no terminal:

```bash
curl -X POST http://localhost:8000/v1/download \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://www.youtube.com/shorts/q70k78OJpic",
    "platform": "youtube",
    "external_video_id": "q70k78OJpic",
    "group_name": "teste",
    "source_name": "shorts"
  }'
```

O vídeo será salvo em `downloads/teste/shorts/` (ou em `/content-downloads` no Docker).

### Swagger UI

Com a API rodando, acesse **http://localhost:8000/docs** para testar os endpoints pela interface.

---

**Desenvolvido para uso com n8n e Docker em VPS.**
