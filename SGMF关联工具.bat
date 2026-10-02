@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion
title SGMF 文件关联一体化工具

:: ============================================================
:: 自动提权
:: ============================================================
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -NoProfile -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"

:: ============================================================
:: 初始化
:: ============================================================
set "PLAYER_PATH="
set "ICON_DIR=%~dp0assets"

:: 如果当前目录没有 assets，尝试从 exe 目录找
if not exist "%ICON_DIR%\icon.ico" (
    set "ICON_DIR="
)

:: 尝试自动探测播放器
if exist "%~dp0dist\SGMFPlayer.exe" (
    set "PLAYER_PATH=%~dp0dist\SGMFPlayer.exe"
) else if exist "%~dp0SGMFPlayer.exe" (
    set "PLAYER_PATH=%~dp0SGMFPlayer.exe"
)

:: ============================================================
:: 主菜单
:: ============================================================
:MainMenu
cls
call :Banner

echo   当前播放器:
if defined PLAYER_PATH (
    echo     !PLAYER_PATH!
) else (
    echo     [未设置]
)
echo.
if defined ICON_DIR (
    echo   图标目录: !ICON_DIR!
) else (
    echo   图标目录: [未找到]
)
echo.
echo   ------------------------------------------------------------
echo.
echo     [1]  设置播放器路径
echo     [2]  注册文件关联
echo     [3]  注销文件关联
echo     [4]  查看当前关联状态
echo     [5]  刷新系统图标缓存
echo     [6]  打开文件所在目录
echo     [0]  退出
echo.
echo   ------------------------------------------------------------
echo.
set /p "CHOICE=请输入选项 [0-6]: "

if "%CHOICE%"=="1" goto SetPath
if "%CHOICE%"=="2" goto DoRegister
if "%CHOICE%"=="3" goto DoUnregister
if "%CHOICE%"=="4" goto ShowStatus
if "%CHOICE%"=="5" goto RefreshIcons
if "%CHOICE%"=="6" goto OpenFolder
if "%CHOICE%"=="0" goto Quit
goto MainMenu


:: ============================================================
:: [1] 设置播放器路径
:: ============================================================
:SetPath
cls
call :Banner
echo   设置播放器路径
echo   ------------------------------------------------------------
echo.
echo   你可以：
echo     - 直接粘贴完整路径（例：C:\SGMF\SGMFPlayer.exe）
echo     - 或者把 exe 文件拖到本窗口后按回车
echo     - 输入 B 打开文件选择对话框
echo     - 输入 Q 返回主菜单
echo.
echo   当前: !PLAYER_PATH!
echo.
set /p "INPUT=请输入: "

if /i "!INPUT!"=="Q" goto MainMenu
if /i "!INPUT!"=="B" (
    call :BrowseFile
    goto SetPath
)

:: 去掉引号
set "INPUT=!INPUT:"=!"

if not exist "!INPUT!" (
    echo.
    echo   [错误] 文件不存在: !INPUT!
    echo.
    pause
    goto SetPath
)

:: 检查扩展名
for %%F in ("!INPUT!") do set "INPUT_EXT=%%~xF"
if /i not "!INPUT_EXT!"==".exe" (
    echo.
    echo   [警告] 该文件不是 .exe，确定继续吗？
    set /p "CONFIRM=继续? [Y/N]: "
    if /i not "!CONFIRM!"=="Y" goto SetPath
)

:: 转为绝对路径
for %%F in ("!INPUT!") do set "PLAYER_PATH=%%~fF"

:: 尝试从播放器目录探测图标
call :ProbeIcons

echo.
echo   [OK] 播放器路径已设置
echo        !PLAYER_PATH!
echo.
pause
goto MainMenu


:: ============================================================
:: [2] 注册文件关联
:: ============================================================
:DoRegister
cls
call :Banner

if not defined PLAYER_PATH (
    echo   [错误] 请先设置播放器路径（选项 1）
    echo.
    pause
    goto MainMenu
)

