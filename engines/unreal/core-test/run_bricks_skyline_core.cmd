@echo off
setlocal
if "%~1"=="" exit /b 2
set "SKYLINE_CORE_BUILD=%~f1"
if exist "%SKYLINE_CORE_BUILD%" (
    echo Refusing to replace an existing check directory.
    exit /b 2
)
mkdir "%SKYLINE_CORE_BUILD%"
if errorlevel 1 exit /b 1
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /Fo"%SKYLINE_CORE_BUILD%\skyline.obj" /Fe"%SKYLINE_CORE_BUILD%\skyline.exe" "%~dp0bricks_skyline_core_test.cpp"
if errorlevel 1 exit /b 1
"%SKYLINE_CORE_BUILD%\skyline.exe"
exit /b %errorlevel%
