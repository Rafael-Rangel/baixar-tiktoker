# 🧪 Guia de Teste do Selenium

Script para testar o Selenium localmente e ver o navegador funcionando antes de fazer deploy na VPS.

## 📋 Pré-requisitos

1. **Chrome/Chromium instalado** no seu sistema
   - Ubuntu/Debian: `sudo apt install chromium-browser` ou `sudo apt install google-chrome-stable`
   - O script usa `undetected-chromedriver` que baixa o ChromeDriver automaticamente

2. **Python 3.8+** instalado

## 🚀 Como Usar

### Opção 1: Usar ambiente virtual (recomendado)

```bash
# 1. Criar ambiente virtual (se ainda não criou)
python3 -m venv venv

# 2. Ativar ambiente virtual
source venv/bin/activate

# 3. Instalar dependências
pip install selenium undetected-chromedriver beautifulsoup4 requests setuptools

# 4. Rodar teste VISÍVEL (você verá o navegador abrir)
python3 test_selenium.py oprimorico 1

# Ou rodar em modo HEADLESS (sem interface gráfica)
python3 test_selenium.py oprimorico 2
```

### Opção 2: Instalar globalmente (não recomendado)

```bash
pip install --user selenium undetected-chromedriver beautifulsoup4 requests setuptools
python3 test_selenium.py oprimorico 1
```

## 📝 Exemplos de Uso

```bash
# Teste visível com username "oprimorico"
python3 test_selenium.py oprimorico 1

# Teste headless (sem abrir navegador)
python3 test_selenium.py oprimorico 2

# Teste interativo (pergunta username e modo)
python3 test_selenium.py
```

## 🎯 O que o Script Faz

1. ✅ Abre Chrome com configurações anti-detecção
2. ✅ Acessa `https://urlebird.com/pt/user/{username}/`
3. ✅ Aguarda página carregar completamente
4. ✅ Extrai HTML e procura links de vídeo
5. ✅ Mostra resultados no terminal
6. ✅ **Mantém navegador aberto** (modo visível) para você ver

## 📊 Saída Esperada

```
============================================================
🧪 TESTE SELENIUM - Urlebird
============================================================
Username: @oprimorico
Modo: VISÍVEL (você verá o navegador abrir)
============================================================

📌 URL: https://urlebird.com/pt/user/oprimorico/

🌐 Abrindo navegador... (aguarde alguns segundos)
🔧 Criando driver Chrome...
✅ Driver criado com sucesso!

🛡️ Aplicando proteções anti-detecção...
✅ Proteções aplicadas!

🌐 Acessando página: https://urlebird.com/pt/user/oprimorico/
✅ Página carregada!

⏳ Aguardando conteúdo carregar...
✅ Conteúdo carregado!

📊 Verificando status da página...
   URL atual: https://urlebird.com/pt/user/oprimorico/
   Título: oprimorico (@oprimorico) | Urlebird

📄 Extraindo HTML da página...
   Tamanho do HTML: 123456 caracteres

🔍 Procurando links de vídeo...
✅ Vídeo encontrado!
   URL Urlebird: https://urlebird.com/pt/video/oprimorico-1234567890/

✅ URL do TikTok extraída:
   https://www.tiktok.com/@oprimorico/video/1234567890

============================================================
👀 NAVEGADOR ABERTO - Você pode ver a página agora!
   Feche o navegador quando terminar de visualizar
============================================================

Pressione ENTER para fechar o navegador...
```

## ⚠️ Troubleshooting

### Erro: "ChromeDriver não encontrado"
- O `undetected-chromedriver` baixa automaticamente
- Certifique-se de ter Chrome/Chromium instalado

### Erro: "403 Forbidden"
- O Urlebird pode estar bloqueando mesmo com Selenium
- Tente novamente mais tarde
- Verifique se o Chrome está atualizado

### Navegador não abre
- Verifique se tem interface gráfica (X11/Wayland)
- Use modo headless: `python3 test_selenium.py oprimorico 2`

## 🎬 Próximos Passos

Após testar localmente e verificar que funciona:

1. ✅ Fazer commit das mudanças
2. ✅ Fazer deploy na VPS
3. ✅ Testar endpoint `/channels/latest` na VPS
