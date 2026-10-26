@echo off
setlocal
if "%~1"=="" exit /b 2
set "LOCAL_APP_TEST_OUTPUT=%~1"
call "%~dp0run_photo_pdf_core.cmd" "%LOCAL_APP_TEST_OUTPUT%"
if errorlevel 1 exit /b 1
set "LOCAL_APP_VCVARS="
if defined VSINSTALLDIR if exist "%VSINSTALLDIR%VC\Auxiliary\Build\vcvars64.bat" set "LOCAL_APP_VCVARS=%VSINSTALLDIR%VC\Auxiliary\Build\vcvars64.bat"
if not defined LOCAL_APP_VCVARS if exist "%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" (
  for /f "usebackq delims=" %%V in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "LOCAL_APP_VCVARS=%%V\VC\Auxiliary\Build\vcvars64.bat"
)
if not defined LOCAL_APP_VCVARS exit /b 2
if not exist "%LOCAL_APP_VCVARS%" exit /b 2
call "%LOCAL_APP_VCVARS%" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /I"%~dp0..\DaedalusLink\Source\DaedalusLink\Public" "%~dp0local_app_core_test.cpp" /Fo"%LOCAL_APP_TEST_OUTPUT%\local_app_core_test.obj" /Fe"%LOCAL_APP_TEST_OUTPUT%\local_app_core_test.exe"
if errorlevel 1 exit /b 1
"%LOCAL_APP_TEST_OUTPUT%\local_app_core_test.exe"
exit /b %errorlevel%
