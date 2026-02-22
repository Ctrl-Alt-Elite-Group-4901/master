@echo off
echo ============================================
echo  Arete - Building .exe with PyInstaller
echo ============================================

:: Move to areteDemo/ folder (where this script lives)
cd /d "%~dp0"

:: Point explicitly to the venv one level up (master/.venv)
set VENV=%~dp0..\.venv
set PYTHON=%VENV%\Scripts\python.exe
set PIP=%VENV%\Scripts\pip.exe

:: Try venv name if .venv doesn't exist
if not exist "%PYTHON%" (
    set VENV=%~dp0..\venv
    set PYTHON=%VENV%\Scripts\python.exe
    set PIP=%VENV%\Scripts\pip.exe
)

if not exist "%PYTHON%" (
    echo ERROR: Could not find .venv or venv in master folder.
    echo Make sure your virtual environment is at master\.venv\
    pause
    exit /b 1
)

echo Using Python: %PYTHON%
echo.

:: Install PyInstaller if missing
"%PYTHON%" -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    "%PIP%" install pyinstaller
)

:: Install kivy_deps if missing
"%PYTHON%" -c "from kivy_deps import sdl2, glew, angle" >nul 2>&1
if errorlevel 1 (
    echo Installing Kivy Windows dependencies...
    "%PIP%" install kivy_deps.sdl2 kivy_deps.glew kivy_deps.angle
)

:: Clean previous build
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

echo.
echo Building...
"%PYTHON%" -m PyInstaller areteDemo.spec

if errorlevel 1 (
    echo.
    echo BUILD FAILED. Set console=True in areteDemo.spec and rebuild to see errors.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  BUILD SUCCESSFUL
echo  Executable folder: dist\Arete\
echo  Zip dist\Arete\ and upload to GitHub Releases.
echo ============================================
pause
