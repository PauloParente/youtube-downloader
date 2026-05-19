# YouTube Downloader

Aplicativo desktop em Python para baixar vídeos e playlists do YouTube, com interface gráfica em CustomTkinter.

## Requisitos

### Para quem usa o .exe (distribuição)

- Windows 64 bits
- Internet
- **Não** precisa de Python nem FFmpeg instalados (o `.exe` gerado por `build.ps1` inclui o FFmpeg)

### Para desenvolvimento (rodar com Python)

- Python 3.10 ou superior
- FFmpeg no PATH, em `%LOCALAPPDATA%\ffmpeg`, ou gere o `.exe` com `build.ps1` (usa `vendor/ffmpeg`)

## Instalação

```powershell
cd c:\Users\paulo.parente\PythonProject
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Execução

**Importante:** use o interpretador do ambiente virtual (`.venv`). Se o Cursor/VS Code estiver usando outro Python, selecione o interpretador em *Python: Select Interpreter* → `.venv\Scripts\python.exe`.

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

## Funcionalidades

- Download de vídeo único; playlist só se marcar **Baixar playlist inteira**
- Preview com thumbnail e título ao colar a URL
- Escolha de qualidade: Melhor disponível, 1080p, 720p, 480p
- Vídeos com faixas separadas são mesclados automaticamente em **MP4** (requer FFmpeg; incluído no `.exe` gerado por `build.ps1`)
- Modo somente áudio (MP3)
- Barra de progresso, label de status e log de marcos
- Progresso de playlist (ex.: `3/10 concluídos`)
- Preferências salvas em `settings.json` (pasta, qualidade, áudio, playlist)
- Barra de menu **Arquivo / Editar / Ajuda** e janela **Preferências** (Editar → Preferências ou `Ctrl+,`)
- Atalhos: `Ctrl+V` colar URL; ações como abrir pasta, logs e último arquivo no menu
- Cancelamento de download em andamento (botão ou Arquivo → Cancelar download)

Veja o backlog futuro em [ROADMAP.md](ROADMAP.md).

## Uso

1. Cole a URL do vídeo ou da playlist do YouTube (`Ctrl+V` ou Editar → Colar URL)
2. Escolha a pasta de destino (ou defina o padrão em **Editar → Preferências**)
3. Selecione a qualidade ou marque "Somente áudio (MP3)"
4. Para baixar todos os vídeos de uma playlist, marque **Baixar playlist inteira**
5. Clique em **Baixar**

## Gerar executável (.exe)

Na raiz do projeto:

```powershell
.\build.ps1
```

O script baixa o FFmpeg automaticamente (primeira vez) e gera:

`dist\YouTubeDownloader\YouTubeDownloader.exe` + pasta `ffmpeg\` (ffmpeg.exe, ffprobe.exe).

**Distribuir para amigos:** compacte a pasta inteira `dist\YouTubeDownloader` em um `.zip` (~150–200 MB). Quem receber só extrai e abre o `.exe` — sem instalar Python nem FFmpeg.

Ao rodar, a pasta `downloads` é criada **ao lado do .exe**.

O pacote inclui licença do FFmpeg em `ffmpeg\LICENSE.txt` (FFmpeg é software GPL).

## Logs de diagnóstico

O aplicativo grava logs em arquivos ao lado do `.exe` (ou na raiz do projeto em desenvolvimento):

- `logs/app.log` — histórico completo (DEBUG, INFO, erros)
- `logs/errors.log` — apenas erros (ERROR e acima)
- `logs/cache/` — thumbnails temporárias do preview

Use o botão **Abrir logs** na interface para abrir a pasta no Explorer.

Se algo falhar, reproduza o problema e envie `logs/app.log` e, se existir, `logs/errors.log`.

O log registra de forma pontual: inicio/fim/cancelamento/erro de download, falhas de preview, estado do FFmpeg e validacoes que impedem o download (URL vazia, pasta invalida). O progresso percentual e mensagens rotineiras da interface nao vao para o arquivo.

## Aviso legal

Use este software apenas para conteúdo que você tem direito de baixar. Respeite os [Termos de Serviço do YouTube](https://www.youtube.com/t/terms) e as leis de direitos autorais aplicáveis.

## Solução de problemas

- **FFmpeg não encontrado (versão .exe):** regenere com `.\build.ps1` e confira se existe `dist\YouTubeDownloader\ffmpeg\ffmpeg.exe` ao lado do executável.
- **FFmpeg não encontrado (desenvolvimento):** instale no PATH ou rode `.\build.ps1` uma vez para popular `vendor\ffmpeg\bin`.
- **Download falha sem motivo claro:** atualize dependências com `.\update-deps.ps1` ou `pip install -U yt-dlp`
- **Vídeo indisponível:** o vídeo pode ser privado, restrito por região ou removido.
- **Aviso sobre JavaScript runtime:** versões recentes do yt-dlp podem pedir Deno ou outro runtime JS para extrair todos os formatos do YouTube. Consulte a [documentação do yt-dlp](https://github.com/yt-dlp/yt-dlp/wiki/EJS) se alguns formatos estiverem ausentes.
- **Preview com caixa cinza:** abra `logs/app.log` e procure por `Falha ao exibir thumbnail` ou `preview sem thumbnail_bytes`; envie o trecho do log ao reportar o bug.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

## Atualizar dependências

```powershell
.\update-deps.ps1
```

## Checklist de release

Antes de distribuir um novo `.zip` para outras pessoas:

1. Rodar `.\.venv\Scripts\python.exe -m pytest`
2. Testar `python main.py` (download de vídeo e, se possível, playlist curta)
3. Gerar o executável: `.\build.ps1`
4. Testar `dist\YouTubeDownloader\YouTubeDownloader.exe` (FFmpeg embutido, merge MP4, settings)
5. Compactar a pasta inteira `dist\YouTubeDownloader` em `.zip`
