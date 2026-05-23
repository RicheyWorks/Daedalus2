@echo off
REM ============================================================
REM  Daedalus 5-module migration script
REM
REM  RUN AFTER:
REM    Phase 1 - IntelliJ F6 refactors (3 moves, NOT 5):
REM      DaedalusApp.java         -> com.daedalus.server
REM      DaedalusLauncher.java    -> com.daedalus.desktop
REM      DaedalusPrimaryStage.java -> com.daedalus.desktop
REM
REM    PluginManager and PluginRegistry are NO LONGER on the F6
REM    list. They get deleted-and-replaced when Pass 1 / Pass 2
REM    land in Phase 4.
REM
REM    'mvn clean compile' must be GREEN with 74 source files
REM    before this script runs.
REM
REM  WHAT THIS SCRIPT DOES:
REM    1. Creates the 5-module Maven layout under module roots
REM    2. Moves source files into their target modules
REM    3. Cleans up the empty old src/ tree
REM
REM  WHAT THIS SCRIPT DOES NOT DO:
REM    - Copy poms (Phase 3 does that)
REM    - Copy server resources (Phase 3 does that)
REM    - Touch _migration/ (left intact for Phase 3)
REM    - Touch target/ (run 'mvn clean' first to be safe)
REM
REM  PAUSE ONEDRIVE BEFORE RUNNING.
REM ============================================================

setlocal enabledelayedexpansion

set ROOT=%cd%
set OLD_SRC=%ROOT%\src\main\java\com\daedalus

if not exist "%OLD_SRC%" (
    echo ERROR: %OLD_SRC% not found. Run from the project root [Daedalus2].
    exit /b 1
)

if not exist "%ROOT%\_migration\pom.xml" (
    echo ERROR: _migration\pom.xml not found. Refusing to run without staged poms.
    exit /b 1
)

echo.
echo === Daedalus 5-module migration ===
echo Project root: %ROOT%
echo.

REM ------------------------------------------------------------
REM 1. Create module directory layout
REM ------------------------------------------------------------
echo [1/7] Creating module directories...

mkdir "daedalus-plugin-api\src\main\java\com\daedalus\plugin"        2>nul
mkdir "daedalus-plugin-api\src\main\java\com\daedalus\plugin\events" 2>nul
mkdir "daedalus-plugin-api\src\test\java\com\daedalus\plugin"        2>nul

mkdir "daedalus-core\src\main\java\com\daedalus\engine"             2>nul
mkdir "daedalus-core\src\main\java\com\daedalus\engine\generators"  2>nul
mkdir "daedalus-core\src\main\java\com\daedalus\solver"             2>nul
mkdir "daedalus-core\src\main\java\com\daedalus\solver\solvers"     2>nul
mkdir "daedalus-core\src\main\java\com\daedalus\model"              2>nul
mkdir "daedalus-core\src\test\java\com\daedalus\engine"             2>nul

mkdir "daedalus-plugin-runtime\src\main\java\com\daedalus\plugin\runtime" 2>nul
mkdir "daedalus-plugin-runtime\src\test\java\com\daedalus\plugin\runtime" 2>nul

mkdir "daedalus-server\src\main\java\com\daedalus\server"            2>nul
mkdir "daedalus-server\src\main\java\com\daedalus\server\config"     2>nul
mkdir "daedalus-server\src\main\java\com\daedalus\server\controller" 2>nul
mkdir "daedalus-server\src\main\java\com\daedalus\server\service"    2>nul
mkdir "daedalus-server\src\main\resources"                            2>nul
mkdir "daedalus-server\src\test\java\com\daedalus\server"            2>nul

mkdir "daedalus-desktop\src\main\java\com\daedalus\desktop"          2>nul
mkdir "daedalus-desktop\src\main\java\com\daedalus\desktop\ui"       2>nul
mkdir "daedalus-desktop\src\main\java\com\daedalus\desktop\ui\themes" 2>nul
mkdir "daedalus-desktop\src\test\java\com\daedalus\desktop"          2>nul

