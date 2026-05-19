# Contribuindo

Obrigado por ajudar no YouTube Downloader.

## Ambiente

1. Clone o repositório e crie um venv (veja [README.md](README.md) — seção *Começar do zero*).
2. Instale dependências: `pip install -r requirements-lock.txt` (reprodutível) ou `pip install -r requirements.txt -r requirements-dev.txt` (mais recentes dentro dos ranges).
3. Rode os testes antes de abrir PR: `python -m pytest`.

## Branches e pull requests

- Trabalhe em um branch à parte; abra PR para `main`.
- Descreva o que mudou e por quê.
- Se alterar a interface, atualize o README quando fizer sentido.
- O CI (GitHub Actions) deve passar no Windows.

## Commits

- Mensagens claras em português ou inglês.
- Um assunto por commit quando possível (ex.: `fix: qualidade 1080p`, `docs: atualizar README`).

## O que não commitar

- `settings.json`, `history.json`, `downloads/`, `logs/`, `.venv/`, `vendor/`, `dist/`
- Credenciais ou cookies

## Distribuição com FFmpeg

O código do app está sob MIT ([LICENSE](LICENSE)). Ao distribuir o `.exe` gerado por `build.ps1`, o pacote inclui FFmpeg (GPL) — respeite a licença do FFmpeg e o aviso legal do README.

## Orientação para Cursor / agentes

- **[AGENTS.md](AGENTS.md)** — mapa do projeto, fluxos (download, preview), o que está implementado vs. pendente, backlog de refatoração.
- **[`.cursor/rules/`](.cursor/rules/)** — regras automáticas do Cursor (`project-core`, `python-standards`, `ui-customtkinter`, `refactoring`, `tests`).

Leia o `AGENTS.md` antes de mudanças grandes em `app.py` ou ao ligar opções de Configurações ao downloader.

## Reportar bugs

Use o template de issue no GitHub e anexe trechos relevantes de `logs/app.log` e `logs/errors.log` quando possível.
