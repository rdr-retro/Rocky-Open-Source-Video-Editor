@echo off
setlocal enabledelayedexpansion

echo === Rocky Video Editor - Windows Compilation Script ===

:: 1. Setup Directories
set LIB_DIR=lib
set BIN_DIR=bin
set FFMPEG_DIR=ffmpeg
if not exist "%LIB_DIR%" mkdir "%LIB_DIR%"
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"
if not exist "%FFMPEG_DIR%" mkdir "%FFMPEG_DIR%"

:: 2. Download and Setup FFmpeg (Portable)
echo.
echo === Configurando FFmpeg ===
if not exist "%FFMPEG_DIR%\bin\ffmpeg.exe" (
    echo FFmpeg no encontrado. Descargando...
    
    :: URL de FFmpeg builds oficiales (gyan.dev - builds estables)
    set FFMPEG_URL=https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
    set FFMPEG_ZIP=%FFMPEG_DIR%\ffmpeg.zip
    
    echo Descargando FFmpeg desde gyan.dev...
    curl -L "!FFMPEG_URL!" -o "!FFMPEG_ZIP!"
    
    if !errorlevel! equ 0 (
        echo Extrayendo FFmpeg...
        powershell -command "Expand-Archive -Path '!FFMPEG_ZIP!' -DestinationPath '%FFMPEG_DIR%' -Force"
        
        :: Mover archivos de la carpeta extraída al directorio ffmpeg
        for /d %%d in (%FFMPEG_DIR%\ffmpeg-*) do (
            echo Moviendo archivos de %%d...
            xcopy "%%d\bin\*.*" "%FFMPEG_DIR%\bin\" /E /I /Y
            xcopy "%%d\doc\*.*" "%FFMPEG_DIR%\doc\" /E /I /Y
            xcopy "%%d\presets\*.*" "%FFMPEG_DIR%\presets\" /E /I /Y
            rd /s /q "%%d"
        )
        
        del "!FFMPEG_ZIP!"
        echo FFmpeg instalado correctamente en %FFMPEG_DIR%\bin\
    ) else (
        echo ERROR: No se pudo descargar FFmpeg.
        echo Por favor, descarga FFmpeg manualmente desde https://www.gyan.dev/ffmpeg/builds/
        echo y extrae los archivos en la carpeta %FFMPEG_DIR%\
        pause
        exit /b 1
    )
) else (
    echo FFmpeg ya esta instalado en %FFMPEG_DIR%\bin\
)

:: Agregar FFmpeg al PATH del sistema de forma permanente
echo.
echo === Agregando FFmpeg al PATH del sistema ===
set "FFMPEG_BIN_PATH=%CD%\%FFMPEG_DIR%\bin"

:: Verificar si FFmpeg ya está en el PATH
echo Verificando PATH actual...
echo %PATH% | find /i "%FFMPEG_BIN_PATH%" >nul
if !errorlevel! neq 0 (
    echo FFmpeg no esta en el PATH. Agregando...
    
    :: Usar PowerShell para agregar al PATH del usuario de forma permanente
    powershell -Command "$oldPath = [Environment]::GetEnvironmentVariable('Path', 'User'); if ($oldPath -notlike '*%FFMPEG_BIN_PATH%*') { $newPath = $oldPath + ';%FFMPEG_BIN_PATH%'; [Environment]::SetEnvironmentVariable('Path', $newPath, 'User'); Write-Host 'FFmpeg agregado al PATH del usuario correctamente' } else { Write-Host 'FFmpeg ya estaba en el PATH' }"
    
    :: Actualizar PATH en la sesión actual
    set "PATH=%PATH%;%FFMPEG_BIN_PATH%"
    
    echo.
    echo ===============================
    echo FFmpeg agregado al PATH!
    echo Ruta: %FFMPEG_BIN_PATH%
    echo.
    echo NOTA: El PATH se ha actualizado para el usuario actual.
    echo Puede que necesites reiniciar el CMD para que otros programas lo detecten.
    echo ===============================
    echo.
) else (
    echo FFmpeg ya esta en el PATH del sistema.
)

