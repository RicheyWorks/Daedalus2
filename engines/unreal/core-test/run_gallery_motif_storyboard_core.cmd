@echo off
setlocal
if "%~1"=="" exit /b 2
set "STORYBOARD_CORE_BUILD=%~f1"
set "STORYBOARD_CORE_PYTHON=python"
if not "%~2"=="" set "STORYBOARD_CORE_PYTHON=%~f2"
if exist "%STORYBOARD_CORE_BUILD%" (
    echo Refusing to replace an existing check directory.
    exit /b 2
)
mkdir "%STORYBOARD_CORE_BUILD%"
if errorlevel 1 exit /b 1
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /Fo"%STORYBOARD_CORE_BUILD%\storyboard.obj" /Fe"%STORYBOARD_CORE_BUILD%\storyboard.exe" "%~dp0gallery_motif_storyboard_core_test.cpp"
if errorlevel 1 exit /b 1
"%STORYBOARD_CORE_BUILD%\storyboard.exe" "%STORYBOARD_CORE_BUILD%"
if errorlevel 1 exit /b 1
"%STORYBOARD_CORE_PYTHON%" "%~dp0verify_gallery_motif_storyboard.py" "%STORYBOARD_CORE_BUILD%"
exit /b %errorlevel%
