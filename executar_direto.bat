@echo off
chcp 65001 >nul
title MF System Jur

:: ─── Verificar Python ─────────────────────────────────────────
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  Python nao encontrado.
    echo  Baixe em: https://www.python.org/downloads/
    echo  Marque "Add Python to PATH" durante a instalacao!
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

:: ─── Instalar pywebview na primeira execucao ───────────────────
python -c "import webview" >nul 2>&1
if %errorlevel% neq 0 (
    echo  Instalando pywebview pela primeira vez...
    pip install pywebview --quiet
)

:: ─── Iniciar MF System Jur ────────────────────────────────────
python jurisgest.py
