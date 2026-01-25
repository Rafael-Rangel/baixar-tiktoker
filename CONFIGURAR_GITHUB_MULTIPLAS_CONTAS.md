# 🔐 Configuração de Múltiplas Contas GitHub

Este guia configura seu ambiente para trabalhar automaticamente com duas contas do GitHub:
- **rafael-rangel** (pessoal) - `rafael@rangel.dev`
- **genesis** (trabalho) - email da conta genesis

## 📋 Pré-requisitos

1. Ter acesso às duas contas do GitHub
2. Ter permissões para adicionar SSH keys em ambas as contas

## 🚀 Passo a Passo

### 1. Gerar Chaves SSH para Cada Conta

Execute os comandos abaixo no terminal:

#### Para conta pessoal (rafael-rangel):
```bash
ssh-keygen -t ed25519 -C "rafael@rangel.dev" -f ~/.ssh/id_ed25519_rafael
```

#### Para conta trabalho (genesis):
```bash
ssh-keygen -t ed25519 -C "seu-email-genesis@exemplo.com" -f ~/.ssh/id_ed25519_genesis
```

**Importante:** Quando pedir senha, você pode deixar em branco (Enter) ou criar uma senha forte.

### 2. Adicionar Chaves ao SSH Agent

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519_rafael
ssh-add ~/.ssh/id_ed25519_genesis
```

### 3. Adicionar Chaves Públicas ao GitHub

#### Para conta rafael-rangel:
```bash
cat ~/.ssh/id_ed25519_rafael.pub
```
Copie a saída e adicione em: https://github.com/settings/keys (conta rafael-rangel)

#### Para conta genesis:
```bash
cat ~/.ssh/id_ed25519_genesis.pub
```
Copie a saída e adicione em: https://github.com/settings/keys (conta genesis)

### 4. Configurar SSH Config

O arquivo `~/.ssh/config` já foi criado automaticamente pelo script. Ele contém:

```
# Conta pessoal - rafael-rangel
Host github.com-rafael
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_rafael
    IdentitiesOnly yes

# Conta trabalho - genesis
Host github.com-genesis
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_genesis
    IdentitiesOnly yes
```

### 5. Testar Conexões SSH

```bash
ssh -T git@github.com-rafael
# Deve retornar: Hi Rafael-Rangel! You've successfully authenticated...

ssh -T git@github.com-genesis
# Deve retornar: Hi genesis! You've successfully authenticated...
```

### 6. Configurar Repositórios

#### Para repositórios da conta rafael-rangel:
```bash
git remote set-url origin git@github.com-rafael:USUARIO/REPOSITORIO.git
```

#### Para repositórios da conta genesis:
```bash
git remote set-url origin git@github.com-genesis:USUARIO/REPOSITORIO.git
```

### 7. Configuração Automática por Diretório (Opcional)

O script `setup-git-user.sh` pode ser usado para configurar automaticamente o usuário Git baseado no diretório do projeto.

## 🔄 Como Usar no Dia a Dia

### Opção A: Configuração Manual por Repositório

1. Clone o repositório normalmente
2. Configure o remote com o host correto:
   - `git@github.com-rafael:` para conta pessoal
   - `git@github.com-genesis:` para conta trabalho
3. Configure user.name e user.email localmente:
   ```bash
   git config user.name "Rafael Rangel"
   git config user.email "rafael@rangel.dev"
   ```

### Opção B: Script Automático

Use o script `setup-git-user.sh` que detecta automaticamente qual conta usar baseado em padrões de diretório.

## 📝 Notas Importantes

- **Cursor/VS Code** vai usar automaticamente as configurações do Git
- **Commits** vão usar o `user.name` e `user.email` configurados no repositório
- **Push/Pull** vão usar a chave SSH correta baseada no remote URL
- Você pode ter múltiplos repositórios abertos, cada um com sua própria configuração

## 🛠️ Troubleshooting

### Se o push falhar:
1. Verifique o remote: `git remote -v`
2. Certifique-se que está usando o host correto (`github.com-rafael` ou `github.com-genesis`)
3. Teste a conexão SSH: `ssh -T git@github.com-rafael`

### Se o commit usar email errado:
1. Verifique a configuração local: `git config user.email`
2. Configure manualmente: `git config user.email "email@correto.com"`
