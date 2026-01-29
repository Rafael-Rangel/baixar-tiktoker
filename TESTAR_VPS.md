# 🧪 Testar na VPS - Comandos

## 1. Ver Logs em Tempo Real

```bash
docker logs -f tiktok-downloader-api
```

## 2. Testar Endpoint (em outro terminal)

```bash
# Teste 1: Com channels
curl -X POST http://localhost:5000/channels/latest \
  -H "Content-Type: application/json" \
  -d '{"channels": ["oprimorico"]}'

# Teste 2: Com URLs do Urlebird
curl -X POST http://localhost:5000/channels/latest \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://urlebird.com/pt/user/oprimorico/"]}'
```

## 3. O que Esperar nos Logs

### ✅ Se Selenium Funcionar:
```
INFO:__main__:Tentando método Selenium (anti-detecção)...
INFO:__main__:Buscando vídeo mais recente de @oprimorico via Selenium (anti-detecção)...
INFO:__main__:Acessando: https://urlebird.com/pt/user/oprimorico/
INFO:__main__:✓ Vídeo mais recente encontrado via Selenium: https://www.tiktok.com/@oprimorico/video/...
```

### ⚠️ Se Selenium Falhar (fallback):
```
INFO:__main__:Tentando método Selenium (anti-detecção)...
WARNING:__main__:Selenium falhou, tentando método requests...
INFO:__main__:Tentando acessar: https://urlebird.com/pt/user/oprimorico/
```

## 4. Verificar Resposta JSON

A resposta deve incluir:
- `success: true`
- `url`: URL do TikTok
- `urlebird_url`: URL do Urlebird
- `channel_data`: Seguidores, likes totais, etc.
- `video`: Metadados do vídeo (caption, metrics, cdn_link)

## 5. Verificar se Chrome Está Funcionando

```bash
docker exec tiktok-downloader-api google-chrome --version
```

## 6. Verificar Dependências Selenium

```bash
docker exec tiktok-downloader-api pip list | grep -E "selenium|undetected"
```
