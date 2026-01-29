# 🔧 Instalar Chrome para Testes Locais

O script de teste precisa do Chrome instalado. Siga os passos abaixo:

## Ubuntu/Debian/Pop!_OS

```bash
# Opção 1: Instalar Google Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install ./google-chrome-stable_current_amd64.deb

# Opção 2: Instalar Chromium (mais leve)
sudo apt update
sudo apt install chromium-browser
```

## Após Instalar

Teste se o Chrome está funcionando:

```bash
google-chrome --version
# ou
chromium --version
```

Depois rode o teste:

```bash
cd "/home/rafael/Área de trabalho/Projetos/tiktok-api"
source venv/bin/activate
python3 test_selenium.py oprimorico 1
```

## Alternativa: Testar Direto na VPS

Se não quiser instalar Chrome localmente, você pode testar direto na VPS onde o Chrome já está instalado no Docker.
