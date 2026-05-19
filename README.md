# YouTube Downloader

[![CI](https://github.com/PauloParente/youtube-downloader/actions/workflows/ci.yml/badge.svg)](https://github.com/PauloParente/youtube-downloader/actions/workflows/ci.yml)

Aplicativo desktop em Python para baixar vídeos e playlists do YouTube, com interface gráfica em CustomTkinter.

## Requisitos

### Para quem usa o .exe (distribuição)

- Windows 64 bits
- Internet
- **Não** precisa de Python nem FFmpeg instalados (o `.exe` gerado por `build.ps1` inclui o FFmpeg)

### Para desenvolvimento (rodar com Python)

- Python 3.10 ou superior
- FFmpeg no PATH, em `%LOCALAPPDATA%\ffmpeg`, ou rode `.\build.ps1` uma vez para popular `vendor\ffmpeg\bin`

## Começar do zero (clone)

```powershell
git clone https://github.com/PauloParente/youtube-downloader.git
cd youtube-downloader
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
python main.py
python -m pytest
```

**FFmpeg em desenvolvimento:** instale no PATH, coloque em `%LOCALAPPDATA%\ffmpeg`, ou execute `.\build.ps1` uma vez (baixa para `vendor\ffmpeg` sem gerar o `.exe`).

**Configurações opcionais:** copie `settings.example.json` para `settings.json` na raiz do projeto se quiser valores iniciais. O app cria e atualiza `settings.json` automaticamente ao salvar na tela Configurações.

**Atualizar yt-dlp após o clone:** `.\update-deps.ps1`

Para versões fixas (como no CI), use `pip install -r requirements-lock.txt` em vez de `requirements.txt`.

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

## Funcionalidades

- Download de vídeo único; playlist só se marcar **Baixar playlist inteira**
- Preview com thumbnail e título ao colar a URL
- Escolha de qualidade: Melhor disponível, 1080p, 720p, 480p
- Vídeos com faixas separadas são mesclados automaticamente em **MP4** (requer FFmpeg; incluído no `.exe` gerado por `build.ps1`)
- Modo somente áudio (MP3)
- Barra de progresso, label de status e log de marcos
- Progresso de playlist (ex.: `3/10 concluídos`)
- Preferências em `settings.json` (pasta, qualidade, áudio, playlist e opções avançadas)
- Navegação por **sidebar**: Downloads, Biblioteca (em breve), Histórico, Configurações
- Página **Histórico** com downloads recentes (persistido em `history.json`, local)
- Página **Configurações** com cards Geral, Qualidade e Formato, Avançado
- Atalhos: `Ctrl+V` colar URL; `Ctrl+,` ou ícone ⚙ abrir Configurações
- Cancelamento de download em andamento

Veja o backlog futuro em [ROADMAP.md](ROADMAP.md).

## Uso

1. Na sidebar, abra **Downloads**
2. Cole a URL do vídeo ou da playlist (`Ctrl+V`)
3. Escolha a pasta de destino (ou defina o padrão em **Configurações** na sidebar ou `Ctrl+,`)
4. Selecione a qualidade ou marque "Somente áudio (MP3)"
5. Para baixar todos os vídeos de uma playlist, marque **Baixar playlist inteira**
6. Clique em **Baixar**

Consulte **Histórico** na sidebar para reabrir arquivos baixados recentemente.

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

- **FFmpeg não encontrado (versão .exe):** regenere com `.\build.ps1` e confira se existe `dist\YouTubeDownloader\ffmpeg\ffmpeg.exe` ao lado do executável.
- **FFmpeg não encontrado (desenvolvimento):** instale no PATH ou rode `.\build.ps1` uma vez para popular `vendor\ffmpeg\bin`.
- **Download falha sem motivo claro:** atualize dependências com `.\update-deps.ps1` ou `pip install -U yt-dlp`
- **Vídeo indisponível:** o vídeo pode ser privado, restrito por região ou removido.
- **Aviso sobre JavaScript runtime:** versões recentes do yt-dlp podem pedir Deno ou outro runtime JS para extrair todos os formatos do YouTube. Consulte a [documentação do yt-dlp](https://github.com/yt-dlp/yt-dlp/wiki/EJS) se alguns formatos estiverem ausentes.
- **Preview com caixa cinza:** abra `logs/app.log` e procure por `Falha ao exibir thumbnail` ou `preview sem thumbnail_bytes`.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

## Atualizar dependências

```powershell
.\update-deps.ps1
```

## Contribuir

Veja [CONTRIBUTING.md](CONTRIBUTING.md).

## Checklist de release

Antes de distribuir um novo `.zip` para outras pessoas:

1. Rodar `.\.venv\Scripts\python.exe -m pytest`
2. Testar `python main.py` (download de vídeo e, se possível, playlist curta)
3. Gerar o executável: `.\build.ps1`
4. Testar `dist\YouTubeDownloader\YouTubeDownloader.exe` (FFmpeg embutido, merge MP4, settings)
5. Compactar a pasta inteira `dist\YouTubeDownloader` em `.zip`