REM ------------------------------------------------------------
REM 2. daedalus-core: engine, solver, model
REM ------------------------------------------------------------
echo [2/7] Moving daedalus-core sources [engine, solver, model]...
move "%OLD_SRC%\engine\generators\*.java" "daedalus-core\src\main\java\com\daedalus\engine\generators\" >nul
move "%OLD_SRC%\engine\*.java"            "daedalus-core\src\main\java\com\daedalus\engine\" >nul
move "%OLD_SRC%\solver\solvers\*.java"    "daedalus-core\src\main\java\com\daedalus\solver\solvers\" >nul
move "%OLD_SRC%\solver\*.java"            "daedalus-core\src\main\java\com\daedalus\solver\" >nul
move "%OLD_SRC%\model\*.java"             "daedalus-core\src\main\java\com\daedalus\model\" >nul

REM ------------------------------------------------------------
REM 3. daedalus-plugin-api: SPI files [Pass 1 will replace these]
REM    AbstractPlugin, MazePlugin, PluginContext, PluginLifecycle,
REM    PluginManifest, and events/*.
REM ------------------------------------------------------------
echo [3/7] Moving daedalus-plugin-api sources [SPI surface]...
if exist "%OLD_SRC%\plugin\AbstractPlugin.java"  move "%OLD_SRC%\plugin\AbstractPlugin.java"  "daedalus-plugin-api\src\main\java\com\daedalus\plugin\" >nul
if exist "%OLD_SRC%\plugin\MazePlugin.java"      move "%OLD_SRC%\plugin\MazePlugin.java"      "daedalus-plugin-api\src\main\java\com\daedalus\plugin\" >nul
if exist "%OLD_SRC%\plugin\PluginContext.java"   move "%OLD_SRC%\plugin\PluginContext.java"   "daedalus-plugin-api\src\main\java\com\daedalus\plugin\" >nul
if exist "%OLD_SRC%\plugin\PluginLifecycle.java" move "%OLD_SRC%\plugin\PluginLifecycle.java" "daedalus-plugin-api\src\main\java\com\daedalus\plugin\" >nul
if exist "%OLD_SRC%\plugin\PluginManifest.java"  move "%OLD_SRC%\plugin\PluginManifest.java"  "daedalus-plugin-api\src\main\java\com\daedalus\plugin\" >nul
if exist "%OLD_SRC%\plugin\events"               move "%OLD_SRC%\plugin\events\*.java" "daedalus-plugin-api\src\main\java\com\daedalus\plugin\events\" >nul

REM ------------------------------------------------------------
REM 4. daedalus-plugin-runtime: PluginManager + PluginRegistry
REM    [Pass 2 will replace these wholesale; we move them here so
REM    the project compiles in the interim. Package will need to
REM    change from com.daedalus.plugin to com.daedalus.plugin.runtime
REM    when Pass 2 lands - Pass 2 does that for you.]
REM ------------------------------------------------------------
echo [4/7] Moving daedalus-plugin-runtime sources [manager, registry]...
if exist "%OLD_SRC%\plugin\PluginManager.java"  move "%OLD_SRC%\plugin\PluginManager.java"  "daedalus-plugin-runtime\src\main\java\com\daedalus\plugin\runtime\" >nul
if exist "%OLD_SRC%\plugin\PluginRegistry.java" move "%OLD_SRC%\plugin\PluginRegistry.java" "daedalus-plugin-runtime\src\main\java\com\daedalus\plugin\runtime\" >nul

REM ------------------------------------------------------------
REM 5. daedalus-server: app, config, controllers, services
REM    [DaedalusApp.java was moved by F6 to com.daedalus.server,
REM    so it lives at OLD_SRC\server\DaedalusApp.java now.]
REM ------------------------------------------------------------
echo [5/7] Moving daedalus-server sources...
if exist "%OLD_SRC%\server"           move "%OLD_SRC%\server\*.java"     "daedalus-server\src\main\java\com\daedalus\server\" >nul
if exist "%OLD_SRC%\DaedalusApp.java" move "%OLD_SRC%\DaedalusApp.java"  "daedalus-server\src\main\java\com\daedalus\server\" >nul
move "%OLD_SRC%\config\*.java"     "daedalus-server\src\main\java\com\daedalus\server\config\" >nul
move "%OLD_SRC%\controller\*.java" "daedalus-server\src\main\java\com\daedalus\server\controller\" >nul
move "%OLD_SRC%\service\*.java"    "daedalus-server\src\main\java\com\daedalus\server\service\" >nul

REM ------------------------------------------------------------
REM 6. daedalus-desktop: launcher, primary stage, ui
REM ------------------------------------------------------------
echo [6/7] Moving daedalus-desktop sources...
if exist "%OLD_SRC%\desktop"                    move "%OLD_SRC%\desktop\*.java"             "daedalus-desktop\src\main\java\com\daedalus\desktop\" >nul
if exist "%OLD_SRC%\DaedalusLauncher.java"      move "%OLD_SRC%\DaedalusLauncher.java"      "daedalus-desktop\src\main\java\com\daedalus\desktop\" >nul
if exist "%OLD_SRC%\DaedalusPrimaryStage.java"  move "%OLD_SRC%\DaedalusPrimaryStage.java"  "daedalus-desktop\src\main\java\com\daedalus\desktop\" >nul
move "%OLD_SRC%\ui\themes\*.java" "daedalus-desktop\src\main\java\com\daedalus\desktop\ui\themes\" >nul
move "%OLD_SRC%\ui\*.java"        "daedalus-desktop\src\main\java\com\daedalus\desktop\ui\" >nul

REM ------------------------------------------------------------
REM 7. Clean up empty directories from old layout
REM ------------------------------------------------------------
echo [7/7] Cleaning up old directory tree...
rmdir "%OLD_SRC%\engine\generators" 2>nul
rmdir "%OLD_SRC%\engine"            2>nul
rmdir "%OLD_SRC%\solver\solvers"    2>nul
rmdir "%OLD_SRC%\solver"            2>nul
rmdir "%OLD_SRC%\model"             2>nul
rmdir "%OLD_SRC%\plugin\events"     2>nul
rmdir "%OLD_SRC%\plugin"            2>nul
rmdir "%OLD_SRC%\config"            2>nul
rmdir "%OLD_SRC%\controller"        2>nul
rmdir "%OLD_SRC%\service"           2>nul
rmdir "%OLD_SRC%\server"            2>nul
rmdir "%OLD_SRC%\desktop"           2>nul
rmdir "%OLD_SRC%\ui\themes"         2>nul
rmdir "%OLD_SRC%\ui"                2>nul
rmdir "%OLD_SRC%"                   2>nul
rmdir "%ROOT%\src\main\java\com"    2>nul
rmdir "%ROOT%\src\main\java"        2>nul
rmdir "%ROOT%\src\main\resources"   2>nul
rmdir "%ROOT%\src\main"             2>nul
rmdir "%ROOT%\src\test\java\com\daedalus" 2>nul
rmdir "%ROOT%\src\test\java\com"    2>nul
rmdir "%ROOT%\src\test\java"        2>nul
rmdir "%ROOT%\src\test"             2>nul
rmdir "%ROOT%\src"                  2>nul

echo.
echo === Migration complete ===
echo.
echo PHASE 3 - copy staged poms and resources:
echo   copy /Y _migration\pom.xml                                    pom.xml
echo   copy /Y _migration\daedalus-plugin-api\pom.xml                daedalus-plugin-api\pom.xml
echo   copy /Y _migration\daedalus-core\pom.xml                      daedalus-core\pom.xml
echo   copy /Y _migration\daedalus-plugin-runtime\pom.xml            daedalus-plugin-runtime\pom.xml
echo   copy /Y _migration\daedalus-server\pom.xml                    daedalus-server\pom.xml
echo   copy /Y _migration\daedalus-desktop\pom.xml                   daedalus-desktop\pom.xml
echo   xcopy /Y /E _migration\daedalus-server\src\main\resources\*   daedalus-server\src\main\resources\
echo.
echo Then sanity check:  mvn -N validate
echo.

endlocal
