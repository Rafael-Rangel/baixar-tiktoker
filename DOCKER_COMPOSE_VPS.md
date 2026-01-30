# Configuração do multivideos-api no docker-compose.yml da VPS

No arquivo `/root/docker-compose.yml` da VPS, adicione a variável `APIFY_API_TOKEN` no serviço `multivideos-api`:

```yaml
multivideos-api:
    build:
      context: ./tiktok-downloader-api
      dockerfile: Dockerfile
    container_name: multivideos-api
    restart: always
    user: "1000:1000"
    environment:
      - PORT=5000
      - DOWNLOAD_DIR=/data/multivideos/tmp/downloads
      - COOKIES_FILE=/app/cookies.txt
      - APIFY_API_TOKEN=${APIFY_API_TOKEN}  # ← ADICIONAR ESTA LINHA (configure no .env ou diretamente)
    volumes:
      - /srv/multivideos:/data/multivideos
      - ./cookies.txt:/app/cookies.txt:ro
    ports:
      - "127.0.0.1:5002:5000"
```

Depois de adicionar, execute:

```bash
cd /root
docker compose up -d --no-deps --force-recreate multivideos-api
docker compose logs -f --tail 50 multivideos-api
```
