@echo off
setlocal
if "%~1"=="" exit /b 2
set "PHOTO_PDF_TEST_OUTPUT=%~1"
if not exist "%PHOTO_PDF_TEST_OUTPUT%" mkdir "%PHOTO_PDF_TEST_OUTPUT%"
if errorlevel 1 exit /b 1
set "PHOTO_PDF_VCVARS="
if defined VSINSTALLDIR if exist "%VSINSTALLDIR%VC\Auxiliary\Build\vcvars64.bat" set "PHOTO_PDF_VCVARS=%VSINSTALLDIR%VC\Auxiliary\Build\vcvars64.bat"
if not defined PHOTO_PDF_VCVARS if exist "%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" (
  for /f "usebackq delims=" %%V in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "PHOTO_PDF_VCVARS=%%V\VC\Auxiliary\Build\vcvars64.bat"
)
if not defined PHOTO_PDF_VCVARS exit /b 2
if not exist "%PHOTO_PDF_VCVARS%" exit /b 2
call "%PHOTO_PDF_VCVARS%" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /W4 /WX /I"%~dp0..\DaedalusLink\Source\DaedalusLink\Public" "%~dp0photo_pdf_core_test.cpp" /Fo"%PHOTO_PDF_TEST_OUTPUT%\photo_pdf_core_test.obj" /Fe"%PHOTO_PDF_TEST_OUTPUT%\photo_pdf_core_test.exe"
if errorlevel 1 exit /b 1
"%PHOTO_PDF_TEST_OUTPUT%\photo_pdf_core_test.exe"
exit /b %errorlevel%
