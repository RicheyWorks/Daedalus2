@echo off
setlocal
if "%~1"=="" exit /b 2
set "FLIPBOOK_CORE_BUILD=%~f1"
if exist "%FLIPBOOK_CORE_BUILD%" (
    echo Refusing to replace an existing check directory.
    exit /b 2
)
mkdir "%FLIPBOOK_CORE_BUILD%"
if errorlevel 1 exit /b 1
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /Fo"%FLIPBOOK_CORE_BUILD%\flipbook.obj" /Fe"%FLIPBOOK_CORE_BUILD%\flipbook.exe" "%~dp0gallery_motif_flipbook_core_test.cpp"
if errorlevel 1 exit /b 1
"%FLIPBOOK_CORE_BUILD%\flipbook.exe"
exit /b %errorlevel%
