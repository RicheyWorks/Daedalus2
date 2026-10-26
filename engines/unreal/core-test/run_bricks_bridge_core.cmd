@echo off
setlocal
if "%~1"=="" exit /b 2
set "BRIDGE_CORE_BUILD=%~f1"
if exist "%BRIDGE_CORE_BUILD%" (
    echo Refusing to replace an existing check directory.
    exit /b 2
)
mkdir "%BRIDGE_CORE_BUILD%"
if errorlevel 1 exit /b 1
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /Fo"%BRIDGE_CORE_BUILD%\bridge.obj" /Fe"%BRIDGE_CORE_BUILD%\bridge.exe" "%~dp0bricks_bridge_core_test.cpp"
if errorlevel 1 exit /b 1
"%BRIDGE_CORE_BUILD%\bridge.exe"
exit /b %errorlevel%
