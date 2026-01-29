#!/bin/bash
# Script para limpar arquivos desnecessários na VPS

echo "🧹 Limpando arquivos desnecessários..."

cd ~/tiktok-downloader-api || exit 1

# Remover arquivos de documentação
rm -f *.md *.txt *.sh 2>/dev/null
rm -f DEPLOY_* COMANDOS_* 2>/dev/null

# Remover arquivos de teste (se existirem)
rm -f test_*.py 2>/dev/null

# Remover cache Python
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null

# Remover arquivos de lock
rm -f *.lock 2>/dev/null

# Limpar downloads antigos (manter apenas estrutura)
if [ -d "downloads" ]; then
    find downloads/ -type f -name "*.mp4" -mtime +1 -delete 2>/dev/null
    echo "✅ Downloads antigos removidos"
fi

# Remover venv se existir (não deve estar no repo)
if [ -d "venv" ]; then
    echo "⚠️  Pasta venv encontrada (não deveria estar no repo)"
    read -p "Remover venv? (s/N): " resposta
    if [ "$resposta" = "s" ]; then
        rm -rf venv/
        echo "✅ venv removido"
    fi
fi

# Mostrar espaço liberado
echo ""
echo "📊 Espaço usado:"
du -sh . 2>/dev/null

echo ""
echo "✅ Limpeza concluída!"
