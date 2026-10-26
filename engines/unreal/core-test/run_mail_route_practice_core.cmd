@echo off
setlocal
if "%~1"=="" exit /b 2
set "MAIL_PRACTICE_BUILD=%~f1"
if exist "%MAIL_PRACTICE_BUILD%" (
    echo Refusing to replace an existing check directory.
    exit /b 2
)
mkdir "%MAIL_PRACTICE_BUILD%"
if errorlevel 1 exit /b 1
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /Fo"%MAIL_PRACTICE_BUILD%\mail_practice.obj" /Fe"%MAIL_PRACTICE_BUILD%\mail_practice.exe" "%~dp0mail_route_practice_core_test.cpp"
if errorlevel 1 exit /b 1
"%MAIL_PRACTICE_BUILD%\mail_practice.exe"
exit /b %errorlevel%
