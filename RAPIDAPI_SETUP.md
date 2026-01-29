# 🔑 Configuração da RapidAPI TikTok Scraper

## O que é?

A **RapidAPI TikTok Scraper** é uma API profissional que permite listar vídeos de usuários do TikTok sem precisar lidar com Cloudflare ou scraping manual.

## ✅ Vantagens

- ✅ API profissional e confiável
- ✅ Não precisa lidar com Cloudflare
- ✅ Resposta JSON estruturada
- ✅ Mais rápido que scraping

## 📝 Como Configurar

### 1. Criar Conta no RapidAPI

1. Acesse: https://rapidapi.com
2. Crie uma conta (gratuita)
3. Faça login

### 2. Assinar a API TikTok Scraper

1. Procure por "TikTok Scraper" na busca
2. Selecione: **TikTok Scraper** (por tiktok-scraper7)
3. Clique em "Subscribe to Test"
4. Escolha o plano (geralmente há um plano gratuito com limite de requisições)

### 3. Obter sua Chave de API

1. Após assinar, vá em "My Apps" ou "Dashboard"
2. Encontre sua chave de API (x-rapidapi-key)
3. Copie a chave

### 4. Configurar no Projeto

#### Opção 1: Variável de Ambiente (Recomendado)

```bash
# No seu terminal local
export RAPIDAPI_KEY=sua_chave_aqui

# Ou adicionar ao ~/.bashrc ou ~/.zshrc
echo 'export RAPIDAPI_KEY=sua_chave_aqui' >> ~/.bashrc
source ~/.bashrc
```

#### Opção 2: Arquivo .env

Crie um arquivo `.env` na raiz do projeto:

```bash
RAPIDAPI_KEY=sua_chave_aqui
```

E carregue no código (precisa instalar `python-dotenv`):

```python
from dotenv import load_dotenv
load_dotenv()
```

#### Opção 3: Docker/VPS

No `docker-compose.yml` ou ao iniciar o container:

```yaml
environment:
  - RAPIDAPI_KEY=sua_chave_aqui
```

Ou ao executar:

```bash
docker run -e RAPIDAPI_KEY=sua_chave_aqui ...
```

## 🧪 Testar

Após configurar a chave, teste:

```bash
# Definir chave
export RAPIDAPI_KEY=sua_chave_aqui

# Testar
python3 test_alternativas.py oprimorico
```

## 📊 Limites

Verifique os limites do seu plano no RapidAPI:
- Plano gratuito geralmente tem limite de requisições por mês
- Planos pagos têm limites maiores

## 🔄 Ordem de Tentativas

Com a RapidAPI configurada, a ordem de tentativas é:

1. **RapidAPI TikTok Scraper** ← Primeira tentativa (mais confiável)
2. TikWM API
3. Countik
4. Urlebird com Selenium
5. Urlebird com requests

## 💡 Dica

Se você não quiser usar RapidAPI (por causa dos limites ou custo), o código automaticamente pula para as próximas alternativas.
