@echo off
setlocal
rem Run from an MSVC developer shell. Output must be a new, caller-chosen directory.
if "%~1"=="" exit /b 2
if not "%~2"=="" exit /b 2
set "OCEAN_TEST_OUTPUT=%~f1"
if exist "%OCEAN_TEST_OUTPUT%" exit /b 3
mkdir "%OCEAN_TEST_OUTPUT%"
if errorlevel 1 exit /b 4
cl /nologo /std:c++17 /EHsc /W4 /WX "%~dp0ocean_travel_core_test.cpp" /Fo"%OCEAN_TEST_OUTPUT%\ocean_travel_core_test.obj" /Fe"%OCEAN_TEST_OUTPUT%\ocean_travel_core_test.exe"
set "OCEAN_COMPILE_EXIT=%errorlevel%"
if not "%OCEAN_COMPILE_EXIT%"=="0" exit /b %OCEAN_COMPILE_EXIT%
"%OCEAN_TEST_OUTPUT%\ocean_travel_core_test.exe"
exit /b %errorlevel%