if not exist "!PLAYER_PATH!" (
    echo   [错误] 播放器文件不存在:
    echo        !PLAYER_PATH!
    echo.
    echo   请重新设置路径（选项 1）
    echo.
    pause
    goto MainMenu
)

echo   准备注册文件关联
echo   ------------------------------------------------------------
echo.
echo   播放器: !PLAYER_PATH!
if defined ICON_DIR (
    echo   图标:   !ICON_DIR!
) else (
    echo   图标:   [未找到，将使用 exe 内置图标]
)
echo.
echo   将关联以下扩展名:
echo     .sgmic  →  SGMF 音频
echo     .sgpim  →  SGMF 视频
echo     .sgwb   →  SGMF 文本
echo     .sgtp   →  SGMF 图片
echo.
set /p "CONFIRM=确认注册? [Y/N]: "
if /i not "!CONFIRM!"=="Y" goto MainMenu

echo.
echo   正在注册...
echo.

:: 图标
set "ICON_MAIN="
set "ICON_AUDIO="
set "ICON_VIDEO="
set "ICON_TEXT="
set "ICON_IMAGE="

if defined ICON_DIR (
    if exist "!ICON_DIR!\icon.ico"        set "ICON_MAIN=!ICON_DIR!\icon.ico"
    if exist "!ICON_DIR!\icon_audio.ico"  set "ICON_AUDIO=!ICON_DIR!\icon_audio.ico"
    if exist "!ICON_DIR!\icon_video.ico"  set "ICON_VIDEO=!ICON_DIR!\icon_video.ico"
    if exist "!ICON_DIR!\icon_text.ico"   set "ICON_TEXT=!ICON_DIR!\icon_text.ico"
    if exist "!ICON_DIR!\icon_image.ico"  set "ICON_IMAGE=!ICON_DIR!\icon_image.ico"
)

:: 没有专用图标时回退
if not defined ICON_AUDIO if defined ICON_MAIN set "ICON_AUDIO=!ICON_MAIN!"
if not defined ICON_VIDEO if defined ICON_MAIN set "ICON_VIDEO=!ICON_MAIN!"
if not defined ICON_TEXT  if defined ICON_MAIN set "ICON_TEXT=!ICON_MAIN!"
if not defined ICON_IMAGE if defined ICON_MAIN set "ICON_IMAGE=!ICON_MAIN!"

:: 逐个注册
call :RegisterOne ".sgmic" "SGMF.Audio" "SGMF 音频" "!ICON_AUDIO!"
call :RegisterOne ".sgpim" "SGMF.Video" "SGMF 视频" "!ICON_VIDEO!"
call :RegisterOne ".sgwb"  "SGMF.Text"  "SGMF 文本" "!ICON_TEXT!"
call :RegisterOne ".sgtp"  "SGMF.Image" "SGMF 图片" "!ICON_IMAGE!"

echo.
echo   ------------------------------------------------------------
echo   [完成] 已注册 4 种扩展名
echo   ------------------------------------------------------------
echo.
echo   提示:
echo     1. 首次双击 .sgmic 文件，Windows 可能弹「选择默认程序」
echo        选一次 SGMF 播放器 + 勾选「始终使用」即可。
echo     2. 如果图标没更新，用选项 [5] 刷新图标缓存。
echo.
pause
goto MainMenu


:: ============================================================
:: [3] 注销文件关联
:: ============================================================
:DoUnregister
cls
call :Banner
echo   注销文件关联
echo   ------------------------------------------------------------
echo.
echo   将删除以下扩展名的 SGMF 关联:
echo     .sgmic / .sgpim / .sgwb / .sgtp
echo.
echo   注意：不会影响这些扩展名的其他关联。
echo.
set /p "CONFIRM=确认注销? [Y/N]: "
if /i not "!CONFIRM!"=="Y" goto MainMenu

echo.
echo   正在注销...
echo.

