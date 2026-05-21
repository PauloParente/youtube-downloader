# Fluxo Git — YouTube Downloader

Referência para contribuidores humanos e agentes Cursor. Complementa [CONTRIBUTING.md](../CONTRIBUTING.md) e [AGENTS.md](../AGENTS.md).

## Modelo: GitHub Flow

- A branch **`main`** está sempre integrável (CI verde, código utilizável).
- Desenvolvimento em **branches curtas** derivadas de `main`.
- Integração **somente via Pull Request** (sem push direto em `main`).
- Após o merge, apagar a branch (local e remota) quando não for mais necessária.

```text
main ──► feat/fix branch ──► PR ──► CI (Windows + Ubuntu) ──► squash merge ──► main
```

### Merge no GitHub (recomendado)

- **Squash merge** — um commit por PR na `main`, histórico legível.
- Configuração sugerida no repositório: *Settings → General → Pull Requests* → permitir squash; opcionalmente desabilitar merge commit; *Automatically delete head branches*.

### Proteção da `main` (configurar no GitHub)

- Exigir Pull Request antes de merge.
- Exigir status checks: jobs `test` e `test-ubuntu` do workflow [ci.yml](../.github/workflows/ci.yml).
- Não permitir force-push em `main`.

## Branches

### Atualizar `main` antes de criar branch

```powershell
git fetch origin
git checkout main
git pull origin main
```

### Nomenclatura (inglês, kebab-case)

| Prefixo | Uso |
|---------|-----|
| `feat/` | Nova funcionalidade |
| `fix/` | Correção de bug |
| `docs/` | Documentação |
| `refactor/` | Só reorganização (sem mudança de comportamento) |
| `test/` | Só testes |
| `chore/` | Manutenção (deps, scripts, build) |
| `ci/` | GitHub Actions / CI |

Exemplos: `feat/queue-drag-reorder`, `fix/ubuntu-qt-ci`, `docs/git-workflow`, `refactor/extract-queue-cards`.

**Uma branch = um assunto = um PR.** Não misturar correções ou features não relacionadas na mesma branch.

### Criar e publicar branch

```powershell
git checkout -b feat/minha-feature
# ... commits ...
git push -u origin HEAD
```

## Commits — Conventional Commits (obrigatório)

Formato:

```text
<type>(<scope opcional>): <descrição imperativa curta>

[corpo opcional — contexto e motivação]
```

### Tipos (`type`)

| Tipo | Uso |
|------|-----|
| `feat` | Comportamento novo |
| `fix` | Correção de bug |
| `docs` | README, AGENTS, `docs/` |
| `refactor` | Estrutura sem mudar comportamento |
| `test` | Apenas testes |
| `chore` | Housekeeping, build, deps |
| `ci` | `.github/workflows/` |

### Escopos (`scope`) — opcionais

`ui`, `core`, `ci`, `deps`, `docs`

### Exemplos do projeto

```text
feat(ui): adicionar arrastar URL na tela Downloads
fix(core): priorizar DASH em QUALITY_FORMATS
docs: documentar fluxo Git para agentes
refactor(ui): extrair cards da fila para queue_cards
test: cobrir build_ytdl_opts com cookies
ci: instalar libEGL no job Ubuntu
chore(release): v1.2.0
```

Regras:

- Assunto ≤ ~72 caracteres; imperativo (“adicionar”, não “adicionado”).
- Um assunto lógico por commit quando possível.
- Corpo em português ou inglês.

## O que não commitar

Nunca versionar (ver [.gitignore](../.gitignore)):

- `settings.json`, `history.json`
- `downloads/`, `logs/`, `dist/`, `.venv/`, `vendor/`
- Cookies, tokens, credenciais

## Pull Request

### Checklist antes de abrir

- [ ] `python -m pytest` passou localmente
- [ ] `git diff origin/main...HEAD` revisado (todo o branch, não só o último commit)
- [ ] Commits seguem Conventional Commits
- [ ] README atualizado se mudou UX ou instalação
- [ ] Nenhum arquivo local sensível no diff
- [ ] Para diff grande: revisão com skill `youtube-downloader-code-review`

