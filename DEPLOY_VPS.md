# 🚀 Guia de Deploy na VPS Ubuntu

Este guia explica como instalar e rodar a API de download de vídeos TikTok na sua VPS Ubuntu com Docker e Traefik.

## 📋 Pré-requisitos

- Ubuntu 24.04 LTS (ou similar)
- Docker e Docker Compose instalados
- Traefik configurado (você já tem!)
- Acesso SSH root/sudo

## 🔧 Instalação

### 1. Preparar diretório do projeto

```bash
# Criar diretório para o projeto
mkdir -p ~/tiktok-downloader-api
cd ~/tiktok-downloader-api

# Clonar ou copiar os arquivos do projeto aqui
# Você pode usar git clone ou fazer upload via SCP/SFTP
```

### 2. Estrutura de arquivos necessários

Certifique-se de ter os seguintes arquivos no diretório:

```
tiktok-downloader-api/
├── app.py              # API Flask
├── requirements.txt    # Dependências Python
├── Dockerfile         # Imagem Docker
├── docker-compose.yml # Configuração Docker Compose
└── .dockerignore      # Arquivos ignorados no build
```

### 3. Adicionar serviço ao docker-compose.yml principal

**IMPORTANTE:** Adicione este serviço ao seu `docker-compose.yml` existente em `~/docker-compose.yml`.

Edite o arquivo:
```bash
nano ~/docker-compose.yml
```

Adicione este serviço na seção `services:` (pode adicionar no final, antes de `volumes:`):

> 💡 **Dica:** Veja o arquivo `docker-compose-snippet.yml` para copiar o código facilmente.

```yaml
  tiktok-downloader-api:
    build:
      context: ~/tiktok-downloader-api
      dockerfile: Dockerfile
    container_name: tiktok-downloader-api
    restart: always
    environment:
      - PORT=5000
      - DOWNLOAD_DIR=/app/downloads
    volumes:
      - ~/tiktok-downloader-api/downloads:/app/downloads
    ports:
      - "127.0.0.1:5000:5000"
    labels:
      - traefik.enable=true
      - traefik.http.routers.tiktok-api.rule=Host(`tiktok-api.${DOMAIN_NAME}`)
      - traefik.http.routers.tiktok-api.entrypoints=web,websecure
      - traefik.http.routers.tiktok-api.tls=true
      - traefik.http.routers.tiktok-api.tls.certresolver=mytlschallenge
      - traefik.http.services.tiktok-api.loadbalancer.server.port=5000
```

**Salve o arquivo** (Ctrl+O, Enter, Ctrl+X no nano).

### 4. Build e iniciar serviço

```bash
# Navegar para diretório raiz onde está o docker-compose.yml
cd ~

# Build do serviço
docker-compose build tiktok-downloader-api

# Iniciar serviço
docker-compose up -d tiktok-downloader-api

# Verificar se subiu corretamente
docker-compose ps tiktok-downloader-api
```

### 5. Verificar se está rodando

```bash
# Ver logs
docker logs tiktok-downloader-api

# Verificar se está respondendo
curl http://localhost:5000/health

# Verificar containers
docker ps | grep tiktok
```

## 🌐 Configuração Traefik

Com a configuração acima, a API estará acessível em:

- **HTTPS:** `https://tiktok-api.postagensapp.shop`
- **Local:** `http://localhost:5000`

### Testar API via Traefik

```bash
curl -X POST https://tiktok-api.postagensapp.shop/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.tiktok.com/@usuario/video/123456"}'
```

## 🔗 Integração com n8n

No seu n8n (que já está rodando na mesma rede Docker), configure:

**HTTP Request Node:**
- Method: `POST`
- URL (escolha uma opção):
  - **Opção 1 (mesma rede Docker - recomendado):** `http://tiktok-downloader-api:5000/download`
  - **Opção 2 (via Traefik público):** `https://tiktok-api.postagensapp.shop/download`
- Headers: 
  - `Content-Type: application/json`
- Body (JSON):
  ```json
  {
    "url": "{{ $json.tiktok_url }}"
  }
  ```
- Response: Binary

**Após o download, use o FFmpeg no n8n para limpar metadados** (veja seção no README_API.md).

## 📁 Volumes e Persistência

O diretório `downloads/` é mapeado como volume:
- **Host:** `~/tiktok-downloader-api/downloads`
- **Container:** `/app/downloads`

Os arquivos temporários são automaticamente removidos após download, mas você pode limpar manualmente:

```bash
cd ~/tiktok-downloader-api
rm -rf downloads/*.mp4
```

## 🔄 Atualizações

Para atualizar o serviço:

```bash
cd ~/tiktok-downloader-api
# Faça as alterações nos arquivos
cd ~
docker-compose build tiktok-downloader-api
docker-compose up -d tiktok-downloader-api
```

## 🐛 Troubleshooting

### Ver logs
```bash
docker logs -f tiktok-downloader-api
```

### Rebuild completo
```bash
docker-compose down tiktok-downloader-api
docker-compose build --no-cache tiktok-downloader-api
docker-compose up -d tiktok-downloader-api
```

### Verificar portas
```bash
# Ver se a porta 5000 está em uso
netstat -tulpn | grep 5000

# Ver portas dos containers
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

### Problemas com permissões
```bash
# Ajustar permissões do diretório downloads
chown -R 1000:1000 ~/tiktok-downloader-api/downloads
chmod -R 755 ~/tiktok-downloader-api/downloads
```

## 📝 Variáveis de Ambiente

Você pode criar um arquivo `.env` no diretório do projeto:

```bash
PORT=5000
DOWNLOAD_DIR=/app/downloads
```

Ou definir diretamente no `docker-compose.yml` (já está configurado).

## ✅ Checklist de Deploy

- [ ] Arquivos copiados para VPS
- [ ] Docker Compose atualizado
- [ ] Serviço buildado (`docker-compose build`)
- [ ] Serviço iniciado (`docker-compose up -d`)
- [ ] Health check OK (`curl http://localhost:5000/health`)
- [ ] Traefik roteando corretamente
- [ ] Teste de download funcionando
- [ ] Integração com n8n configurada

## 🔒 Segurança

- O serviço está exposto apenas localmente (`127.0.0.1:5000`)
- Acesso externo é feito via Traefik com HTTPS
- Certificado SSL automático via Let's Encrypt
- Container roda como usuário não-root (appuser)