call :UnregisterOne ".sgmic" "SGMF.Audio"
call :UnregisterOne ".sgpim" "SGMF.Video"
call :UnregisterOne ".sgwb"  "SGMF.Text"
call :UnregisterOne ".sgtp"  "SGMF.Image"

echo.
echo   [完成] 已注销 4 种扩展名
echo.
pause
goto MainMenu


:: ============================================================
:: [4] 查看当前关联状态
:: ============================================================
:ShowStatus
cls
call :Banner
echo   当前关联状态
echo   ============================================================
echo.

call :CheckOne ".sgmic" "SGMF.Audio"
call :CheckOne ".sgpim" "SGMF.Video"
call :CheckOne ".sgwb"  "SGMF.Text"
call :CheckOne ".sgtp"  "SGMF.Image"

echo.
echo   ------------------------------------------------------------
echo.
echo   说明:
echo     ✓ 已关联  → 该扩展名指向 SGMF 播放器
echo     ✗ 未关联  → 该扩展名未关联到 SGMF
echo.
echo   当前播放器: 
if defined PLAYER_PATH (
    echo     !PLAYER_PATH!
) else (
    echo     [未设置]
)
echo.
pause
goto MainMenu


:: ============================================================
:: [5] 刷新图标缓存
:: ============================================================
:RefreshIcons
cls
call :Banner
echo   刷新系统图标缓存
echo   ------------------------------------------------------------
echo.
echo   正在执行...
ie4uinit.exe -show >nul 2>&1
echo.
echo   [完成] 图标缓存已刷新
echo.
echo   如果资源管理器图标还是旧的，可以:
echo     - 注销后重新登录
echo     - 或重启资源管理器
echo.
set /p "RESTART=是否重启资源管理器? [Y/N]: "
if /i "!RESTART!"=="Y" (
    echo   重启中...
    taskkill /f /im explorer.exe >nul 2>&1
    start explorer.exe
    echo   [完成]
)
echo.
pause
goto MainMenu


:: ============================================================
:: [6] 打开文件所在目录
:: ============================================================
:OpenFolder
cls
call :Banner
if not defined PLAYER_PATH (
    echo   [错误] 请先设置播放器路径
    echo.
    pause
    goto MainMenu
)
for %%F in ("!PLAYER_PATH!") do set "PLAYER_DIR=%%~dpF"
echo   正在打开: !PLAYER_DIR!
start "" "!PLAYER_DIR!"
timeout /t 1 >nul
goto MainMenu


:: ============================================================
:: 退出
:: ============================================================
:Quit
cls
echo.
echo   感谢使用 SGMF 文件关联工具，再见！
echo.
timeout /t 1 >nul
exit /b 0


:: ============================================================
:: 子过程: 显示标题
:: ============================================================
:Banner
echo.
echo   ============================================================
echo                    SGMF 文件关联一体化工具
echo   ============================================================
echo.
exit /b 0


:: ============================================================
:: 子过程: 文件浏览对话框（用 PowerShell）
:: ============================================================
:BrowseFile
echo.
echo   正在打开文件选择对话框...
echo.
for /f "usebackq tokens=*" %%P in (`powershell -NoProfile -Command ^
    "Add-Type -AssemblyName System.Windows.Forms;" ^
    "$d = New-Object System.Windows.Forms.OpenFileDialog;" ^
    "$d.Filter = '可执行文件 (*.exe)|*.exe|所有文件 (*.*)|*.*';" ^
    "$d.Title = '选择 SGMF 播放器 exe';" ^
    "if ($d.ShowDialog() -eq 'OK') { Write-Output $d.FileName }"`) do (
    set "BROWSE_RESULT=%%P"
)
if defined BROWSE_RESULT (
    set "PLAYER_PATH=!BROWSE_RESULT!"
    echo   [OK] 已选择: !PLAYER_PATH!
    call :ProbeIcons
    timeout /t 1 >nul
)
exit /b 0


