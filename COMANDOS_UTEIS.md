# 🛠️ Comandos Úteis para VPS

## 📋 Verificação de Status

```bash
# Ver containers rodando
docker ps | grep tiktok

# Ver logs em tempo real
docker logs -f tiktok-downloader-api

# Ver últimas 50 linhas de log
docker logs --tail 50 tiktok-downloader-api

# Verificar health check
curl http://localhost:5000/health

# Ver status do serviço no docker-compose
cd ~
docker-compose ps tiktok-downloader-api
```

## 🔄 Gerenciamento do Serviço

```bash
# Parar serviço
docker-compose stop tiktok-downloader-api

# Iniciar serviço
docker-compose start tiktok-downloader-api

# Reiniciar serviço
docker-compose restart tiktok-downloader-api

# Parar e remover container
docker-compose down tiktok-downloader-api

# Rebuild e iniciar
docker-compose up -d --build tiktok-downloader-api
```

## 🔨 Rebuild Completo

```bash
# Rebuild sem cache (útil após atualizar código)
cd ~
docker-compose build --no-cache tiktok-downloader-api
docker-compose up -d tiktok-downloader-api

# Rebuild forçando pull de base image
docker-compose build --pull tiktok-downloader-api
docker-compose up -d tiktok-downloader-api
```

## 🧪 Testes

```bash
# Testar health endpoint
curl http://localhost:5000/health

# Testar download (substitua pela URL real)
curl -X POST http://localhost:5000/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.tiktok.com/@tiktok/video/7581251376873868551"}' \
  --output test_video.mp4

# Testar via Traefik (após configurar subdomínio)
curl -X POST https://tiktok-api.postagensapp.shop/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.tiktok.com/@tiktok/video/7581251376873868551"}' \
  --output test_video.mp4

# Ver serviços disponíveis
curl http://localhost:5000/services
```

## 🧹 Limpeza

```bash
# Limpar downloads antigos (mais de 1 dia)
find ~/tiktok-downloader-api/downloads -type f -mtime +1 -delete

# Limpar todos os downloads
rm -rf ~/tiktok-downloader-api/downloads/*

# Limpar imagens Docker não utilizadas
docker image prune -a

# Limpar volumes não utilizados
docker volume prune

# Limpar tudo (containers parados, redes, imagens, volumes)
docker system prune -a --volumes
```

## 📊 Monitoramento

```bash
# Uso de recursos do container
docker stats tiktok-downloader-api

# Uso de disco
du -sh ~/tiktok-downloader-api/downloads

# Espaço em disco geral
df -h

# Processos do container
docker top tiktok-downloader-api

# Informações do container
docker inspect tiktok-downloader-api
```

## 🔍 Troubleshooting

```bash
# Verificar portas em uso
netstat -tulpn | grep 5000
ss -tulpn | grep 5000

# Verificar logs do Traefik (se API não estiver acessível externamente)
docker logs root-traefik-1 | grep tiktok

# Executar comando dentro do container
docker exec -it tiktok-downloader-api /bin/bash

# Verificar variáveis de ambiente
docker exec tiktok-downloader-api env | grep -E "PORT|DOWNLOAD_DIR"

# Verificar permissões
ls -la ~/tiktok-downloader-api/downloads

# Ajustar permissões (se necessário)
chown -R 1000:1000 ~/tiktok-downloader-api/downloads
chmod -R 755 ~/tiktok-downloader-api/downloads
```

## 📝 Atualização do Código

```bash
# 1. Fazer backup (opcional)
cp ~/tiktok-downloader-api/app.py ~/tiktok-downloader-api/app.py.bak

# 2. Atualizar arquivos (via SCP, Git, ou editor)
# Exemplo: scp app.py root@vps:~/tiktok-downloader-api/

# 3. Rebuild e reiniciar
cd ~
docker-compose build tiktok-downloader-api
docker-compose up -d tiktok-downloader-api

# 4. Verificar logs
docker logs -f tiktok-downloader-api
```

## 🌐 Traefik e Domínio

```bash
# Verificar rotas do Traefik
docker exec root-traefik-1 traefik api --raw

# Testar certificado SSL
curl -vI https://tiktok-api.postagensapp.shop/health

# Verificar logs do Traefik para o serviço
docker logs root-traefik-1 2>&1 | grep -i tiktok
```

## 🔒 Segurança

```bash
# Verificar usuário do container (deve ser appuser, não root)
docker exec tiktok-downloader-api whoami

# Verificar se porta está apenas em localhost
ss -tulpn | grep 5000
# Deve mostrar: 127.0.0.1:5000 (não 0.0.0.0:5000)

# Verificar volumes montados
docker inspect tiktok-downloader-api | grep -A 10 Mounts
```

## 📦 Backup

```bash
# Fazer backup do código
tar -czf ~/backup-tiktok-api-$(date +%Y%m%d).tar.gz \
  ~/tiktok-downloader-api/

# Fazer backup do docker-compose.yml (se modificado)
cp ~/docker-compose.yml ~/backups/docker-compose.yml.bak
```

## 🚀 Restart Rápido

```bash
# Script para restart rápido
cd ~ && \
docker-compose restart tiktok-downloader-api && \
sleep 3 && \
curl http://localhost:5000/health && \
echo "✅ Serviço reiniciado com sucesso!"
```

