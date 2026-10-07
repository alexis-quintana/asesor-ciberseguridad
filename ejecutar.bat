@echo off
rem Crea el entorno virtual si no existe, instala dependencias y ejecuta el asesor.
rem Uso: ejecutar.bat [--web] [--demo] [--explicar] [--con-impacto]
rem   ejecutar.bat --web   abre la interfaz web en http://127.0.0.1:5000
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" goto instalar

echo Creando el entorno virtual en .venv ...
where py >nul 2>nul
if errorlevel 1 goto usar_python
py -3 -m venv .venv
goto comprobar_venv

:usar_python
python -m venv .venv

:comprobar_venv
if errorlevel 1 goto error_venv

:instalar
echo Instalando dependencias de requirements.txt ...
".venv\Scripts\python" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto error_pip

echo Iniciando el asesor ...
".venv\Scripts\python" main.py %*
if errorlevel 1 goto error_ejecucion
goto fin

:error_venv
echo ERROR: no se pudo crear el entorno virtual. Instale Python 3 desde python.org y vuelva a intentarlo.
pause
exit /b 1

:error_pip
echo ERROR: no se pudieron instalar las dependencias. Revise su conexion a Internet.
pause
exit /b 1

:error_ejecucion
echo ERROR: el asesor termino con errores.
pause
exit /b 1

:fin
endlocal
