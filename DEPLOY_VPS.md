# 🚀 Deploy na VPS - Comandos

## Passo a Passo

```bash
# 1. Entrar no diretório do projeto
cd ~/tiktok-downloader-api

# 2. Atualizar código do GitHub
git pull origin main

# 3. Rebuildar o container
docker compose build tiktok-downloader-api

# 4. Reiniciar o serviço
docker compose up -d tiktok-downloader-api

# 5. Verificar logs
docker logs -f tiktok-downloader-api

# 6. Testar saúde
curl http://localhost:5000/health
```

## Verificar se está funcionando

```bash
# Ver status do container
docker ps | grep tiktok

# Ver logs recentes
docker logs --tail 50 tiktok-downloader-api

# Testar endpoint
curl http://localhost:5000/health
```
