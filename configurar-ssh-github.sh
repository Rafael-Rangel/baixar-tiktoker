#!/bin/bash

# Script para configurar SSH para múltiplas contas do GitHub
# Este script cria as chaves SSH e configura o arquivo ~/.ssh/config

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "🔐 Configurando SSH para múltiplas contas do GitHub"
echo ""

# Criar diretório .ssh se não existir
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Verificar se as chaves já existem
if [ -f ~/.ssh/id_ed25519_rafael ] && [ -f ~/.ssh/id_ed25519_genesis ]; then
    echo -e "${YELLOW}⚠${NC} Chaves SSH já existem. Pulando criação de chaves."
    echo "   Se quiser recriar, delete as chaves primeiro:"
    echo "   rm ~/.ssh/id_ed25519_rafael* ~/.ssh/id_ed25519_genesis*"
    echo ""
else
    echo "📝 Gerando chaves SSH..."
    echo ""
    
    # Gerar chave para conta pessoal (rafael-rangel)
    if [ ! -f ~/.ssh/id_ed25519_rafael ]; then
        echo "Gerando chave para conta rafael-rangel..."
        ssh-keygen -t ed25519 -C "stackflow.soft@gmail.com" -f ~/.ssh/id_ed25519_rafael -N ""
        echo -e "${GREEN}✓${NC} Chave criada: ~/.ssh/id_ed25519_rafael"
    fi
    
    # Gerar chave para conta trabalho (genesis)
    if [ ! -f ~/.ssh/id_ed25519_genesis ]; then
        echo "Gerando chave para conta genesis..."
        ssh-keygen -t ed25519 -C "gnstecnologiaoficial@gmail.com" -f ~/.ssh/id_ed25519_genesis -N ""
        echo -e "${GREEN}✓${NC} Chave criada: ~/.ssh/id_ed25519_genesis"
    fi
    
    echo ""
fi

# Configurar SSH Agent
echo "🔧 Configurando SSH Agent..."
eval "$(ssh-agent -s)" > /dev/null 2>&1

# Adicionar chaves ao agent
if ! ssh-add -l | grep -q "id_ed25519_rafael"; then
    ssh-add ~/.ssh/id_ed25519_rafael 2>/dev/null || true
fi

if ! ssh-add -l | grep -q "id_ed25519_genesis"; then
    ssh-add ~/.ssh/id_ed25519_genesis 2>/dev/null || true
fi

echo -e "${GREEN}✓${NC} Chaves adicionadas ao SSH Agent"
echo ""

# Criar/atualizar arquivo ~/.ssh/config
echo "📝 Configurando ~/.ssh/config..."

SSH_CONFIG="$HOME/.ssh/config"

# Backup do config existente se não tiver nossa configuração
if [ -f "$SSH_CONFIG" ] && ! grep -q "github.com-rafael" "$SSH_CONFIG"; then
    cp "$SSH_CONFIG" "$SSH_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"
    echo "Backup criado: $SSH_CONFIG.backup.*"
fi

# Criar configuração SSH
cat > "$SSH_CONFIG" << 'EOF'
# Configuração para múltiplas contas do GitHub
# Gerado automaticamente pelo script configurar-ssh-github.sh

# Conta pessoal - rafael-rangel
Host github.com-rafael
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_rafael
    IdentitiesOnly yes
    AddKeysToAgent yes

# Conta trabalho - genesis
Host github.com-genesis
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_genesis
    IdentitiesOnly yes
    AddKeysToAgent yes

# Host padrão github.com (usa a primeira chave encontrada)
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_rafael
    IdentitiesOnly yes
EOF

chmod 600 "$SSH_CONFIG"
echo -e "${GREEN}✓${NC} Arquivo ~/.ssh/config configurado"
echo ""

# Mostrar chaves públicas para adicionar no GitHub
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 PRÓXIMOS PASSOS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Adicione as chaves públicas ao GitHub:"
echo ""
echo "   ${YELLOW}Conta rafael-rangel:${NC}"
echo "   https://github.com/settings/keys"
echo ""
cat ~/.ssh/id_ed25519_rafael.pub | sed 's/^/   /'
echo ""
echo "   ${YELLOW}Conta genesis:${NC}"
echo "   https://github.com/settings/keys"
echo ""
cat ~/.ssh/id_ed25519_genesis.pub | sed 's/^/   /'
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "2. Depois de adicionar as chaves, teste as conexões:"
echo ""
echo "   ssh -T git@github.com-rafael"
echo "   ssh -T git@github.com-genesis"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}✅ Configuração SSH concluída!${NC}"
echo ""