### Abrir PR

- **Base:** `main`
- **Compare:** sua branch (`feat/...`, `fix/...`, etc.)
- Preencher o [template de PR](../.github/pull_request_template.md)

```powershell
# Com GitHub CLI (se instalado)
gh pr create --base main --title "feat(ui): descrição curta" --body-file .github/pull_request_template.md
```

Aguardar CI verde (Windows + Ubuntu). Preferir **squash merge** ao integrar.

### Após o merge

```powershell
git checkout main
git pull origin main
git branch -d feat/minha-feature
git push origin --delete feat/minha-feature   # se ainda existir no remoto
```

## Releases e tags

1. Código já está em `main` (via PR mergeado).
2. Seguir skill `youtube-downloader-release` (`APP_VERSION`, `build.ps1`, zip).
3. Criar tag anotada alinhada à versão:

```powershell
git tag -a v1.2.0 -m "chore(release): v1.2.0"
git push origin v1.2.0
```

`APP_VERSION` em `src/youtube_downloader/config.py` deve coincidir com a tag (sem o prefixo `v` no arquivo).

## Agentes Cursor

- Regra sempre ativa: [`.cursor/rules/git-workflow.mdc`](../.cursor/rules/git-workflow.mdc)
- Playbook detalhado: skill `youtube-downloader-git` em [`.cursor/skills/`](../.cursor/skills/)
- **Commit, push e PR somente quando o usuário pedir explicitamente.**
- Nunca `git config`, nunca `--no-verify`, nunca force-push em `main`.

### Antes de editar código (obrigatório)

Agentes **não** devem começar a implementar sem verificar Git:

1. `git fetch origin`, `git branch --show-current`, `git branch -a`, `git status`, `git log -5 --oneline`
2. Comparar o **pedido atual** com o nome da branch e commits locais (`git log origin/main..HEAD`, `git diff origin/main...HEAD` se útil)
3. **Decidir:** manter a branch (mesmo assunto em curso), fazer checkout de branch existente para o mesmo assunto, ou criar branch nova a partir de `main` (`git pull` + `git checkout -b <tipo>/<assunto>`)
4. **Comunicar** ao usuário a branch escolhida e o motivo antes da primeira alteração de ficheiro

Tabela completa e recuperação com stash: skill `youtube-downloader-git` (*Antes de editar código*).

### Evitar confusão ao trocar de branch

Problema comum: código do **assunto B** desenvolvido na branch do **assunto A**, ou commit após o PR de A já ter sido mergeado em `main`.

| Regra | Detalhe |
|-------|---------|
| Um assunto por branch | Ex.: splash → `fix/ui-splash-screen`; URL → `fix/ui-url-tool-row-align` (branches separadas) |
| Novo assunto após merge | `git checkout main` + `git pull` + **branch nova** — não reutilizar branch mergeada |
| Antes de codar | Verificar branch atual, `git branch -a`, decidir manter/trocar/criar; comunicar branch ao usuário |
| Antes de commit/push | Verificar `git branch --show-current`, `git status`, `git diff`; commitar só ficheiros do assunto |
| Branch errada | `git stash push` (caminhos específicos) → `main` → branch nova → `stash pop` — ver skill `youtube-downloader-git` |
| Comunicação | Agente informa branch, ficheiros no commit e URL do PR antes de push |

Evitar `git add -A` quando o working tree mistura alterações de tarefas diferentes.

## Fluxo completo sugerido

```text
verificar branch (atual + existentes) → decidir manter/trocar/criar → implementar
  → pytest → youtube-downloader-code-review (se necessário)
  → commit(s) convencionais → push → PR → CI verde → squash merge → limpar branch
```

Para bugs: `youtube-downloader-bugfix` → `pytest` → PR.

Para release: merge em `main` → `youtube-downloader-release` → tag `vX.Y.Z`.

## Referências externas

- [GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git branching guidance (Microsoft)](https://learn.microsoft.com/en-us/azure/devops/repos/git/git-branching-guidance)
