# 📤 Comando SCP Correto

## ❌ Errado
```bash
scp cookies.txt root@93.127.211.69/root/cookies.txt
```

## ✅ Correto
```bash
scp cookies.txt root@93.127.211.69:/root/cookies.txt
```

**Diferença**: Precisa do `:` após o IP!

## Comando Completo

```bash
# Do seu computador local
scp cookies.txt root@93.127.211.69:/root/cookies.txt
```

## Depois na VPS

```bash
# Verificar se arquivo chegou
ls -la /root/cookies.txt

# Copiar para container
docker cp /root/cookies.txt tiktok-downloader-api:/app/cookies.txt

# Verificar no container
docker exec tiktok-downloader-api ls -la /app/cookies.txt
docker exec tiktok-downloader-api head -5 /app/cookies.txt

# Reiniciar
docker compose restart tiktok-downloader-api
```
