@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion
title SGMF 一键安装

:: ============================================================
::  自动提权
:: ============================================================
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [信息] 正在请求管理员权限...
    powershell -NoProfile -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"

:: ============================================================
::  配置区
:: ============================================================
set "PYTHON_MIN_MAJOR=3"
set "PYTHON_MIN_MINOR=8"
set "FFMPEG_DIR=%CD%\tools\ffmpeg"
set "FFMPEG_URL=https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
set "VENV_DIR=%CD%\.venv"
set "USE_VENV=0"
set "PIP_MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple"

:: 检测 Windows 版本
set "IS_WIN7=0"
ver | findstr /i "6\.1\." >nul 2>&1 && set "IS_WIN7=1"

:: ============================================================
::  彩色输出辅助
:: ============================================================
call :Banner

:: ============================================================
::  [1/7] Python 检测
:: ============================================================
call :Step "1/7" "检测 Python 环境"

set "PY_CMD="
for %%P in (python py python3) do (
    if not defined PY_CMD (
        where %%P >nul 2>&1 && (
            for /f "tokens=2" %%V in ('%%P --version 2^>^&1') do (
                set "PY_CMD=%%P"
                set "PY_VER=%%V"
            )
        )
    )
)

if not defined PY_CMD (
    echo   [错误] 未检测到 Python。
    echo.
    echo   请先安装 Python 3.8 ^(Windows 7 兼容版^):
    echo     https://www.python.org/downloads/release/python-3810/
    echo.
    echo   安装时务必勾选 "Add Python to PATH"。
    echo.
    pause
    exit /b 1
)

echo   [OK] Python 版本: !PY_VER!  ^(命令: !PY_CMD!^)

for /f "tokens=1,2 delims=." %%A in ("!PY_VER!") do (
    set "PY_MAJOR=%%A"
    set "PY_MINOR=%%B"
)
if !PY_MAJOR! LSS %PYTHON_MIN_MAJOR% (
    echo   [错误] Python 版本过低，需要 %PYTHON_MIN_MAJOR%.%PYTHON_MIN_MINOR% 或更高。
    pause & exit /b 1
)
if !PY_MAJOR! EQU %PYTHON_MIN_MAJOR% if !PY_MINOR! LSS %PYTHON_MIN_MINOR% (
    echo   [错误] Python 版本过低，需要 %PYTHON_MIN_MAJOR%.%PYTHON_MIN_MINOR% 或更高。
    pause & exit /b 1
)

:: ============================================================
::  [2/7] 虚拟环境（可选）
:: ============================================================
call :Step "2/7" "虚拟环境配置"

if "%USE_VENV%"=="1" (
    if not exist "%VENV_DIR%\Scripts\python.exe" (
        echo   创建虚拟环境: %VENV_DIR%
        !PY_CMD! -m venv "%VENV_DIR%"
        if !errorlevel! neq 0 (
            echo   [错误] 虚拟环境创建失败。
            pause & exit /b 1
        )
    ) else (
        echo   已存在虚拟环境，跳过创建。
    )
    set "PY_CMD=%VENV_DIR%\Scripts\python.exe"
    echo   [OK] 使用虚拟环境: %VENV_DIR%
) else (
    echo   跳过（使用系统 Python）
)

:: ============================================================
::  [3/7] 升级 pip
:: ============================================================
call :Step "3/7" "升级 pip / setuptools / wheel"

!PY_CMD! -m pip install --upgrade pip setuptools wheel -i %PIP_MIRROR%
if !errorlevel! neq 0 (
    echo   [警告] pip 升级失败，继续安装依赖。
)

:: ============================================================
::  [4/7] 生成并安装依赖
:: ============================================================
call :Step "4/7" "安装 Python 依赖"

set "REQ_TMP=%TEMP%\sgmf_req_%RANDOM%.txt"

if "%IS_WIN7%"=="1" (
    echo   检测到 Windows 7，使用 PySide2 兼容版依赖
    call :WriteWin7Req
) else (
    echo   检测到 Windows 10/11，使用 PySide6 依赖
    call :WriteWin10Req
)

echo.
echo   正在安装... 首次安装可能需要 3-10 分钟，请耐心等待。
echo.

!PY_CMD! -m pip install -r "%REQ_TMP%" -i %PIP_MIRROR% --trusted-host pypi.tuna.tsinghua.edu.cn
set "PIP_ERR=!errorlevel!"
del "%REQ_TMP%" >nul 2>&1

if !PIP_ERR! neq 0 (
    echo.
    echo   [错误] 依赖安装失败 ^(错误码: !PIP_ERR!^)
    echo.
    echo   可尝试手动排查:
    echo     1. 检查网络连接
    echo     2. 升级 pip:  !PY_CMD! -m pip install --upgrade pip
    echo     3. 重试本脚本
    echo.
    pause & exit /b 1
)
echo   [OK] Python 依赖安装完成

:: ============================================================
::  [5/7] FFmpeg 检测 / 下载
:: ============================================================
call :Step "5/7" "检查 FFmpeg"

set "FFMPEG_OK=0"
where ffmpeg >nul 2>&1 && set "FFMPEG_OK=1"
if exist "%FFMPEG_DIR%\bin\ffmpeg.exe" (
    set "FFMPEG_OK=1"
    set "PATH=%FFMPEG_DIR%\bin;%PATH%"
)

