# ✅ Resumo da Configuração - Múltiplas Contas GitHub

## 🎯 O Que Foi Feito

Criei uma solução completa para você trabalhar com **duas contas do GitHub** (rafael-rangel e genesis) de forma automática no Cursor.

## 📁 Arquivos Criados

1. **`configurar-ssh-github.sh`** - Script principal para configurar SSH
2. **`setup-git-user.sh`** - Script para configurar cada repositório automaticamente
3. **`CONFIGURAR_GITHUB_MULTIPLAS_CONTAS.md`** - Guia completo detalhado
4. **`QUICK_START_GITHUB.md`** - Guia rápido de uso

## 🚀 Próximos Passos (IMPORTANTE!)

### 1. Execute o script de configuração SSH:

```bash
./configurar-ssh-github.sh
```

Este script vai:
- Gerar chaves SSH para ambas as contas
- Configurar o arquivo `~/.ssh/config`
- Mostrar as chaves públicas que você precisa adicionar no GitHub

### 2. Adicione as chaves no GitHub:

O script vai mostrar duas chaves públicas. Você precisa:

1. **Conta rafael-rangel**: 
   - Acesse: https://github.com/settings/keys
   - Clique em "New SSH key"
   - Cole a chave pública mostrada pelo script
   - Salve

2. **Conta genesis**:
   - Faça login na conta genesis
   - Acesse: https://github.com/settings/keys
   - Clique em "New SSH key"
   - Cole a segunda chave pública
   - Salve

### 3. Teste as conexões:

```bash
ssh -T git@github.com-rafael
# Deve mostrar: Hi Rafael-Rangel! You've successfully authenticated...

ssh -T git@github.com-genesis
# Deve mostrar: Hi genesis! You've successfully authenticated...
```

## ✅ Este Repositório Já Está Configurado!

O repositório atual (`workflow_multivideos`) já foi configurado para usar:
- **Conta**: rafael-rangel (pessoal)
- **Remote**: `git@github.com-rafael:Rafael-Rangel/orquestrador.git`
- **User**: Rafael Rangel
- **Email**: rafael@rangel.dev

## 🔄 Como Usar no Dia a Dia

### Para repositórios da conta pessoal (rafael-rangel):

```bash
git clone git@github.com-rafael:USUARIO/REPOSITORIO.git
cd REPOSITORIO
./setup-git-user.sh  # Se o script estiver no repositório
```

### Para repositórios da conta trabalho (genesis):

```bash
git clone git@github.com-genesis:USUARIO/REPOSITORIO.git
cd REPOSITORIO
./setup-git-user.sh  # Se o script estiver no repositório
```

### Se você já tem repositórios clonados:

1. Entre no diretório do repositório
2. Execute: `./setup-git-user.sh` (se o script estiver lá)
3. Ou configure manualmente:
   ```bash
   git config user.name "Rafael Rangel"  # ou "Genesis"
   git config user.email "rafael@rangel.dev"  # ou email da genesis
   git remote set-url origin git@github.com-rafael:USUARIO/REPO.git
   ```

## 🎯 Como Funciona

1. **SSH Config** (`~/.ssh/config`): Define dois "hosts" diferentes:
   - `github.com-rafael` → usa chave da conta pessoal
   - `github.com-genesis` → usa chave da conta trabalho

2. **Git Config Local**: Cada repositório tem suas próprias configurações de `user.name` e `user.email`

3. **Cursor/VS Code**: Usa automaticamente as configurações do Git de cada repositório

## ⚠️ Importante

- **Antes de fazer push**: Certifique-se de que as chaves SSH foram adicionadas no GitHub
- **Email da conta genesis**: Você precisa editar o script `setup-git-user.sh` na linha 25 e colocar o email correto da conta genesis
- **Repositórios existentes**: Se você já tem repositórios clonados com HTTPS, converta para SSH usando o script `setup-git-user.sh`

## 🆘 Precisa de Ajuda?

Consulte os arquivos:
- `QUICK_START_GITHUB.md` - Guia rápido
- `CONFIGURAR_GITHUB_MULTIPLAS_CONTAS.md` - Guia completo detalhado
