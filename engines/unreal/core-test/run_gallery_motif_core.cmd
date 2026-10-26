@echo off
setlocal
if "%~1"=="" exit /b 2
set "MOTIF_CORE_BUILD=%~f1"
if exist "%MOTIF_CORE_BUILD%" (
    echo Refusing to replace an existing check directory.
    exit /b 2
)
mkdir "%MOTIF_CORE_BUILD%"
if errorlevel 1 exit /b 1
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /Fo"%MOTIF_CORE_BUILD%\motif.obj" /Fe"%MOTIF_CORE_BUILD%\motif.exe" "%~dp0gallery_motif_core_test.cpp"
if errorlevel 1 exit /b 1
"%MOTIF_CORE_BUILD%\motif.exe"
exit /b %errorlevel%
