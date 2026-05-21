# YouTube Downloader

[![CI](https://github.com/PauloParente/youtube-downloader/actions/workflows/ci.yml/badge.svg)](https://github.com/PauloParente/youtube-downloader/actions/workflows/ci.yml)

Aplicativo desktop em Python para baixar vídeos e playlists do YouTube, com interface gráfica em PySide6 (Qt).

## Download (Windows)

Para usar sem instalar Python:

1. Abra [Releases](https://github.com/PauloParente/youtube-downloader/releases) e baixe o `.zip` da versão mais recente.
2. Extraia a pasta `YouTubeDownloader` e execute `YouTubeDownloader.exe`.

**Requisitos:** Windows 64 bits e internet. O pacote já inclui FFmpeg — não é preciso instalar Python nem FFmpeg.

A pasta `downloads` é criada ao lado do `.exe`. O zip inclui a licença do FFmpeg em `ffmpeg\LICENSE.txt` (GPL).

Para gerar o `.exe` a partir do código-fonte, veja [Gerar executável](#gerar-executável-exe). Checklist de publicação: [docs/release.md](docs/release.md).

## Funcionalidades

- Download de vídeo único; **playlist** expande para vários itens na fila (um job por vídeo)
- Preview com thumbnail e título ao colar a URL
- Qualidade (melhor disponível, 1080p, 720p, 480p), MP3 e merge **MP4** ou **WebM** (FFmpeg)
- **Perfil de exportação:** H.264 compatível com Windows ou melhor qualidade (AV1/VP9)
- Sidebar: **Downloads**, **Fila**, **Biblioteca**, **Histórico**, **Configurações**
- Fila sequencial com progresso, cancelar, pular e remover itens — ver [docs/ux-downloads-queue.md](docs/ux-downloads-queue.md)
- Preferências em `settings.json` (pasta, formato, banda, legendas, tema, `cookies.txt`, notificações)
- Histórico com reabrir arquivo/pasta e **Baixar de novo**; **Biblioteca** lista a pasta de destino
- Tema claro/escuro; identidade visual em [docs/design-system.md](docs/design-system.md)

Backlog futuro: [ROADMAP.md](ROADMAP.md).

## Uso

1. Na sidebar, abra **Downloads**
2. Cole a URL do vídeo ou da playlist (`Ctrl+V`)
3. Ajuste pasta e opções em **Configurações** (`Ctrl+,`) se necessário
4. Escolha qualidade ou **Somente áudio (MP3)**
5. **Baixar** inicia (ou enfileira e começa o primeiro); **+ Fila** só enfileira

**Playlists:** link `playlist?list=…` ou *Playlist inteira* quando a URL traz `list=` — cada vídeo vira um item na fila. URL só com `watch?v=` baixa um vídeo. Abra **Fila** para ver o atual e os pendentes; **Pular** avança; **Cancelar** interrompe e esvazia a fila. A fila não é salva ao fechar o app.

**Histórico** registra conclusões; **Biblioteca** lista arquivos na pasta de destino.

## Desenvolvimento

### Requisitos

- Python 3.10+
- **PySide6** e dependências via `pip` (ver abaixo)
- **FFmpeg** no PATH (vídeo/MP3 com merge)
  - **Windows:** PATH, `%LOCALAPPDATA%\ffmpeg`, ou `.\build.ps1` uma vez → `vendor\ffmpeg\bin`
  - **Linux:** ex. `sudo apt install ffmpeg` (Debian/Ubuntu), `sudo dnf install ffmpeg` (Fedora)

### Clone e ambiente virtual

```bash
git clone https://github.com/PauloParente/youtube-downloader.git
cd youtube-downloader
```

Instale **FFmpeg** no sistema antes do venv (Linux):

| Distro | FFmpeg |
|--------|--------|
| Fedora / Bazzite (rpm-ostree) | `rpm-ostree install ffmpeg` ou equivalente |
| Debian / Ubuntu | `sudo apt install ffmpeg` |

No **Windows**, FFmpeg: PATH ou `build.ps1` (secção [Gerar executável](#gerar-executável-exe)).

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-lock.txt -r requirements-dev.txt
```

**Linux (bash):**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-lock.txt -r requirements-dev.txt
```

**Dependências:** `requirements-lock.txt` + `requirements-dev.txt` reproduzem o CI (recomendado). Alternativa com versões dentro dos ranges: `pip install -r requirements.txt -r requirements-dev.txt`.

**Configurações opcionais:** copie `settings.example.json` para `settings.json` na raiz se quiser valores iniciais. O app cria e atualiza `settings.json` ao salvar em **Configurações**.

Use o interpretador do venv (`.venv`). No Cursor/VS Code: *Python: Select Interpreter* → `.venv\Scripts\python.exe` (Windows) ou `.venv/bin/python` (Linux).

### Comandos do dia a dia

| Ação | Comando |
|------|---------|
| Executar | `python main.py` ou `python -m youtube_downloader` (a partir de `src/`) |
| Testes | `python -m pytest` |
| Atualizar yt-dlp (Windows) | `.\update-deps.ps1` |
| Atualizar yt-dlp (Linux) | `pip install -U yt-dlp` (venv ativado) |

Ao abrir, uma **splash** (logo e carregamento) é exibida até a janela principal ficar pronta.

## Gerar executável (.exe)

Na raiz do projeto:

```powershell
.\build.ps1
```

O script baixa o FFmpeg na primeira execução e gera:

`dist\YouTubeDownloader\YouTubeDownloader.exe` + pasta `ffmpeg\`.

**Distribuir:** compacte a pasta inteira `dist\YouTubeDownloader` em `.zip`. Detalhes e checklist: [docs/release.md](docs/release.md).

## Logs de diagnóstico

Em desenvolvimento, logs na raiz do projeto; na distribuição, ao lado do `.exe`:

- `logs/app.log` — histórico completo
- `logs/errors.log` — apenas erros
- `logs/cache/` — thumbnails do preview

Reproduza o problema e envie `logs/app.log` e, se existir, `logs/errors.log`. O progresso percentual da UI não é gravado no arquivo; downloads, preview, FFmpeg e erros sim.

## Solução de problemas

- **`ModuleNotFoundError: No module named 'PySide6'`:** ative o venv e execute `pip install -r requirements-lock.txt -r requirements-dev.txt`.
- **FFmpeg não encontrado (.exe):** regenere com `.\build.ps1` e confira `dist\YouTubeDownloader\ffmpeg\ffmpeg.exe`.
- **FFmpeg não encontrado (dev):** PATH ou `vendor\ffmpeg\bin` (Windows, via `build.ps1`) / pacote da distro (Linux).
- **Download falha:** `.\update-deps.ps1` ou `pip install -U yt-dlp`.
- **Vídeo indisponível:** privado, região ou removido.
- **JavaScript runtime (yt-dlp):** ver [wiki EJS](https://github.com/yt-dlp/yt-dlp/wiki/EJS) se faltarem formatos.
- **Preview cinza:** procure em `logs/app.log` por `Falha ao exibir thumbnail` ou `preview sem thumbnail_bytes`.
- **Não abre no Filmes e TV (AV1/Opus):** em **Configurações** → **Perfil de exportação**, use **Compatível com Windows (H.264)** e **MP4**, ou use o [VLC](https://www.videolan.org/vlc/).

## Aviso legal

Use este software apenas para conteúdo que você tem direito de baixar. Respeite os [Termos de Serviço do YouTube](https://www.youtube.com/t/terms) e as leis de direitos autorais aplicáveis.

## Contribuir

Veja [CONTRIBUTING.md](CONTRIBUTING.md). Para agentes de IA e arquitetura: [AGENTS.md](AGENTS.md).
