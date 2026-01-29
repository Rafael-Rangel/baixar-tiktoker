# ⚡ Instalação Rápida na VPS

Guia passo-a-passo simplificado para instalar a API na sua VPS Ubuntu.

## 📦 Passo 1: Enviar arquivos para VPS

No seu computador local (Windows), use um destes métodos:

### Opção A: Via SCP (PowerShell)
```powershell
# Navegar até a pasta do projeto
cd C:\Users\GC1\Desktop\PROJETOS\JSONS

# Enviar arquivos para VPS (substitua pelo IP/domínio da sua VPS)
scp app.py requirements.txt Dockerfile root@93.127.211.69:~/tiktok-downloader-api/
```

### Opção B: Via SFTP (FileZilla/WinSCP)
- Host: `93.127.211.69` (ou seu domínio)
- Usuário: `root`
- Porta: `22`
- Enviar para: `~/tiktok-downloader-api/`

### Opção C: Via Git (se tiver repositório)
```bash
# Na VPS
cd ~
git clone [seu-repositorio] tiktok-downloader-api
cd tiktok-downloader-api
```

## 🔧 Passo 2: Preparar na VPS

Conecte-se via SSH:
```bash
ssh root@93.127.211.69
```

Execute na VPS:
```bash
# Criar diretório
mkdir -p ~/tiktok-downloader-api
cd ~/tiktok-downloader-api

# Criar pasta downloads
mkdir -p downloads
chmod 755 downloads

# Verificar se arquivos estão presentes
ls -la
# Deve mostrar: app.py, requirements.txt, Dockerfile
```

## 📝 Passo 3: Adicionar ao docker-compose.yml

```bash
# Editar docker-compose.yml
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

## 🚀 Passo 4: Build e Iniciar

```bash
# Voltar para diretório raiz
cd ~

# Build da imagem
docker-compose build tiktok-downloader-api

# Iniciar serviço
docker-compose up -d tiktok-downloader-api

# Verificar logs
docker logs -f tiktok-downloader-api
```

Pressione `Ctrl+C` para sair dos logs.

## ✅ Passo 5: Testar

```bash
# Health check
curl http://localhost:5000/health

# Deve retornar: {"status":"ok"}

# Ver containers rodando
docker ps | grep tiktok

# Testar download (substitua pela URL real)
curl -X POST http://localhost:5000/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.tiktok.com/@tiktok/video/7581251376873868551"}' \
  --output test_video.mp4
```

## 🌐 Passo 6: Configurar n8n

No seu n8n, adicione um **HTTP Request Node**:

- **Method:** `POST`
- **URL:** `http://tiktok-downloader-api:5000/download`
- **Headers:**
  ```
  Content-Type: application/json
  ```
- **Body (JSON):**
  ```json
  {
    "url": "{{ $json.tiktok_url }}"
  }
  ```
- **Response:** `Binary File`

## 🎯 Pronto!

A API estará disponível em:
- **Interno (n8n):** `http://tiktok-downloader-api:5000`
- **Externo (HTTPS):** `https://tiktok-api.postagensapp.shop`

---

## 🆘 Problemas?

### Container não inicia
```bash
docker logs tiktok-downloader-api
```

### Porta já em uso
```bash
# Verificar o que usa a porta 5000
netstat -tulpn | grep 5000
```

### Permissões
```bash
chown -R 1000:1000 ~/tiktok-downloader-api/downloads
```

### Rebuild completo
```bash
docker-compose down tiktok-downloader-api
docker-compose build --no-cache tiktok-downloader-api
docker-compose up -d tiktok-downloader-api
```

