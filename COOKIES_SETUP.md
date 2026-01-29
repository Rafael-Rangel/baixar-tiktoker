# 🍪 Configuração de Cookies para Bypass Cloudflare

O Urlebird usa Cloudflare para proteção anti-bot. Para contornar isso, você pode usar cookies de uma sessão válida.

## Como Obter Cookies

1. **Abra o navegador** e acesse `https://urlebird.com/pt/user/oprimorico/`
2. **Abra DevTools** (F12)
3. Vá em **Application** > **Cookies** > `https://urlebird.com`
4. **Exporte os cookies** usando uma extensão como "Get cookies.txt LOCALLY" ou copie manualmente

## Formato do Arquivo

O arquivo deve estar no formato **Netscape**:

```
.urlebird.com	TRUE	/	FALSE	1804213800	_ga	GA1.2.2141088358.1769644462
.urlebird.com	TRUE	/	FALSE	1769740199	_gid	GA1.2.867063945.1769644464
```

Formato: `domain	flag	path	secure	expiration	name	value`

## Como Usar na VPS

### Opção 1: Copiar arquivo para o container

```bash
# Na VPS, copie o arquivo de cookies
docker cp cookies.txt tiktok-downloader-api:/app/cookies.txt
```

### Opção 2: Montar como volume (recomendado)

No `docker-compose.yml`, adicione:

```yaml
services:
  tiktok-downloader-api:
    volumes:
      - ./cookies.txt:/app/cookies.txt:ro
```

### Opção 3: Variável de ambiente

O código procura cookies em `/app/cookies.txt` por padrão. Você pode mudar com:

```bash
docker run -e COOKIES_FILE=/caminho/para/cookies.txt ...
```

## Verificar se Funcionou

Nos logs, você deve ver:

```
INFO:__main__:Carregando cookies para bypass Cloudflare...
INFO:__main__:✓ X cookie(s) carregado(s)
```

Se não aparecer essa mensagem, o arquivo não foi encontrado ou está vazio.

## Importante

- ⚠️ **Cookies expiram**: Atualize o arquivo periodicamente
- 🔒 **Segurança**: Não compartilhe cookies publicamente
- 📝 **Formato**: Use formato Netscape (veja `cookies.example.txt`)
