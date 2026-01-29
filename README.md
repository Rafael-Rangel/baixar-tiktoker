# 🎬 TikTok Downloader API

API Flask completa para download de vídeos do TikTok e extração de metadados de canais, com múltiplas estratégias de bypass para contornar proteções anti-scraping.

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Arquitetura](#arquitetura)
3. [Endpoints](#endpoints)
4. [Métodos de Download](#métodos-de-download)
5. [Bypass de Proteções](#bypass-de-proteções)
6. [Problemas Enfrentados](#problemas-enfrentados)
7. [Soluções Implementadas](#soluções-implementadas)
8. [Instalação e Deploy](#instalação-e-deploy)
9. [Uso](#uso)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Visão Geral

Esta API foi desenvolvida para automatizar o download de vídeos do TikTok e a extração de metadados de canais, integrando-se com workflows do n8n. O projeto enfrenta desafios significativos devido às proteções anti-scraping do TikTok e de serviços terceirizados como o Urlebird.

### Funcionalidades Principais

- ✅ Download de vídeos individuais ou em lote
- ✅ Listagem dos últimos vídeos de múltiplos canais
- ✅ Extração completa de metadados (legenda, métricas, CDN links)
- ✅ Múltiplos métodos de download com fallback automático
- ✅ Bypass de Cloudflare e proteções anti-bot
- ✅ Suporte a cookies para autenticação
- ✅ API RESTful com CORS habilitado

---

## 🏗️ Arquitetura

### Stack Tecnológico

- **Framework**: Flask 3.0+
- **Linguagem**: Python 3.11
- **Containerização**: Docker + Docker Compose
- **Bibliotecas Principais**:
  - `tiktok-downloader`: Múltiplos serviços de download
  - `selenium` + `undetected-chromedriver`: Bypass anti-bot
  - `beautifulsoup4`: Parsing HTML
  - `requests`: Requisições HTTP

### Estrutura de Arquivos

```
tiktok-api/
├── app.py                 # Aplicação Flask principal
├── requirements.txt       # Dependências Python
├── Dockerfile            # Build da imagem Docker
├── docker-compose.yml    # Orquestração (na VPS)
├── cookies.txt          # Cookies para bypass (opcional)
└── README.md            # Este arquivo
```

---

## 🔌 Endpoints

### 1. `GET /health`

**Descrição**: Health check da API

**Resposta**:
```json
{
  "status": "ok",
  "message": "API funcionando",
  "tiktok_downloader_available": true,
  "urlebird_available": true,
  "selenium_available": true
}
```

---

### 2. `POST /download`

**Descrição**: Download de vídeo(s) do TikTok

#### Modo 1: Download Único (retorna MP4)

**Request**:
```json
{
  "url": "https://www.tiktok.com/@username/video/1234567890"
}
```

**Response**: Arquivo MP4 direto

#### Modo 2: Download Múltiplo (retorna JSON)

**Request**:
```json
{
  "urls": [
    "https://www.tiktok.com/@username/video/1234567890",
    "https://www.tiktok.com/@username/video/0987654321"
  ]
}
```

**Response**:
```json
{
  "total": 2,
  "success": 2,
  "failed": 0,
  "results": [
    {
      "url": "https://www.tiktok.com/@username/video/1234567890",
      "success": true,
      "filename": "video_1234567890.mp4",
      "file_path": "/app/downloads/video_1234567890.mp4",
      "file_size": 5242880,
      "file_size_mb": 5.0
    }
  ],
  "message": "2 de 2 vídeo(s) baixado(s) com sucesso"
}
```

---

### 3. `POST /channels/latest`

**Descrição**: Lista últimos vídeos e metadados de canais ou URLs

#### Modo 1: Por Lista de Canais

**Request**:
```json
{
  "channels": ["oprimorico", "username2"]
}
```

#### Modo 2: Por Lista de URLs

**Request**:
```json
{
  "urls": [
    "https://www.tiktok.com/@oprimorico",
    "https://urlebird.com/pt/user/oprimorico/"
  ]
}
```

**Response**:
```json
{
  "total": 1,
  "success": 1,
  "failed": 0,
  "results": [
    {
      "channel": "oprimorico",
      "success": true,
      "url": "https://www.tiktok.com/@oprimorico/video/1234567890",
      "urlebird_url": "https://urlebird.com/pt/video/oprimorico-1234567890/",
      "channel_data": {
        "followers": "1.2M",
        "total_likes": "50M",
        "videos_count": "500"
      },
      "video": {
        "caption": "Legenda do vídeo...",
        "posted_time": "2 horas atrás",
        "metrics": {
          "views": "100K",
          "likes": "10K",
          "comments": "500",
          "shares": "200"
        },
        "cdn_link": "https://cdn.tiktok.com/video/..."
      }
    }
  ],
  "message": "1 de 1 item(s) processado(s) com sucesso"
}
```

---

### 4. `GET /services`

**Descrição**: Lista serviços de download disponíveis

**Response**:
```json
{
  "services": [
    "Snaptik",
    "Tikmate",
    "SSStik",
    "TTDownloader",
    "TikWM",
    "MusicallyDown",
    "Tikdown",
    "Urlebird"
  ],
  "available": true,
  "urlebird_available": true,
  "selenium_available": true
}
```

---

## 🔄 Métodos de Download

A API utiliza uma estratégia de **fallback em cascata**, tentando múltiplos métodos até encontrar um que funcione.

### Ordem de Prioridade

1. **Snaptik** (via `tiktok-downloader`)
2. **Tikmate** (via `tiktok-downloader`)
3. **SSStik** (via `tiktok-downloader`)
4. **TTDownloader** (via `tiktok-downloader`)
5. **TikWM** (via `tiktok-downloader`)
6. **MusicallyDown** (via `tiktok-downloader`)
7. **Tikdown** (via `tiktok-downloader`)
8. **Urlebird** (web scraping - último recurso)

### Como Funciona

```python
# Para cada serviço na lista:
for service_name, service_func, requires_url, is_urlebird in services:
    try:
        if is_urlebird:
            # Método Urlebird (web scraping)
            video_file = download_via_urlebird(url)
        else:
            # Método tiktok-downloader
            video_file = service_func(url)
        
        if video_file:
            return video_file, None  # Sucesso!
    except Exception as e:
        continue  # Tenta próximo método

# Se todos falharem:
return None, "Todos os métodos falharam"
```

---

## 🛡️ Bypass de Proteções

### Problema: TikTok Anti-Scraping

O TikTok implementa várias proteções:
- ✅ Bloqueio de requisições automatizadas
- ✅ JavaScript complexo para carregar conteúdo
- ✅ Rate limiting por IP
- ✅ Verificação de User-Agent e headers

### Solução: Urlebird + Múltiplas Estratégias

#### 1. Urlebird como Intermediário

O **Urlebird** (`urlebird.com`) é um visualizador de perfis do TikTok que:
- Renderiza conteúdo de forma mais estática
- Facilita web scraping
- Não requer autenticação direta

**Fluxo**:
```
TikTok Profile → Urlebird → Nossa API → Cliente
```

#### 2. Web Scraping com Requests (Método 1)

**Estratégias**:
- Headers realistas (User-Agent, Accept, etc.)
- Session management (cookies persistentes)
- Delays entre requisições
- Múltiplas tentativas com diferentes referers

**Código**:
```python
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0...',
    'Accept': 'text/html,application/xhtml+xml...',
    'Accept-Language': 'pt-BR,pt;q=0.9...',
    'Referer': 'https://www.google.com/'
})

# Tentar obter cookies primeiro
session.get('https://urlebird.com/pt/')
time.sleep(1)

# Acessar perfil
response = session.get(f'https://urlebird.com/pt/user/{username}/')
```

**Problema**: Cloudflare bloqueia com `403 Forbidden`

---

#### 3. Selenium com Anti-Detecção (Método 2)

**Por que Selenium?**
- Navegador real = difícil de detectar como bot
- Executa JavaScript completo
- Suporta cookies e sessões reais

**Biblioteca**: `undetected-chromedriver`
- Remove propriedades que identificam automação
- Bypass de detecção de webdriver
- Simula navegador humano

**Configurações Anti-Detecção**:
```python
options = uc.ChromeOptions()
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_experimental_option('useAutomationExtension', False)

# Script para remover webdriver property
driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
    'source': '''
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    '''
})
```

**Problema Enfrentado**: 
- Erro `excludeSwitches` não suportado → **Corrigido removendo opção**
- Cloudflare ainda bloqueia mesmo com Selenium → **Solução: Cookies**

---

#### 4. Cookies para Bypass Cloudflare (Método 3)

**Como Funciona**:
1. Usuário acessa Urlebird manualmente no navegador
2. Exporta cookies da sessão válida
3. API carrega cookies antes de fazer requisições
4. Cloudflare reconhece como sessão legítima

**Implementação**:
```python
# Carregar cookies do arquivo
cookies_file = '/app/cookies.txt'
if os.path.exists(cookies_file):
    driver.get('https://urlebird.com/')
    time.sleep(2)
    
    # Ler cookies formato Netscape
    with open(cookies_file, 'r') as f:
        for line in f:
            # Parse formato: domain flag path secure expiration name value
            parts = line.split('\t')
            if 'urlebird.com' in parts[0]:
                driver.add_cookie({
                    'name': parts[5],
                    'value': parts[6],
                    'domain': parts[0],
                    'path': parts[2]
                })
```

**Formato do Arquivo** (Netscape):
```
.urlebird.com	TRUE	/	FALSE	1804213800	_ga	GA1.2.2141088358.1769644462
```

---

## 🚧 Problemas Enfrentados

### 1. Erro 403 Forbidden do Urlebird

**Sintoma**:
```
WARNING:__main__:403 Forbidden em https://urlebird.com/pt/user/oprimorico/
ERROR:__main__:Todas as estratégias falharam
```

**Causa**: Cloudflare detecta requisições automatizadas

**Soluções Tentadas**:
1. ✅ Headers mais realistas
2. ✅ Session management
3. ✅ Delays entre requisições
4. ✅ Múltiplos User-Agents
5. ✅ Selenium com anti-detecção
6. ✅ **Cookies de sessão válida** ← Mais eficaz

---

### 2. Erro Selenium: `excludeSwitches` não suportado

**Sintoma**:
```
ERROR: invalid argument: unrecognized chrome option: excludeSwitches
```

**Causa**: Versão do ChromeDriver não suporta essa opção

**Solução**: Removida opção `excludeSwitches` do código

---

### 3. Erro Selenium: `Binary Location Must be a String`

**Sintoma**:
```
TypeError: Binary Location Must be a String
```

**Causa**: Chrome não encontrado ou caminho inválido

**Solução**: 
- Detecção automática do Chrome
- Fallback para auto-detecção do undetected-chromedriver
- Dockerfile instala Chrome automaticamente

---

### 4. Rate Limiting e Bloqueios Temporários

**Sintoma**: Funciona às vezes, falha outras vezes

**Causa**: 
- Muitas requisições em pouco tempo
- IP sendo bloqueado temporariamente

**Soluções**:
- Delays entre requisições (`time.sleep()`)
- Rotação de métodos (fallback automático)
- Cookies válidos reduzem bloqueios

---

## ✅ Soluções Implementadas

### 1. Sistema de Fallback em Cascata

```python
def download_tiktok_video(url):
    services = [
        ('Snaptik', snaptik, True, False),
        ('Tikmate', Tikmate, False, False),
        # ... outros serviços
        ('Urlebird', None, False, True),  # Último recurso
    ]
    
    for service_name, service_func, requires_url, is_urlebird in services:
        try:
            if is_urlebird:
                return download_via_urlebird(url)
            else:
                return service_func(url)
        except:
            continue
    
    return None, "Todos os métodos falharam"
```

**Vantagem**: Alta taxa de sucesso mesmo se alguns serviços falharem

---

### 2. Extração Robusta de Metadados

**Dados Extraídos do Canal**:
- Seguidores
- Total de curtidas
- Quantidade de vídeos

**Dados Extraídos do Vídeo**:
- Legenda (caption)
- Data/hora de postagem
- Visualizações
- Curtidas
- Comentários
- Compartilhamentos
- Link CDN direto

**Implementação**:
```python
# Parsing HTML com BeautifulSoup
soup = BeautifulSoup(html, 'html.parser')

# Extrair métricas
views_elem = soup.find('span', class_='views')
likes_elem = soup.find('span', class_='likes')
# ... etc
```

---

### 3. Suporte a Múltiplos Formatos de Input

**Aceita**:
- URLs do TikTok: `https://www.tiktok.com/@user/video/123`
- URLs do Urlebird: `https://urlebird.com/pt/user/user/`
- Usernames simples: `oprimorico`

**Normalização Automática**:
```python
def validate_username(username):
    # Remove @, espaços, etc.
    username = username.strip().lstrip('@')
    return username if re.match(r'^[\w.]+$', username) else None
```

---

### 4. Gerenciamento de Arquivos Temporários

**Problema**: Arquivos baixados ocupam espaço

**Solução**:
- Arquivos únicos: Removidos após envio
- Arquivos múltiplos: Mantidos para download manual
- Limpeza automática após timeout

```python
def remove_file(response):
    time.sleep(1)  # Aguardar download completar
    if os.path.exists(video_file):
        os.remove(video_file)
    return response

response.call_on_close(lambda: remove_file(None))
```

---

## 🚀 Instalação e Deploy

### Desenvolvimento Local

```bash
# 1. Clonar repositório
git clone https://github.com/Rafael-Rangel/baixar-tiktoker.git
cd baixar-tiktoker

# 2. Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Rodar aplicação
python app.py
```

### Deploy na VPS com Docker

```bash
# 1. Clonar na VPS
cd ~
git clone https://github.com/Rafael-Rangel/baixar-tiktoker.git tiktok-downloader-api

# 2. Build da imagem
cd ~
docker compose build tiktok-downloader-api

# 3. Iniciar container
docker compose up -d tiktok-downloader-api

# 4. Ver logs
docker logs -f tiktok-downloader-api
```

### Configurar Cookies (Opcional mas Recomendado)

```bash
# 1. Exportar cookies do navegador (formato Netscape)
# Salvar como cookies.txt

# 2. Copiar para container
docker cp cookies.txt tiktok-downloader-api:/app/cookies.txt

# 3. Reiniciar
docker compose restart tiktok-downloader-api
```

---

## 📖 Uso

### Exemplo 1: Download Único

```bash
curl -X POST http://localhost:5000/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.tiktok.com/@user/video/123"}' \
  --output video.mp4
```

### Exemplo 2: Listar Últimos Vídeos

```bash
curl -X POST http://localhost:5000/channels/latest \
  -H "Content-Type: application/json" \
  -d '{"channels": ["oprimorico"]}' | jq .
```

### Exemplo 3: Integração n8n

**Workflow**:
1. **HTTP Request** → `POST /channels/latest` com lista de canais
2. **Split In Batches** → Processar cada resultado
3. **HTTP Request** → `POST /download` com URL do vídeo
4. **Save File** → Salvar vídeo baixado

**Body do n8n**:
```json
{
  "channels": ["oprimorico", "username2"]
}
```

---

## 🔧 Troubleshooting

### Problema: Todos os métodos falham

**Soluções**:
1. Verificar se serviços estão online
2. Atualizar cookies do Urlebird
3. Verificar logs: `docker logs tiktok-downloader-api`
4. Testar manualmente: `curl http://localhost:5000/health`

---

### Problema: Selenium não funciona

**Verificar**:
```bash
# Chrome instalado?
docker exec tiktok-downloader-api google-chrome --version

# Selenium instalado?
docker exec tiktok-downloader-api pip list | grep selenium
```

**Solução**: Rebuild da imagem
```bash
docker compose build --no-cache tiktok-downloader-api
```

---

### Problema: Cookies não carregam

**Verificar**:
```bash
# Arquivo existe?
docker exec tiktok-downloader-api ls -la /app/cookies.txt

# Formato correto?
docker exec tiktok-downloader-api head -5 /app/cookies.txt
```

**Solução**: Verificar formato Netscape e domínio `.urlebird.com`

---

### Problema: 403 Forbidden persistente

**Soluções**:
1. ✅ Atualizar cookies (podem ter expirado)
2. ✅ Aumentar delays entre requisições
3. ✅ Usar Selenium ao invés de requests
4. ✅ Verificar se IP não está bloqueado
5. ✅ Tentar em horários diferentes (menos tráfego)

---

## 📊 Status Atual

### ✅ Funcionando

- Download via `tiktok-downloader` (métodos 1-7)
- Extração de metadados básicos
- API RESTful completa
- Health checks
- Suporte a múltiplos formatos de input

### ⚠️ Parcialmente Funcionando

- Urlebird com requests: **Bloqueado por Cloudflare (403)**
- Urlebird com Selenium: **Funciona com cookies válidos**

### 🔄 Em Melhoria

- Rotação automática de cookies
- Cache de sessões
- Retry inteligente com backoff exponencial
- Monitoramento de taxa de sucesso por método

---

## 🎯 Próximos Passos

1. **Proxy Rotation**: Rotacionar IPs para evitar bloqueios
2. **Cookie Management**: Sistema automático de renovação de cookies
3. **Rate Limiting**: Implementar delays inteligentes baseados em resposta
4. **Caching**: Cache de metadados para reduzir requisições
5. **Monitoring**: Dashboard de saúde dos serviços

---

## 📝 Notas Importantes

### Limitações

- ⚠️ Dependência de serviços terceiros (podem mudar/parar)
- ⚠️ Cookies expiram e precisam ser atualizados
- ⚠️ Rate limiting pode ocorrer com muitas requisições
- ⚠️ Cloudflare pode bloquear IPs temporariamente

### Boas Práticas

- ✅ Sempre ter fallback para múltiplos métodos
- ✅ Implementar retry com delays
- ✅ Monitorar logs regularmente
- ✅ Manter cookies atualizados
- ✅ Não fazer muitas requisições simultâneas

---

## 📄 Licença

Este projeto é de uso pessoal/educacional. Respeite os Termos de Serviço do TikTok e dos serviços utilizados.

---

## 👤 Autor

Desenvolvido para automação de workflows no n8n.

**Repositório**: https://github.com/Rafael-Rangel/baixar-tiktoker

---**Última Atualização**: Janeiro 2026
