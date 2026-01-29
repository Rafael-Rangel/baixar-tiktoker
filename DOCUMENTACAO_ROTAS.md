# 📚 Documentação Completa das Rotas e Métodos

## 🔌 Rotas Disponíveis

### 1. `GET /health`
**Descrição**: Health check da API  
**Método**: GET  
**Parâmetros**: Nenhum  
**Resposta**: Status de todas as bibliotecas disponíveis

---

### 2. `GET /services`
**Descrição**: Lista todos os serviços de download disponíveis  
**Método**: GET  
**Parâmetros**: Nenhum  
**Resposta**: Lista de serviços e status de disponibilidade

---

### 3. `POST /channels/latest`
**Descrição**: Lista os últimos vídeos de múltiplos canais OU extrai metadados de URLs

**Método**: POST  
**Content-Type**: `application/json`

**Body (opção 1 - Canais)**:
```json
{
  "channels": ["usuario1", "@usuario2", "usuario3"]
}
```

**Body (opção 2 - URLs)**:
```json
{
  "urls": [
    "https://www.tiktok.com/@usuario/video/123456",
    "https://urlebird.com/pt/user/usuario/"
  ]
}
```

**Resposta**:
```json
{
  "total": 2,
  "success": 2,
  "failed": 0,
  "results": [
    {
      "url": "https://www.tiktok.com/@usuario/video/123456",
      "success": true,
      "channel": "usuario",
      "video": {
        "caption": "Legenda do vídeo",
        "posted_time": "há 2 horas",
        "metrics": {
          "views": "1.2M",
          "likes": "50K",
          "comments": "1.2K",
          "shares": "500"
        }
      },
      "channel_data": {
        "followers": "100K",
        "total_likes": "5M",
        "videos_count": "150"
      }
    }
  ]
}
```

---

### 4. `POST /download`
**Descrição**: Baixa vídeo(s) do TikTok

**Método**: POST  
**Content-Type**: `application/json`

**Body (opção 1 - URL única)**:
```json
{
  "url": "https://www.tiktok.com/@usuario/video/123456"
}
```
**Resposta**: Arquivo MP4 direto (binary)

**Body (opção 2 - Múltiplas URLs)**:
```json
{
  "urls": [
    "https://www.tiktok.com/@usuario/video/123456",
    "https://www.tiktok.com/@usuario2/video/789012"
  ]
}
```
**Resposta**: JSON com resultados de cada download

---

### 5. `GET /download?url=...`
**Descrição**: Baixa vídeo via query parameter  
**Método**: GET  
**Parâmetros**: `url` (query string)  
**Resposta**: Arquivo MP4 direto (binary)

---

## 🔄 Ordem de Prioridade dos Métodos

### Para `/channels/latest` (Buscar último vídeo de canal)

A função `get_latest_video_url_from_channel()` tenta os métodos nesta ordem:

#### 🥇 **1. Apify TikTok Scraper** (PRIMEIRO - MAIS CONFIÁVEL)
- **Biblioteca**: `apify-client`
- **Requisito**: `APIFY_API_TOKEN` configurado
- **Vantagens**:
  - ✅ Resolve Cloudflare automaticamente
  - ✅ Anti-bot detection profissional
  - ✅ Alta taxa de sucesso
  - ✅ Proxy rotation automático
  - ✅ Cookies management automático
- **Desvantagens**: Requer token (pago por uso)
- **Status**: ✅ **RECOMENDADO**

#### 🥈 **2. RapidAPI TikTok Scraper**
- **Biblioteca**: `requests`
- **Requisito**: `RAPIDAPI_KEY` (opcional)
- **Vantagens**: API profissional
- **Desvantagens**: Pode requerer chave de API
- **Status**: ⚠️ Pode falhar sem chave

#### 🥉 **3. TikWM API**
- **Biblioteca**: `requests`
- **Requisito**: Nenhum
- **Vantagens**: API pública gratuita
- **Desvantagens**: Pode ser bloqueado pelo Cloudflare
- **Status**: ⚠️ Instável

#### **4. Countik**
- **Biblioteca**: `requests` + `beautifulsoup4`
- **Requisito**: Nenhum
- **Vantagens**: Alternativa ao Urlebird
- **Desvantagens**: Também bloqueado pelo Cloudflare
- **Status**: ⚠️ Instável

#### **5. Playwright + Stealth** (Método do Manus)
- **Biblioteca**: `playwright` + `playwright-stealth`
- **Requisito**: Playwright instalado
- **Vantagens**:
  - ✅ Bypass avançado de Cloudflare
  - ✅ Emulação de GPU (WebGL)
  - ✅ Persistent context (cookies)
  - ✅ Movimentos de mouse Bezier
  - ✅ User-Agent sincronizado com SO
- **Desvantagens**: Mais lento, requer mais recursos
- **Status**: ✅ Bom fallback

#### **6. Browser Use**
- **Biblioteca**: `browser-use`
- **Requisito**: `BROWSER_USE_API_KEY` (opcional)
- **Vantagens**: Agent-based automation
- **Desvantagens**: Pode ser lento
- **Status**: ⚠️ Fallback

#### **7. SeleniumBase**
- **Biblioteca**: `seleniumbase`
- **Requisito**: Chrome instalado
- **Vantagens**: Undetected ChromeDriver integrado
- **Desvantagens**: Requer Chrome, pode ser detectado
- **Status**: ⚠️ Fallback

#### **8. Selenium Padrão**
- **Biblioteca**: `selenium` + `undetected-chromedriver`
- **Requisito**: Chrome instalado
- **Vantagens**: Anti-detecção básica
- **Desvantagens**: Pode ser detectado pelo Cloudflare
- **Status**: ⚠️ Fallback