:: 3. Automated Dependency Management
echo.
echo === Verificando dependencias Java en %LIB_DIR%... ===

set "LIBS=https://repo1.maven.org/maven2/org/bytedeco/javacv/1.5.9/javacv-1.5.9.jar https://repo1.maven.org/maven2/org/bytedeco/javacv-platform/1.5.9/javacv-platform-1.5.9.jar https://repo1.maven.org/maven2/org/bytedeco/javacpp/1.5.9/javacpp-1.5.9.jar https://repo1.maven.org/maven2/org/bytedeco/javacpp/1.5.9/javacpp-1.5.9-linux-x86_64.jar https://repo1.maven.org/maven2/org/bytedeco/javacpp/1.5.9/javacpp-1.5.9-macosx-arm64.jar https://repo1.maven.org/maven2/org/bytedeco/javacpp/1.5.9/javacpp-1.5.9-macosx-x86_64.jar https://repo1.maven.org/maven2/org/bytedeco/javacpp/1.5.9/javacpp-1.5.9-windows-x86.jar https://repo1.maven.org/maven2/org/bytedeco/javacpp/1.5.9/javacpp-1.5.9-windows-x86_64.jar https://repo1.maven.org/maven2/org/bytedeco/ffmpeg/6.0-1.5.9/ffmpeg-6.0-1.5.9.jar https://repo1.maven.org/maven2/org/bytedeco/ffmpeg/6.0-1.5.9/ffmpeg-6.0-1.5.9-linux-x86_64.jar https://repo1.maven.org/maven2/org/bytedeco/ffmpeg/6.0-1.5.9/ffmpeg-6.0-1.5.9-macosx-arm64.jar https://repo1.maven.org/maven2/org/bytedeco/ffmpeg/6.0-1.5.9/ffmpeg-6.0-1.5.9-macosx-x86_64.jar https://repo1.maven.org/maven2/org/bytedeco/ffmpeg/6.0-1.5.9/ffmpeg-6.0-1.5.9-windows-x86.jar https://repo1.maven.org/maven2/org/bytedeco/ffmpeg/6.0-1.5.9/ffmpeg-6.0-1.5.9-windows-x86_64.jar"

for %%u in (%LIBS%) do (
    set "url=%%u"
    for %%f in ("!url!") do set "filename=%%~nxf"
    if not exist "%LIB_DIR%\!filename!" (
        echo Descargando !filename!...
        curl -L "!url!" -o "%LIB_DIR%\!filename!"
    )
)

:: 4. Compilation
echo.
echo === Compilando codigo fuente... ===
dir /s /b src\*.java > sources.txt
if not exist "bin_user" mkdir "bin_user"
javac -encoding UTF-8 -d bin_user -cp "lib/*;src" @sources.txt

if %errorlevel% equ 0 (
    echo.
    echo === Compilando y empaquetando plugins... ===
    dir /s /b plugins_src\*.java > plugins_sources.txt
    if not exist "bin_plugins" mkdir "bin_plugins"
    javac -encoding UTF-8 -d bin_plugins -cp "lib/*;bin_user" @plugins_sources.txt
    
    if not exist "bin_plugins\META-INF" mkdir "bin_plugins\META-INF"
    xcopy "plugins_src\META-INF" "bin_plugins\META-INF" /E /I /Y
    
    if not exist "plugins" mkdir "plugins"
    jar cf plugins/samples.jar -C bin_plugins .
    
    del plugins_sources.txt
    rd /s /q bin_plugins

    echo.
    echo ===============================
    echo ¡Compilacion exitosa!
    echo FFmpeg portable configurado en: %FFMPEG_DIR%\bin\
    echo Usa run.bat para iniciar.
    echo ===============================
) else (
    echo.
    echo ===============================
    echo ERROR en la compilacion del núcleo.
    echo ===============================
    del sources.txt
    pause
    exit /b 1
)

del sources.txt
pause
