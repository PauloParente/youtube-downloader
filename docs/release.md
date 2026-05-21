# Release — executável Windows

Checklist para publicar um novo `.zip` do YouTube Downloader. Comandos detalhados: [build.ps1](../build.ps1). Git e tags: [git-workflow.md](git-workflow.md).

## Pré-requisitos

- Código integrado na **`main`** (PR mergeado, CI verde).
- `APP_VERSION` em `src/youtube_downloader/config.py` alinhada com a tag (ex.: `1.2.0` → tag `v1.2.0`).

## Checklist

| # | Passo | Comando / verificação |
|---|--------|------------------------|
| 1 | Versão | Atualizar `APP_VERSION` em `config.py` |
| 2 | Testes | `python -m pytest` (mesmo ambiente que o CI: `requirements-lock.txt`) |
| 3 | Smoke app | `python main.py` — download de vídeo curto; playlist opcional |
| 4 | Build | `.\build.ps1` |
| 5 | FFmpeg no pacote | Existe `dist\YouTubeDownloader\ffmpeg\ffmpeg.exe` |
| 6 | Sem settings do dev | `build.ps1` remove `settings.json` do `dist` (caminhos locais) |
| 7 | Testar .exe | `dist\YouTubeDownloader\YouTubeDownloader.exe` — merge, settings, pasta `downloads` |
| 8 | Zip | Compactar a pasta inteira `dist\YouTubeDownloader` (~150–200 MB) |
| 9 | Tag | Em `main`: `git tag -a v1.2.0 -m "chore(release): v1.2.0"` → `git push origin v1.2.0` |
| 10 | GitHub Release | Anexar o `.zip` à release da tag |

## Distribuição

- Quem recebe o zip só extrai e abre o `.exe` — sem Python nem FFmpeg no sistema.
- A pasta `downloads` é criada **ao lado do .exe**.
- O pacote inclui licença do FFmpeg em `ffmpeg\LICENSE.txt` (GPL).
- Não incluir `settings.json`, `history.json`, cookies ou credenciais no zip.

## Comandos úteis

```powershell
.\.venv\Scripts\python.exe -m pytest
python main.py
.\build.ps1
git tag -a v1.2.0 -m "chore(release): v1.2.0"
git push origin v1.2.0
```
