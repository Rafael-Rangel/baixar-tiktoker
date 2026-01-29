# 🚀 Guia Completo: GitHub → VPS

Este guia explica como fazer push para o GitHub e depois instalar na VPS.

## 📦 PARTE 1: Preparar e Subir para o GitHub

### 1. Inicializar Git (se ainda não foi feito)

```powershell
# No PowerShell, navegue até a pasta do projeto
cd C:\Users\GC1\Desktop\PROJETOS\JSONS

# Inicializar repositório Git
git init

# Adicionar remote do GitHub
git remote add origin https://github.com/Rafael-Rangel/baixar-tiktoker.git

# Verificar remote
git remote -v
```

### 2. Adicionar e Fazer Commit

```powershell
# Adicionar todos os arquivos (exceto os ignorados pelo .gitignore)
git add .

# Verificar o que será commitado
git status

# Fazer commit
git commit -m "Initial commit: API TikTok Downloader com Docker"

# Verificar branch (deve estar em main ou master)
git branch
```

### 3. Fazer Push para o GitHub

```powershell
# Se estiver na branch master, renomear para main (ou manter master)
git branch -M main

# Fazer push
git push -u origin main
```

**OU** se o repositório já tiver conteúdo e pedir para fazer pull primeiro:

```powershell
git pull origin main --allow-unrelated-histories
# Resolver conflitos se houver
git push -u origin main
```

### 4. Verificar no GitHub

Acesse: https://github.com/Rafael-Rangel/baixar-tiktoker e verifique se os arquivos estão lá.

---

## 🖥️ PARTE 2: Instalar na VPS

### Passo 1: Conectar na VPS

```bash
ssh root@93.127.211.69
```

### Passo 2: Clonar Repositório

```bash
# Ir para diretório home
cd ~

# Remover diretório antigo se existir (opcional)
rm -rf tiktok-downloader-api

# Clonar repositório do GitHub
git clone https://github.com/Rafael-Rangel/baixar-tiktoker.git tiktok-downloader-api

# Entrar no diretório
cd tiktok-downloader-api

# Verificar arquivos
ls -la
```

### Passo 3: Criar Pasta Downloads

```bash
mkdir -p downloads
chmod 755 downloads
```

### Passo 4: Adicionar Serviço ao docker-compose.yml

```bash
# Editar docker-compose.yml principal
nano ~/docker-compose.yml
```

**Copie e cole este código ANTES da seção `volumes:` (no final da seção `services:`):**

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

**Salvar:** `Ctrl+O`, `Enter`, `Ctrl+X`

### Passo 5: Build e Iniciar Serviço

```bash
# Voltar para diretório raiz
cd ~

# Build da imagem Docker
docker-compose build tiktok-downloader-api

# Iniciar serviço
docker-compose up -d tiktok-downloader-api

# Ver logs (aguardar alguns segundos para inicializar)
sleep 5
docker logs tiktok-downloader-api
```

### Passo 6: Verificar se Está Funcionando

```bash
# Health check
curl http://localhost:5000/health

# Deve retornar: {"status":"ok"}

# Ver container rodando
docker ps | grep tiktok

# Ver status no docker-compose
docker-compose ps tiktok-downloader-api
```

### Passo 7: Testar Download (Opcional)

```bash
# Testar com um vídeo TikTok
curl -X POST http://localhost:5000/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.tiktok.com/@tiktok/video/7581251376873868551"}' \
  --output test_video.mp4

# Verificar se baixou
ls -lh test_video.mp4
```

---

## ✅ Checklist Final

- [ ] Repositório no GitHub atualizado
- [ ] Repositório clonado na VPS
- [ ] Serviço adicionado ao docker-compose.yml
- [ ] Build executado com sucesso
- [ ] Container rodando (`docker ps | grep tiktok`)
- [ ] Health check OK (`curl http://localhost:5000/health`)
- [ ] Logs sem erros (`docker logs tiktok-downloader-api`)

---

## 🔄 Comandos Úteis para Manutenção

### Atualizar Código do GitHub

```bash
# Na VPS
cd ~/tiktok-downloader-api
git pull origin main
cd ~
docker-compose build tiktok-downloader-api
docker-compose up -d tiktok-downloader-api
```

### Ver Logs

```bash
docker logs -f tiktok-downloader-api
```

### Reiniciar Serviço

```bash
docker-compose restart tiktok-downloader-api
```

### Rebuild Completo

```bash
cd ~
docker-compose build --no-cache tiktok-downloader-api
docker-compose up -d tiktok-downloader-api
```

---

## 🌐 Integração com n8n

No seu n8n, configure um **HTTP Request Node**:

- **Method:** `POST`
- **URL:** `http://tiktok-downloader-api:5000/download`
- **Headers:** `Content-Type: application/json`
- **Body (JSON):**
  ```json
  {
    "url": "{{ $json.tiktok_url }}"
  }
  ```
- **Response:** `Binary File`

Depois use FFmpeg no n8n para limpar metadados (veja README_API.md).

---

## 🔗 Acesso Externo

Após alguns minutos, o Traefik criará o certificado SSL e você poderá acessar:

**HTTPS:** `https://tiktok-api.postagensapp.shop`

---

## 🆘 Problemas?

### Container não inicia
```bash
docker logs tiktok-downloader-api
```

### Erro no build
```bash
docker-compose build --no-cache tiktok-downloader-api
```

### Porta já em uso
```bash
# Ver o que está usando a porta 5000
netstat -tulpn | grep 5000
```

### Permissões
```bash
chown -R 1000:1000 ~/tiktok-downloader-api/downloads
chmod -R 755 ~/tiktok-downloader-api/downloads
```