#### **9. Requests (Último Recurso)**
- **Biblioteca**: `requests` + `beautifulsoup4`
- **Requisito**: Nenhum
- **Vantagens**: Leve, rápido
- **Desvantagens**: ❌ Geralmente bloqueado pelo Cloudflare
- **Status**: ❌ Raramente funciona

---

### Para `/download` (Baixar vídeo)

A função `download_tiktok_video()` tenta os serviços nesta ordem:

#### 🥇 **1. Snaptik**
- **Status**: Primeiro na lista
- **Taxa de sucesso**: Alta

#### 🥈 **2. Tikmate**
- **Status**: Segundo na lista
- **Taxa de sucesso**: Alta

#### 🥉 **3. SSStik**
- **Status**: Terceiro na lista
- **Taxa de sucesso**: Média-Alta

#### **4. TTDownloader**
- **Status**: Quarto na lista
- **Taxa de sucesso**: Média

#### **5. TikWM**
- **Status**: Quinto na lista
- **Taxa de sucesso**: Média

#### **6. MusicallyDown**
- **Status**: Sexto na lista
- **Taxa de sucesso**: Média

#### **7. Tikdown**
- **Status**: Sétimo na lista
- **Taxa de sucesso**: Média

#### **8. Urlebird** (Último Fallback)
- **Status**: Último recurso
- **Método**: Scraping direto do Urlebird
- **Taxa de sucesso**: Baixa (bloqueado pelo Cloudflare)

---

## 📊 Resumo Visual

### Para Buscar Último Vídeo (`/channels/latest`)

```
┌─────────────────────────────────────────┐
│ 1. Apify TikTok Scraper ⭐ RECOMENDADO │ ← Mais confiável
├─────────────────────────────────────────┤
│ 2. RapidAPI TikTok Scraper              │
├─────────────────────────────────────────┤
│ 3. TikWM API                            │
├─────────────────────────────────────────┤
│ 4. Countik                              │
├─────────────────────────────────────────┤
│ 5. Playwright + Stealth                │ ← Método do Manus
├─────────────────────────────────────────┤
│ 6. Browser Use                          │
├─────────────────────────────────────────┤
│ 7. SeleniumBase                         │
├─────────────────────────────────────────┤
│ 8. Selenium Padrão                      │
├─────────────────────────────────────────┤
│ 9. Requests (Último Recurso)           │ ← Raramente funciona
└─────────────────────────────────────────┘
```

### Para Baixar Vídeo (`/download`)

```
┌─────────────────────────────────────────┐
│ 1. Snaptik                             │ ← Primeiro
├─────────────────────────────────────────┤
│ 2. Tikmate                              │
├─────────────────────────────────────────┤
│ 3. SSStik                               │
├─────────────────────────────────────────┤
│ 4. TTDownloader                         │
├─────────────────────────────────────────┤
│ 5. TikWM                                │
├─────────────────────────────────────────┤
│ 6. MusicallyDown                        │
├─────────────────────────────────────────┤
│ 7. Tikdown                              │
├─────────────────────────────────────────┤
│ 8. Urlebird (Fallback)                  │ ← Último recurso
└─────────────────────────────────────────┘
```

---

## 🎯 Recomendações

### Para Produção (VPS)

1. **Configure Apify** (primeira opção):
   ```bash
   export APIFY_API_TOKEN='seu_token'
   ```
   - ✅ Mais confiável
   - ✅ Resolve Cloudflare automaticamente
   - ✅ Alta taxa de sucesso

2. **Mantenha Playwright como fallback**:
   - ✅ Funciona quando Apify não está disponível
   - ✅ Método do Manus (bem testado)

### Para Desenvolvimento Local

- Use Apify se tiver token
- Ou teste com Playwright + Stealth
- Os outros métodos são fallbacks automáticos

---

## 🔍 Como Verificar Qual Método Foi Usado

Os logs mostram qual método foi usado:

```
INFO:__main__:Tentando método Apify TikTok Scraper (API profissional)...
INFO:__main__:✓ Vídeo mais recente encontrado via Apify: https://...
```

Ou:

```
WARNING:__main__:Apify falhou, tentando RapidAPI...
WARNING:__main__:RapidAPI falhou, tentando TikWM...
...
INFO:__main__:✓ Vídeo mais recente encontrado via Playwright + Stealth: https://...
```

---

## 📝 Notas Importantes

1. **Apify é pago por uso**, mas tem plano gratuito com créditos
2. **Playwright** requer instalação de browsers: `playwright install chromium`
3. **Selenium** requer Chrome instalado no sistema
4. **Requests** geralmente falha devido ao Cloudflare
5. Todos os métodos têm **fallback automático** - se um falhar, tenta o próximo

---

## 🚀 Exemplo de Uso Completo

### Workflow no n8n:

**Passo 1**: Listar últimos vídeos
```json
POST /channels/latest
{
  "channels": ["oprimorico", "nathanharenice"]
}
```

**Passo 2**: Baixar vídeos encontrados
```json
POST /download
{
  "urls": [
    "https://www.tiktok.com/@oprimorico/video/123456",
    "https://www.tiktok.com/@nathanharenice/video/789012"
  ]
}
```

---

## ✅ Status Atual

- ✅ Apify integrado e funcionando
- ✅ Playwright + Stealth implementado (método do Manus)
- ✅ Todos os métodos têm fallback automático
- ✅ Logs detalhados para debug
- ✅ Health check mostra status de cada biblioteca
