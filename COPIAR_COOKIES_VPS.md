# 🍪 Como Copiar Cookies para VPS

## Arquivo cookies.txt Criado ✅

O arquivo `cookies.txt` foi criado localmente com **43 cookies do Urlebird** extraídos do arquivo `cookies(1).txt`.

**⚠️ IMPORTANTE**: O arquivo `cookies.txt` está no `.gitignore` (não será commitado no GitHub por segurança).

## Passo a Passo na VPS

### 1. Enviar arquivo para VPS

**Opção A: Via SCP (do seu computador local)**
```bash
scp cookies.txt root@seu-vps-ip:/root/cookies.txt
```

**Opção B: Criar diretamente na VPS**
```bash
# Na VPS, criar arquivo
nano cookies.txt
# Colar o conteúdo do cookies.txt
# Salvar: Ctrl+X, Y, Enter
```

### 2. Copiar para Container

```bash
# Certifique-se de que o arquivo está na VPS
ls -la cookies.txt

# Copiar para container
docker cp cookies.txt tiktok-downloader-api:/app/cookies.txt

# Verificar se foi copiado
docker exec tiktok-downloader-api ls -la /app/cookies.txt
docker exec tiktok-downloader-api head -5 /app/cookies.txt
```

### 3. Reiniciar Container

```bash
docker compose restart tiktok-downloader-api
```

### 4. Verificar Logs

```bash
docker logs -f tiktok-downloader-api
```

Você deve ver:
```
INFO:__main__:✓ X cookie(s) carregado(s) de /app/cookies.txt
```

## Verificar se Funcionou

Após reiniciar, teste:

```bash
curl -X POST http://localhost:5000/channels/latest \
  -H "Content-Type: application/json" \
  -d '{"channels": ["oprimorico"]}'
```

Nos logs, você deve ver:
- `✓ X cookie(s) carregado(s)` - Cookies carregados
- `Aplicando cookies carregados à sessão requests...` - Cookies sendo usados
- Sem erro 403 Forbidden (ou menos frequente)

## Importante

- ⚠️ Cookies expiram: Se parar de funcionar, exporte novos cookies
- 🔒 Segurança: Não compartilhe cookies publicamente
- 📝 Formato: Arquivo deve estar em formato Netscape (já está correto)
