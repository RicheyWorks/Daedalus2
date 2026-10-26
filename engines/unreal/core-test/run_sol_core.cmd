@echo off
setlocal
if "%~1"=="" exit /b 2
set "SOL_TEST_OUTPUT=%~1"
if not exist "%SOL_TEST_OUTPUT%" mkdir "%SOL_TEST_OUTPUT%"
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /I"%~dp0..\DaedalusLink\Source\DaedalusLink\Public" "%~dp0sol_reach_core_test.cpp" /Fo"%SOL_TEST_OUTPUT%\sol_reach_core_test.obj" /Fe"%SOL_TEST_OUTPUT%\sol_reach_core_test.exe"
if errorlevel 1 exit /b 1
"%SOL_TEST_OUTPUT%\sol_reach_core_test.exe"
exit /b %errorlevel%