if "%FFMPEG_OK%"=="1" (
    echo   [OK] 已检测到 FFmpeg
) else (
    echo   未检测到 FFmpeg，准备下载便携版...
    if not exist "tools" mkdir "tools"

    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$ProgressPreference='SilentlyContinue';" ^
        "try {" ^
        "  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
        "  Invoke-WebRequest -Uri '%FFMPEG_URL%' -OutFile 'tools\ffmpeg.zip' -UseBasicParsing;" ^
        "  exit 0" ^
        "} catch { Write-Host $_.Exception.Message; exit 1 }"

    if !errorlevel! neq 0 (
        echo   [警告] FFmpeg 下载失败。
        echo   请手动下载后解压到: %FFMPEG_DIR%
        echo   下载地址: %FFMPEG_URL%
    ) else (
        echo   解压中...
        powershell -NoProfile -Command ^
            "Expand-Archive -Force 'tools\ffmpeg.zip' 'tools\ffmpeg_tmp';" ^
            "$src = Get-ChildItem 'tools\ffmpeg_tmp' -Directory ^| Select-Object -First 1;" ^
            "if ^(Test-Path '%FFMPEG_DIR%'^) { Remove-Item '%FFMPEG_DIR%' -Recurse -Force };" ^
            "Move-Item $src.FullName '%FFMPEG_DIR%';" ^
            "Remove-Item 'tools\ffmpeg_tmp' -Recurse -Force;" ^
            "Remove-Item 'tools\ffmpeg.zip' -Force"

        if exist "%FFMPEG_DIR%\bin\ffmpeg.exe" (
            echo   [OK] FFmpeg 已就绪
            setx PATH "%FFMPEG_DIR%\bin;%PATH%" >nul 2>&1
        ) else (
            echo   [警告] FFmpeg 解压异常，请手动检查 %FFMPEG_DIR%
        )
    )
)

:: ============================================================
::  [6/7] VLC 检测
:: ============================================================
call :Step "6/7" "检查 VLC"

set "VLC_OK=0"
if exist "%ProgramFiles%\VideoLAN\VLC\libvlc.dll" set "VLC_OK=1"
if exist "%ProgramFiles(x86)%\VideoLAN\VLC\libvlc.dll" set "VLC_OK=1"
where vlc >nul 2>&1 && set "VLC_OK=1"

if "%VLC_OK%"=="1" (
    echo   [OK] 已检测到 VLC
) else (
    echo   [警告] 未检测到 VLC，视频播放功能将不可用。
    echo   安装时 VLC 位数必须与 Python 一致。
    echo.
    set /p "OPEN_VLC=是否现在打开 VLC 下载页面? [Y/N]: "
    if /i "!OPEN_VLC!"=="Y" (
        start "" "https://www.videolan.org/vlc/download-windows.html"
    )
)

:: ============================================================
::  [7/7] VC++ 运行库检测
:: ============================================================
call :Step "7/7" "检查 VC++ 运行库"

set "VCREDIST_OK=0"
reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" >nul 2>&1 && set "VCREDIST_OK=1"
reg query "HKLM\SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" >nul 2>&1 && set "VCREDIST_OK=1"

if "%VCREDIST_OK%"=="1" (
    echo   [OK] 已检测到 VC++ 2015-2022 运行库
) else (
    echo   [警告] 未检测到 VC++ 运行库，Qt 可能无法启动。
    echo.
    set /p "OPEN_VC=是否现在打开 VC++ 运行库下载页面? [Y/N]: "
    if /i "!OPEN_VC!"=="Y" (
        start "" "https://aka.ms/vs/17/release/vc_redist.x64.exe"
    )
)

:: ============================================================
::  完成
:: ============================================================
echo.
echo ============================================================
echo   安装完成
echo ============================================================
echo.
echo   启动命令:
echo.
echo     转换器:  !PY_CMD! -m converter.main
echo     播放器:  !PY_CMD! -m player.main
echo.
echo   若刚刚安装了 FFmpeg / VLC / VC++，建议重启后再运行。
echo.
pause
exit /b 0


:: ============================================================
::  子过程：写依赖清单
:: ============================================================
:WriteWin7Req
(
echo cryptography^>=41.0.0
echo PySide2==5.15.2
echo pydub^>=0.25.1
echo sounddevice^>=0.4.6
echo numpy^>=1.24.0,^<2.0
echo python-vlc^>=3.0.18
echo Pillow^>=9.5.0
echo pyinstaller==5.1
) > "%REQ_TMP%"
exit /b 0

:WriteWin10Req
(
echo cryptography^>=41.0.0
echo PySide6==6.1.*
echo pydub^>=0.25.1
echo sounddevice^>=0.4.6
echo numpy^>=1.24.0
echo python-vlc^>=3.0.18
echo Pillow^>=10.0.0
echo pyinstaller^>=6.0
) > "%REQ_TMP%"
exit /b 0

:Banner
echo.
echo ============================================================
echo              SGMF 一键安装脚本  v1.1
echo ============================================================
echo.
exit /b 0

:Step
echo.
echo ------------------------------------------------------------
echo   [%~1] %~2
echo ------------------------------------------------------------
exit /b 0