---
name: youtube-downloader-git
description: >-
  Protocolo Git do projeto: verificar branch e branches existentes ANTES de
  editar código; GitHub Flow, uma branch por assunto/PR, checklist antes de
  commit/push, stash se branch errada, Conventional Commits, PR, tags. Use em
  git, branch, commit, push, pull request, merge, tag ou ao iniciar qualquer
  implementação.
---

# YouTube Downloader — Git (agentes e contribuidores)

Referência: [docs/git-workflow.md](../../../docs/git-workflow.md). Regra: [`.cursor/rules/git-workflow.mdc`](../../rules/git-workflow.mdc).

## Modelo

- **GitHub Flow** — `main` estável; trabalho em branch curta; integração via **PR**; **squash merge** recomendado.
- **Conventional Commits obrigatórios** em todas as mensagens.

## Antes de editar código (obrigatório para agentes)

**Não** alterar ficheiros do projeto até concluir esta verificação e decidir a branch. Aplica-se a features, fixes, UI, docs, refactor e testes.

### 1. Recolher contexto Git

Correr em paralelo:

```powershell
git fetch origin
git branch --show-current
git branch -a
git status
git log -5 --oneline
```

Opcional se a branch já existir há tempo: `git log origin/main..HEAD --oneline` e `git diff origin/main...HEAD --stat`.

### 2. Identificar o assunto do pedido

Resumir em uma linha (ex.: `feat/ui-appearance-toggle`, `docs/git-workflow`, `fix/core-download-cancel`). O **prefixo** da branch deve corresponder ao tipo de trabalho (`feat/`, `fix/`, `docs/`, etc.).

### 3. Avaliar: manter branch atual ou trocar?

| Situação | Ação |
|----------|------|
| Branch atual **é** a do assunto (nome alinhado; commits/diff só deste assunto; PR ainda aberto ou trabalho em curso) | **Manter** e desenvolver aqui |
| Já existe `origin/<tipo>/<assunto>` (ou local) para **o mesmo** pedido e não há conflito com outro trabalho | **Checkout** dessa branch; `git pull` se já publicada |
| Assunto **novo**, branch com outro nome, ou branch de PR **já mergeada** em `main` | **Nova branch** a partir de `main` atualizada (ver abaixo) |
| Pedido é só documentação/regras Cursor e a branch ativa é `feat/` ou `fix/` | **Trocar** para `docs/...` — não misturar |
| `git status` com alterações de **outro** assunto na branch errada | **Não** commitar; `git stash` (caminhos específicos) → branch correta → `stash pop` |

Se houver dúvida entre manter e criar nova, preferir **branch nova** a partir de `main` (evita misturar PRs).

### 4. Comunicar ao usuário (breve)

Antes da primeira edição de código, indicar em 1–2 frases:

- branch em que vai trabalhar (ou que vai criar);
- motivo (ex.: “assunto novo”, “continuação de `feat/ui-…`”, “estava em `docs/…`, a criar `feat/…`”).

### 5. Preparar a branch escolhida

**Manter branch atual:** `git pull` se existir `origin/<branch>` e fizer sentido sincronizar.

**Nova branch ou troca:**

```powershell
git fetch origin
git checkout main
git pull origin main
git checkout -b <tipo>/<descricao-kebab>   # ou: git checkout <branch-existente>
```

Se `git status` não estiver limpo ao trocar, usar `git stash push -u -m "<assunto>"` antes do `checkout` e `git stash pop` na branch destino.

## Início de uma tarefa (branch nova)

Quando a decisão for criar branch (secção acima):

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
