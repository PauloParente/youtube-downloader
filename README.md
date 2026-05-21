# YouTube Downloader

[![CI](https://github.com/PauloParente/youtube-downloader/actions/workflows/ci.yml/badge.svg)](https://github.com/PauloParente/youtube-downloader/actions/workflows/ci.yml)

Aplicativo desktop em Python para baixar vídeos e playlists do YouTube, com interface gráfica em PySide6 (Qt).

## Requisitos

### Para quem usa o .exe (distribuição)

- Windows 64 bits
- Internet
- **Não** precisa de Python nem FFmpeg instalados (o `.exe` gerado por `build.ps1` inclui o FFmpeg)

### Para desenvolvimento (rodar com Python)

- Python 3.10 ou superior
- **PySide6** (interface gráfica): instalado via `pip` com `requirements-lock.txt` (não precisa de Tkinter no sistema)
- **FFmpeg** no PATH (obrigatório para vídeo/MP3 com merge)
  - **Windows:** PATH, `%LOCALAPPDATA%\ffmpeg`, ou `.\build.ps1` uma vez → `vendor\ffmpeg\bin`
  - **Linux:** ex. `sudo dnf install ffmpeg` (Fedora), `sudo apt install ffmpeg` (Debian/Ubuntu)

## Começar do zero (clone)

```bash
git clone https://github.com/PauloParente/youtube-downloader.git
cd youtube-downloader
```

Instale **FFmpeg** no sistema antes do venv (Linux):

| Distro | FFmpeg |
|--------|--------|
| Fedora / Bazzite (rpm-ostree) | `rpm-ostree install ffmpeg` ou equivalente |
| Debian / Ubuntu | `sudo apt install ffmpeg` |

No **Windows**, FFmpeg: PATH ou `build.ps1` (abaixo).

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-lock.txt -r requirements-dev.txt
python main.py
python -m pytest
```

### Linux (bash)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-lock.txt -r requirements-dev.txt
python main.py
python -m pytest
```

**Configurações opcionais:** copie `settings.example.json` para `settings.json` na raiz do projeto se quiser valores iniciais. O app cria e atualiza `settings.json` automaticamente ao salvar na tela Configurações.

**Atualizar yt-dlp (Windows):** `.\update-deps.ps1` — no Linux: `pip install -U yt-dlp` com o venv ativado.

**Versões fixas:** `requirements-lock.txt` é o mesmo arquivo usado no CI (Windows e Ubuntu).

## Instalação (já com o código local)

```powershell
cd youtube-downloader
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Execução

**Importante:** use o interpretador do ambiente virtual (`.venv`). No Cursor/VS Code: *Python: Select Interpreter* → `.venv\Scripts\python.exe`.

Na raiz do projeto, com o venv ativado:

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

Ou diretamente:

```powershell
.\.venv\Scripts\python.exe main.py
```

Ou a partir da pasta `src`:

```powershell
cd src
python -m youtube_downloader
```

Ao abrir, uma **tela de splash** (logo, nome e mensagem de carregamento) é exibida enquanto a interface principal carrega.

## Funcionalidades

- Download de vídeo único; link de **playlist** expande automaticamente para vários vídeos na fila (um job por vídeo)
- Preview com thumbnail e título ao colar a URL
- Escolha de qualidade: Melhor disponível, 1080p, 720p, 480p
- Vídeos com faixas separadas são mesclados em **MP4** ou **WebM** conforme Configurações (requer FFmpeg; incluído no `.exe` gerado por `build.ps1`)
- Modo somente áudio (MP3)
- Barra de progresso e status do download atual na tela **Fila**; log de marcos na tela Downloads
- Preferências em `settings.json` (pasta, qualidade, áudio e opções avançadas — formato WebM/MP4, **perfil de exportação** (H.264 compatível com Windows ou melhor qualidade), bitrate MP3, limite de banda, legendas, tema claro/escuro, `cookies.txt` e notificação ao concluir aplicados no download)
- **Identidade visual** unificada (tema escuro/claro, ícones SVG, componentes Qt) — ver [docs/design-system.md](docs/design-system.md)
- **Fila de downloads**: **+ Fila** na tela Downloads; na sidebar **Fila**, cards com miniatura, título e duração (como o Histórico), progresso do vídeo atual, Cancelar, Pular e remover por item; processamento sequencial automático
- Navegação por **sidebar**: Downloads, Fila, Biblioteca, Histórico, Configurações
- Página **Biblioteca** — lista arquivos de mídia na pasta de destino
- Página **Histórico** — cards com thumbnail, nome do canal (link para o YouTube) e botão para abrir o vídeo no site (`history.json`); abrir arquivo/pasta, **Baixar de novo**, remover ou **Limpar histórico** (não apaga arquivos no disco)
- Botões **Abrir pasta** / **Abrir arquivo** após cada download na tela Downloads
- Página **Configurações** com cards Geral, Qualidade e Formato, Avançado
- Atalhos: `Ctrl+V` colar URL; `Ctrl+,` ou **Configurações** na sidebar; **Sobre** no rodapé da sidebar
- Cancelamento de download em andamento
- Janela redimensionável (tamanho mínimo ~900×680): na tela **Downloads**, o conteúdo superior rola e os botões **Baixar** / **Cancelar** permanecem fixos no rodapé

Veja o backlog futuro em [ROADMAP.md](ROADMAP.md).

## Uso

1. Na sidebar, abra **Downloads**
2. Cole a URL do vídeo ou da playlist (`Ctrl+V`)
3. Defina a pasta de destino em **Configurações** na sidebar (ou `Ctrl+,`) se necessário
4. Selecione a qualidade ou marque "Somente áudio (MP3)"
5. Clique em **Baixar** (vídeo único) ou **+ Fila** para enfileirar sem iniciar

**Playlists:** ao colar um link de playlist (`playlist?list=…`) ou ao escolher *Playlist inteira* quando a URL traz `list=` junto com o vídeo, o app obtém os vídeos e coloca cada um na fila. **Baixar** com uma playlist no campo enfileira todos e inicia o primeiro; os restantes seguem em sequência. URL só com `watch?v=` baixa apenas esse vídeo.

Use **+ Fila** para enfileirar sem iniciar (também durante um download). Abra **Fila** na sidebar: o download atual com progresso e, abaixo, um card por vídeo pendente (miniatura, título e duração). **Pular** avança na fila; **🗑** remove um pendente. **Cancelar** no rodapé de Downloads ou na tela Fila interrompe tudo e esvazia a fila. **Histórico** registra cada vídeo concluído; **Biblioteca** lista arquivos na pasta de destino. A fila não é salva ao fechar o app.

### Redimensionar a janela

- Tamanho inicial 980×720; mínimo ~900×680.
- Em **Downloads**, role o painel central se a altura for pequena; **Baixar** e **Cancelar** ficam sempre no rodapé.
- Com pouca largura, os botões do rodapé passam para duas linhas automaticamente.
- **Configurações**, **Histórico** e **Biblioteca** usam lista rolável que preenche a altura disponível.

## Gerar executável (.exe)

Na raiz do projeto:

```powershell
.\build.ps1
```

O script baixa o FFmpeg automaticamente (primeira vez) e gera:

`dist\YouTubeDownloader\YouTubeDownloader.exe` + pasta `ffmpeg\` (ffmpeg.exe, ffprobe.exe).

**Distribuir:** compacte a pasta inteira `dist\YouTubeDownloader` em um `.zip` (~150–200 MB). Quem receber só extrai e abre o `.exe` — sem instalar Python nem FFmpeg.

Ao rodar, a pasta `downloads` é criada **ao lado do .exe**.

O pacote inclui licença do FFmpeg em `ffmpeg\LICENSE.txt` (FFmpeg é software GPL).

## Logs de diagnóstico

O aplicativo grava logs na raiz do projeto em desenvolvimento, ou ao lado do `.exe` na distribuição:

- `logs/app.log` — histórico completo (DEBUG, INFO, erros)
- `logs/errors.log` — apenas erros (ERROR e acima)
- `logs/cache/` — thumbnails temporárias do preview

Abra a pasta `logs` no Explorer para inspecionar os arquivos (não há botão dedicado na interface).

Se algo falhar, reproduza o problema e envie `logs/app.log` e, se existir, `logs/errors.log`.

O log registra de forma pontual: início/fim/cancelamento/erro de download, falhas de preview, estado do FFmpeg e validações que impedem o download. O progresso percentual rotineiro da interface não vai para o arquivo.

## Aviso legal

Use este software apenas para conteúdo que você tem direito de baixar. Respeite os [Termos de Serviço do YouTube](https://www.youtube.com/t/terms) e as leis de direitos autorais aplicáveis.

## Solução de problemas

- **`ModuleNotFoundError: No module named 'PySide6'`:** ative o venv e execute `pip install -r requirements-lock.txt`.
- **FFmpeg não encontrado (versão .exe):** regenere com `.\build.ps1` e confira se existe `dist\YouTubeDownloader\ffmpeg\ffmpeg.exe` ao lado do executável.
- **FFmpeg não encontrado (desenvolvimento):** instale no PATH; no Windows pode usar `.\build.ps1` para popular `vendor\ffmpeg\bin`; no Linux use o gerenciador de pacotes da distro.
- **Download falha sem motivo claro:** atualize dependências com `.\update-deps.ps1` ou `pip install -U yt-dlp`
- **Vídeo indisponível:** o vídeo pode ser privado, restrito por região ou removido.
- **Aviso sobre JavaScript runtime:** versões recentes do yt-dlp podem pedir Deno ou outro runtime JS para extrair todos os formatos do YouTube. Consulte a [documentação do yt-dlp](https://github.com/yt-dlp/yt-dlp/wiki/EJS) se alguns formatos estiverem ausentes.
- **Preview com caixa cinza:** abra `logs/app.log` e procure por `Falha ao exibir thumbnail` ou `preview sem thumbnail_bytes`.
- **Vídeo baixado não abre no Filmes e TV (AV1 / Opus):** em **Configurações** → **Perfil de exportação**, use **Compatível com Windows (H.264)** e **MP4**, salve e baixe de novo. Ou instale o [VLC](https://www.videolan.org/vlc/). O perfil **Melhor qualidade** pode gerar AV1/VP9.

## Testes

Com o venv ativado:

```bash
python -m pytest
```

No Windows, se preferir caminho explícito: `.\.venv\Scripts\python.exe -m pytest`

## Atualizar dependências

```powershell
.\update-deps.ps1
```

## Contribuir

Veja [CONTRIBUTING.md](CONTRIBUTING.md). Para desenvolvimento com Cursor ou outros agentes de IA, leia também [AGENTS.md](AGENTS.md).

## Checklist de release

Antes de distribuir um novo `.zip` para outras pessoas:

1. Rodar `.\.venv\Scripts\python.exe -m pytest`
2. Testar `python main.py` (download de vídeo e, se possível, playlist curta)
3. Gerar o executável: `.\build.ps1`
4. Testar `dist\YouTubeDownloader\YouTubeDownloader.exe` (FFmpeg embutido, merge MP4, settings)
5. Compactar a pasta inteira `dist\YouTubeDownloader` em `.zip`
