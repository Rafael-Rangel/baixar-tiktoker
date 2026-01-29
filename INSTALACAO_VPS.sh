#!/bin/bash
# Script de instalação automática na VPS Ubuntu

set -e

echo "🚀 Instalando API TikTok Downloader na VPS..."

# Verificar se está como root
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Execute como root ou com sudo"
    exit 1
fi

# Criar diretório do projeto
PROJECT_DIR="$HOME/tiktok-downloader-api"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

echo "📁 Diretório criado: $PROJECT_DIR"

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não encontrado. Instalando..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

# Verificar se Docker Compose está instalado
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose não encontrado. Instalando..."
    apt-get update
    apt-get install -y docker-compose-plugin
fi

echo "✅ Docker e Docker Compose verificados"

# Criar estrutura de diretórios
mkdir -p downloads
chmod 755 downloads

echo "📦 Arquivos prontos. Agora:"
echo ""
echo "1. Copie os arquivos do projeto para: $PROJECT_DIR"
echo "   - app.py"
echo "   - requirements.txt"
echo "   - Dockerfile"
echo ""
echo "2. Adicione o serviço ao seu docker-compose.yml:"
echo ""
echo "3. Execute:"
echo "   cd ~"
echo "   docker-compose build tiktok-downloader-api"
echo "   docker-compose up -d tiktok-downloader-api"
echo ""
echo "✅ Setup inicial concluído!"

