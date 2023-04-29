@echo off
setlocal enabledelayedexpansion

:input_emulator
set /p emulator=Enter the emulator (Yuzu, Ryujinx, or Both): 
if /i "%emulator%"=="Yuzu" goto display_versions
if /i "%emulator%"=="Ryujinx" goto display_versions
if /i "%emulator%"=="Both" goto display_versions
echo Invalid emulator specified.
set "emulator= "
goto input_emulator

:display_versions
echo.
echo Available versions:
for /d %%f in (*) do (
    if "%%~nxf" neq "%~n0" (
        echo %%~nxf
    )
)
echo.
set /p version=Enter the version number (available versions are shown above): 
set version=%version: =%
for /d %%f in (*) do (
    if "%%~nxf" neq "%~n0" (
        if %%~nxf==%version% goto install
    )
)
echo Invalid version number
set "version= "
goto display_versions

:install
echo.
if /i "%emulator%"=="Both" (
    set "yuzu_dest=%appdata%\Yuzu"
    set "ryujinx_dest=%appdata%\Ryujinx"
    echo Deleting old keys and firmware for Yuzu...
    del /q "!yuzu_dest!\keys\prod.keys"
    del /q "!yuzu_dest!\nand\system\Contents\registered\*.*"
    echo Deleting old keys and firmware for Ryujinx...
    del "!ryujinx_dest!\system\prod.keys"
    rmdir /s /q "!ryujinx_dest!\bis\system\Contents\registered"
    echo.
    echo Copying files for Yuzu...
    xcopy "%version%\Yuzu" "!yuzu_dest!" /S /E /I /Y /Q
    echo.
    echo Copying files for Ryujinx...
    xcopy "%version%\Ryujinx" "!ryujinx_dest!" /S /E /I /Y /Q
    echo.
    echo Successfully installed keys and firmware for version %version%
    goto end
) else if /i "%emulator%"=="Yuzu" (
    set "dest=%appdata%\Yuzu"
    echo Deleting old keys and firmware...
    del /q "!dest!\keys\prod.keys"
    del /q "!dest!\nand\system\Contents\registered\*.*"
) else (
    set "dest=%appdata%\Ryujinx"
    echo Deleting old keys and firmware...
    del "!dest!\system\prod.keys"
    rmdir /s /q "!dest!\bis\system\Contents\registered"
    
)
echo.
echo Copying files for %emulator%...
xcopy "%version%\%emulator%" "!dest!" /S /E /I /Y /Q

:end
echo.
pause
