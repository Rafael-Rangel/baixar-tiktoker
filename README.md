# Content Orchestrator - Arquitetura Funcional Completa

## 📋 Índice

1. [Visão Geral da Arquitetura](#visão-geral-da-arquitetura)
2. [Arquitetura do Sistema de Download](#arquitetura-do-sistema-de-download)
3. [Camadas do Sistema](#camadas-do-sistema)
4. [Fluxo de Dados e Processamento](#fluxo-de-dados-e-processamento)
5. [Componentes Principais](#componentes-principais)
6. [Estratégias de Download Detalhadas](#estratégias-de-download-detalhadas)
7. [Estrutura de Armazenamento](#estrutura-de-armazenamento)
8. [Integração com n8n](#integração-com-n8n)
9. [API Endpoints - Especificação Técnica](#api-endpoints---especificação-técnica)
10. [Tratamento de Erros e Resiliência](#tratamento-de-erros-e-resiliência)
11. [Performance e Escalabilidade](#performance-e-escalabilidade)
12. [Deploy e Configuração](#deploy-e-configuração)

---

## 🏗️ Visão Geral da Arquitetura

O **Content Orchestrator** é uma API REST assíncrona construída com **FastAPI** que atua como uma camada de orquestração entre workflows do **n8n** e fontes de conteúdo de múltiplas plataformas (YouTube, Instagram, TikTok). O sistema é **stateless** e **stateless-first**, projetado para processar requisições de forma independente, sem manter estado entre chamadas.

### Princípios Arquiteturais

- **Stateless Design**: Cada requisição é independente; não há sessões ou estado compartilhado
- **Service-Oriented**: Lógica de negócio isolada em serviços especializados
- **Async-First**: Uso extensivo de `async/await` para I/O não-bloqueante
- **Fail-Safe**: Múltiplas estratégias de fallback para operações críticas
- **Container-Ready**: Otimizado para execução em containers Docker
- **Multi-Strategy Download**: Sistema de download em cascata com fallback automático

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
│  │  - /v1/download   (Download de vídeos)                    │  │
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
│  │  └──────────────────┘  └────────┬─────────┘            │  │
│  │                                  │                        │  │
│  │                          ┌───────▼────────┐            │  │
│  │                          │ SeleniumService │            │  │
│  │                          │ (Fallback)      │            │  │
│  │                          └────────────────┘            │  │
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
│  │   yt-dlp     │  │   ffmpeg     │  │  Chrome      │         │
│  │  (Library)   │  │  (Binary)    │  │  (Selenium)  │         │
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

## 🎯 Arquitetura do Sistema de Download

O sistema de download implementa uma **arquitetura em cascata com múltiplas camadas de fallback**, garantindo máxima taxa de sucesso mesmo quando plataformas implementam medidas anti-bot.

### Estratégia de Download em Cascata

```
┌─────────────────────────────────────────────────────────────┐
│  DownloaderService.download_video()                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  ESTRATÉGIA 1: yt-dlp (Múltiplas Tentativas)              │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Tentativa 1.1: Format 18 (sem cookies)              │ │
│  │ Tentativa 1.2: bestvideo+bestaudio + merge         │ │
│  │ Tentativa 1.3: best (formato único)                 │ │
│  │ Fallback URL: watch?v=ID (se shorts falhar)          │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Se todas falharem com erro de bot detection
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  ESTRATÉGIA 2: Selenium Fallback (Chrome Headless)       │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ 1. Inicializar Chrome com anti-detecção             │ │
│  │ 2. Carregar cookies existentes de /app/data/        │ │
│  │ 3. Estabelecer sessão na homepage do YouTube        │ │
│  │ 4. Navegar até o vídeo com interações humanas       │ │
│  │ 5. Extrair cookies atualizados do navegador        │ │
│  │ 6. Tentar download com yt-dlp usando cookies      │ │
│  │    - Estratégia 2.1: bestvideo+bestaudio           │ │
│  │    - Estratégia 2.2: best format                   │ │
│  │    - Estratégia 2.3: format 18                     │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Se todas falharem
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Retorno de Erro Detalhado                                 │
│  {                                                          │
│    "status": "failed",                                      │
│    "error": "All download strategies failed..."            │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
```

### Componentes do Sistema de Download

#### 1. DownloaderService (`app/services/downloader/service.py`)

**Responsabilidade Principal**: Orquestrar todas as estratégias de download e gerenciar o fluxo de fallback.

**Métodos Principais**:

- `download_video()`: Método principal assíncrono que coordena todo o processo
- `_download_with_ytdlp_library()`: Implementa estratégias primárias com yt-dlp
- `_get_video_title()`: Extrai título do vídeo para nomear arquivo
- `_sanitize_filename()`: Normaliza nomes de arquivo
- `_resolve_cookies_path()`: Localiza arquivo de cookies

**Fluxo de Execução**:

1. **Resolução de Caminho**: Determina onde salvar o arquivo baseado em `group_name` e `source_name`
2. **Busca de Título**: Tenta obter título do vídeo para nomear arquivo
3. **Verificação de Existência**: Verifica se arquivo já existe (evita downloads duplicados)
4. **Execução de Download**: Chama `_download_with_ytdlp_library()` com múltiplas estratégias
5. **Detecção de Bot**: Se todas as estratégias falharem com erro de bot detection, aciona Selenium
6. **Validação Final**: Verifica se arquivo foi criado e tem tamanho > 1KB

#### 2. SeleniumDownloaderService (`app/services/downloader/selenium_service.py`)

**Responsabilidade**: Implementar fallback usando navegador real quando yt-dlp é detectado como bot.

**Arquitetura Interna**:

```
SeleniumDownloaderService
├── _init_driver()
│   └── Configura Chrome headless com anti-detecção avançada
│
├── _get_chrome_options()
│   └── Define flags e preferências para parecer navegador real
│
├── _load_existing_cookies()
│   └── Carrega cookies de /app/data/cookies.txt no navegador
│
├── _extract_cookies_from_browser()
│   ├── 1. Inicializa driver Chrome
│   ├── 2. Carrega cookies existentes
│   ├── 3. Navega para homepage do YouTube
│   ├── 4. Simula interações humanas (scroll, mouse)
│   ├── 5. Navega até o vídeo
│   ├── 6. Aguarda carregamento completo
│   ├── 7. Simula mais interações (scroll, play)
│   ├── 8. Extrai cookies atualizados
│   └── 9. Salva cookies em arquivo temporário (formato Netscape)
│
└── download_video()
    ├── 1. Extrai cookies do navegador (em thread separada)
    ├── 2. Valida arquivo de cookies
    ├── 3. Tenta múltiplas estratégias com yt-dlp
    │   ├── Estratégia 1: bestvideo+bestaudio
    │   ├── Estratégia 2: best format
    │   └── Estratégia 3: format 18
    └── 4. Retorna resultado ou erro detalhado
```

**Técnicas Anti-Detecção Implementadas**:

1. **Flags do Chrome**:
   - `--disable-blink-features=AutomationControlled`
   - `--excludeSwitches=enable-automation`
   - `--disable-features=IsolateOrigins,site-per-process`
   - User-Agent atualizado (Chrome 131.0.0.0)

2. **Scripts JavaScript**:
   - Remove `navigator.webdriver`
   - Define `window.chrome.runtime`
   - Mascara propriedades do navegador (plugins, languages, permissions)
   - Mascara WebGL para evitar fingerprinting

3. **Simulação de Comportamento Humano**:
   - Scroll gradual em múltiplas posições
   - Movimento de mouse simulado
   - Tempos de espera variáveis
   - Interação com player de vídeo

4. **Gerenciamento de Cookies**:
   - Carrega cookies existentes antes de navegar
   - Estabelece sessão na homepage primeiro
   - Extrai cookies atualizados após interações
   - Valida formato Netscape antes de usar

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
│ 3. DOWNLOAD (Download Síncrono com Fallback Automático)      │
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
│   Estratégia 1.1: Format 18 (YouTube, sem cookies)           │
│   Estratégia 1.2: bestvideo+bestaudio + merge (com ffmpeg)     │
│   Estratégia 1.3: best (formato único)                        │
│   Fallback URL: watch?v=ID (se shorts falhar)                   │
│                                                                 │
│ ↓ Se todas falharem com erro de bot detection:                │
│   SeleniumDownloaderService.download_video()                  │
│   - Inicializa Chrome headless com anti-detecção              │
│   - Carrega cookies de /app/data/cookies.txt                  │
│   - Estabelece sessão na homepage do YouTube                  │
│   - Navega até o vídeo com interações humanas                 │
│   - Extrai cookies atualizados                                │
│   - Tenta download com yt-dlp usando cookies                 │
│     • Estratégia 2.1: bestvideo+bestaudio                     │
│     • Estratégia 2.2: best format                             │
│     • Estratégia 2.3: format 18                               │
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
   - Se todas falharem com erro de bot detection, aciona `SeleniumDownloaderService`
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
4. `/app/data/cookies.txt` (caminho absoluto no container Docker)

**Uso**: Se encontrado, adiciona `"cookiefile": path` nas opções do yt-dlp

### SeleniumDownloaderService

**Localização**: `app/services/downloader/selenium_service.py`

**Responsabilidade**: Implementar fallback usando navegador real quando yt-dlp é detectado como bot.

**Dependências**:
- `selenium`: Biblioteca para automação de navegador
- `webdriver-manager`: Gerenciamento automático de ChromeDriver
- `yt-dlp`: Usado após extrair cookies do navegador
- `Chrome/Chromium`: Navegador instalado no container Docker

**Métodos Principais**:

#### `_init_driver()`
```python
def _init_driver(self) -> webdriver.Chrome
```

**Funcionalidade**: Inicializa instância do Chrome WebDriver com configurações anti-detecção.

**Processo**:
1. Obtém opções do Chrome via `_get_chrome_options()`
2. Instala ChromeDriver automaticamente via `ChromeDriverManager`
3. Cria instância do WebDriver
4. Injeta scripts JavaScript para remover indicadores de automação
5. Retorna driver configurado

#### `_get_chrome_options()`
```python
def _get_chrome_options(self) -> Options
```

**Flags Anti-Detecção**:
- `--headless=new`: Modo headless moderno do Chrome
- `--disable-blink-features=AutomationControlled`: Remove indicadores de automação
- `--excludeSwitches=enable-automation`: Remove switch de automação
- `--disable-features=IsolateOrigins,site-per-process`: Melhora compatibilidade
- User-Agent atualizado: Chrome 131.0.0.0
- Preferências de perfil configuradas para parecer navegador real

**Scripts JavaScript Injetados**:
- Remove `navigator.webdriver`
- Define `window.chrome.runtime`
- Mascara `navigator.plugins`
- Define `navigator.languages`
- Mascara WebGL para evitar fingerprinting

#### `_load_existing_cookies()`
```python
def _load_existing_cookies(self) -> bool
```

**Funcionalidade**: Carrega cookies existentes do arquivo `/app/data/cookies.txt` no navegador.

**Processo**:
1. Localiza arquivo de cookies usando `DownloaderService._resolve_cookies_path()`
2. Navega para `https://www.youtube.com` para estabelecer domínio
3. Lê arquivo no formato Netscape
4. Converte cada cookie para formato do Selenium
5. Adiciona cookies ao navegador via `driver.add_cookie()`
6. Retorna `True` se pelo menos um cookie foi carregado

**Formato Netscape**:
```
domain    flag    path    secure    expiration    name    value
.youtube.com    TRUE    /    TRUE    1735689600    VISITOR_INFO1_LIVE    abc123
```

#### `_extract_cookies_from_browser()`
```python
def _extract_cookies_from_browser(self, video_url: str) -> Optional[str]
```

**Funcionalidade**: Extrai cookies atualizados do navegador após estabelecer sessão e navegar até o vídeo.

**Processo Detalhado**:

1. **Inicialização**:
   - Inicializa driver Chrome via `_init_driver()`
   - Carrega cookies existentes via `_load_existing_cookies()`

2. **Estabelecimento de Sessão**:
   - Navega para `https://www.youtube.com`
   - Aguarda 5 segundos para página carregar
   - Simula interações humanas (scroll múltiplo, movimento de mouse)
   - Aguarda mais 5 segundos para sessão se estabelecer

3. **Navegação até o Vídeo**:
   - Navega para URL do vídeo
   - Aguarda 3 segundos
   - Verifica se há bloqueio de bot (não desiste imediatamente)
   - Aguarda elemento `<video>` aparecer (timeout: 30s)

4. **Interações com a Página**:
   - Aguarda 10 segundos para página carregar completamente
   - Faz scroll gradual em múltiplas posições (5 vezes)
   - Simula movimento de mouse
   - Tenta interagir com player de vídeo (play, click)
   - Aguarda mais 5 segundos para cookies serem atualizados

5. **Extração de Cookies**:
   - Extrai todos os cookies via `driver.get_cookies()`
   - Loga cookies importantes (`__Secure-3PSID`, `__Secure-3PAPISID`, etc.)
   - Cria arquivo temporário no formato Netscape
   - Escreve cookies no arquivo
   - Valida arquivo criado (tamanho > 100 bytes)
   - Retorna caminho do arquivo temporário

6. **Limpeza**:
   - Fecha driver via `driver.quit()`
   - Retorna `None` em caso de erro

#### `download_video()`
```python
async def download_video(
    self,
    video_url: str,
    output_path: str,
    external_video_id: Optional[str] = None
) -> dict
```

**Funcionalidade**: Orquestra o processo completo de download usando Selenium como fallback.

**Processo**:

1. **Extração de Cookies**:
   - Executa `_extract_cookies_from_browser()` em thread separada (para não bloquear asyncio)
   - Valida arquivo de cookies criado
   - Lê e valida conteúdo do arquivo (número de cookies, tamanho)

2. **Múltiplas Estratégias de Download**:
   - Tenta 3 estratégias diferentes com yt-dlp usando cookies extraídos:
     - **Estratégia 1**: `bestvideo+bestaudio` com headers HTTP customizados
     - **Estratégia 2**: `best` format com user-agent iOS
     - **Estratégia 3**: `format 18` (fallback de qualidade)
   - Para cada estratégia:
     - Executa yt-dlp com cookies do navegador
     - Verifica se arquivo foi criado (> 1KB)
     - Verifica extensões alternativas (`.webm`, `.mkv`, `.m4a`)
     - Se bem-sucedido, retorna imediatamente

3. **Limpeza**:
   - Remove arquivo temporário de cookies
   - Garante que driver está fechado
   - Retorna resultado ou erro detalhado

---

## 🎯 Estratégias de Download Detalhadas

### Estratégia 1: yt-dlp Direto (Primária)

**Objetivo**: Download rápido usando yt-dlp sem necessidade de navegador.

**Vantagens**:
- Rápido e eficiente
- Baixo consumo de recursos
- Não requer Chrome/Selenium

**Desvantagens**:
- Pode ser detectado como bot pelo YouTube
- Requer cookies válidos para alguns vídeos

**Estratégias em Cascata**:

1. **Format 18**:
   - Formato MP4 de baixa qualidade (360p)
   - Sem necessidade de cookies
   - Rápido mas qualidade limitada

2. **bestvideo+bestaudio + merge**:
   - Melhor qualidade disponível
   - Requer `ffmpeg` para merge
   - Usa cookies se disponível

3. **best (formato único)**:
   - Formato único de melhor qualidade
   - Não requer merge
   - Pode não ser MP4

**Fallback de URL**:
- Se URL `/shorts/ID` falhar, tenta `watch?v=ID`

### Estratégia 2: Selenium Fallback (Secundária)

**Objetivo**: Contornar detecção de bot usando navegador real.

**Quando é Acionada**:
- Todas as estratégias do yt-dlp falharam
- Erro contém palavras-chave: "bot", "sign in", "authentication", "confirm you're not a bot"
- Plataforma é YouTube

**Vantagens**:
- Contorna detecção de bot
- Estabelece sessão real no YouTube
- Extrai cookies atualizados e válidos

**Desvantagens**:
- Mais lento (requer inicialização do navegador)
- Maior consumo de recursos (RAM, CPU)
- Requer Chrome/Chromium instalado

**Processo Completo**:

1. **Inicialização do Navegador** (5-10s):
   - Inicializa Chrome headless com anti-detecção
   - Injeta scripts para remover indicadores de automação

2. **Carregamento de Cookies** (2-5s):
   - Carrega cookies existentes de `/app/data/cookies.txt`
   - Navega para homepage do YouTube

3. **Estabelecimento de Sessão** (10-15s):
   - Simula interações humanas na homepage
   - Aguarda sessão se estabelecer

4. **Navegação até o Vídeo** (5-10s):
   - Navega para URL do vídeo
   - Aguarda página carregar completamente
   - Verifica se não há bloqueio

5. **Interações com a Página** (15-20s):
   - Scroll gradual em múltiplas posições
   - Simulação de movimento de mouse
   - Interação com player de vídeo
   - Aguarda cookies serem atualizados

6. **Extração de Cookies** (1-2s):
   - Extrai todos os cookies do navegador
   - Salva em arquivo temporário (formato Netscape)

7. **Download com yt-dlp** (variável):
   - Usa cookies extraídos com yt-dlp
   - Tenta múltiplas estratégias
   - Valida arquivo criado

**Tempo Total Estimado**: 40-60 segundos (sem contar tempo de download)

**Estratégias de Download com Cookies**:

1. **bestvideo+bestaudio**:
   - Headers HTTP customizados
   - User-Agent: Chrome 131.0.0.0
   - Player clients: ios, android, mweb, web

2. **best format**:
   - User-Agent: iOS Safari
   - Player clients: ios, android

3. **format 18**:
   - Formato de baixa qualidade
   - Fallback final

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

### Arquivos de Cookies

**Localização**: `/app/data/cookies.txt` (no container Docker)

**Formato**: Netscape HTTP Cookie File

**Uso**:
- Carregado pelo `DownloaderService` para estratégias primárias
- Carregado pelo `SeleniumDownloaderService` antes de estabelecer sessão
- Atualizado automaticamente pelo Selenium após interações

**Importante**: Cookies devem ser exportados de um navegador real com sessão ativa no YouTube.

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
   │  Timeout: 600 segundos (10 minutos)
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

**Descrição**: Faz download de um vídeo. **Aguarda conclusão antes de retornar** (síncrono). Implementa fallback automático para Selenium se yt-dlp falhar por detecção de bot.

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
  "detail": "Falha ao baixar o vídeo: All download strategies failed. Errors: ..."
}
```

**Comportamento**:
- Aguarda conclusão do download (não retorna imediatamente)
- Tenta múltiplas estratégias de download em cascata:
  1. yt-dlp direto (format 18, merge, best)
  2. Selenium fallback (se erro de bot detection)
- Verifica se arquivo foi criado e tem tamanho > 1KB
- Retorna caminho absoluto do arquivo

**Timeout**: Depende do timeout do cliente HTTP (n8n). Recomenda-se configurar timeout alto (ex: 10 minutos) para permitir tempo suficiente para Selenium fallback.

**Fluxo de Fallback**:
1. Tenta todas as estratégias do yt-dlp
2. Se todas falharem com erro de bot detection → aciona Selenium
3. Selenium estabelece sessão e extrai cookies
4. Tenta novamente com yt-dlp usando cookies do navegador
5. Se ainda falhar → retorna erro detalhado

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

#### 1. Múltiplas Estratégias de Download em Cascata

O `DownloaderService` implementa **fallback em cascata**:

**Nível 1 - yt-dlp Direto**:
- Se estratégia 1 falhar → tenta estratégia 2
- Se estratégia 2 falhar → tenta estratégia 3
- Se estratégia 3 falhar → tenta fallback de URL

**Nível 2 - Selenium Fallback**:
- Se todas as estratégias do nível 1 falharem com erro de bot detection → aciona Selenium
- Selenium estabelece sessão real e extrai cookies
- Tenta novamente com yt-dlp usando cookies do navegador
- Múltiplas estratégias também no nível 2

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

#### 5. Validação de Cookies

No Selenium fallback:
- Valida arquivo de cookies antes de usar
- Verifica tamanho e número de cookies
- Loga cookies importantes para debug
- Continua mesmo se alguns cookies falharem ao carregar

#### 6. Tratamento de Erros por Camada

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
- Aciona Selenium fallback automaticamente quando apropriado

**SeleniumDownloaderService**:
- Valida cada etapa do processo
- Continua mesmo se algumas interações falharem
- Limpa recursos (driver, arquivos temporários) mesmo em caso de erro

### Logging

**Níveis de Log**:
- `INFO`: Operações normais (fetch iniciado, download concluído)
- `WARNING`: Situações recuperáveis (formato 18 falhou, tentando próximo)
- `ERROR`: Erros que impedem operação (exceções não tratadas)
- `DEBUG`: Informações detalhadas (cookies extraídos, estratégias tentadas)

**Formato**:
```
2024-01-15 10:30:00 - app.services.downloader.service - INFO - Downloading abc123 with yt-dlp
2024-01-15 10:30:05 - app.services.downloader.service - WARNING - yt-dlp format 18 failed: [erro]
2024-01-15 10:30:10 - app.services.downloader.service - INFO - yt-dlp failed with bot detection, trying Selenium fallback...
2024-01-15 10:30:15 - app.services.downloader.selenium_service - INFO - Selenium: Starting download fallback for abc123
2024-01-15 10:30:20 - app.services.downloader.selenium_service - INFO - Selenium: Loaded 12 cookies from file
2024-01-15 10:30:35 - app.services.downloader.selenium_service - INFO - Selenium: Extracted 17 cookies to /tmp/tmpXXX.txt
2024-01-15 10:30:40 - app.services.downloader.selenium_service - INFO - Selenium: Download successful with bestvideo+bestaudio!
```

---

## ⚡ Performance e Escalabilidade

### Características de Performance

#### 1. Async-First

- **FastAPI**: Framework assíncrono nativo
- **Endpoints Async**: Todos os endpoints são `async def`
- **I/O Não-Bloqueante**: Operações de rede e filesystem não bloqueiam thread principal

**Limitação**: `yt-dlp` e Selenium são síncronos, mas execução é rápida para extração de metadados. Download é bloqueante, mas necessário para garantir conclusão. Selenium é executado em thread separada via `run_in_executor()` para não bloquear asyncio.

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

#### 5. Selenium Otimizado

- **Headless Mode**: Chrome headless consome menos recursos que modo gráfico
- **Thread Pool**: Execução em thread separada não bloqueia outras requisições
- **Cleanup Automático**: Driver e arquivos temporários são limpos automaticamente

### Limitações e Considerações

#### 1. Download Síncrono

**Problema**: `POST /v1/download` aguarda conclusão, bloqueando conexão HTTP.

**Impacto**:
- Timeout do cliente (n8n) deve ser alto (ex: 10 minutos)
- Uma requisição de download longo pode ocupar worker do FastAPI
- Selenium fallback adiciona 40-60 segundos ao tempo de resposta

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

#### 4. Recursos do Selenium

**Problema**: Chrome headless consome recursos significativos (RAM, CPU).

**Impacto**:
- Cada requisição que aciona Selenium consome ~200-300MB RAM
- Múltiplas requisições simultâneas podem esgotar recursos

**Solução Atual**: Execução sequencial (uma requisição por vez)
**Solução Futura**: Pool de instâncias Selenium reutilizáveis

### Recomendações de Deploy

#### 1. Recursos do Container

**Mínimo**:
- CPU: 1 core
- RAM: 1GB (para suportar Selenium)
- Disco: 10GB (para downloads)

**Recomendado**:
- CPU: 2 cores
- RAM: 2GB (para múltiplas requisições simultâneas com Selenium)
- Disco: 50GB+ (dependendo do volume de downloads)

#### 2. Configuração do n8n

**Timeout HTTP**:
- `POST /v1/download`: 600 segundos (10 minutos) - necessário para Selenium fallback
- Outros endpoints: 60 segundos

**Retry Logic**:
- Implementar retry com backoff exponencial
- Máximo 3 tentativas para downloads
- Não fazer retry imediato se erro for de bot detection (aguardar alguns minutos)

#### 3. Monitoramento

**Métricas Recomendadas**:
- Tempo de resposta por endpoint
- Taxa de sucesso de downloads
- Taxa de uso do Selenium fallback
- Uso de disco (armazenamento)
- Uso de CPU/RAM (especialmente durante Selenium)

**Alertas**:
- Disco > 80% de uso
- Taxa de erro > 10%
- Tempo de resposta > 60s (média)
- Uso de RAM > 90% (pode indicar vazamento no Selenium)

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
    # Recursos recomendados
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### Dependências do Sistema (Dockerfile)

O Dockerfile instala automaticamente:

**Binários do Sistema**:
- `ffmpeg`: Para merge de vídeo/áudio
- `google-chrome-stable`: Para Selenium fallback
- Bibliotecas do sistema necessárias para Chrome

**Bibliotecas Python**:
- `fastapi`: Framework web
- `uvicorn`: Servidor ASGI
- `yt-dlp`: Download de vídeos
- `selenium`: Automação de navegador
- `webdriver-manager`: Gerenciamento de ChromeDriver

### Execução

```bash
# Build e start
docker compose up -d

# Logs
docker logs -f content-orchestrator

# Logs filtrados (Selenium)
docker logs -f content-orchestrator | grep -E "(Selenium|bot|fallback)"

# Stop
docker compose down
```

### Configuração de Cookies

Para melhorar taxa de sucesso, configure cookies do YouTube:

1. **Exportar Cookies**:
   - Use extensão do navegador (ex: "Get cookies.txt LOCALLY")
   - Ou use `yt-dlp --cookies-from-browser chrome`
   - Exporte cookies de uma sessão ativa no YouTube

2. **Colocar no Container**:
   ```bash
   # Copiar para pasta data/
   cp cookies.txt ./data/cookies.txt
   
   # Ou montar volume
   volumes:
     - ./data:/app/data
   ```

3. **Permissões**:
   ```bash
   chmod 644 ./data/cookies.txt
   chown 1000:1000 ./data/cookies.txt  # Se necessário
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
| **selenium** | ≥4.15.0 | Automação de navegador (fallback) |
| **webdriver-manager** | ≥4.0.0 | Gerenciamento de ChromeDriver |
| **httpx** | Latest | Cliente HTTP assíncrono (futuro) |
| **tenacity** | Latest | Retry logic (futuro) |
| **ffmpeg** | Latest | Merge de vídeo/áudio (binário do sistema) |
| **google-chrome-stable** | Latest | Navegador para Selenium (binário do sistema) |
| **Docker** | Latest | Containerização |
| **Python** | 3.11 | Linguagem de programação |

---

## 🔍 Detalhes Técnicos da Arquitetura de Download

### Fluxo de Decisão para Fallback

```
┌─────────────────────────────────────────────────────────┐
│ download_video() chamado                                │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Verifica arquivo existente                              │
│ Se existe → retorna imediatamente                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ _download_with_ytdlp_library()                         │
│                                                         │
│ Para cada URL (original, fallback):                     │
│   ├─ Tentativa 1: Format 18                           │
│   ├─ Tentativa 2: bestvideo+bestaudio                  │
│   └─ Tentativa 3: best                                 │
│                                                         │
│ Coleta erros de cada tentativa                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Todas as tentativas falharam?                          │
│                                                         │
│ Sim → Verifica tipo de erro                            │
│   ├─ Erro contém "bot", "sign in", "authentication"?  │
│   ├─ Plataforma é YouTube?                             │
│   └─ Sim para ambos → Aciona Selenium                 │
│                                                         │
│ Não → Retorna erro                                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ SeleniumDownloaderService.download_video()              │
│                                                         │
│ 1. Extrai cookies do navegador                         │
│ 2. Valida cookies                                      │
│ 3. Tenta download com yt-dlp usando cookies           │
│    ├─ Estratégia 1: bestvideo+bestaudio               │
│    ├─ Estratégia 2: best                              │
│    └─ Estratégia 3: format 18                          │
│                                                         │
│ Se sucesso → Retorna resultado                         │
│ Se falha → Retorna erro detalhado                      │
└─────────────────────────────────────────────────────────┘
```

### Gerenciamento de Recursos no Selenium

**Inicialização**:
- Driver criado apenas quando necessário
- Configurações anti-detecção aplicadas imediatamente
- Cookies carregados antes de navegar

**Execução**:
- Operações síncronas executadas em thread separada
- Não bloqueia event loop do asyncio
- Timeouts configurados para evitar travamentos

**Limpeza**:
- Driver sempre fechado via `driver.quit()`
- Arquivos temporários sempre removidos
- Exceções capturadas para garantir limpeza

### Otimizações Implementadas

1. **Cache de Cookies**: Cookies extraídos são reutilizados para múltiplas tentativas
2. **Validação Precoce**: Verifica arquivo existente antes de qualquer download
3. **Fallback Inteligente**: Só aciona Selenium se erro for de bot detection
4. **Thread Pool**: Selenium executa em thread separada para não bloquear
5. **Cleanup Automático**: Recursos sempre liberados mesmo em caso de erro

---

**Desenvolvido para integração com n8n e deploy em VPS com Docker. Arquitetura projetada para máxima resiliência e taxa de sucesso em downloads, mesmo quando plataformas implementam medidas anti-bot.**
