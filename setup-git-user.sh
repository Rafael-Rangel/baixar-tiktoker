#!/bin/bash

# Script para configurar automaticamente user.name e user.email do Git
# baseado no diretório do projeto

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Obter o diretório atual do repositório Git
REPO_DIR=$(git rev-parse --show-toplevel 2>/dev/null)

if [ -z "$REPO_DIR" ]; then
    echo "❌ Erro: Este não é um repositório Git válido."
    exit 1
fi

# Detectar qual conta usar baseado no caminho do diretório
# Ajuste os caminhos abaixo conforme sua estrutura de pastas

if [[ "$REPO_DIR" == *"genesis"* ]] || [[ "$REPO_DIR" == *"Genesis"* ]] || [[ "$REPO_DIR" == *"GENESIS"* ]]; then
    # Conta trabalho - genesis
    USER_NAME="Genesis"
    USER_EMAIL="gnstecnologiaoficial@gmail.com"
    GITHUB_HOST="github.com-genesis"
    echo -e "${GREEN}✓${NC} Detectado: Conta GENESIS (trabalho)"
elif [[ "$REPO_DIR" == *"rafael"* ]] || [[ "$REPO_DIR" == *"Rafael"* ]] || [[ "$REPO_DIR" == *"pessoal"* ]] || [[ "$REPO_DIR" == *"Pessoal"* ]]; then
    # Conta pessoal - rafael-rangel
    USER_NAME="Rafael Rangel"
    USER_EMAIL="stackflow.soft@gmail.com"
    GITHUB_HOST="github.com-rafael"
    echo -e "${GREEN}✓${NC} Detectado: Conta RAFAEL-RANGEL (pessoal)"
else
    # Padrão: usar conta pessoal
    USER_NAME="Rafael Rangel"
    USER_EMAIL="stackflow.soft@gmail.com"
    GITHUB_HOST="github.com-rafael"
    echo -e "${YELLOW}⚠${NC} Não detectado padrão específico. Usando conta pessoal (padrão)."
fi

# Configurar Git localmente
echo ""
echo "Configurando Git para este repositório:"
echo "  Diretório: $REPO_DIR"
echo "  Nome: $USER_NAME"
echo "  Email: $USER_EMAIL"
echo "  GitHub Host: $GITHUB_HOST"
echo ""

git config user.name "$USER_NAME"
git config user.email "$USER_EMAIL"

# Verificar e atualizar remote se necessário
CURRENT_REMOTE=$(git remote get-url origin 2>/dev/null)

if [ -n "$CURRENT_REMOTE" ]; then
    # Se o remote usa HTTPS, converter para SSH
    if [[ "$CURRENT_REMOTE" == https://github.com/* ]]; then
        REPO_PATH=$(echo "$CURRENT_REMOTE" | sed 's|https://github.com/||' | sed 's|\.git$||')
        NEW_REMOTE="git@${GITHUB_HOST}:${REPO_PATH}.git"
        echo "Atualizando remote de HTTPS para SSH..."
        git remote set-url origin "$NEW_REMOTE"
        echo -e "${GREEN}✓${NC} Remote atualizado: $NEW_REMOTE"
    # Se já é SSH mas com host errado, corrigir
    elif [[ "$CURRENT_REMOTE" == git@github.com:* ]] && [[ "$CURRENT_REMOTE" != *"$GITHUB_HOST"* ]]; then
        REPO_PATH=$(echo "$CURRENT_REMOTE" | sed 's|git@github.com:||' | sed 's|git@github.com-.*:||')
        NEW_REMOTE="git@${GITHUB_HOST}:${REPO_PATH}"
        echo "Corrigindo host do remote SSH..."
        git remote set-url origin "$NEW_REMOTE"
        echo -e "${GREEN}✓${NC} Remote atualizado: $NEW_REMOTE"
    else
        echo -e "${GREEN}✓${NC} Remote já está configurado corretamente"
    fi
fi

echo ""
echo -e "${GREEN}✅ Configuração concluída!${NC}"
echo ""
echo "Configuração atual:"
git config --local --list | grep -E "(user\.|remote\.origin\.url)" | sed 's/^/  /'
