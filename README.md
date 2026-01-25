# Content Orchestrator - Arquitetura Funcional

## 📋 Índice

1. [Visão Geral da Arquitetura](#visão-geral-da-arquitetura)
2. [Camadas do Sistema](#camadas-do-sistema)
3. [Fluxo de Dados e Processamento](#fluxo-de-dados-e-processamento)
4. [Componentes Principais](#componentes-principais)
5. [Estratégias de Download](#estratégias-de-download)
6. [Estrutura de Armazenamento](#estrutura-de-armazenamento)
7. [Integração com n8n](#integração-com-n8n)
8. [API Endpoints - Especificação Técnica](#api-endpoints---especificação-técnica)
9. [Tratamento de Erros e Resiliência](#tratamento-de-erros-e-resiliência)
10. [Performance e Escalabilidade](#performance-e-escalabilidade)

---

## 🏗️ Visão Geral da Arquitetura

O **Content Orchestrator** é uma API REST assíncrona construída com **FastAPI** que atua como uma camada de orquestração entre workflows do **n8n** e fontes de conteúdo de múltiplas plataformas (YouTube, Instagram, TikTok). O sistema é **stateless** e **stateless-first**, projetado para processar requisições de forma independente, sem manter estado entre chamadas.

### Princípios Arquiteturais

- **Stateless Design**: Cada requisição é independente; não há sessões ou estado compartilhado
- **Service-Oriented**: Lógica de negócio isolada em serviços especializados
- **Async-First**: Uso extensivo de `async/await` para I/O não-bloqueante
- **Fail-Safe**: Múltiplas estratégias de fallback para operações críticas
- **Container-Ready**: Otimizado para execução em containers Docker

### Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                         n8n Workflow                            │
│  (Orquestração, Google Sheets, Lógica de Negócio)              │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/REST
                             │ (JSON)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Content Orchestrator API (FastAPI)                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  API Layer (Routes)                                       │  │
│  │  - /v1/n8n/*      (Integração n8n)                      │  │
│  │  - /v1/fetch/*    (Busca de conteúdo)                    │  │
│  │  - /v1/select     (Seleção de conteúdo)                  │  │
│  │  - /v1/download   (Download de vídeos)                  │  │
│  │  - /v1/confirm_publish (Confirmação)                     │  │
│  │  - /health        (Health check)                          │  │
│  └───────────────────────┬──────────────────────────────────┘  │
│                           │                                      │
│  ┌───────────────────────▼──────────────────────────────────┐  │
│  │  Service Layer (Business Logic)                           │  │
│  │  ┌──────────────────┐  ┌──────────────────┐            │  │
│  │  │ FetcherService    │  │ DownloaderService│            │  │
│  │  │ - fetch_from_     │  │ - download_video │            │  │
│  │  │   source_data()   │  │ - _download_with │            │  │
│  │  │ - _construct_url() │  │   _ytdlp_library│            │  │
│  │  └──────────────────┘  └──────────────────┘            │  │
│  └───────────────────────┬──────────────────────────────────┘  │
│                           │                                      │
│  ┌───────────────────────▼──────────────────────────────────┐  │
│  │  Core Layer (Configuration & Logging)                   │  │
│  │  - Settings (Pydantic Settings)                        │  │
│  │  - Logging (Python logging)                            │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              External Dependencies                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   yt-dlp     │  │   ffmpeg     │  │  Platform    │         │
│  │  (Library)   │  │  (Binary)    │  │   APIs       │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Local Filesystem Storage                           │
│  downloads/                                                     │
│  ├── {group_name}/                                             │
│  │   └── {source_name}/                                       │
│  │       └── {video_title}.mp4                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Camadas do Sistema

### 1. API Layer (`app/api/routes/`)

**Responsabilidade**: Receber requisições HTTP, validar dados de entrada, e retornar respostas formatadas.

**Características**:
- **FastAPI Routers**: Cada módulo de rota é um `APIRouter` independente
- **Pydantic Models**: Validação automática de entrada via `BaseModel`
- **Async Endpoints**: Todos os endpoints são `async def` para não-bloqueio
- **Error Handling**: Exceções convertidas em respostas HTTP apropriadas

**Módulos**:
- `n8n.py`: Endpoints específicos para integração com n8n
- `fetch.py`: Busca de conteúdo de fontes
- `select.py`: Seleção de conteúdo disponível
- `download.py`: Download síncrono de vídeos (aguarda conclusão)
- `confirm.py`: Confirmação de publicação
- `health.py`: Health check simples

### 2. Service Layer (`app/services/`)

**Responsabilidade**: Implementar lógica de negócio isolada, reutilizável e testável.

#### FetcherService (`app/services/fetcher/service.py`)

**Funcionalidade**: Extrair metadados de vídeos de plataformas usando `yt-dlp`.

**Métodos Principais**:
- `fetch_from_source_data()`: Método principal assíncrono que busca vídeos
- `_construct_url()`: Constrói URLs específicas por plataforma

**Estratégia de Extração**:
```python
ydl_opts = {
    'quiet': True,              # Suprime output
    'extract_flat': True,       # Não baixa, apenas extrai metadados
    'force_generic_extractor': False,
    'playlistend': limit        # Limita quantidade se fornecido
}
```

**Suporte a Plataformas**:
- **YouTube**: Suporta handles (`@canal`) e channel IDs (`UC_xxx`), com suporte a `videos` e `shorts`
- **Instagram**: URLs de perfil
- **TikTok**: URLs de perfil com `@username`

#### DownloaderService (`app/services/downloader/service.py`)

**Funcionalidade**: Download de vídeos usando múltiplas estratégias de fallback.

**Métodos Principais**:
- `download_video()`: Método principal assíncrono
- `_download_with_ytdlp_library()`: Implementa estratégias de download
- `_get_video_title()`: Extrai título do vídeo para nomear arquivo
- `_sanitize_filename()`: Normaliza nomes de arquivo (remove acentos, emojis, caracteres especiais)
- `_resolve_cookies_path()`: Localiza arquivo de cookies para autenticação

**Estratégias de Download** (ordem de tentativa):

1. **Format 18 (YouTube apenas)**: Formato MP4 de baixa complexidade, sem cookies
2. **bestvideo+bestaudio + merge**: Melhor qualidade, requer `ffmpeg` para merge
3. **best**: Formato único de melhor qualidade disponível

**Fallback de URL**:
- Tentativa 1: URL original (ex: `https://www.youtube.com/shorts/ID`)
- Tentativa 2: URL alternativa `watch?v=ID` (se YouTube)

### 3. Core Layer (`app/core/`)

**Responsabilidade**: Configuração centralizada e logging.

#### Settings (`app/core/config.py`)

**Tecnologia**: `pydantic-settings` com `BaseSettings`

**Variáveis Configuráveis**:
- `PROJECT_NAME`: Nome do projeto
- `API_V1_STR`: Prefixo da API (`/v1`)
- `STORAGE_TYPE`: Tipo de armazenamento (`local`)
- `LOCAL_STORAGE_PATH`: Caminho base para downloads
- `DATA_PATH`: Caminho para dados auxiliares (cookies)

**Carregamento**: Via `.env` ou variáveis de ambiente, com cache via `@lru_cache()`

#### Logging (`app/core/logging.py`)

**Configuração**: Python `logging` padrão com formato estruturado

**Formato**: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

**Output**: `stdout` (capturado por Docker logs)

### 4. Application Entry Point (`app/main.py`)

**Responsabilidade**: Inicializar FastAPI, registrar rotas, e configurar aplicação.

**Estrutura**:
```python
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Registro de rotas com prefixos
app.include_router(n8n.router, prefix=f"{settings.API_V1_STR}/n8n", tags=["n8n"])
# ... outras rotas
```

**Root Endpoint**: Retorna HTML com links para documentação e endpoints principais

---

## 🔄 Fluxo de Dados e Processamento

### Fluxo Completo: Descoberta → Download → Publicação

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. DISCOVERY (Descoberta de Conteúdo)                         │
│                                                                 │
│ n8n → POST /v1/n8n/process-sources                            │
│   {                                                             │
│     "sources": [                                                │
│       {                                                         │
│         "platform": "youtube",                                 │
│         "external_id": "@canal",                               │
│         "group_name": "PodCasts",                              │
│         "video_type": "shorts"                                 │
│       }                                                         │
│     ],                                                          │
│     "limit": 10                                                 │
│   }                                                             │
│                                                                 │
│ ↓ FetcherService.fetch_from_source_data()                     │
│   - Constrói URL: https://www.youtube.com/@canal/shorts        │
│   - yt-dlp.extract_info() (extract_flat=True)                  │
│   - Extrai metadados: id, title, url, view_count, duration    │
│                                                                 │
│ ↓ Retorna:                                                      │
│   {                                                             │
│     "status": "completed",                                      │
│     "videos_found": 10,                                         │
│     "videos": [                                                 │
│       {                                                         │
│         "platform": "youtube",                                 │
│         "external_video_id": "abc123",                        │
│         "url": "https://www.youtube.com/shorts/abc123",        │
│         "title": "Video Title",                                 │
│         "view_count": 1000000,                                 │
│         "group_name": "PodCasts"                               │
│       }                                                         │
│     ]                                                           │
│   }                                                             │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. SELECTION (Seleção - opcional, pode ser feito no n8n)      │
│                                                                 │
│ n8n → POST /v1/select                                          │
│   {                                                             │
│     "destination_platform": "youtube",                          │
│     "destination_account_id": "@destino",                       │
│     "group_name": "PodCasts",                                  │
│     "available_videos": [...]                                  │
│   }                                                             │
│                                                                 │
│ ↓ Lógica simples: retorna primeiro vídeo disponível           │
│   (n8n pode implementar lógica mais complexa)                   │
│                                                                 │
│ ↓ Retorna:                                                      │
│   {                                                             │
│     "message": "Content selected",                               │
│     "selected": { video_data }                                 │
│   }                                                             │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. DOWNLOAD (Download Síncrono)                                │
│                                                                 │
│ n8n → POST /v1/download                                        │
│   {                                                             │
│     "video_url": "https://www.youtube.com/shorts/abc123",      │
│     "platform": "youtube",                                      │
│     "external_video_id": "abc123",                              │
│     "group_name": "PodCasts",                                   │
│     "source_name": "@canal"                                     │
│   }                                                             │
│                                                                 │
│ ↓ DownloaderService.download_video()                           │
│   - Resolve caminho: downloads/podcasts/canal/                 │
│   - Busca título: _get_video_title()                           │
│   - Sanitiza nome: _sanitize_filename()                        │
│   - Verifica se arquivo já existe (> 1KB)                      │
│                                                                 │
│ ↓ _download_with_ytdlp_library()                              │
│   Estratégia 1: Format 18 (YouTube, sem cookies)              │
│   Estratégia 2: bestvideo+bestaudio + merge (com ffmpeg)       │
│   Estratégia 3: best (formato único)                          │
│   Fallback URL: watch?v=ID (se shorts falhar)                  │
│                                                                 │
│ ↓ Verifica arquivo criado (> 1KB)                              │
│                                                                 │
│ ↓ Retorna (aguarda conclusão):                                 │
│   {                                                             │
│     "status": "completed",                                      │
│     "path": "/content-downloads/podcasts/canal/video_title.mp4",│
│     "message": "Vídeo baixado com sucesso"                     │
│   }                                                             │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. PUBLICATION (Fora do Orchestrator)                          │
│                                                                 │
│ n8n → Publica vídeo na plataforma de destino                  │
│   (YouTube API, Instagram API, etc.)                            │
│                                                                 │
│ ↓ Após sucesso, chama CONFIRM                                  │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. CONFIRMATION (Confirmação de Publicação)                    │
│                                                                 │
│ n8n → POST /v1/confirm_publish                                 │
│   {                                                             │
│     "video_id": "abc123",                                       │
│     "destination_platform": "youtube",                          │
│     "destination_account_id": "@destino",                       │
│     "result": "success",                                        │
│     "platform_post_id": "xyz789"                                │
│   }                                                             │
│                                                                 │
│ ↓ Retorna confirmação                                           │
│   (Histórico gerenciado no n8n/Google Sheets)                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Componentes Principais

### FetcherService

**Localização**: `app/services/fetcher/service.py`

**Responsabilidade**: Extrair metadados de vídeos de plataformas sem fazer download.

**Dependências**:
- `yt-dlp`: Biblioteca Python para extração de metadados
- `logging`: Logging de operações

**Métodos**:

#### `fetch_from_source_data()`
```python
async def fetch_from_source_data(
    platform: str,
    external_id: str,
    group_name: Optional[str] = None,
    limit: Optional[int] = None,
    video_type: str = "videos"
) -> List[Dict]
```

**Parâmetros**:
- `platform`: Plataforma (`youtube`, `instagram`, `tiktok`)
- `external_id`: ID do canal/perfil (ex: `@canal` ou `UC_xxx`)
- `group_name`: Nome do grupo/nicho (opcional, para organização)
- `limit`: Limite de vídeos a retornar (opcional)
- `video_type`: Tipo de vídeo (`videos` ou `shorts` para YouTube)

**Retorno**: Lista de dicionários com metadados:
```python
{
    "platform": "youtube",
    "external_id": "@canal",
    "external_video_id": "abc123",
    "title": "Video Title",
    "url": "https://www.youtube.com/shorts/abc123",
    "duration": 60,
    "view_count": 1000000,
    "group_name": "PodCasts",
    "fetched_at": "20240115"
}
```

**Tratamento de Erros**:
- Retorna lista vazia `[]` em caso de erro
- Loga erro detalhado para debugging
- Não propaga exceções para não quebrar o fluxo

#### `_construct_url()`
```python
def _construct_url(
    platform: str,
    external_id: str,
    video_type: str = "videos"
) -> Optional[str]
```

**Lógica**:
- **YouTube**: Detecta se `external_id` começa com `@` (handle) ou é channel ID
  - Handle: `https://www.youtube.com/{external_id}/{video_type}`
  - Channel ID: `https://www.youtube.com/channel/{external_id}/{video_type}`
- **Instagram**: `https://www.instagram.com/{external_id}/`
- **TikTok**: `https://www.tiktok.com/@{external_id}`
- Retorna `None` se plataforma não suportada

### DownloaderService

**Localização**: `app/services/downloader/service.py`

**Responsabilidade**: Download de vídeos com múltiplas estratégias de fallback.

**Dependências**:
- `yt-dlp`: Biblioteca Python para download
- `ffmpeg`: Binário do sistema (via Docker) para merge de vídeo/áudio
- `os`: Operações de filesystem
- `unicodedata`, `re`: Sanitização de nomes de arquivo

**Métodos Principais**:

#### `download_video()`
```python
async def download_video(
    video_url: str,
    platform: str,
    external_video_id: str,
    group_name: Optional[str] = None,
    source_name: Optional[str] = None
) -> dict
```

**Fluxo**:
1. **Resolve caminho de destino**:
   - Base: `LOCAL_STORAGE_PATH` (padrão: `downloads`)
   - Estrutura: `{base}/{group_name}/{source_name}/{filename}.mp4`
   - Sanitização: `group_name` e `source_name` convertidos para lowercase, espaços → underscores

2. **Busca título do vídeo**:
   - Chama `_get_video_title()` assincronamente
   - Se disponível, usa título sanitizado como nome do arquivo
   - Se não disponível, usa `external_video_id`

3. **Verifica arquivo existente**:
   - Verifica se arquivo já existe e tem tamanho > 1KB
   - Verifica tanto pelo nome do título quanto pelo `external_video_id`
   - Se existe, retorna imediatamente sem fazer download

4. **Executa download**:
   - Chama `_download_with_ytdlp_library()` com múltiplas estratégias
   - Aguarda conclusão (síncrono dentro do método assíncrono)

5. **Valida resultado**:
   - Verifica se arquivo foi criado e tem tamanho > 1KB
   - Retorna `{"status": "completed", "path": "..."}` ou `{"status": "failed", "error": "..."}`

#### `_download_with_ytdlp_library()`
```python
async def _download_with_ytdlp_library(
    video_url: str,
    output_path: str,
    external_video_id: Optional[str] = None
) -> dict
```

**Estratégias de Download** (ordem de tentativa):

**1. Format 18 (YouTube apenas)**:
```python
opts = {
    "format": "18",  # MP4 360p (baixa complexidade)
    "outtmpl": output_path.replace(".mp4", ".%(ext)s"),
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True
}
```
- **Vantagem**: Rápido, sem necessidade de cookies
- **Desvantagem**: Qualidade limitada (360p)

**2. bestvideo+bestaudio + merge**:
```python
opts = {
    "format": "bestvideo+bestaudio/best",
    "merge_output_format": "mp4",
    "outtmpl": output_path.replace(".mp4", ".%(ext)s"),
    "extractor_args": {"youtube": {"player_client": ["web", "android"]}},
    "cookiefile": cookies_path,  # Se disponível
    "quiet": True,
    "no_warnings": True
}
```
- **Vantagem**: Melhor qualidade disponível
- **Requisito**: `ffmpeg` instalado para merge
- **Fallback**: Usa cookies se disponível

**3. best (formato único)**:
```python
opts = {
    "format": "best",
    "outtmpl": output_path.replace(".mp4", ".%(ext)s"),
    "extractor_args": {"youtube": {"player_client": ["web", "android"]}},
    "cookiefile": cookies_path,  # Se disponível
    "quiet": True,
    "no_warnings": True
}
```
- **Vantagem**: Não requer merge, formato único
- **Desvantagem**: Pode não ser MP4

**Fallback de URL**:
- Se download falhar com URL original (`/shorts/ID`), tenta `watch?v=ID`

**Validação de Arquivo**:
- Verifica se arquivo existe e tem tamanho > 1KB
- Aceita extensões: `.mp4`, `.webm`, `.mkv`, `.m4a`
- Se extensão diferente de `.mp4`, renomeia para `.mp4`

#### `_sanitize_filename()`
```python
def _sanitize_filename(filename: str, max_length: int = 200) -> str
```

**Processo de Sanitização**:
1. **Remove emojis**: Regex para ranges Unicode de emojis
2. **Mapeia caracteres especiais**: `ª` → `a`, `º` → `o`, `ç` → `c`, etc.
3. **Normaliza Unicode**: `NFD` (Normalized Form Decomposed)
4. **Remove acentos**: Remove diacríticos (categoria `Mn`)
5. **Filtra caracteres**: Mantém apenas ASCII alfanumérico + ` _-.`
6. **Converte para lowercase**
7. **Remove caracteres inválidos**: `<>:"/\|?*`
8. **Substitui espaços/hífens/pontos**: Por underscore `_`
9. **Remove underscores múltiplos**: `_+` → `_`
10. **Limita tamanho**: Máximo `max_length` caracteres
11. **Fallback**: Se vazio, retorna `"video"`

**Exemplo**:
```
"Receita de Bolo 🎂 - Tutorial #1" 
→ "receita_de_bolo_tutorial_1"
```

#### `_resolve_cookies_path()`
```python
def _resolve_cookies_path() -> Optional[str]
```

**Locais de Busca** (ordem):
1. `{DATA_PATH}/cookies.txt` (padrão: `data/cookies.txt`)
2. `{cwd}/cookies.txt` (raiz do projeto)
3. `{project_root}/cookies.txt` (raiz absoluta do projeto)

**Uso**: Se encontrado, adiciona `"cookiefile": path` nas opções do yt-dlp

---

## 📁 Estrutura de Armazenamento

### Organização de Arquivos

```
downloads/                          # LOCAL_STORAGE_PATH
├── {group_name}/                   # Nome do grupo (sanitizado)
│   └── {source_name}/              # Nome da fonte (sanitizado)
│       └── {video_title}.mp4       # Título do vídeo (sanitizado)
│
└── {platform}/                     # Fallback se group_name/source_name não fornecidos
    └── {external_video_id}.mp4
```

### Sanitização de Caminhos

**Group Name**:
- Espaços → underscores
- Lowercase
- Exemplo: `"PodCasts"` → `"podcasts"`

**Source Name**:
- Remove `@` do início
- Espaços → underscores
- Lowercase
- Exemplo: `"@ShortsPodcuts"` → `"shortspodcuts"`

**Video Filename**:
- Processo completo de `_sanitize_filename()`
- Extensão: `.mp4` (forçado)

### Caminhos Absolutos

Todos os caminhos são convertidos para absolutos usando `os.path.abspath()` para garantir consistência entre diferentes contextos de execução (local, Docker, etc.).

---

## 🔌 Integração com n8n

### Modelo de Integração

O Content Orchestrator é **stateless** e **API-first**. O n8n é responsável por:
- **Gerenciamento de Estado**: Google Sheets para fontes, destinos, histórico
- **Orquestração**: Workflows complexos, loops, condições
- **Lógica de Negócio**: Seleção de conteúdo, filtros, regras

O Orchestrator fornece apenas:
- **Operações Atômicas**: Fetch, Download, Select, Confirm
- **Processamento**: Extração e download de vídeos

### Workflow n8n Típico

```
1. Trigger: Cron (ex: a cada 6 horas)
   ↓
2. HTTP Request: GET /v1/n8n/health
   ↓
3. Google Sheets: Ler "Fontes" filtrado por group_name
   ↓
4. Loop: Para cada fonte
   │
   ├─ HTTP Request: POST /v1/n8n/process-sources
   │  Body: { sources: [{ platform, external_id, group_name, video_type }], limit: 10 }
   │  ↓
   │  Retorna: { status, videos_found, videos: [...], errors: [] }
   │
   └─ Google Sheets: Salvar vídeos encontrados em "Vídeos Encontrados"
   ↓
5. Google Sheets: Ler "Vídeos Encontrados" e "Vídeos Publicados"
   ↓
6. Code Node: Filtrar vídeos não publicados, ordenar por view_count
   ↓
7. Loop: Para cada destino
   │
   ├─ Selecionar melhor vídeo disponível
   │  ↓
   ├─ HTTP Request: POST /v1/download
   │  Body: { video_url, platform, external_video_id, group_name, source_name }
   │  ↓
   │  Aguarda conclusão (síncrono)
   │  Retorna: { status: "completed", path: "...", message: "..." }
   │  ↓
   ├─ Ler arquivo do filesystem (path retornado)
   │  ↓
   ├─ Publicar na plataforma (YouTube API, Instagram API, etc.)
   │  ↓
   └─ HTTP Request: POST /v1/confirm_publish
      Body: { video_id, destination_platform, destination_account_id, result, platform_post_id }
      ↓
      Retorna: { status: "confirmed", message: "..." }
   ↓
8. Google Sheets: Atualizar "Vídeos Publicados"
```

### Volume Compartilhado

Para que o n8n acesse os arquivos baixados:

**Docker Compose**:
```yaml
volumes:
  - ./downloads:/content-downloads  # Mesmo caminho no container
```

**n8n Container** (deve montar o mesmo volume):
```yaml
volumes:
  - ./downloads:/content-downloads  # Mesmo caminho
```

**n8n Workflow**:
```bash
# Limpar pasta antes de download
rm -rf /content-downloads/{group_name}

# Após download, arquivo estará em:
/content-downloads/{group_name}/{source_name}/{video_title}.mp4
```

---

## 📡 API Endpoints - Especificação Técnica

### Base URL

```
http://localhost:8000/v1
```

### 1. n8n Endpoints (`/v1/n8n/*`)

#### `POST /v1/n8n/process-sources`

**Descrição**: Processa múltiplas fontes e retorna vídeos encontrados. Aguarda conclusão antes de retornar.

**Request Body**:
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
  "limit": 10
}
```

**Response (200)**:
```json
{
  "status": "completed",
  "videos_found": 10,
  "videos": [
    {
      "platform": "youtube",
      "external_id": "@canal",
      "external_video_id": "abc123",
      "title": "Video Title",
      "url": "https://www.youtube.com/shorts/abc123",
      "duration": 60,
      "view_count": 1000000,
      "group_name": "PodCasts",
      "fetched_at": "20240115"
    }
  ],
  "errors": []
}
```

**Comportamento**:
- Processa cada fonte sequencialmente
- Para cada fonte, chama `FetcherService.fetch_from_source_data()`
- Agrega todos os vídeos em uma lista única
- Coleta erros sem interromper processamento
- Retorna apenas quando todas as fontes foram processadas

**Tratamento de Erros**:
- Erros individuais são coletados em `errors[]`
- Status sempre `"completed"` (mesmo com erros parciais)

#### `GET /v1/n8n/health`

**Descrição**: Health check simples para verificar disponibilidade da API.

**Response (200)**:
```json
{
  "status": "ok",
  "message": "n8n integration ready"
}
```

### 2. Fetch Endpoints (`/v1/fetch/*`)

#### `POST /v1/fetch/run`

**Descrição**: Busca vídeos de uma única fonte.

**Request Body**:
```json
{
  "platform": "youtube",
  "external_id": "@canal",
  "group_name": "PodCasts",
  "limit": 10,
  "video_type": "shorts"
}
```

**Response (200)**:
```json
{
  "status": "completed",
  "videos_found": 10,
  "videos": [...]
}
```

### 3. Select Endpoint (`/v1/select`)

#### `POST /v1/select`

**Descrição**: Seleciona conteúdo disponível. Lógica simples (retorna primeiro disponível). Lógica complexa deve ser implementada no n8n.

**Request Body**:
```json
{
  "destination_platform": "youtube",
  "destination_account_id": "@destino",
  "group_name": "PodCasts",
  "available_videos": [
    {
      "external_video_id": "abc123",
      "view_count": 1000000,
      "group_name": "PodCasts"
    }
  ]
}
```

**Response (200)**:
```json
{
  "message": "Content selected",
  "selected": {
    "external_video_id": "abc123",
    "view_count": 1000000,
    "group_name": "PodCasts"
  }
}
```

**Response (200) - Sem conteúdo**:
```json
{
  "message": "No content available",
  "selected": null
}
```

### 4. Download Endpoint (`/v1/download`)

#### `POST /v1/download`

**Descrição**: Faz download de um vídeo. **Aguarda conclusão antes de retornar** (síncrono).

**Request Body**:
```json
{
  "video_url": "https://www.youtube.com/shorts/abc123",
  "platform": "youtube",
  "external_video_id": "abc123",
  "group_name": "PodCasts",
  "source_name": "@canal"
}
```

**Response (200) - Sucesso**:
```json
{
  "status": "completed",
  "path": "/content-downloads/podcasts/canal/video_title.mp4",
  "external_video_id": "abc123",
  "message": "Vídeo baixado com sucesso"
}
```

**Response (422) - Erro**:
```json
{
  "detail": "Falha ao baixar o vídeo: [mensagem de erro]"
}
```

**Comportamento**:
- Aguarda conclusão do download (não retorna imediatamente)
- Tenta múltiplas estratégias de download
- Verifica se arquivo foi criado e tem tamanho > 1KB
- Retorna caminho absoluto do arquivo

**Timeout**: Depende do timeout do cliente HTTP (n8n). Recomenda-se configurar timeout alto (ex: 10 minutos).

### 5. Confirm Endpoint (`/v1/confirm_publish`)

#### `POST /v1/confirm_publish`

**Descrição**: Confirma publicação de um vídeo. Apenas retorna confirmação; histórico deve ser gerenciado no n8n/Google Sheets.

**Request Body**:
```json
{
  "video_id": "abc123",
  "destination_platform": "youtube",
  "destination_account_id": "@destino",
  "result": "success",
  "platform_post_id": "xyz789",
  "error_message": null
}
```

**Response (200)**:
```json
{
  "status": "confirmed",
  "message": "Publish success confirmed for video abc123",
  "data": {
    "video_id": "abc123",
    "destination": "youtube/@destino",
    "result": "success",
    "platform_post_id": "xyz789",
    "error_message": null
  }
}
```

### 6. Health Endpoint (`/health`)

#### `GET /health`

**Descrição**: Health check geral da API.

**Response (200)**:
```json
{
  "status": "ok"
}
```

---

## 🛡️ Tratamento de Erros e Resiliência

### Estratégias de Resiliência

#### 1. Múltiplas Estratégias de Download

O `DownloaderService` implementa **fallback em cascata**:
- Se estratégia 1 falhar → tenta estratégia 2
- Se estratégia 2 falhar → tenta estratégia 3
- Se todas falharem → retorna erro

#### 2. Fallback de URL

Para YouTube:
- Tentativa 1: URL original (`/shorts/ID`)
- Tentativa 2: URL alternativa (`watch?v=ID`)

#### 3. Verificação de Arquivo Existente

Antes de fazer download:
- Verifica se arquivo já existe (por título ou `external_video_id`)
- Se existe e tem tamanho > 1KB, retorna imediatamente
- Evita downloads duplicados

#### 4. Limpeza de Arquivos Parciais

Após cada tentativa de download:
- Remove arquivos com tamanho ≤ 1KB (downloads incompletos)
- Previne acúmulo de arquivos corrompidos

#### 5. Tratamento de Erros por Camada

**API Layer**:
- Captura exceções e converte em respostas HTTP apropriadas
- `422 Unprocessable Entity` para erros de validação
- `500 Internal Server Error` para erros inesperados

**Service Layer**:
- Retorna estruturas de erro padronizadas: `{"status": "failed", "error": "..."}`
- Não propaga exceções para não quebrar o fluxo
- Loga erros detalhados para debugging

**FetcherService**:
- Retorna lista vazia `[]` em caso de erro
- Continua processamento de outras fontes mesmo se uma falhar

**DownloaderService**:
- Tenta múltiplas estratégias antes de falhar
- Valida arquivo criado mesmo se estratégia reportar erro

### Logging

**Níveis de Log**:
- `INFO`: Operações normais (fetch iniciado, download concluído)
- `WARNING`: Situações recuperáveis (formato 18 falhou, tentando próximo)
- `ERROR`: Erros que impedem operação (exceções não tratadas)

**Formato**:
```
2024-01-15 10:30:00 - app.services.downloader.service - INFO - Downloading abc123 with yt-dlp
2024-01-15 10:30:05 - app.services.downloader.service - WARNING - yt-dlp format 18 failed: [erro]
2024-01-15 10:30:10 - app.services.downloader.service - INFO - Merge: file found, size 5242880
```

---

## ⚡ Performance e Escalabilidade

### Características de Performance

#### 1. Async-First

- **FastAPI**: Framework assíncrono nativo
- **Endpoints Async**: Todos os endpoints são `async def`
- **I/O Não-Bloqueante**: Operações de rede e filesystem não bloqueiam thread principal

**Limitação**: `yt-dlp` é síncrono, mas execução é rápida para extração de metadados. Download é bloqueante, mas necessário para garantir conclusão.

#### 2. Stateless Design

- **Sem Estado Compartilhado**: Cada requisição é independente
- **Horizontalmente Escalável**: Múltiplas instâncias podem rodar em paralelo
- **Sem Sessões**: Não há necessidade de sticky sessions

#### 3. Cache de Configuração

- **Settings Cache**: `@lru_cache()` em `get_settings()`
- **Evita Reload**: Configurações carregadas uma vez na inicialização

#### 4. Verificação de Arquivo Existente

- **Evita Downloads Duplicados**: Verifica existência antes de baixar
- **I/O Rápido**: `os.path.exists()` e `os.path.getsize()` são operações rápidas

### Limitações e Considerações

#### 1. Download Síncrono

**Problema**: `POST /v1/download` aguarda conclusão, bloqueando conexão HTTP.

**Impacto**:
- Timeout do cliente (n8n) deve ser alto (ex: 10 minutos)
- Uma requisição de download longo pode ocupar worker do FastAPI

**Solução Futura**: Implementar jobs assíncronos com polling:
- `POST /v1/download` retorna `job_id` imediatamente
- Cliente faz polling em `GET /v1/jobs/{job_id}` até conclusão

#### 2. Processamento Sequencial

**Problema**: `POST /v1/n8n/process-sources` processa fontes sequencialmente.

**Impacto**: Se há muitas fontes, tempo de resposta pode ser alto.

**Solução Futura**: Processamento paralelo com `asyncio.gather()`:
```python
tasks = [fetcher.fetch_from_source_data(...) for source in sources]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

#### 3. Armazenamento Local

**Problema**: Arquivos salvos em filesystem local do container.

**Limitações**:
- Não escala horizontalmente (múltiplas instâncias não compartilham storage)
- Requer volume compartilhado para acesso do n8n
- Backup manual necessário

**Solução Futura**: Integração com storage remoto (S3, Supabase Storage):
- Upload automático após download
- URLs públicas para acesso
- Escalável e redundante

### Recomendações de Deploy

#### 1. Recursos do Container

**Mínimo**:
- CPU: 1 core
- RAM: 512MB
- Disco: 10GB (para downloads)

**Recomendado**:
- CPU: 2 cores
- RAM: 1GB
- Disco: 50GB+ (dependendo do volume de downloads)

#### 2. Configuração do n8n

**Timeout HTTP**:
- `POST /v1/download`: 600 segundos (10 minutos)
- Outros endpoints: 60 segundos

**Retry Logic**:
- Implementar retry com backoff exponencial
- Máximo 3 tentativas para downloads

#### 3. Monitoramento

**Métricas Recomendadas**:
- Tempo de resposta por endpoint
- Taxa de sucesso de downloads
- Uso de disco (armazenamento)
- Uso de CPU/RAM

**Alertas**:
- Disco > 80% de uso
- Taxa de erro > 10%
- Tempo de resposta > 30s (média)

---

## 🚀 Deploy e Configuração

### Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```bash
# Aplicação
PROJECT_NAME=Content Orchestrator
API_V1_STR=/v1

# Armazenamento
STORAGE_TYPE=local
LOCAL_STORAGE_PATH=downloads
DATA_PATH=data
```

### Docker Compose

```yaml
services:
  content-orchestrator:
    build: .
    container_name: content-orchestrator
    restart: always
    environment:
      - STORAGE_TYPE=local
      - LOCAL_STORAGE_PATH=/content-downloads
      - DATA_PATH=/app/data
    volumes:
      - ./downloads:/content-downloads
      - ./data:/app/data
    ports:
      - "127.0.0.1:8000:8000"
```

### Execução

```bash
# Build e start
docker compose up -d

# Logs
docker logs -f content-orchestrator

# Stop
docker compose down
```

### Documentação Interativa

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## 📚 Tecnologias Utilizadas

| Tecnologia | Versão | Propósito |
|------------|--------|-----------|
| **FastAPI** | ≥0.100.0 | Framework web assíncrono |
| **uvicorn** | Latest | Servidor ASGI |
| **pydantic** | ≥2.0 | Validação de dados |
| **pydantic-settings** | Latest | Gerenciamento de configurações |
| **yt-dlp** | ≥2023.12.30 | Extração e download de vídeos |
| **httpx** | Latest | Cliente HTTP assíncrono (futuro) |
| **tenacity** | Latest | Retry logic (futuro) |
| **ffmpeg** | Latest | Merge de vídeo/áudio (binário do sistema) |
| **Docker** | Latest | Containerização |
| **Python** | 3.11 | Linguagem de programação |

---

**Desenvolvido para integração com n8n e deploy em VPS com Docker.**
