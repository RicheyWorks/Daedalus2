@echo off
setlocal
if "%~1"=="" exit /b 2
set "MAIL_ROUTE_OUTPUT=%~f1"
if not exist "%MAIL_ROUTE_OUTPUT%" mkdir "%MAIL_ROUTE_OUTPUT%"
if errorlevel 1 exit /b 1
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /I"%~dp0..\DaedalusLink\Source\DaedalusLink\Public" "%~dp0mail_route_core_test.cpp" /Fo"%MAIL_ROUTE_OUTPUT%\mail_route_core_test.obj" /Fe"%MAIL_ROUTE_OUTPUT%\mail_route_core_test.exe"
if errorlevel 1 exit /b 1
"%MAIL_ROUTE_OUTPUT%\mail_route_core_test.exe"
exit /b %errorlevel%
