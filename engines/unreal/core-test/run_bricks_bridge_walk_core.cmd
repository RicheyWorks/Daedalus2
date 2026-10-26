@echo off
setlocal
if "%~1"=="" exit /b 2
set "BRIDGE_WALK_BUILD=%~f1"
if exist "%BRIDGE_WALK_BUILD%" (
    echo Refusing to replace an existing check directory.
    exit /b 2
)
mkdir "%BRIDGE_WALK_BUILD%"
if errorlevel 1 exit /b 1
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /Fo"%BRIDGE_WALK_BUILD%\bridge_walk.obj" /Fe"%BRIDGE_WALK_BUILD%\bridge_walk.exe" "%~dp0bricks_bridge_walk_core_test.cpp"
if errorlevel 1 exit /b 1
"%BRIDGE_WALK_BUILD%\bridge_walk.exe"
exit /b %errorlevel%
