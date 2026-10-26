@echo off
setlocal
if "%~1"=="" exit /b 2
set "NPC_TEST_OUTPUT=%~1"
if not exist "%NPC_TEST_OUTPUT%" mkdir "%NPC_TEST_OUTPUT%"
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHs-c- /D_HAS_EXCEPTIONS=0 /D_CRT_SECURE_NO_WARNINGS /W4 /WX /I"%~dp0..\DaedalusLink\Source\DaedalusLink\Public" "%~dp0twin_doors_guide_test.cpp" /Fo"%NPC_TEST_OUTPUT%\twin_doors_guide_test.obj" /Fe"%NPC_TEST_OUTPUT%\twin_doors_guide_test.exe"
if errorlevel 1 exit /b 1
"%NPC_TEST_OUTPUT%\twin_doors_guide_test.exe"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHs-c- /D_HAS_EXCEPTIONS=0 /D_CRT_SECURE_NO_WARNINGS /W4 /WX /I"%~dp0..\DaedalusLink\Source\DaedalusLink\Public" "%~dp0twin_doors_plugin\twin_doors_plugin_test.cpp" /Fo"%NPC_TEST_OUTPUT%\twin_doors_plugin_test.obj" /Fe"%NPC_TEST_OUTPUT%\twin_doors_plugin_test.exe"
if errorlevel 1 exit /b 1
"%NPC_TEST_OUTPUT%\twin_doors_plugin_test.exe" "%~dp0..\..\..\docs\contracts\twin-doors-v1\riddles.twd"
exit /b %errorlevel%