:: ============================================================
:: 子过程: 从播放器目录探测图标
:: ============================================================
:ProbeIcons
if not defined PLAYER_PATH exit /b 0

for %%F in ("!PLAYER_PATH!") do set "PLAYER_DIR=%%~dpF"

:: 依次尝试几个可能的图标目录
if exist "!PLAYER_DIR!assets\icon.ico" (
    set "ICON_DIR=!PLAYER_DIR!assets"
    exit /b 0
)
if exist "!PLAYER_DIR!..\assets\icon.ico" (
    pushd "!PLAYER_DIR!..\assets" >nul 2>&1
    set "ICON_DIR=!CD!"
    popd >nul 2>&1
    exit /b 0
)
exit /b 0


:: ============================================================
:: 子过程: 注册一个扩展名
:: 参数: 扩展名 ProgID 描述 图标路径
:: ============================================================
:RegisterOne
set "EXT=%~1"
set "PROG=%~2"
set "DESC=%~3"
set "ICO=%~4"

echo   [注册] %EXT%  →  %PROG%

:: 1. 扩展名默认值
reg add "HKCU\Software\Classes\%EXT%" /ve /d "%PROG%" /f >nul 2>&1

:: 2. OpenWithProgids
reg add "HKCU\Software\Classes\%EXT%\OpenWithProgids" /v "%PROG%" /t REG_NONE /d "" /f >nul 2>&1

:: 3. ProgID 描述
reg add "HKCU\Software\Classes\%PROG%" /ve /d "%DESC%" /f >nul 2>&1

:: 4. 图标
if defined ICO (
    reg add "HKCU\Software\Classes\%PROG%\DefaultIcon" /ve /d "%ICO%,0" /f >nul 2>&1
)

:: 5. 打开命令
reg add "HKCU\Software\Classes\%PROG%\shell" /ve /d "open" /f >nul 2>&1
reg add "HKCU\Software\Classes\%PROG%\shell\open" /ve /d "用 SGMF 播放器打开" /f >nul 2>&1
if defined ICO (
    reg add "HKCU\Software\Classes\%PROG%\shell\open" /v "Icon" /d "%ICO%,0" /f >nul 2>&1
)
reg add "HKCU\Software\Classes\%PROG%\shell\open\command" /ve /d "\"%PLAYER_PATH%\" \"%%1\"" /f >nul 2>&1

exit /b 0


:: ============================================================
:: 子过程: 注销一个扩展名
:: ============================================================
:UnregisterOne
set "EXT=%~1"
set "PROG=%~2"

echo   [注销] %EXT%  ←  %PROG%

reg delete "HKCU\Software\Classes\%EXT%" /ve /f >nul 2>&1
reg delete "HKCU\Software\Classes\%EXT%\OpenWithProgids" /v "%PROG%" /f >nul 2>&1
reg delete "HKCU\Software\Classes\%PROG%" /f >nul 2>&1

exit /b 0


:: ============================================================
:: 子过程: 检查一个扩展名
:: ============================================================
:CheckOne
set "EXT=%~1"
set "PROG=%~2"

set "CURRENT="
for /f "tokens=2,*" %%A in ('reg query "HKCU\Software\Classes\%EXT%" /ve 2^>nul ^| findstr /i "REG_SZ"') do (
    set "CURRENT=%%B"
)

set "CMD="
for /f "tokens=2,*" %%A in ('reg query "HKCU\Software\Classes\%PROG%\shell\open\command" /ve 2^>nul ^| findstr /i "REG_SZ"') do (
    set "CMD=%%B"
)

if "!CURRENT!"=="%PROG%" (
    if defined CMD (
        echo   [✓] %EXT%   已关联
        echo        命令: !CMD!
    ) else (
        echo   [!] %EXT%   部分关联（缺命令）
    )
) else (
    if "!CURRENT!"=="" (
        echo   [✗] %EXT%   未关联
    ) else (
        echo   [✗] %EXT%   已关联到其他程序: !CURRENT!
    )
)
exit /b 0