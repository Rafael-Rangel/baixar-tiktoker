#!/bin/bash
# Script para copiar cookies.txt para a VPS

echo "📋 Copiando cookies.txt para a VPS..."
echo ""
echo "Opções:"
echo "1. Via SCP (recomendado se você tem acesso SSH)"
echo "2. Via edição manual (copiar/colar conteúdo)"
echo ""
read -p "Escolha uma opção (1 ou 2): " opcao

if [ "$opcao" == "1" ]; then
    echo ""
    echo "Execute este comando na sua máquina local:"
    echo ""
    echo "scp ~/Área\ de\ trabalho/Projetos/workflow_multivideos/cookies.txt root@SEU_IP_VPS:~/content-orchestrator/data/cookies.txt"
    echo ""
    echo "Depois, na VPS, execute:"
    echo "chown 1000:1000 ~/content-orchestrator/data/cookies.txt"
    echo "chmod 644 ~/content-orchestrator/data/cookies.txt"
    echo "docker compose restart content-orchestrator"
    echo ""
elif [ "$opcao" == "2" ]; then
    echo ""
    echo "1. Abra o arquivo cookies.txt localmente"
    echo "2. Copie TODO o conteúdo (Ctrl+A, Ctrl+C)"
    echo "3. Na VPS, execute:"
    echo ""
    echo "   nano ~/content-orchestrator/data/cookies.txt"
    echo ""
    echo "4. Cole o conteúdo (Ctrl+Shift+V ou botão direito → Paste)"
    echo "5. Salve (Ctrl+X, Y, Enter)"
    echo "6. Execute:"
    echo ""
    echo "   chown 1000:1000 ~/content-orchestrator/data/cookies.txt"
    echo "   chmod 644 ~/content-orchestrator/data/cookies.txt"
    echo "   docker compose restart content-orchestrator"
    echo ""
else
    echo "Opção inválida!"
    exit 1
fi
