# 📋 Comandos para Executar na VPS

## Deploy Rápido (Copiar e Colar)

Execute estes comandos na VPS, um por vez:

```bash
# 1. Ir para o diretório raiz
cd ~

# 2. Fazer backup do código antigo (opcional, mas recomendado)
mv content-orchestrator content-orchestrator_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

# 3. Clonar/Atualizar código do GitHub
if [ -d "content-orchestrator" ]; then
    cd content-orchestrator
    git fetch origin
    git reset --hard origin/main
    git pull origin main
    cd ..
else
    git clone https://github.com/Rafael-Rangel/orquestrador.git content-orchestrator
fi

# 4. Criar .env se não existir
if [ ! -f "content-orchestrator/.env" ]; then
    cat > content-orchestrator/.env << 'EOF'
PROJECT_NAME=Content Orchestrator
API_V1_STR=/v1
STORAGE_TYPE=local
LOCAL_STORAGE_PATH=/app/downloads
DATA_PATH=/app/data
EOF
fi

# 5. Criar diretórios necessários
mkdir -p content-orchestrator/downloads
mkdir -p content-orchestrator/logs
mkdir -p content-orchestrator/data

# 6. Ajustar permissões
chown -R 1000:1000 content-orchestrator/downloads
chown -R 1000:1000 content-orchestrator/logs
chown -R 1000:1000 content-orchestrator/data

# 7. Rebuild do container
docker compose build content-orchestrator

# 8. Parar e remover container antigo
docker compose stop content-orchestrator
docker compose rm -f content-orchestrator

# 9. Iniciar novo container
docker compose up -d content-orchestrator

# 10. Aguardar inicialização
sleep 5

# 11. Verificar status
docker ps | grep content-orchestrator

# 12. Ver logs
docker logs --tail 30 content-orchestrator

# 13. Testar API
curl http://localhost:8002/health
curl http://localhost:8002/v1/n8n/health
```

## Verificação Pós-Deploy

```bash
# Ver status do container
docker ps | grep content-orchestrator

# Ver logs em tempo real
docker logs -f content-orchestrator

# Testar endpoints
curl http://localhost:8002/health
curl http://localhost:8002/v1/n8n/health
curl http://localhost:8002/docs
```

## Se Algo Der Errado

### Rebuild forçado (sem cache)

```bash
docker compose build content-orchestrator --no-cache
docker compose up -d content-orchestrator
```

### Ver logs de erro

```bash
docker logs content-orchestrator
```

### Verificar se o código está atualizado

```bash
cd content-orchestrator
git log --oneline -5
git status
cd ..
```

### Restaurar backup

```bash
# Se você fez backup, pode restaurar:
mv content-orchestrator_backup_* content-orchestrator
docker compose up -d content-orchestrator
```
