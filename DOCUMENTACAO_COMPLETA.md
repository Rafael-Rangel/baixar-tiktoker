# 🎬 TikTok Downloader API - Documentação Completa

**Documentação técnica completa do projeto**: Como funciona o download, como estamos contornando problemas, o que estamos enfrentando para listar vídeos, e todas as soluções implementadas.

---

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Arquitetura do Sistema](#arquitetura-do-sistema)
3. [Como Funciona o Download](#como-funciona-o-download)
4. [Como Funciona a Listagem de Vídeos](#como-funciona-a-listagem-de-vídeos)
5. [Problemas Enfrentados](#problemas-enfrentados)
6. [Soluções Implementadas](#soluções-implementadas)
7. [Bypass de Proteções](#bypass-de-proteções)
8. [Endpoints da API](#endpoints-da-api)
9. [Fluxo de Dados](#fluxo-de-dados)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Visão Geral

Esta API foi desenvolvida para automatizar o download de vídeos do TikTok e a extração de metadados de canais, integrando-se com workflows do n8n. O projeto enfrenta desafios significativos devido às proteções anti-scraping do TikTok e de serviços terceirizados como o Urlebird.

### Objetivos

- ✅ Download automatizado de vídeos do TikTok
- ✅ Listagem dos últimos vídeos de múltiplos canais
- ✅ Extração completa de metadados (legenda, métricas, CDN links)
- ✅ Integração com n8n para automação
- ✅ Deploy em VPS com Docker

### Desafios Principais

1. **TikTok Anti-Scraping**: Bloqueio de requisições automatizadas
2. **Cloudflare Protection**: Proteção anti-bot no Urlebird
3. **Rate Limiting**: Limites de requisições por IP
4. **Múltiplos Formatos**: Diferentes formatos de URLs e inputs

---

## 🏗️ Arquitetura do Sistema

### Stack Tecnológico

```
┌─────────────────────────────────────────┐
│         Cliente (n8n/Browser)          │
└─────────────────┬───────────────────────┘
                   │ HTTP/REST
┌──────────────────▼───────────────────────┐
│      Flask API (Python 3.11)            │
│  ┌──────────────────────────────────┐  │
│  │  Endpoints REST                  │  │
│  │  - /download                     │  │
│  │  - /channels/latest              │  │
│  │  - /health                       │  │
│  └──────────────────────────────────┘  │
└──────────┬───────────────────┬──────────┘
           │                   │
    ┌──────▼──────┐    ┌──────▼──────┐
    │ tiktok-     │    │ Urlebird    │
    │ downloader  │    │ Scraping    │
    │ (7 métodos)  │    │ + Selenium  │
    └──────┬──────┘    └──────┬──────┘
           │                   │
    ┌──────▼───────────────────▼──────┐
    │      Serviços Externos           │
    │  - Snaptik, Tikmate, SSStik...   │
    │  - urlebird.com                  │
    └──────────────────────────────────┘
```

### Componentes Principais

1. **Flask Application** (`app.py`)
   - Endpoints REST
   - Gerenciamento de requisições
   - Fallback entre métodos

2. **Download Services**
   - `tiktok-downloader`: 7 métodos diferentes
   - Urlebird scraping: Web scraping + Selenium

3. **Anti-Detection**
   - Selenium com `undetected-chromedriver`
   - Cookies de sessão válida
   - Headers realistas

---

## 🔄 Como Funciona o Download

### Fluxo Geral

```
1. Cliente envia URL do TikTok
   ↓
2. API valida URL
   ↓
3. Tenta métodos em cascata (fallback)
   ├─ Snaptik
   ├─ Tikmate
   ├─ SSStik
   ├─ TTDownloader
   ├─ TikWM
   ├─ MusicallyDown
   ├─ Tikdown
   └─ Urlebird (último recurso)
   ↓
4. Retorna arquivo MP4 ou erro
```

### Método 1-7: tiktok-downloader

**Como Funciona**:
```python
# Cada serviço tem sua própria implementação
services = [
    ('Snaptik', snaptik, True, False),
    ('Tikmate', Tikmate, False, False),
    # ... outros
]

for service_name, service_func, requires_url, is_urlebird in services:
    try:
        # Chamar função do serviço
        data_list = service_func(url)
        
        # Extrair link de download
        video_item = data_list[0]
        download_url = video_item.get('url') or video_item.get('video')
        
        # Baixar vídeo
        response = requests.get(download_url)
        # Salvar arquivo
        return video_file, None
    except:
        continue  # Tenta próximo método
```

**Vantagens**:
- ✅ Rápido
- ✅ Não requer scraping
- ✅ Alta taxa de sucesso

**Desvantagens**:
- ⚠️ Depende de serviços terceiros
- ⚠️ Podem parar de funcionar

### Método 8: Urlebird (Web Scraping)

**Quando é Usado**:
- Todos os outros métodos falharam
- Último recurso

**Como Funciona**:
```
1. Acessar perfil no Urlebird
   https://urlebird.com/pt/user/{username}/
   ↓
2. Extrair URL do vídeo mais recente
   (primeiro link com /video/)
   ↓
3. Acessar página do vídeo
   https://urlebird.com/pt/video/{video-id}/
   ↓
4. Extrair link CDN direto
   (<video src="...">)
   ↓
5. Download direto do CDN
```

**Implementação**:
```python
# 1. Buscar último vídeo do canal
tiktok_url, urlebird_video_url, _, _ = get_latest_video_url_from_channel(username)

# 2. Extrair detalhes e CDN link
video_details, _ = get_video_details_from_urlebird(urlebird_video_url)
cdn_link = video_details['cdn_link']

# 3. Download direto
response = requests.get(cdn_link)
with open(video_file, 'wb') as f:
    f.write(response.content)
```

---

## 📋 Como Funciona a Listagem de Vídeos

### Endpoint: `/channels/latest`

**Objetivo**: Listar últimos vídeos de múltiplos canais com metadados completos

### Fluxo Completo

```
1. Cliente envia lista de canais ou URLs
   ↓
2. Para cada canal/URL:
   ├─ Extrair username
   ├─ Buscar último vídeo no Urlebird
   │  ├─ Tentar Selenium primeiro
   │  └─ Fallback para requests
   ├─ Extrair dados do canal
   │  ├─ Seguidores
   │  ├─ Total de curtidas
   │  └─ Quantidade de vídeos
   ├─ Extrair metadados do vídeo
   │  ├─ Legenda
   │  ├─ Data de postagem
   │  ├─ Métricas (views, likes, comments, shares)
   │  └─ Link CDN direto
   └─ Retornar JSON completo
   ↓
3. Retornar lista de resultados
```

### Extração de Dados do Canal

**HTML do Urlebird**:
```html
<div class="profile-stats">
  <span class="followers">1.2M seguidores</span>
  <span class="hearts">50M curtidas</span>
  <span class="videos">500 vídeos</span>
</div>
```

**Parsing com BeautifulSoup**:
```python
soup = BeautifulSoup(html, 'html.parser')

# Buscar elementos por classe ou texto
followers_elem = soup.find('span', class_=lambda x: x and 'follower' in x.lower())
followers_text = followers_elem.get_text(strip=True)
# Extrair número: "1.2M" → "1.2M"
followers_match = re.search(r'([\d.]+[KMB]?)', followers_text)
```

### Extração de Metadados do Vídeo

**HTML do Vídeo**:
```html
<h1>Legenda do vídeo...</h1>
<h6>Postado há 2 horas</h6>
<div class="stats">
  <span class="views">100K visualizações</span>
  <span class="likes">10K curtidas</span>
  <span class="comments">500 comentários</span>
  <span class="shares">200 compartilhamentos</span>
</div>
<video src="https://cdn.tiktok.com/video/..."></video>
```

**Parsing**:
```python
caption = soup.find('h1').text.strip()
posted_time = soup.find('h6').text.strip()

# Métricas
stats_div = soup.find('div', class_='stats')
views = stats_div.find('span', class_='views').text
likes = stats_div.find('span', class_='likes').text

# CDN Link
video_tag = soup.find('video')
cdn_link = video_tag.get('src')
```

---

## 🚧 Problemas Enfrentados

### 1. Erro 403 Forbidden do Urlebird

**Sintoma**:
```
WARNING:__main__:403 Forbidden em https://urlebird.com/pt/user/oprimorico/
ERROR:__main__:Todas as estratégias falharam
```

**Causa Raiz**:
- Cloudflare detecta requisições automatizadas
- Headers suspeitos
- Falta de cookies de sessão válida
- IP pode estar bloqueado

**Impacto**:
- ❌ Não consegue acessar perfis
- ❌ Não consegue listar vídeos
- ❌ Método Urlebird fica inutilizável

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
TypeError: Binary Location Must be a String
```

**Causa**:
- Versão do ChromeDriver não suporta `excludeSwitches`
- Chrome não encontrado no sistema

**Impacto**:
- ❌ Selenium não inicia
- ❌ Fallback para requests (que também falha)

**Solução**:
- Removida opção `excludeSwitches`
- Detecção automática do Chrome
- Dockerfile instala Chrome automaticamente

---

### 3. Rate Limiting e Bloqueios Temporários

**Sintoma**:
- Funciona às vezes, falha outras vezes
- Erros intermitentes

**Causa**:
- Muitas requisições em pouco tempo
- IP sendo bloqueado temporariamente
- Cloudflare Challenge

**Impacto**:
- ⚠️ Inconsistência no funcionamento
- ⚠️ Requer retry manual

**Soluções**:
- Delays entre requisições (`time.sleep()`)
- Rotação de métodos (fallback automático)
- Cookies válidos reduzem bloqueios

---

### 4. Dependência de Serviços Terceiros

**Problema**:
- Serviços podem mudar/parar
- APIs podem mudar sem aviso
- Sem controle sobre disponibilidade

**Impacto**:
- ⚠️ Métodos podem parar de funcionar
- ⚠️ Requer manutenção constante

**Solução**:
- Múltiplos métodos com fallback
- Monitoramento de saúde dos serviços
- Urlebird como último recurso

---

## ✅ Soluções Implementadas

### 1. Sistema de Fallback em Cascata

**Estratégia**: Tentar múltiplos métodos até encontrar um que funcione

```python
def download_tiktok_video(url):
    services = [
        ('Snaptik', snaptik, True, False),
        ('Tikmate', Tikmate, False, False),
        ('SSStik', ssstik, True, False),
        ('TTDownloader', ttdownloader, True, False),
        ('TikWM', tikwm, True, False),
        ('MusicallyDown', mdown, True, False),
        ('Tikdown', tikdown, True, False),
        ('Urlebird', None, False, True),  # Último recurso
    ]
    
    for service_name, service_func, requires_url, is_urlebird in services:
        try:
            if is_urlebird:
                return download_via_urlebird(url)
            else:
                return service_func(url)
        except Exception as e:
            logger.warning(f"{service_name} falhou: {e}")
            continue
    
    return None, "Todos os métodos falharam"
```

**Vantagem**: Alta taxa de sucesso mesmo se alguns serviços falharem

---

### 2. Selenium com Anti-Detecção

**Problema**: Cloudflare detecta automação

**Solução**: `undetected-chromedriver` + configurações anti-detecção

```python
# Configurar Chrome
options = uc.ChromeOptions()
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_experimental_option('useAutomationExtension', False)

# Remover propriedades que identificam automação
driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
    'source': '''
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        window.navigator.chrome = { runtime: {} };
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
    '''
})
```

**Resultado**: Navegador parece humano para Cloudflare

---

### 3. Suporte a Cookies

**Problema**: Cloudflare ainda bloqueia mesmo com Selenium

**Solução**: Carregar cookies de sessão válida

```python
# Carregar cookies antes de acessar
cookies_file = '/app/cookies.txt'
if os.path.exists(cookies_file):
    driver.get('https://urlebird.com/')
    time.sleep(2)
    
    # Ler cookies formato Netscape
    with open(cookies_file, 'r') as f:
        for line in f:
            parts = line.split('\t')
            if 'urlebird.com' in parts[0]:
                driver.add_cookie({
                    'name': parts[5],
                    'value': parts[6],
                    'domain': parts[0],
                    'path': parts[2]
                })
```

**Como Obter Cookies**:
1. Acessar Urlebird manualmente no navegador
2. Exportar cookies (extensão "Get cookies.txt LOCALLY")
3. Copiar para `/app/cookies.txt` no container

**Resultado**: Cloudflare reconhece como sessão legítima

---

### 4. Extração Robusta de Metadados

**Desafio**: HTML pode mudar, elementos podem não existir

**Solução**: Múltiplas estratégias de busca

```python
def get_channel_data(username, soup):
    channel_data = {'followers': None, 'total_likes': None, 'videos_count': None}
    
    # Estratégia 1: Buscar por classe
    followers_elem = soup.find('span', class_=lambda x: x and 'follower' in x.lower())
    
    # Estratégia 2: Buscar por texto
    if not followers_elem:
        followers_elem = soup.find('span', string=lambda x: x and 'follower' in x.lower())
    
    # Estratégia 3: Buscar por regex no texto
    if not followers_elem:
        all_spans = soup.find_all('span')
        for span in all_spans:
            if re.search(r'follower', span.get_text(), re.IGNORECASE):
                followers_elem = span
                break
    
    # Extrair número
    if followers_elem:
        text = followers_elem.get_text(strip=True)
        match = re.search(r'([\d.]+[KMB]?)', text)
        if match:
            channel_data['followers'] = match.group(1)
    
    return channel_data
```

**Vantagem**: Funciona mesmo se HTML mudar parcialmente

---

### 5. Normalização de Inputs

**Problema**: Usuários podem enviar URLs ou usernames em formatos diferentes

**Solução**: Normalização automática

```python
def validate_username(username):
    # Remove @, espaços, etc.
    username = username.strip().lstrip('@')
    # Validar formato
    if re.match(r'^[\w.]+$', username):
        return username
    return None

# Aceita múltiplos formatos:
# - "oprimorico"
# - "@oprimorico"
# - "https://www.tiktok.com/@oprimorico"
# - "https://urlebird.com/pt/user/oprimorico/"
```

---

## 🛡️ Bypass de Proteções

### Camadas de Proteção Enfrentadas

```
┌─────────────────────────────────────┐
│   TikTok Anti-Scraping              │
│   - Bloqueio de bots                │
│   - JavaScript complexo             │
│   - Rate limiting                   │
└──────────────┬──────────────────────┘
               │
               │ Usamos Urlebird como intermediário
               ↓
┌─────────────────────────────────────┐
│   Urlebird (urlebird.com)           │
│   - Renderiza conteúdo estático     │
│   - Facilita scraping               │
└──────────────┬──────────────────────┘
               │
               │ Cloudflare protege Urlebird
               ↓
┌─────────────────────────────────────┐
│   Cloudflare Protection             │
│   - Detecção de bots                │
│   - Challenge pages                 │
│   - Rate limiting                   │
└──────────────┬──────────────────────┘
               │
               │ Nossas estratégias de bypass
               ↓
┌─────────────────────────────────────┐
│   Nossas Soluções                   │
│   1. Selenium (navegador real)      │
│   2. Anti-detecção                  │
│   3. Cookies válidos                │
│   4. Headers realistas              │
│   5. Delays entre requisições       │
└─────────────────────────────────────┘
```

### Estratégias de Bypass

#### 1. Headers Realistas

```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9...',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8...',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://www.google.com/',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none'
}
```

#### 2. Session Management

```python
session = requests.Session()
session.headers.update(headers)

# Obter cookies primeiro
session.get('https://urlebird.com/pt/')
time.sleep(1)

# Cookies são mantidos automaticamente
response = session.get(f'https://urlebird.com/pt/user/{username}/')
```

#### 3. Delays Entre Requisições

```python
import time

# Delay antes de cada requisição
time.sleep(0.5)  # Parecer mais humano
response = session.get(url)

# Delay maior após erro
if response.status_code == 403:
    time.sleep(2)
    # Tentar novamente
```

#### 4. Múltiplas Tentativas

```python
urls_to_try = [
    f"https://urlebird.com/pt/user/{username}/",
    f"https://urlebird.com/user/{username}/"
]

for url in urls_to_try:
    try:
        response = session.get(url)
        if response.status_code == 200:
            return response
    except:
        continue
```

---

## 🔌 Endpoints da API

### 1. `GET /health`

**Descrição**: Health check da API

**Response**:
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

**Descrição**: Download de vídeo(s)

**Modo 1: URL única** → Retorna MP4
**Modo 2: Múltiplas URLs** → Retorna JSON

**Request**:
```json
{
  "url": "https://www.tiktok.com/@user/video/123"
}
```

ou

```json
{
  "urls": [
    "https://www.tiktok.com/@user/video/123",
    "https://www.tiktok.com/@user/video/456"
  ]
}
```

---

### 3. `POST /channels/latest`

**Descrição**: Listar últimos vídeos com metadados

**Request**:
```json
{
  "channels": ["oprimorico", "username2"]
}
```

ou

```json
{
  "urls": [
    "https://www.tiktok.com/@oprimorico",
    "https://urlebird.com/pt/user/oprimorico/"
  ]
}
```

**Response**: JSON com metadados completos (veja exemplo na seção anterior)

---

### 4. `GET /services`

**Descrição**: Lista serviços disponíveis

**Response**:
```json
{
  "services": ["Snaptik", "Tikmate", ...],
  "available": true,
  "urlebird_available": true,
  "selenium_available": true
}
```

---

## 📊 Fluxo de Dados

### Download de Vídeo

```
Cliente
  │ POST /download {"url": "..."}
  ↓
Flask API
  │ validate_tiktok_url()
  ↓
download_tiktok_video()
  │ Tenta Snaptik
  │ ├─ Sucesso → Retorna arquivo
  │ └─ Falha → Próximo método
  │ Tenta Tikmate
  │ ├─ Sucesso → Retorna arquivo
  │ └─ Falha → Próximo método
  │ ... (7 métodos)
  │ Tenta Urlebird
  │ ├─ get_latest_video_url_from_channel()
  │ ├─ get_video_details_from_urlebird()
  │ ├─ Extrai CDN link
  │ └─ Download direto
  ↓
Retorna MP4 ou JSON com erro
```

### Listagem de Canais

```
Cliente
  │ POST /channels/latest {"channels": [...]}
  ↓
Flask API
  │ Para cada canal:
  │ ├─ validate_username()
  │ ├─ get_latest_video_url_from_channel()
  │ │  ├─ Tentar Selenium
  │ │  │  ├─ Carregar cookies
  │ │  │  ├─ Acessar Urlebird
  │ │  │  ├─ Extrair HTML
  │ │  │  └─ Parse com BeautifulSoup
  │ │  └─ Fallback: requests
  │ ├─ get_channel_data()
  │ │  ├─ Extrair seguidores
  │ │  ├─ Extrair curtidas
  │ │  └─ Extrair vídeos
  │ ├─ get_video_details_from_urlebird()
  │ │  ├─ Extrair legenda
  │ │  ├─ Extrair métricas
  │ │  └─ Extrair CDN link
  │ └─ Montar JSON
  ↓
Retorna JSON com todos os dados
```

---

## 🔧 Troubleshooting

### Problema: Todos os métodos falham

**Diagnóstico**:
```bash
# Verificar health
curl http://localhost:5000/health

# Ver logs
docker logs tiktok-downloader-api | grep ERROR
```

**Soluções**:
1. Verificar se serviços estão online
2. Atualizar cookies do Urlebird
3. Verificar se IP não está bloqueado
4. Tentar em horários diferentes

---

### Problema: 403 Forbidden persistente

**Diagnóstico**:
```bash
# Verificar se cookies existem
docker exec tiktok-downloader-api ls -la /app/cookies.txt

# Verificar formato dos cookies
docker exec tiktok-downloader-api head -5 /app/cookies.txt
```

**Soluções**:
1. ✅ Atualizar cookies (podem ter expirado)
2. ✅ Verificar formato Netscape
3. ✅ Verificar domínio `.urlebird.com`
4. ✅ Usar Selenium ao invés de requests
5. ✅ Aumentar delays entre requisições

---

### Problema: Selenium não funciona

**Diagnóstico**:
```bash
# Chrome instalado?
docker exec tiktok-downloader-api google-chrome --version

# Selenium instalado?
docker exec tiktok-downloader-api pip list | grep selenium
```

**Soluções**:
1. Rebuild da imagem: `docker compose build --no-cache tiktok-downloader-api`
2. Verificar logs: `docker logs tiktok-downloader-api | grep Selenium`
3. Verificar se Chrome está instalado no Dockerfile

---

## 📈 Status Atual

### ✅ Funcionando Bem

- Download via `tiktok-downloader` (métodos 1-7)
- Extração de metadados básicos
- API RESTful completa
- Health checks
- Suporte a múltiplos formatos de input
- Fallback automático entre métodos

### ⚠️ Funcionando Parcialmente

- **Urlebird com requests**: Bloqueado por Cloudflare (403)
- **Urlebird com Selenium**: Funciona com cookies válidos
- **Rate limiting**: Pode ocorrer com muitas requisições

### 🔄 Em Melhoria

- Rotação automática de cookies
- Cache de sessões
- Retry inteligente com backoff exponencial
- Monitoramento de taxa de sucesso por método
- Proxy rotation para evitar bloqueios de IP

---

## 🎯 Próximos Passos

1. **Cookie Management**: Sistema automático de renovação
2. **Proxy Rotation**: Rotacionar IPs para evitar bloqueios
3. **Rate Limiting**: Implementar delays inteligentes
4. **Caching**: Cache de metadados para reduzir requisições
5. **Monitoring**: Dashboard de saúde dos serviços
6. **Retry Logic**: Retry automático com backoff exponencial

---

## 📝 Notas Finais

### Limitações Conhecidas

- ⚠️ Dependência de serviços terceiros (podem mudar/parar)
- ⚠️ Cookies expiram e precisam ser atualizados manualmente
- ⚠️ Rate limiting pode ocorrer com muitas requisições
- ⚠️ Cloudflare pode bloquear IPs temporariamente
- ⚠️ HTML do Urlebird pode mudar (requer atualização do parsing)

### Boas Práticas

- ✅ Sempre ter fallback para múltiplos métodos
- ✅ Implementar retry com delays
- ✅ Monitorar logs regularmente
- ✅ Manter cookies atualizados
- ✅ Não fazer muitas requisições simultâneas
- ✅ Testar em horários de menor tráfego

---

## 📚 Referências

- [tiktok-downloader](https://github.com/sudoguy/tiktok-downloader)
- [undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver)
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)
- [Flask](https://flask.palletsprojects.com/)

---

**Última Atualização**: Janeiro 2026

**Versão**: 1.0.0

**Autor**: Desenvolvido para automação de workflows no n8n
