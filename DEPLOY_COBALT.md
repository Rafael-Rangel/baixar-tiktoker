# Deploy do Cobalt - Guia Completo

## Visão Geral

O Cobalt é uma ferramenta open-source robusta para download de vídeos que lida automaticamente com bloqueios do YouTube, Instagram e outras plataformas. Este guia mostra como auto-hospedar o Cobalt na mesma VPS.

## Pré-requisitos

- Docker e Docker Compose instalados
- VPS com pelo menos 1GB RAM disponível
- Porta disponível (recomendado: 9000 ou outra porta)

## Opção 1: Deploy Rápido com Docker Compose

### 1. Criar diretório para o Cobalt

```bash
cd ~
mkdir cobalt
cd cobalt
```

### 2. Criar docker-compose.yml

```bash
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  cobalt:
    image: ghcr.io/imputnet/cobalt:latest
    container_name: cobalt-api
    restart: always
    ports:
      - "127.0.0.1:9000:8080"  # Apenas localhost, acesso via nginx ou diretamente
    environment:
      - API_URL=http://localhost:9000
    # Opcional: cookies para autenticação
    # volumes:
    #   - ./cookies.json:/app/cookies.json
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:8080/api/json"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
EOF
```

### 3. Iniciar o Cobalt

```bash
docker compose up -d
```

### 4. Verificar se está rodando

```bash
# Ver logs
docker logs cobalt-api

# Testar API
curl http://localhost:9000/api/json -X POST -H "Content-Type: application/json" -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

### 5. Configurar no Content Orchestrator

Edite o `.env` do content-orchestrator:

```bash
cd ~/content-orchestrator
nano .env
```

Adicione:

```bash
COBALT_API_URL=http://cobalt-api:8080
```

**Importante**: Use `http://cobalt-api:8080` (nome do container e porta interna) para comunicação entre containers Docker, não `localhost:9000`.

### 6. Conectar Cobalt à mesma rede do n8n

```bash
docker network connect root_default cobalt-api
```

### 7. Reiniciar Content Orchestrator

```bash
cd ~/content-orchestrator
docker compose restart content-orchestrator
```

## Opção 2: Deploy com Nginx (Recomendado para Produção)

Se quiser expor o Cobalt publicamente ou usar HTTPS:

### 1. Criar configuração Nginx

```bash
cat > /etc/nginx/sites-available/cobalt << 'EOF'
server {
    listen 80;
    server_name sua-vps.com;  # Substitua pelo seu domínio

    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Habilitar site
ln -s /etc/nginx/sites-available/cobalt /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

### 2. Configurar no .env

```bash
COBALT_API_URL=https://sua-vps.com
```

## Verificação e Testes

### 1. Testar Cobalt diretamente

```bash
# Teste simples
curl -X POST http://localhost:9000/api/json \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "vCodec": "h264",
    "vQuality": "max"
  }'
```

### 2. Testar via Content Orchestrator

Faça um download pelo n8n e verifique os logs:

```bash
docker logs -f content-orchestrator | grep -i cobalt
```

Você deve ver:
```
INFO - Cobalt: Starting download fallback for VIDEO_ID
INFO - Cobalt: Requesting video info from http://cobalt-api:8080
INFO - Cobalt: Got download URL, downloading file...
INFO - Cobalt: Download successful!
```

## Troubleshooting

### Erro: "Connection refused"

**Causa**: Cobalt não está na mesma rede Docker ou URL incorreta.

**Solução**:
```bash
# Verificar se está na rede
docker network inspect root_default | grep cobalt

# Se não estiver, conectar
docker network connect root_default cobalt-api

# Verificar URL no .env
cat ~/content-orchestrator/.env | grep COBALT
```

### Erro: "API returned status 400"

**Causa**: Formato da requisição ou URL inválida.

**Solução**: Verifique os logs do Cobalt:
```bash
docker logs cobalt-api
```

### Cobalt não inicia

**Causa**: Porta já em uso ou problema de permissões.

**Solução**:
```bash
# Verificar se porta está em uso
netstat -tlnp | grep 9000

# Ver logs detalhados
docker logs cobalt-api

# Reiniciar
docker compose restart
```

## Configuração Avançada

### Adicionar Cookies (Opcional)

Para melhorar taxa de sucesso, você pode adicionar cookies do YouTube:

1. Exporte cookies do seu navegador (extensão "Get cookies.txt LOCALLY")
2. Converta para formato JSON do Cobalt
3. Coloque em `~/cobalt/cookies.json`
4. Descomente a seção `volumes` no docker-compose.yml

### Rate Limiting

Para proteger sua instância, considere adicionar rate limiting no Nginx ou usar Turnstile.

### Monitoramento

Adicione ao seu sistema de monitoramento:

```bash
# Health check
curl -f http://localhost:9000/api/json || echo "Cobalt down"
```

## Referências

- **Repositório**: https://github.com/imputnet/cobalt
- **Documentação**: https://github.com/imputnet/cobalt/blob/main/docs/run-an-instance.md
- **Docker Hub**: https://ghcr.io/imputnet/cobalt
