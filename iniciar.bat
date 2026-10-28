@echo off
rem Prepara e inicia o sistema para TESTE local no Windows. Dê duplo clique neste arquivo.
setlocal
cd /d "%~dp0"
set PORTA=8000

where py >nul 2>nul
if errorlevel 1 (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Python nao encontrado. Instale o Python 3.11 ou mais novo em https://www.python.org/downloads/
    echo Marque a opcao "Add python.exe to PATH" durante a instalacao e rode este arquivo de novo.
    pause
    exit /b 1
  )
  set PY=python
) else (
  set PY=py -3
)

if not exist .venv (
  echo Criando ambiente virtual...
  %PY% -m venv .venv
  if errorlevel 1 goto erro
)
call .venv\Scripts\activate.bat
echo Instalando dependencias (so na primeira vez demora)...
python -m pip install -q --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto erro

if not exist .env (
  echo DJANGO_DEBUG=1> .env
  echo EXIGIR_2FA=0>> .env
)

echo Preparando o banco de dados e os dados de demonstracao...
python manage.py migrate -v0
if errorlevel 1 goto erro
python manage.py seed_inicial --demo -v0
if errorlevel 1 goto erro

echo.
echo ======================================================================
echo   Sistema da Loja pronto para teste
echo   Endereco:  http://127.0.0.1:%PORTA%/
echo   Usuarios:  veneravel, secretario, tesoureiro, mestre, companheiro, aprendiz
echo   Senha de todos:  demo-senha-123
echo   (Feche esta janela ou use Ctrl+C para parar. Roteiro: docs\TESTE.md)
echo   Obs.: PDFs exigem o GTK for Windows Runtime; sem ele o resto funciona normalmente.
echo ======================================================================
echo.
start "" "http://127.0.0.1:%PORTA%/"
python manage.py runserver 127.0.0.1:%PORTA%
goto fim

:erro
echo.
echo Algo deu errado. Copie as mensagens acima e envie para quem esta ajudando.
pause
:fim
endlocal
