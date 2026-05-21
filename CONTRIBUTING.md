# Contribuindo

Obrigado por ajudar no YouTube Downloader.

## Ambiente

1. Clone o repositório e crie um venv (veja [README.md](README.md) — seção *Começar do zero*).
2. Instale dependências: `pip install -r requirements-lock.txt` (reprodutível) ou `pip install -r requirements.txt -r requirements-dev.txt` (mais recentes dentro dos ranges).
3. Rode os testes antes de abrir PR: `python -m pytest`.

## Fluxo Git (resumo)

Detalhes em **[docs/git-workflow.md](docs/git-workflow.md)**.

- **GitHub Flow:** desenvolva em branch curta (`feat/`, `fix/`, etc.); integre na `main` **somente via Pull Request**.
- **Uma branch = um assunto = um PR** — após merge, crie branch nova para o próximo trabalho (não reutilize a branch antiga).
- **Squash merge** recomendado no GitHub (histórico da `main` com um commit por PR).
- **Conventional Commits obrigatórios** — ex.: `feat(ui): …`, `fix(core): …`, `docs: …`, `ci: …`.
- Não faça push direto na `main`.

### Abrir branch

```powershell
git fetch origin
git checkout main
git pull origin main
git checkout -b feat/minha-alteracao
```

### Antes do PR

- [ ] `python -m pytest`
- [ ] Revisar `git diff origin/main...HEAD`
- [ ] Commits no formato convencional
- [ ] README atualizado se mudou comportamento visível ou instalação

O CI (GitHub Actions) deve passar nos jobs **Windows** e **Ubuntu** (`pytest`; no Ubuntu, smoke de import `PySide6` com `QT_QPA_PLATFORM=offscreen`).

## Pull requests

- Base: **`main`**; compare: sua branch.
- Use o [template de PR](.github/pull_request_template.md).
- Após o merge, apague a branch (local e remota) se não for mais necessária.

## Commits

Formato [Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>(<scope opcional>): <descrição imperativa>
```

Tipos comuns: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`. Um assunto lógico por commit quando possível.

## O que não commitar

- `settings.json`, `history.json`, `downloads/`, `logs/`, `.venv/`, `vendor/`, `dist/`
- Credenciais ou cookies

## Distribuição com FFmpeg

O código do app está sob MIT ([LICENSE](LICENSE)). Ao distribuir o `.exe` gerado por `build.ps1`, o pacote inclui FFmpeg (GPL) — respeite a licença do FFmpeg e o aviso legal do README.

## Orientação para Cursor / agentes

- **[AGENTS.md](AGENTS.md)** — mapa do projeto, fluxos (download, preview), o que está implementado vs. pendente.
- **[docs/git-workflow.md](docs/git-workflow.md)** — protocolo Git completo.
- **[`.cursor/rules/`](.cursor/rules/)** — regras automáticas (`project-core`, `git-workflow`, `python-standards`, `ui-qt`, `refactoring`, `tests`).
- **[`.cursor/skills/`](.cursor/skills/)** — playbooks (`youtube-downloader-git`, `youtube-downloader-feature`, `ui-view`, `release`, `code-review`, etc.).

**Fluxo sugerido:** implementar → `python -m pytest` → `youtube-downloader-code-review` (se diff grande) → PR (skill `youtube-downloader-git`).

Leia o `AGENTS.md` antes de mudanças grandes em `app.py` ou ao ligar opções de Configurações ao downloader.

## Reportar bugs

Use o template de issue no GitHub e anexe trechos relevantes de `logs/app.log` e `logs/errors.log` quando possível.
