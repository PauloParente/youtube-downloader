---
name: youtube-downloader-git
description: >-
  Protocolo Git do projeto: GitHub Flow, uma branch por assunto/PR, checklist
  antes de commit/push, recuperação com stash se branch errada, Conventional
  Commits, PR para main, squash merge, tags. Use em git, branch, commit, push,
  pull request, merge ou tag.
---

# YouTube Downloader — Git (agentes e contribuidores)

Referência: [docs/git-workflow.md](../../../docs/git-workflow.md). Regra: [`.cursor/rules/git-workflow.mdc`](../../rules/git-workflow.mdc).

## Modelo

- **GitHub Flow** — `main` estável; trabalho em branch curta; integração via **PR**; **squash merge** recomendado.
- **Conventional Commits obrigatórios** em todas as mensagens.

## Início de uma tarefa

```powershell
git fetch origin
git checkout main
git pull origin main
git checkout -b <tipo>/<descricao-kebab>
```

| Prefixo | Quando |
|---------|--------|
| `feat/` | Feature nova |
| `fix/` | Bug |
| `docs/` | Documentação |
| `refactor/` | Só mover/organizar código |
| `test/` | Só testes |
| `chore/` | Deps, build, housekeeping |
| `ci/` | Workflows GitHub Actions |

## Durante o desenvolvimento

- Diff mínimo; não misturar refactor grande + feature no mesmo PR (ver `youtube-downloader-refactor-extract`).
- `python -m pytest` antes de considerar pronto para PR.
- **Uma branch = um assunto = um PR.** Ao iniciar trabalho novo, criar branch a partir de `main` atualizada (ver *Início de uma tarefa*).

## Evitar confusão de branches (agentes)

Situação típica: implementaste o assunto B enquanto ainda estás na branch do assunto A (ou A já foi mergeada em `main`).

### Quando criar branch nova

| Situação | Ação |
|----------|------|
| Primeira alteração de um assunto novo | `main` atualizada → `git checkout -b <tipo>/<assunto>` |
| PR anterior já mergeado em `main` | Nova branch a partir de `main`; **não** commitar assunto novo na branch antiga |
| Branch atual não reflete o nome/assunto do commit | Não commitar; corrigir branch primeiro (abaixo) |
| Vários pedidos do usuário (splash, depois URL, etc.) | **Um PR por assunto** — branch separada para cada um |

### Checklist obrigatório antes de `git commit` ou `git push`

Correr em paralelo quando possível:

```powershell
git branch --show-current
git status
git diff
git log -5 --oneline
```

Validar:

1. **Branch** — nome alinhado ao assunto (ex. `fix/ui-url-tool-row-align` para alinhamento do campo URL).
2. **Ficheiros** — só os do assunto atual no stage; ignorar alterações locais de outras tarefas (docs Cursor, `AGENTS.md`, etc.) a menos que o usuário peça explicitamente.
3. **Base** — para PR, `git fetch origin` e `git diff origin/main...HEAD` deve refletir só este assunto.
4. **Comunicar** — antes de commit/push, informar o usuário: branch, lista de ficheiros, mensagem de commit proposta, link de PR se aplicável.

### Trabalho na branch errada (recuperação)

**Não** fazer commit do assunto B na branch do assunto A.

```powershell
# 1) Guardar só os ficheiros do assunto B
git stash push -m "<assunto-b>" -- caminho/para/ficheiro1 caminho/para/ficheiro2

# 2) Ir para main atualizada
git fetch origin
git checkout main
git pull origin main

# 3) Branch nova para B
git checkout -b <tipo>/<assunto-b>

# 4) Restaurar alterações
git stash pop

# 5) pytest → commit → push (só ficheiros de B)
```

Se `stash pop` gerar conflito, resolver antes de commitar.

### Após push de um assunto

- Se o PR desse assunto já foi mergeado: `git checkout main`, `git pull origin main`, apagar branch local/remota antiga.
- Trabalho seguinte: **sempre** nova branch a partir de `main` — não continuar na branch mergeada.

## Commit (somente se o usuário pedir)

1. Completar *Checklist obrigatório* (secção acima) — parar se branch/assunto não coincidirem.
2. `git status`
3. `git diff` e `git diff --staged`
4. `git log -5 --oneline` (estilo do repositório)
5. `git add` **apenas** caminhos do assunto atual (evitar `git add -A` se `status` misturar tarefas).
6. Mensagem **Conventional Commits**:

```text
<type>(<scope>): <imperativo curto>

[corpo opcional — por quê]
```

7. Não incluir: `settings.json`, `history.json`, `logs/`, `.venv/`, `dist/`, cookies, tokens.
8. Nunca `git config`, nunca `--no-verify`.

### Templates

```text
feat(ui): adicionar <o quê>
fix(core): corrigir <problema>
docs: atualizar <documento>
refactor(ui): extrair <módulo> de <origem>
test: cobrir <comportamento>
ci: <mudança no workflow>
chore(release): v1.2.0
```

## Push e Pull Request (somente se o usuário pedir)

Repetir checklist de branch/ficheiros. Confirmar que `origin/main` não foi deixada para trás se outro PR mergeou entretanto (`git fetch origin` antes do push).

### Pré-PR

- [ ] `python -m pytest`
- [ ] `git diff origin/main...HEAD` — revisar **todo** o branch
- [ ] Commits convencionais
- [ ] README se UX/instalação mudou
- [ ] Diff grande → `youtube-downloader-code-review` (read-only primeiro)

### Criar PR

- Base: **`main`**
- Título: linha de assunto convencional (ex. `feat(ui): …`)
- Corpo: [.github/pull_request_template.md](../../../.github/pull_request_template.md)

```powershell
git push -u origin HEAD
gh pr create --base main --title "feat(ui): descricao" --body "..."
```

Se `gh` não estiver instalado, informar o usuário ou usar API — não expor tokens em logs.

### Após merge

```powershell
git checkout main
git pull origin main
git branch -d <branch>
git push origin --delete <branch>
```

## Release (tag em `main`)

Após PR mergeado e checklist de `youtube-downloader-release`:

1. `APP_VERSION` em `config.py` alinhado à versão.
2. Tag: `git tag -a v1.2.0 -m "chore(release): v1.2.0"`
3. `git push origin v1.2.0`

## Skills relacionadas

| Momento | Skill |
|---------|--------|
| Implementação com logs novos | `youtube-downloader-logging` |
| Antes do PR (diff relevante) | `youtube-downloader-code-review` |
| Refactor / extrair módulos | `youtube-downloader-refactor-extract` |
| Empacotar `.exe` + zip | `youtube-downloader-release` |
| Bug | `youtube-downloader-bugfix` → depois este fluxo |

## Proibido (agentes)

- Commit, push ou PR sem pedido explícito do usuário.
- Push ou merge direto em `main`.
- Force-push em `main`.
- Alterar `git config`.
- `--no-verify` nos hooks.
- Commitar arquivos locais listados em `.gitignore` / `docs/git-workflow.md`.

## Não fazer

- GitFlow (`develop`, release branches longas) — fora do padrão do projeto.
- Mensagens vagas (`update`, `fix stuff`, `WIP`).
- Um PR com dezenas de commits não relacionados sem squash na integração.
