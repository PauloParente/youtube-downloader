---
name: youtube-downloader-refactor-extract
description: >-
  Refatora com segurança: extrair UI ou lógica de app.py para ui/ ou core/,
  PRs pequenos, pytest verde. Use ao refatorar, extrair view, reduzir app.py,
  mover código ou organizar módulos sem big-bang.
disable-model-invocation: true
---

# YouTube Downloader — refatoração (extrair / organizar)

Playbook de **estrutura**, não de feature nova. Regra: [`.cursor/rules/refactoring.mdc`](../../rules/refactoring.mdc). Mapa: [AGENTS.md](../../../AGENTS.md) (*Backlog de refatoração*).

## Princípios

1. **Comportamento separado de estrutura** — commit/PR que só move código; outro PR só se mudar regra de negócio.
2. **Extrair antes de reescrever** — copiar para destino, manter assinaturas públicas, `pytest` verde.
3. **Sem big-bang** — fatiar `app.py` em passos pequenos.

## Workflow

```text
- [ ] 1. Identificar bloco (UI → ui/<nome>_view.py; puro → core/)
- [ ] 2. Copiar/mover; app.py deixa callbacks + registro
- [ ] 3. python -m pytest
- [ ] 4. Smoke opcional: python main.py
- [ ] 5. Só então evoluir comportamento (outro PR se necessário)
```

## Extrair view de app.py

| Passo | Onde |
|-------|------|
| Nova classe view | `src/youtube_downloader/ui/<nome>_view.py` |
| Sidebar | `nav_sidebar.py` → `ITEMS` |
| Registro | `app.py` → `_view_frames["id"] = view` |
| Dependências | Construtor com `Callable` (`on_*`), não import circular desnecessário |
| Fila / worker | Permanecem no shell; view só emite eventos/callbacks |

Ver skill `youtube-downloader-ui-view` para threading e tema.

## Extrair lógica para core/

- Sem import de `customtkinter` / `tkinter` em `core/`.
- Função pura extraída → `tests/test_<modulo>.py`.
- Manter nomes e contratos estáveis na primeira extração.

## Testes após cada fatia

```powershell
python -m pytest
```

CI roda Windows + Ubuntu; paths em testes: multiplataforma (evitar só `C:\...` em asserts POSIX).

## Não fazer

- Feature nova + refactor gigante no mesmo PR.
- +200 linhas de UI novas dentro de `app.py`.
- Renomear módulos em massa ou adicionar `ruff`/`mypy` sem pedido do mantenedor.
- Dizer "refatorado" sem `pytest` verde.

## Quando parar e pedir ajuda

- Mudança de comportamento inevitável na mesma fatia → dividir em dois PRs ou confirmar com o usuário.
- Conflito de fila / ownership de `queue.Queue` → documentar em AGENTS ou comentário mínimo no shell.
