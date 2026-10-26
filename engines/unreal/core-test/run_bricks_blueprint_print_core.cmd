@echo off
setlocal
if "%~1"=="" exit /b 2
set "PRINT_CORE_BUILD=%~f1"
set "PRINT_CORE_PYTHON=python"
if not "%~2"=="" set "PRINT_CORE_PYTHON=%~f2"
if exist "%PRINT_CORE_BUILD%" (
    echo Refusing to replace an existing check directory.
    exit /b 2
)
mkdir "%PRINT_CORE_BUILD%"
if errorlevel 1 exit /b 1
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /Fo"%PRINT_CORE_BUILD%\print.obj" /Fe"%PRINT_CORE_BUILD%\print.exe" "%~dp0bricks_blueprint_print_core_test.cpp"
if errorlevel 1 exit /b 1
"%PRINT_CORE_BUILD%\print.exe" "%PRINT_CORE_BUILD%"
if errorlevel 1 exit /b 1
"%PRINT_CORE_PYTHON%" "%~dp0verify_bricks_blueprint_print.py" "%PRINT_CORE_BUILD%"
exit /b %errorlevel%
