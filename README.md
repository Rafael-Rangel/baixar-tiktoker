# 🎬 TikTok Downloader API

API Flask para download de vídeos do TikTok e extração de metadados de canais.

## 🚀 Funcionalidades

- ✅ Download de vídeos individuais ou em lote
- ✅ Listagem dos últimos vídeos de múltiplos canais
- ✅ Extração completa de metadados (legenda, métricas, CDN links)
- ✅ Múltiplos métodos de download com fallback automático
- ✅ Ordenação automática por confiabilidade
- ✅ API RESTful com CORS habilitado

## 📦 Instalação

### Docker (Recomendado)

```bash
# Clone o repositório
git clone https://github.com/Rafael-Rangel/baixar-tiktoker.git
cd baixar-tiktoker

# Build e start
docker compose build
docker compose up -d

# Verificar logs
docker logs -f tiktok-downloader-api
```

### Local

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar
python app.py
```

## 🔌 Endpoints

### `POST /download`
Download de vídeo(s) do TikTok.

**Body:**
```json
{
  "url": "https://www.tiktok.com/@usuario/video/1234567890"
}
```

ou múltiplos:
```json
{
  "urls": [
    "https://www.tiktok.com/@usuario/video/1234567890",
    "https://www.tiktok.com/@usuario/video/0987654321"
  ]
}
```

**Resposta (vídeo único):** Arquivo MP4  
**Resposta (múltiplos):** JSON com resultados

### `POST /channels/latest`
Lista os últimos vídeos de canais.

**Body:**
```json
{
  "channels": ["usuario1", "usuario2"]
}
```

ou URLs:
```json
{
  "urls": [
    "https://www.tiktok.com/@usuario1",
    "https://www.tiktok.com/@usuario2"
  ]
}
```

**Resposta:** JSON com metadados completos

### `GET /health`
Status de saúde da API.

### `GET /services`
Lista serviços disponíveis.

## 🔧 Serviços de Download

A API usa automaticamente os seguintes serviços (em ordem de prioridade):

1. **Snaptik** ✅
2. **TTDownloader** ✅
3. **TikWM** ✅
4. **MusicallyDown** ✅

A ordem é otimizada automaticamente baseada em testes. A ordem atual é salva em `services_order.json`.

## 🌐 Variáveis de Ambiente (Opcional)

```bash
# Apify (para scraping avançado)
APIFY_API_TOKEN=seu_token_aqui

# RapidAPI (para scraping alternativo)
RAPIDAPI_KEY=sua_chave_aqui
```

## 🐳 Deploy em VPS

```bash
# 1. Clonar repositório
git clone https://github.com/Rafael-Rangel/baixar-tiktoker.git
cd baixar-tiktoker

# 2. Limpar arquivos desnecessários
bash limpar_vps.sh

# 3. Build e start
docker compose build
docker compose up -d

# 4. Verificar status
docker ps
docker logs tiktok-downloader-api

# 5. Testar
curl http://localhost:5000/health
```

## 📝 Exemplos de Uso

### Download de vídeo único
```bash
curl -X POST http://localhost:5000/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.tiktok.com/@usuario/video/1234567890"}' \
  --output video.mp4
```

### Listar últimos vídeos de canais
```bash
curl -X POST http://localhost:5000/channels/latest \
  -H "Content-Type: application/json" \
  -d '{"channels": ["usuario1", "usuario2"]}'
```

## 🔒 CORS

CORS está habilitado para integração com n8n e outras ferramentas.

## 📄 Licença

MIT
