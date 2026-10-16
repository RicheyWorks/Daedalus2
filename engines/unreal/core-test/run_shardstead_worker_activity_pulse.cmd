@echo off
setlocal
rem Caller supplies an MSVC developer shell and a fresh output directory.
if "%~1"=="" exit /b 2
if not "%~2"=="" exit /b 2
set "WORKER_PULSE_OUTPUT=%~f1"
if exist "%WORKER_PULSE_OUTPUT%" exit /b 3
mkdir "%WORKER_PULSE_OUTPUT%"
if errorlevel 1 exit /b 4
cl /nologo /std:c++17 /EHsc /W4 /WX "%~dp0shardstead_worker_activity_pulse_test.cpp" /Fo"%WORKER_PULSE_OUTPUT%\shardstead_worker_activity_pulse_test.obj" /Fe"%WORKER_PULSE_OUTPUT%\shardstead_worker_activity_pulse_test.exe"
set "WORKER_PULSE_COMPILE_EXIT=%errorlevel%"
if not "%WORKER_PULSE_COMPILE_EXIT%"=="0" exit /b %WORKER_PULSE_COMPILE_EXIT%
"%WORKER_PULSE_OUTPUT%\shardstead_worker_activity_pulse_test.exe"
exit /b %errorlevel%
