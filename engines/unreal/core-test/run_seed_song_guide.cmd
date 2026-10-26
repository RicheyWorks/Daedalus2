@echo off
setlocal
if "%~1"=="" exit /b 2
set "SEED_SONG_TEST_OUTPUT=%~1"
if not exist "%SEED_SONG_TEST_OUTPUT%" mkdir "%SEED_SONG_TEST_OUTPUT%"
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHs-c- /D_HAS_EXCEPTIONS=0 /D_CRT_SECURE_NO_WARNINGS /W4 /WX /I"%~dp0..\DaedalusLink\Source\DaedalusLink\Public" "%~dp0seed_song_guide_test.cpp" /Fo"%SEED_SONG_TEST_OUTPUT%\seed_song_guide_test.obj" /Fe"%SEED_SONG_TEST_OUTPUT%\seed_song_guide_test.exe"
if errorlevel 1 exit /b 1
"%SEED_SONG_TEST_OUTPUT%\seed_song_guide_test.exe"
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHs-c- /D_HAS_EXCEPTIONS=0 /D_CRT_SECURE_NO_WARNINGS /W4 /WX /I"%~dp0..\DaedalusLink\Source\DaedalusLink\Public" "%~dp0seed_song_core_test.cpp" /Fo"%SEED_SONG_TEST_OUTPUT%\seed_song_core_test.obj" /Fe"%SEED_SONG_TEST_OUTPUT%\seed_song_core_test.exe"
if errorlevel 1 exit /b 1
pushd "%~dp0"
"%SEED_SONG_TEST_OUTPUT%\seed_song_core_test.exe"
set "SEED_SONG_TEST_RESULT=%errorlevel%"
popd
exit /b %SEED_SONG_TEST_RESULT%
