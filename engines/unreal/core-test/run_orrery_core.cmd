@echo off
setlocal
if "%~1"=="" exit /b 2
set "ORR_TEST_OUTPUT=%~1"
if not exist "%ORR_TEST_OUTPUT%" mkdir "%ORR_TEST_OUTPUT%"
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /I"%~dp0..\DaedalusLink\Source\DaedalusLink\Public" "%~dp0orrery_core_test.cpp" /Fo"%ORR_TEST_OUTPUT%\orrery_core_test.obj" /Fe"%ORR_TEST_OUTPUT%\orrery_core_test.exe"
if errorlevel 1 exit /b 1
"%ORR_TEST_OUTPUT%\orrery_core_test.exe"
exit /b %errorlevel%
