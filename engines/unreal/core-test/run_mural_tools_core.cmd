@echo off
setlocal
if "%~1"=="" exit /b 2
set "MURAL_TOOLS_OUTPUT=%~f1"
if not exist "%MURAL_TOOLS_OUTPUT%" mkdir "%MURAL_TOOLS_OUTPUT%"
if errorlevel 1 exit /b 1
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /I"%~dp0..\DaedalusLink\Source\DaedalusLink\Public" "%~dp0mural_tool_core_test.cpp" /Fo"%MURAL_TOOLS_OUTPUT%\mural_tool_core_test.obj" /Fe"%MURAL_TOOLS_OUTPUT%\mural_tool_core_test.exe"
if errorlevel 1 exit /b 1
"%MURAL_TOOLS_OUTPUT%\mural_tool_core_test.exe"
exit /b %errorlevel%
