# 🔄 Rebuild na VPS - Passo a Passo

O código foi atualizado no GitHub, mas o container ainda está usando a versão antiga. Siga estes passos:

## 1. Parar Container

```bash
cd ~
docker compose stop tiktok-downloader-api
```

## 2. Rebuild SEM Cache (Importante!)

```bash
docker compose build --no-cache tiktok-downloader-api
```

**⚠️ IMPORTANTE**: Use `--no-cache` para garantir que todas as mudanças sejam aplicadas!

## 3. Iniciar Container

```bash
docker compose up -d tiktok-downloader-api
```

## 4. Verificar Logs

```bash
docker logs -f tiktok-downloader-api
```

Você deve ver:
- ✅ Sem erro de `excludeSwitches`
- ✅ Se cookies existirem: `Carregando cookies para bypass Cloudflare...`

## 5. Copiar Cookies (Se Ainda Não Fez)

```bash
# Criar arquivo cookies.txt na VPS primeiro
nano cookies.txt
# Colar cookies do Urlebird (formato Netscape)
# Salvar: Ctrl+X, Y, Enter

# Copiar para container
docker cp cookies.txt tiktok-downloader-api:/app/cookies.txt

# Reiniciar
docker compose restart tiktok-downloader-api
```

## 6. Verificar se Cookies Foram Carregados

```bash
# Verificar se arquivo existe
docker exec tiktok-downloader-api ls -la /app/cookies.txt

# Ver conteúdo (primeiras linhas)
docker exec tiktok-downloader-api head -5 /app/cookies.txt
```

## 7. Testar Novamente

```bash
curl -X POST http://localhost:5000/channels/latest \
  -H "Content-Type: application/json" \
  -d '{"channels": ["oprimorico"]}'
```

## Comandos Rápidos (Copiar e Colar)

```bash
cd ~ && docker compose stop tiktok-downloader-api && docker compose build --no-cache tiktok-downloader-api && docker compose up -d tiktok-downloader-api && docker logs -f tiktok-downloader-api
```
