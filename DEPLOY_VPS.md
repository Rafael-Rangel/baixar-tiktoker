# 🚀 Guia de Deploy na VPS

## Pré-requisitos

- Acesso SSH à VPS
- Docker e Docker Compose instalados
- Git instalado
- Permissões para executar Docker

## Passo a Passo

### 1. Conectar na VPS

```bash
ssh root@srv1011759
# ou
ssh root@93.127.211.69
```

### 2. Navegar para o diretório raiz

```bash
cd ~
```

### 3. Executar o script de deploy

**Opção A: Usar o script de deploy (recomendado)**

```bash
# Se você já tem o script na VPS
./deploy.sh
```

**Opção B: Deploy manual**

```bash
# 1. Fazer backup do código antigo (opcional)
mv content-orchestrator content-orchestrator_backup_$(date +%Y%m%d_%H%M%S)

# 2. Clonar/Atualizar código do GitHub
if [ -d "content-orchestrator" ]; then
    cd content-orchestrator
    git fetch origin
    git reset --hard origin/main
    git pull origin main
    cd ..
else
    git clone https://github.com/Rafael-Rangel/orquestrador.git content-orchestrator
fi

# 3. Criar .env se não existir
if [ ! -f "content-orchestrator/.env" ]; then
    cp content-orchestrator/.env.example content-orchestrator/.env
    # Edite o .env se necessário
fi

# 4. Criar diretórios necessários
mkdir -p content-orchestrator/downloads
mkdir -p content-orchestrator/logs
mkdir -p content-orchestrator/data

# 5. Rebuild do container
docker compose build content-orchestrator

# 6. Reiniciar o serviço
docker compose stop content-orchestrator
docker compose rm -f content-orchestrator
docker compose up -d content-orchestrator

# 7. Verificar status
docker ps | grep content-orchestrator
docker logs --tail 20 content-orchestrator
```

### 4. Verificar se está funcionando

```bash
# Health check
curl http://localhost:8002/health

# Health check n8n
curl http://localhost:8002/v1/n8n/health

# Ver logs
docker logs -f content-orchestrator
```

## Estrutura Esperada na VPS

Após o deploy, a estrutura deve ser:

```
~/content-orchestrator/
├── app/
│   ├── main.py
│   ├── api/
│   ├── core/
│   └── services/
├── downloads/          # Criado automaticamente
├── logs/              # Criado automaticamente
├── data/              # Criado automaticamente
├── .env               # Configurações (não versionado)
├── Dockerfile
├── requirements.txt
└── README.md
```

## Configuração do docker-compose.yml

O serviço `content-orchestrator` já está configurado no `docker-compose.yml` da VPS:

```yaml
content-orchestrator:
  user: "1000:1000"
  build:
    context: ./content-orchestrator
    dockerfile: Dockerfile
  container_name: content-orchestrator
  restart: always
  env_file: ./content-orchestrator/.env
  environment:
    - STORAGE_TYPE=local
    - LOCAL_STORAGE_PATH=/app/downloads
  volumes:
    - ./content-orchestrator/downloads:/app/downloads
    - ./content-orchestrator/logs:/app/logs
    - ./content-orchestrator/data:/app/data
  ports:
    - "127.0.0.1:8002:8000"
  labels:
    - traefik.enable=true
    - traefik.http.routers.content-orchestrator.rule=Host(`orchestrator.${DOMAIN_NAME}`)
    - traefik.http.routers.content-orchestrator.entrypoints=web,websecure
    - traefik.http.routers.content-orchestrator.tls=true
    - traefik.http.routers.content-orchestrator.tls.certresolver=mytlschallenge
    - traefik.http.services.content-orchestrator.loadbalancer.server.port=8000
  command: "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
```

## Variáveis de Ambiente (.env)

Crie/edite `content-orchestrator/.env`:

```bash
PROJECT_NAME=Content Orchestrator
API_V1_STR=/v1
STORAGE_TYPE=local
LOCAL_STORAGE_PATH=/app/downloads
DATA_PATH=/app/data
```

## Troubleshooting

### Container não inicia

```bash
# Ver logs detalhados
docker logs content-orchestrator

# Verificar se o build foi bem-sucedido
docker compose build content-orchestrator --no-cache

# Verificar permissões
ls -la content-orchestrator/
```

### Erro de permissão

```bash
# Ajustar permissões
chown -R 1000:1000 content-orchestrator/downloads
chown -R 1000:1000 content-orchestrator/logs
chown -R 1000:1000 content-orchestrator/data
```

### Código não atualiza

```bash
# Forçar pull
cd content-orchestrator
git fetch origin
git reset --hard origin/main
git pull origin main
cd ..

# Rebuild forçado
docker compose build content-orchestrator --no-cache
docker compose up -d content-orchestrator
```

### Verificar se o código está atualizado

```bash
cd content-orchestrator
git log --oneline -5
git status
```

## Atualizações Futuras

Para atualizar o projeto no futuro:

```bash
cd ~/content-orchestrator
git pull origin main
cd ..
docker compose build content-orchestrator
docker compose up -d content-orchestrator
```

Ou simplesmente execute o script de deploy novamente:

```bash
./deploy.sh
```
