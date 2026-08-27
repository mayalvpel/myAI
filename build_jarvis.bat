@echo off

title Jarvis Builder

echo ========================================
echo          BUILDING JARVIS
echo ========================================
echo.

cd /d C:\myAI

echo [1/6] Activating virtual environment...

call .venv\Scripts\activate.bat

if errorlevel 1 (
    echo.
    echo ERROR: Could not activate virtual environment.
    pause
    exit /b 1
)

echo.
echo [2/6] Installing PyInstaller...

python -m pip install pyinstaller

if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller installation failed.
    pause
    exit /b 1
)

echo.
echo [3/6] Cleaning previous build...

if exist build (
    rmdir /s /q build
)

if exist dist (
    rmdir /s /q dist
)

if exist Jarvis.spec (
    del /q Jarvis.spec
)

echo.
echo [4/6] Building Jarvis...

python -m PyInstaller ^
    --name Jarvis ^
    --onedir ^
    --clean ^
    --noconfirm ^
    --console ^
    --collect-all faster_whisper ^
    --collect-all ctranslate2 ^
    --collect-all openwakeword ^
    --collect-all onnxruntime ^
    --collect-all sounddevice ^
    --collect-all wmi ^
    --collect-all win32com ^
    --collect-all pywin32 ^
    --collect-all piper ^
    --hidden-import piper ^
    --hidden-import piper.voice ^
    --hidden-import piper.config ^
    --hidden-import agent ^
    --hidden-import agent.core ^
    --hidden-import agent.memory ^
    --hidden-import agent.memory_manager ^
    --hidden-import agent.tools ^
    --hidden-import wake_word ^
    --hidden-import speak ^
    main.py

if errorlevel 1 (
    echo.
    echo ========================================
    echo BUILD FAILED
    echo ========================================
    echo.
    pause
    exit /b 1
)

echo.
echo [5/6] Copying runtime files...

if not exist dist\Jarvis\generated_files (
    mkdir dist\Jarvis\generated_files
)

if exist memory.json (
    copy /Y memory.json dist\Jarvis\memory.json >nul
)

echo.
echo Copying Piper espeak-ng-data...

if exist ".venv\Lib\site-packages\piper\espeak-ng-data" (

    if not exist "dist\Jarvis\_internal\espeak-ng-data" (
        mkdir "dist\Jarvis\_internal\espeak-ng-data"
    )

    xcopy ^
        ".venv\Lib\site-packages\piper\espeak-ng-data" ^
        "dist\Jarvis\_internal\espeak-ng-data" ^
        /E /I /Y

) else (

    echo ERROR: Piper espeak-ng-data not found.
    pause
    exit /b 1
)

echo.
echo Copying Piper voice model...

if exist "en_GB\en_GB-alan-medium.onnx" (

    if not exist "dist\Jarvis\en_GB" (
        mkdir "dist\Jarvis\en_GB"
    )

    copy /Y ^
        "en_GB\en_GB-alan-medium.onnx" ^
        "dist\Jarvis\en_GB\en_GB-alan-medium.onnx"

) else (

    echo ERROR: Voice model not found:
    echo en_GB\en_GB-alan-medium.onnx

    pause
    exit /b 1
)


echo.
echo Copying Piper voice configuration...

if exist "en_GB\en_GB-alan-medium.onnx.json" (

    copy /Y ^
        "en_GB\en_GB-alan-medium.onnx.json" ^
        "dist\Jarvis\en_GB\en_GB-alan-medium.onnx.json"

) else (

    echo ERROR: Voice configuration not found:
    echo en_GB\en_GB-alan-medium.onnx.json

    pause
    exit /b 1
)

echo.
echo [6/6] Verifying runtime files...

if not exist "dist\Jarvis\_internal\espeak-ng-data\phontab" (

    echo ERROR: phontab was not copied correctly.
    pause
    exit /b 1
)

if not exist "dist\Jarvis\en_GB\en_GB-alan-medium.onnx" (

    echo ERROR: Piper voice model was not copied correctly.
    pause
    exit /b 1
)

if not exist "dist\Jarvis\en_GB\en_GB-alan-medium.onnx.json" (

    echo ERROR: Piper voice configuration was not copied correctly.
    pause
    exit /b 1
)

echo.
echo ========================================
echo       JARVIS BUILD SUCCESSFUL
echo ========================================
echo.

echo EXE:
echo C:\myAI\dist\Jarvis\Jarvis.exe

echo.

echo Piper:
echo OK - espeak-ng-data\phontab

echo Voice:
echo OK - en_GB\en_GB-alan-medium.onnx

echo.

pause