#!/bin/bash
# Script de deploy para VPS

echo "🚀 Iniciando deploy do TikTok Downloader API..."

# 1. Entrar no diretório
cd ~/tiktok-downloader-api || exit 1

# 2. Atualizar código
echo "📥 Atualizando código do GitHub..."
git pull origin main

# 3. Rebuildar
echo "🔨 Reconstruindo container..."
docker compose build tiktok-downloader-api

# 4. Reiniciar
echo "🔄 Reiniciando serviço..."
docker compose up -d tiktok-downloader-api

# 5. Aguardar inicialização
echo "⏳ Aguardando inicialização..."
sleep 5

# 6. Verificar saúde
echo "🏥 Verificando saúde..."
curl -f http://localhost:5000/health && echo "" || echo "❌ Health check falhou"

# 7. Mostrar logs recentes
echo "📋 Últimas linhas do log:"
docker logs --tail 20 tiktok-downloader-api

echo ""
echo "✅ Deploy concluído!"
