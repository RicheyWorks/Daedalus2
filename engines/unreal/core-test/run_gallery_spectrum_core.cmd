@echo off
setlocal
if "%~1"=="" exit /b 2
set "SPECTRUM_CORE_BUILD=%~f1"
if exist "%SPECTRUM_CORE_BUILD%" (
    echo Refusing to replace an existing check directory.
    exit /b 2
)
mkdir "%SPECTRUM_CORE_BUILD%"
if errorlevel 1 exit /b 1
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /Fo"%SPECTRUM_CORE_BUILD%\spectrum.obj" /Fe"%SPECTRUM_CORE_BUILD%\spectrum.exe" "%~dp0gallery_spectrum_core_test.cpp"
if errorlevel 1 exit /b 1
"%SPECTRUM_CORE_BUILD%\spectrum.exe"
exit /b %errorlevel%
