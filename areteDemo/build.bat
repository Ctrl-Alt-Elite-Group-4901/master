@echo off
echo ============================================
echo  Arete - Building .exe with PyInstaller
echo ============================================

:: Move to areteDemo/ folder (where this script lives)
cd /d "%~dp0"

set "USE_LAUNCHER="

:: Point explicitly to the venv one level up (master/.venv)
set "VENV=%~dp0..\.venv"
set "PYTHON=%VENV%\Scripts\python.exe"
set "PIP=%VENV%\Scripts\pip.exe"

:: Try venv name if .venv doesn't exist
if not exist "%PYTHON%" (
    set "VENV=%~dp0..\venv"
    set "PYTHON=%VENV%\Scripts\python.exe"
    set "PIP=%VENV%\Scripts\pip.exe"
)

if not exist "%PYTHON%" (
    where py >nul 2>&1
    if not errorlevel 1 (
        set "USE_LAUNCHER=1"
    ) else (
        echo ERROR: Could not find .venv or venv in the parent folder, and the Python launcher is unavailable.
        echo Create a virtual environment at ..\.venv\ or install Python with the py launcher.
        pause
        exit /b 1
    )
)

if defined USE_LAUNCHER (
    echo Using Python launcher: py -3
) else (
    echo Using Python: %PYTHON%
)
echo.

echo Installing pinned project dependencies...
call :run_pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: Dependency install failed.
    pause
    exit /b 1
)

:: Install PyInstaller if missing
call :run_python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    call :run_pip install pyinstaller==6.19.0
    if errorlevel 1 (
        echo.
        echo ERROR: PyInstaller install failed.
        pause
        exit /b 1
    )
)

:: Install kivy_deps if missing
call :run_python -c "from kivy_deps import sdl2, glew, angle" >nul 2>&1
if errorlevel 1 (
    echo Installing Kivy Windows dependencies...
    call :run_pip install kivy-deps.sdl2==0.8.0 kivy-deps.glew==0.3.1 kivy-deps.angle==0.4.0
    if errorlevel 1 (
        echo.
        echo ERROR: Kivy Windows dependency install failed.
        pause
        exit /b 1
    )
)

:: Clean previous build
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

echo.
echo Building...
call :run_python -m PyInstaller areteDemo.spec

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
echo  Copy cloud_config.json into dist\Arete\ before distributing the build.
echo  Zip dist\Arete\ and upload to GitHub Releases.
echo ============================================
pause
exit /b 0

:run_python
if defined USE_LAUNCHER (
    py -3 %*
) else (
    "%PYTHON%" %*
)
exit /b %errorlevel%

:run_pip
if defined USE_LAUNCHER (
    py -3 -m pip %*
) else (
    "%PIP%" %*
)
exit /b %errorlevel%
