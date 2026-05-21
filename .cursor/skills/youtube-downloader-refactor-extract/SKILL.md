---
name: youtube-downloader-refactor-extract
description: >-
  Refatora com segurança: extrair UI ou lógica para ui_qt/ ou core/, PRs
  pequenos, pytest verde. Use ao refatorar, extrair view, reduzir main_window,
  mover código ou organizar módulos sem big-bang.
disable-model-invocation: true
---

# YouTube Downloader — refatoração (extrair / organizar)

Playbook de **estrutura**, não de feature nova. Regra: [`.cursor/rules/refactoring.mdc`](../../rules/refactoring.mdc). Mapa: [AGENTS.md](../../../AGENTS.md) (*Backlog de refatoração*). Git: skill `youtube-downloader-git`, [docs/git-workflow.md](../../../docs/git-workflow.md).

## Princípios

1. **Comportamento separado de estrutura** — PR que só move código (`refactor:`); outro PR se mudar regra de negócio (`feat:` / `fix:`).
2. **Extrair antes de reescrever** — copiar para destino, manter assinaturas públicas, `pytest` verde.
3. **Sem big-bang** — fatiar em passos pequenos; branch `refactor/<descricao>`.

## Workflow

```text
- [ ] 1. Verificar branch atual e branches existentes; manter, trocar ou criar `refactor/...` a partir de main (youtube-downloader-git, *Antes de editar código*)
- [ ] 2. Identificar bloco (UI → ui_qt/; puro → core/)
- [ ] 3. Copiar/mover; shell deixa callbacks + registro
- [ ] 4. python -m pytest
- [ ] 5. Smoke opcional: python main.py
- [ ] 6. Commit refactor(ui): ou refactor(core): — PR separado se houver feat depois
```

## Extrair view

| Passo | Onde |
|-------|------|
| Nova classe view | `src/youtube_downloader/ui_qt/<nome>_view.py` |
| Sidebar | `nav_registry.py` / `nav_sidebar.py` |
| Registro | `main_window.py` |
| Dependências | Construtor com callbacks (`on_*`), evitar import circular |
| Fila / worker | Permanecem no shell; view só emite eventos/callbacks |

Ver skill `youtube-downloader-ui-view` para threading Qt e tema.

## Extrair lógica para core/

- Sem import de `PySide6` / Qt em `core/`.
- Função pura extraída → `tests/test_<modulo>.py`.
- Manter nomes e contratos estáveis na primeira extração.

## Testes após cada fatia

```powershell
python -m pytest
```

CI roda Windows + Ubuntu; paths em testes: multiplataforma (evitar só `C:\...` em asserts POSIX).

## Não fazer

- Feature nova + refactor gigante no mesmo PR.
- UI nova grande dentro de `main_window.py` sem extrair view.
- Renomear módulos em massa ou adicionar `ruff`/`mypy` sem pedido do mantenedor.
- Dizer "refatorado" sem `pytest` verde.
- Commits sem Conventional Commits.

## Quando parar e pedir ajuda

- Mudança de comportamento inevitável na mesma fatia → dois PRs (`refactor` depois `feat`/`fix`) — ver `youtube-downloader-git`.
- Conflito de fila / ownership de eventos → documentar em AGENTS ou comentário mínimo no shell.
