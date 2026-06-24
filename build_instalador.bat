@echo off
chcp 65001 >nul
title MF System Jur — Compilador
color 0A

echo.
echo  ╔═══════════════════════════════════════════════════════╗
echo  ║          MF System Jur — Gerador de Instalador       ║
echo  ║          Windows 10/11  ^|  Versão 2.0                ║
echo  ╚═══════════════════════════════════════════════════════╝
echo.

:: ─────────────────────────────────────────────────────────────
::  [0] Verificar arquivos necessários
:: ─────────────────────────────────────────────────────────────
if not exist "sistema_juridico_pro.html" (
    echo  [ERRO] sistema_juridico_pro.html nao encontrado!
    echo         Coloque TODOS os arquivos na mesma pasta e tente novamente.
    echo.
    pause & exit /b 1
)
if not exist "jurisgest.py" (
    echo  [ERRO] jurisgest.py nao encontrado!
    pause & exit /b 1
)
if not exist "setup.iss" (
    echo  [ERRO] setup.iss nao encontrado!
    pause & exit /b 1
)
echo  [OK] Arquivos encontrados.

:: ─────────────────────────────────────────────────────────────
::  [1] Verificar / Instalar Python
:: ─────────────────────────────────────────────────────────────
echo.
echo  [1/5] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo        Python nao encontrado. Tentando instalar via winget...
    winget install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
    if %errorlevel% neq 0 (
        echo  [ERRO] Nao foi possivel instalar Python automaticamente.
        echo         Baixe em: https://www.python.org/downloads/
        echo         Marque "Add Python to PATH" durante a instalacao!
        start https://www.python.org/downloads/
        pause & exit /b 1
    )
    call refreshenv >nul 2>&1
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo  [AVISO] Feche e reabra este script apos instalar o Python.
        pause & exit /b 1
    )
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo         %%v

:: ─────────────────────────────────────────────────────────────
::  [2] Instalar dependências Python
:: ─────────────────────────────────────────────────────────────
echo.
echo  [2/5] Instalando dependencias Python (pywebview + PyInstaller)...
python -m pip install --upgrade pip --quiet
python -m pip install pywebview pyinstaller --quiet --upgrade
if %errorlevel% neq 0 (
    echo  [ERRO] Falha ao instalar dependencias. Verifique sua conexao com a internet.
    pause & exit /b 1
)
echo         Dependencias instaladas.

:: ─────────────────────────────────────────────────────────────
::  [3] Compilar com PyInstaller
:: ─────────────────────────────────────────────────────────────
echo.
echo  [3/5] Compilando MFSystemJur.exe (pode levar 1-3 minutos)...
if exist "dist\MFSystemJur.exe" del /f "dist\MFSystemJur.exe" >nul 2>&1

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "MFSystemJur" ^
    --add-data "sistema_juridico_pro.html;." ^
    --hidden-import "webview.platforms.winforms" ^
    --hidden-import "clr" ^
    --collect-all "webview" ^
    --clean ^
    --noconfirm ^
    --log-level ERROR ^
    jurisgest.py

if not exist "dist\MFSystemJur.exe" (
    echo  [ERRO] Falha na compilacao. Rodando novamente com log completo:
    echo.
    pyinstaller --onefile --windowed --name "MFSystemJur" ^
        --add-data "sistema_juridico_pro.html;." --clean jurisgest.py
    pause & exit /b 1
)
echo         dist\MFSystemJur.exe criado ^(~30-60 MB^).

:: ─────────────────────────────────────────────────────────────
::  [4] Limpar temporários
:: ─────────────────────────────────────────────────────────────
echo.
echo  [4/5] Limpando arquivos temporarios...
if exist "build"           rmdir /s /q "build"          >nul 2>&1
if exist "MFSystemJur.spec" del /f "MFSystemJur.spec"   >nul 2>&1
if exist "__pycache__"     rmdir /s /q "__pycache__"    >nul 2>&1
echo         Concluido.

:: ─────────────────────────────────────────────────────────────
::  [5] Criar instalador com Inno Setup
:: ─────────────────────────────────────────────────────────────
echo.
echo  [5/5] Criando instalador com Inno Setup...

set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe"       set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

if "%ISCC%"=="" (
    echo         Inno Setup nao encontrado. Baixando instalador...
    curl -L --progress-bar "https://jrsoftware.org/download.php/is.exe" -o "%TEMP%\is_setup.exe"
    if %errorlevel% equ 0 (
        echo         Instalando Inno Setup silenciosamente...
        "%TEMP%\is_setup.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
        timeout /t 8 /nobreak >nul
        if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
        if exist "C:\Program Files\Inno Setup 6\ISCC.exe"       set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
    )
)

if "%ISCC%"=="" goto :sem_inno

"%ISCC%" setup.iss /Q
if %errorlevel% neq 0 (
    echo  [ERRO] Inno Setup retornou erro.
    goto :sem_inno
)

if not exist "dist\MFSystemJur_Instalador.exe" goto :sem_inno

echo         dist\MFSystemJur_Instalador.exe criado!
goto :fim_ok

:sem_inno
echo.
echo  ┌─────────────────────────────────────────────────────┐
echo  │ Inno Setup nao foi instalado. Opcoes:               │
echo  │                                                      │
echo  │  A) Baixe manualmente em: jrsoftware.org/isinfo.php │
echo  │     Instale e rode este script novamente.            │
echo  │                                                      │
echo  │  B) Use dist\MFSystemJur.exe diretamente            │
echo  │     (funciona, mas sem instalador).                  │
echo  └─────────────────────────────────────────────────────┘
echo.
pause
exit /b 0

:fim_ok
echo.
echo  ╔═══════════════════════════════════════════════════════╗
echo  ║                    CONCLUIDO!                        ║
echo  ║                                                      ║
echo  ║  Instalador: dist\MFSystemJur_Instalador.exe         ║
echo  ║  Executavel: dist\MFSystemJur.exe                    ║
echo  ║                                                      ║
echo  ║  Distribua o arquivo MFSystemJur_Instalador.exe.     ║
echo  ║  Ao executar, ele instala o programa com:            ║
echo  ║    • Atalho na Area de Trabalho                      ║
echo  ║    • Entrada no Menu Iniciar                         ║
echo  ║    • Desinstalador em Programas e Recursos           ║
echo  ╚═══════════════════════════════════════════════════════╝
echo.
explorer dist
pause
