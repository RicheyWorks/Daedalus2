@echo off
setlocal
if "%~1"=="" exit /b 2
set "UNICORN_OUTPUT=%~1"
if not exist "%UNICORN_OUTPUT%" mkdir "%UNICORN_OUTPUT%"
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHs-c- /D_HAS_EXCEPTIONS=0 /W4 /WX "%~dp0unicorn_reward_core_test.cpp" /Fo"%UNICORN_OUTPUT%\unicorn_reward_core_test.obj" /Fe"%UNICORN_OUTPUT%\unicorn_reward_core_test.exe"
if errorlevel 1 exit /b 1
"%UNICORN_OUTPUT%\unicorn_reward_core_test.exe"
exit /b %errorlevel%
