# 📋 Explicação: Docker Compose na VPS

## ❓ Entendendo a Estrutura

### ✅ **Existe APENAS UM docker-compose.yml na VPS**

Na sua VPS, na raiz (`~`), você já tem **UM ÚNICO** `docker-compose.yml` que gerencia **TODOS** os serviços:

```bash
~/docker-compose.yml  # ← ESTE É O ARQUIVO PRINCIPAL
```

Este arquivo já contém:
- `traefik` (proxy reverso)
- `n8n` (automação)
- `postiz` (gerenciamento de posts)
- `content-orchestrator` (orquestrador)
- `telegram-video-downloader` (download de vídeos Telegram)
- ... e outros serviços

---

## 🎯 O Que Precisamos Fazer?

### **NÃO precisamos criar outro docker-compose.yml!**

O que precisamos fazer é **ADICIONAR** o serviço `tiktok-downloader-api` ao `docker-compose.yml` que **JÁ EXISTE** na raiz da VPS.

---

## 📝 Estrutura de Arquivos

### No Projeto (GitHub):
```
tiktok-downloader-api/
├── app.py                    # API Flask
├── requirements.txt          # Dependências
├── Dockerfile               # Imagem Docker
└── docker-compose-snippet.yml  # ← CÓDIGO PARA COPIAR
```

**`docker-compose-snippet.yml`** = Apenas o código YAML que você vai **COPIAR** e **COLAR** no `docker-compose.yml` da raiz da VPS.

### Na VPS (raiz):
```
~/
├── docker-compose.yml       # ← ARQUIVO PRINCIPAL (editar este!)
├── tiktok-downloader-api/   # ← Projeto clonado do GitHub
│   ├── app.py
│   ├── Dockerfile
│   └── ...
└── .env                     # Variáveis de ambiente
```

---

## 🔧 Processo Passo a Passo

### 1. Na VPS, editar o docker-compose.yml da RAIZ:

```bash
nano ~/docker-compose.yml
```

### 2. Encontrar a seção `services:` e ir até o FINAL (antes de `volumes:`)

Você verá algo assim:

```yaml
services:
  traefik:
    # ... configuração traefik ...
  
  n8n:
    # ... configuração n8n ...
  
  content-orchestrator:
    # ... configuração content-orchestrator ...
  
  # ← ADICIONAR AQUI (antes de volumes:)

volumes:
  traefik_data:
    external: true
  # ...
```

### 3. Copiar o código de `docker-compose-snippet.yml` e colar ANTES de `volumes:`

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

### 4. Salvar e executar:

```bash
# Salvar no nano: Ctrl+O, Enter, Ctrl+X

# Build e iniciar
cd ~
docker-compose build tiktok-downloader-api
docker-compose up -d tiktok-downloader-api
```

---

## ✅ Resumo

- ❌ **NÃO precisa** criar um `docker-compose.yml` no projeto
- ✅ **PRECISA** editar o `docker-compose.yml` que JÁ EXISTE na raiz da VPS
- ✅ **COPIAR** o código de `docker-compose-snippet.yml` para dentro do `docker-compose.yml` da raiz
- ✅ **UM ÚNICO** `docker-compose.yml` gerencia TODOS os serviços

---

## 🎯 Por Que Assim?

- **Um único arquivo** é mais fácil de gerenciar
- Todos os serviços compartilham a mesma rede Docker
- Traefik detecta todos os serviços automaticamente
- Fácil de fazer backup (apenas um arquivo)
- Todos os serviços rodam com `docker-compose up -d`

---

**Em resumo: Use o `docker-compose-snippet.yml` como referência, mas cole o código no `docker-compose.yml` da RAIZ da VPS!** 🚀

