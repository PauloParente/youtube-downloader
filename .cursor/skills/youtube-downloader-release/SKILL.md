---
name: youtube-downloader-release
description: >-
  Prepara release do executável Windows: APP_VERSION, pytest, build.ps1,
  validação de dist, zip com FFmpeg, tag vX.Y.Z em main. Use para release,
  tag, build.ps1, distribuir zip, APP_VERSION ou empacotar FFmpeg.
disable-model-invocation: true
---

# YouTube Downloader — release (.exe)

Checklist operacional. Detalhes no [README.md](../../../README.md) (*Checklist de release*), [build.ps1](../../../build.ps1), Git: [docs/git-workflow.md](../../../docs/git-workflow.md).

## Pré-requisito Git

- Código na **`main`** (PR mergeado, CI verde).
- Versão e tag alinhadas — skill `youtube-downloader-git` para o passo de tag.

## Checklist

| # | Passo | Comando / arquivo |
|---|--------|-------------------|
| 1 | Versão | `APP_VERSION` em `src/youtube_downloader/config.py` (ex.: `1.2.0`) |
| 2 | Testes | `python -m pytest` (CI usa `requirements-lock.txt`) |
| 3 | Smoke app | `python main.py` — vídeo curto; playlist opcional |
| 4 | Build | `.\build.ps1` |
| 5 | FFmpeg no pacote | `dist\YouTubeDownloader\ffmpeg\ffmpeg.exe` existe |
| 6 | Sem settings do dev | `build.ps1` remove `dist\...\settings.json` (caminhos de outra máquina) |
| 7 | Testar .exe | `dist\YouTubeDownloader\YouTubeDownloader.exe` — merge, settings, pasta downloads |
| 8 | Zip | Compactar pasta inteira `dist\YouTubeDownloader` |
| 9 | Tag GitHub | Em `main`: `git tag -a v1.2.0 -m "chore(release): v1.2.0"` → `git push origin v1.2.0` |
| 10 | Release GitHub | Anexar zip à release da tag (se publicar no GitHub) |

## Não commitar

- `dist/`, `downloads/`, `logs/`, `.venv/`, `vendor/`
- `settings.json`, `history.json`, cookies, credenciais

## Distribuição

- `settings.example.json`: preferir `"output_dir": "downloads"` (relativo).
- FFmpeg no zip é **GPL** — aviso no README e [CONTRIBUTING.md](../../../CONTRIBUTING.md).

## Comandos úteis

```powershell
.\.venv\Scripts\python.exe -m pytest
python main.py
.\build.ps1
git tag -a v1.2.0 -m "chore(release): v1.2.0"
git push origin v1.2.0
```

## Não fazer

- Incluir `settings.json` pessoal no zip ou em `dist/`.
- Bump de versão só no README sem `config.py`.
- Publicar release sem pytest verde (jobs `test` e `test-ubuntu` no GitHub).
- Tag sem estar em `main` atualizada.
