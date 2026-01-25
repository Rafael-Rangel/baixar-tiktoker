#!/bin/bash

# Script de deploy para VPS
# Atualiza o projeto content-orchestrator na VPS

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Iniciando deploy do Content Orchestrator${NC}"
echo ""

# Cores do projeto
PROJECT_DIR="content-orchestrator"
GIT_REPO="https://github.com/Rafael-Rangel/orquestrador.git"
DOCKER_COMPOSE_FILE="docker-compose.yml"
SERVICE_NAME="content-orchestrator"

# Verificar se estamos no diretório correto (raiz da VPS)
if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
    echo -e "${RED}❌ Erro: docker-compose.yml não encontrado${NC}"
    echo "Execute este script na raiz da VPS (onde está o docker-compose.yml)"
    exit 1
fi

# Backup do código antigo (se existir)
if [ -d "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}📦 Fazendo backup do código antigo...${NC}"
    BACKUP_DIR="${PROJECT_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
    cp -r "$PROJECT_DIR" "$BACKUP_DIR"
    echo -e "${GREEN}✓ Backup criado: $BACKUP_DIR${NC}"
    echo ""
fi

# Clonar/Atualizar código do GitHub
echo -e "${YELLOW}📥 Atualizando código do GitHub...${NC}"
if [ -d "$PROJECT_DIR" ]; then
    cd "$PROJECT_DIR"
    echo "Fazendo pull do repositório..."
    git fetch origin
    git reset --hard origin/main
    git pull origin main
    cd ..
else
    echo "Clonando repositório..."
    git clone "$GIT_REPO" "$PROJECT_DIR"
fi
echo -e "${GREEN}✓ Código atualizado${NC}"
echo ""

# Verificar se existe .env
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo -e "${YELLOW}⚠ Arquivo .env não encontrado${NC}"
    if [ -f "$PROJECT_DIR/.env.example" ]; then
        echo "Criando .env a partir do .env.example..."
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
        echo -e "${YELLOW}⚠ Edite o arquivo $PROJECT_DIR/.env com suas configurações${NC}"
    else
        echo -e "${YELLOW}⚠ Criando .env básico...${NC}"
        cat > "$PROJECT_DIR/.env" << EOF
PROJECT_NAME=Content Orchestrator
API_V1_STR=/v1
STORAGE_TYPE=local
LOCAL_STORAGE_PATH=/app/downloads
DATA_PATH=/app/data
EOF
    fi
    echo ""
fi

# Criar diretórios necessários
echo -e "${YELLOW}📁 Criando diretórios necessários...${NC}"
mkdir -p "$PROJECT_DIR/downloads"
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/data"
echo -e "${GREEN}✓ Diretórios criados${NC}"
echo ""

# Rebuild do container
echo -e "${YELLOW}🔨 Reconstruindo container Docker...${NC}"
docker compose build "$SERVICE_NAME"
echo -e "${GREEN}✓ Build concluído${NC}"
echo ""

# Parar container antigo
echo -e "${YELLOW}🛑 Parando container antigo...${NC}"
docker compose stop "$SERVICE_NAME" || true
docker compose rm -f "$SERVICE_NAME" || true
echo -e "${GREEN}✓ Container antigo parado${NC}"
echo ""

# Iniciar novo container
echo -e "${YELLOW}▶️  Iniciando novo container...${NC}"
docker compose up -d "$SERVICE_NAME"
echo -e "${GREEN}✓ Container iniciado${NC}"
echo ""

# Aguardar alguns segundos
echo -e "${YELLOW}⏳ Aguardando inicialização...${NC}"
sleep 5

# Verificar status
echo -e "${YELLOW}🔍 Verificando status do container...${NC}"
if docker ps | grep -q "$SERVICE_NAME"; then
    echo -e "${GREEN}✅ Container rodando com sucesso!${NC}"
    echo ""
    echo "Status do container:"
    docker ps | grep "$SERVICE_NAME"
    echo ""
    echo "Logs (últimas 20 linhas):"
    docker logs --tail 20 "$SERVICE_NAME"
    echo ""
    echo -e "${GREEN}🎉 Deploy concluído com sucesso!${NC}"
    echo ""
    echo "Para ver os logs em tempo real:"
    echo "  docker logs -f $SERVICE_NAME"
    echo ""
    echo "Para testar a API:"
    echo "  curl http://localhost:8002/health"
    echo "  curl http://localhost:8002/v1/n8n/health"
else
    echo -e "${RED}❌ Erro: Container não está rodando${NC}"
    echo ""
    echo "Logs do container:"
    docker logs "$SERVICE_NAME"
    exit 1
fi
