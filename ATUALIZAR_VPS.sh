#!/bin/bash
# Script para atualizar content-orchestrator na VPS
# Execute na raiz da VPS (onde está o docker-compose.yml)

set -e

echo "🚀 Atualizando Content Orchestrator..."
echo ""

# Ir para o diretório content-orchestrator
cd ~/content-orchestrator

# Verificar se é um repositório git
if [ ! -d ".git" ]; then
    echo "❌ Diretório não é um repositório git. Fazendo clone..."
    cd ~
    mv content-orchestrator content-orchestrator_backup_$(date +%Y%m%d_%H%M%S)
    git clone https://github.com/Rafael-Rangel/orquestrador.git content-orchestrator
    cd content-orchestrator
else
    echo "📥 Fazendo pull do GitHub..."
    git fetch origin
    git reset --hard origin/main
    git pull origin main
fi

# Criar .env se não existir
if [ ! -f ".env" ]; then
    echo "📝 Criando .env..."
    cat > .env << 'EOF'
PROJECT_NAME=Content Orchestrator
API_V1_STR=/v1
STORAGE_TYPE=local
LOCAL_STORAGE_PATH=/app/downloads
DATA_PATH=/app/data
EOF
fi

# Criar diretórios necessários
echo "📁 Criando diretórios..."
mkdir -p downloads logs data
chown -R 1000:1000 downloads logs data

# Voltar para raiz
cd ~

# Rebuild e reiniciar
echo "🔨 Reconstruindo container..."
docker compose build content-orchestrator

echo "🛑 Parando container antigo..."
docker compose stop content-orchestrator
docker compose rm -f content-orchestrator

echo "▶️  Iniciando novo container..."
docker compose up -d content-orchestrator

echo "⏳ Aguardando inicialização..."
sleep 5

echo "✅ Verificando status..."
docker ps | grep content-orchestrator

echo ""
echo "📋 Logs (últimas 20 linhas):"
docker logs --tail 20 content-orchestrator

echo ""
echo "🧪 Testando API..."
curl -s http://localhost:8002/health || echo "❌ Health check falhou"
curl -s http://localhost:8002/v1/n8n/health || echo "❌ n8n health check falhou"

echo ""
echo "🎉 Atualização concluída!"
