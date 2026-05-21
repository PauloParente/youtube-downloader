# Scripts de desenvolvimento

## Medir arranque

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts\measure_startup.py --runs 5
```

Variáveis opcionais:

- `YTD_STARTUP_PROFILE=1` — regista fases em `logs/app.log` ao abrir o app
- `YTD_MEASURE_STARTUP=1` — `startup.run()` termina após `window.show()` (sem event loop)

## Importtime (baseline)

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -X importtime -c "from youtube_downloader.app import run" 2> scripts\importtime-app.txt
```
