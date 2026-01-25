# 🚀 Quick Start - Configuração Rápida

## 1️⃣ Executar Script de Configuração SSH

```bash
./configurar-ssh-github.sh
```

Este script vai:
- ✅ Gerar chaves SSH para ambas as contas
- ✅ Configurar o arquivo `~/.ssh/config`
- ✅ Mostrar as chaves públicas para você adicionar no GitHub

## 2️⃣ Adicionar Chaves no GitHub

O script vai mostrar as chaves públicas. Copie cada uma e adicione em:
- **Conta rafael-rangel**: https://github.com/settings/keys
- **Conta genesis**: https://github.com/settings/keys

## 3️⃣ Testar Conexões

```bash
ssh -T git@github.com-rafael
ssh -T git@github.com-genesis
```

## 4️⃣ Configurar Este Repositório

```bash
./setup-git-user.sh
```

Este script detecta automaticamente qual conta usar e configura tudo!

## 📝 Para Novos Repositórios

### Clone com SSH correto:

**Conta pessoal (rafael-rangel):**
```bash
git clone git@github.com-rafael:USUARIO/REPOSITORIO.git
```

**Conta trabalho (genesis):**
```bash
git clone git@github.com-genesis:USUARIO/REPOSITORIO.git
```

### Ou configure depois do clone:

```bash
cd repositorio
./setup-git-user.sh  # Se o script estiver no repositório
# OU configure manualmente:
git config user.name "Rafael Rangel"
git config user.email "rafael@rangel.dev"
git remote set-url origin git@github.com-rafael:USUARIO/REPOSITORIO.git
```

## 🎯 Como Funciona

- **SSH Config**: Define hosts diferentes (`github.com-rafael` e `github.com-genesis`) que usam chaves diferentes
- **Git Config Local**: Cada repositório tem seu próprio `user.name` e `user.email`
- **Cursor/VS Code**: Usa automaticamente as configurações do Git

## ⚠️ Importante

Se você já tem repositórios clonados com HTTPS, converta para SSH:

```bash
# Ver remote atual
git remote -v

# Converter para SSH (exemplo para conta pessoal)
git remote set-url origin git@github.com-rafael:USUARIO/REPOSITORIO.git
```
