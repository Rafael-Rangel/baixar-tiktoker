# 🚀 Guia de Uso no n8n - TikTok Downloader API

## 📋 Endpoints Disponíveis

### 1. `GET /health`
Verifica se a API está funcionando.

### 2. `GET /services`
Lista serviços disponíveis.

### 3. `POST /download`
Download de vídeo(s) do TikTok.

### 4. `POST /channels/latest`
Lista os últimos vídeos de canais.

---

## 🔧 Configuração no n8n

### URL Base da API

**Dentro do Docker (mesma rede):**
```
http://tiktok-downloader-api:5000
```

**Via Traefik (HTTPS):**
```
https://tiktok-api.postagensapp.shop
```

**Localhost (se n8n estiver na mesma máquina):**
```
http://localhost:5000
```

---

## 📝 Exemplos de Workflows

### Workflow 1: Listar Últimos Vídeos de Canais

**Node: HTTP Request**

**Configuração:**
- **Method**: `POST`
- **URL**: `http://tiktok-downloader-api:5000/channels/latest`
- **Authentication**: None
- **Send Headers**: ✅
  - `Content-Type`: `application/json`
- **Send Body**: ✅
- **Body Content Type**: `JSON`
- **Body**:
```json
{
  "channels": ["nathanharenice", "oprimorico"]
}
```

**Resposta esperada:**
```json
{
  "success": 2,
  "failed": 0,
  "total": 2,
  "message": "2 de 2 item(s) processado(s) com sucesso",
  "results": [
    {
      "success": true,
      "url": "https://www.tiktok.com/@nathanharenice/video/1234567890",
      "tiktok_url": "https://www.tiktok.com/@nathanharenice/video/1234567890",
      "caption": "Legenda do vídeo",
      "posted_time": "há 2 horas",
      "views": "1.2M",
      "likes": "50K",
      "comments": "1.2K",
      "shares": "500",
      "channel_data": {
        "username": "nathanharenice",
        "followers": "2.5M",
        "total_likes": "100M",
        "videos_posted": "500"
      }
    }
  ]
}
```

---

### Workflow 2: Download de Vídeo Único

**Node: HTTP Request**

**Configuração:**
- **Method**: `POST`
- **URL**: `http://tiktok-downloader-api:5000/download`
- **Authentication**: None
- **Send Headers**: ✅
  - `Content-Type`: `application/json`
- **Send Body**: ✅
- **Body Content Type**: `JSON`
- **Body**:
```json
{
  "url": "https://www.tiktok.com/@usuario/video/1234567890"
}
```

**Resposta**: Arquivo MP4 (binary)

**Para salvar o arquivo:**
- Use node **"Write Binary File"** após o HTTP Request
- Ou use **"Download File"** node

---

### Workflow 3: Download de Múltiplos Vídeos

**Node: HTTP Request**

**Configuração:**
- **Method**: `POST`
- **URL**: `http://tiktok-downloader-api:5000/download`
- **Authentication**: None
- **Send Headers**: ✅
  - `Content-Type`: `application/json`
- **Send Body**: ✅
- **Body Content Type**: `JSON`
- **Body**:
```json
{
  "urls": [
    "https://www.tiktok.com/@usuario1/video/1234567890",
    "https://www.tiktok.com/@usuario2/video/0987654321"
  ]
}
```

**Resposta esperada:**
```json
{
  "success": 2,
  "failed": 0,
  "total": 2,
  "message": "2 de 2 vídeo(s) baixado(s) com sucesso",
  "results": [
    {
      "success": true,
      "url": "https://www.tiktok.com/@usuario1/video/1234567890",
      "file_path": "/app/downloads/tiktok_abc123.mp4",
      "file_size": 5242880
    }
  ]
}
```

---

## 🔄 Workflow Completo: Listar e Baixar

### Passo 1: Listar Últimos Vídeos
- **Node**: HTTP Request → `POST /channels/latest`
- **Input**: Lista de canais

### Passo 2: Extrair URLs
- **Node**: Code / Set
- **Ação**: Extrair `tiktok_url` de cada resultado

### Passo 3: Download de Cada Vídeo
- **Node**: HTTP Request → `POST /download`
- **Loop**: Para cada URL extraída
- **Salvar**: Write Binary File

---

## 🎯 Exemplo Prático Completo

### Workflow: Monitorar Canais e Baixar Novos Vídeos

```
1. [Trigger] Cron (executa a cada hora)
   ↓
2. [HTTP Request] POST /channels/latest
   Body: {"channels": ["canal1", "canal2"]}
   ↓
3. [Code] Extrair URLs dos vídeos
   ↓
4. [Split In Batches] Processar em lotes
   ↓
5. [HTTP Request] POST /download
   Body: {"url": "{{ $json.tiktok_url }}"}
   ↓
6. [Write Binary File] Salvar vídeo
   Path: /content-downloads/{{ $json.tiktok_url.split('/').pop() }}.mp4
```

---

## ⚙️ Configurações Importantes

### Headers Necessários
```
Content-Type: application/json
```

### Timeout
Configure timeout adequado (30-60 segundos) pois downloads podem demorar.

### Error Handling
- Use node **"IF"** para verificar `success: true`
- Use node **"Error Trigger"** para capturar erros

---

## 📊 Estrutura de Resposta

### Sucesso (`/channels/latest`)
```json
{
  "success": 1,
  "failed": 0,
  "total": 1,
  "message": "1 de 1 item(s) processado(s) com sucesso",
  "results": [...]
}
```

### Erro
```json
{
  "success": 0,
  "failed": 1,
  "total": 1,
  "message": "0 de 1 item(s) processado(s) com sucesso",
  "results": [
    {
      "success": false,
      "url": "...",
      "error": "Mensagem de erro"
    }
  ]
}
```

---

## 🔗 URLs para n8n

### Dentro do Docker (Recomendado)
```
http://tiktok-downloader-api:5000
```

### Via Traefik (HTTPS)
```
https://tiktok-api.postagensapp.shop
```

---

## ✅ Checklist de Teste

1. ✅ Testar `/health` - deve retornar `200 OK`
2. ✅ Testar `/services` - deve listar serviços
3. ✅ Testar `/channels/latest` - deve retornar vídeos
4. ✅ Testar `/download` - deve baixar vídeo

---

## 💡 Dicas

1. **Use variáveis de ambiente** no n8n para a URL da API
2. **Configure timeout** adequado (30-60s)
3. **Trate erros** com nodes IF/Error Trigger
4. **Salve arquivos** em volume compartilhado (`/content-downloads`)
