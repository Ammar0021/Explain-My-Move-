@echo off
REM ═══════════════════════════════════════════════════════════════════════════
REM  build_exe.bat  —  Explain My Move  v1.3.1
REM  Author: Ammar
REM  OCR A-Level Computer Science NEA — Component 03/04
REM
REM  Produces a single portable .exe in the dist\ folder.
REM  Stockfish is bundled inside — no extra files needed on the target machine.
REM
REM  ─────────────────────────────────────────────────────────────────────────
REM  REQUIREMENTS (run once before building):
REM
REM    pip install pyinstaller python-chess
REM
REM  PROJECT STRUCTURE EXPECTED (v1.3.1 — 9 source files):
REM
REM    explain_my_move.py       <- GUI entry point
REM    engine_interface.py      <- ChessEngineInterface, MoveEvaluator,
REM                                BadMoveAnalyser, format_score
REM    engine_config.py         <- ConfigManager, get_stockfish_path
REM    explanation_engine.py    <- Rule, ExplanationEngine (18 rules, v1.4)
REM    output_formatter.py      <- OutputFormatter
REM    game_statistics.py       <- StatisticsCalculator (Design Class 8)
REM    pgn_annotator.py         <- PGNAnnotator
REM    test_suite.py            <- Formal test runner (T01–T42)
REM    stockfish\
REM        stockfish-windows-x86-64-avx2.exe   <- Stockfish binary
REM    build_exe.bat            <- this file
REM
REM  OUTPUT:
REM    dist\ExplainMyMove.exe   <- single portable executable
REM
REM  ─────────────────────────────────────────────────────────────────────────
REM  OPTIONAL: To add a custom window icon, place a .ico file in this folder
REM  and uncomment the --icon line near the bottom of this script.
REM ═══════════════════════════════════════════════════════════════════════════

SETLOCAL

REM ── Configuration ──────────────────────────────────────────────────────────

SET STOCKFISH_RELATIVE=stockfish\stockfish-windows-x86-64-avx2.exe

SET APP_NAME=ExplainMyMove

SET ENTRY=explain_my_move.py

REM ── Header ─────────────────────────────────────────────────────────────────

echo.
echo ===============================================================
echo    Explain My Move  v1.3.1  --  Build Script
echo    Author: Ammar  ^|  OCR A-Level NEA
echo ===============================================================
echo.

REM ── Pre-flight checks ───────────────────────────────────────────────────────

python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Python not found on PATH.
    echo         Install Python 3 from https://python.org and try again.
    echo.
    pause
    exit /b 1
)

python -c "import PyInstaller" >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] PyInstaller is not installed.
    echo         Run:  pip install pyinstaller
    echo.
    pause
    exit /b 1
)

python -c "import chess" >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] python-chess is not installed.
    echo         Run:  pip install python-chess
    echo.
    pause
    exit /b 1
)

REM ── Check all required .py source files (v1.3.1 adds 2 new modules) ────────

FOR %%F IN (
    explain_my_move.py
    engine_interface.py
    engine_config.py
    explanation_engine.py
    output_formatter.py
    game_statistics.py
    pgn_annotator.py
) DO (
    IF NOT EXIST "%%F" (
        echo [ERROR] Required source file not found: %%F
        echo         Make sure all .py files are in the same folder as this script.
        echo.
        pause
        exit /b 1
    )
)

REM test_suite.py is NOT included in the .exe — it is a development-only tool.
REM Running test_suite.py requires Stockfish on the local machine for T40-T42.

IF NOT EXIST "%STOCKFISH_RELATIVE%" (
    echo [ERROR] Stockfish not found at: %STOCKFISH_RELATIVE%
    echo.
    echo         Download Stockfish from https://stockfishchess.org/download/
    echo         and place the .exe at:  %STOCKFISH_RELATIVE%
    echo         Or edit STOCKFISH_RELATIVE at the top of this file.
    echo.
    pause
    exit /b 1
)

echo [OK] Python found
echo [OK] PyInstaller found
echo [OK] python-chess found
echo [OK] All 7 source files present  (test_suite.py excluded from exe)
echo [OK] Stockfish found at: %STOCKFISH_RELATIVE%
echo.

REM ── Clean previous build output ─────────────────────────────────────────────

IF EXIST "dist\%APP_NAME%.exe" (
    echo Removing previous dist\%APP_NAME%.exe ...
    del /f /q "dist\%APP_NAME%.exe"
)
IF EXIST "build" (
    echo Removing previous build\ folder ...
    rmdir /s /q build
)
IF EXIST "%APP_NAME%.spec" (
    echo Removing previous %APP_NAME%.spec ...
    del /f /q "%APP_NAME%.spec"
)

echo.
echo -- Starting PyInstaller -------------------------------------------
echo.

REM ── PyInstaller command ─────────────────────────────────────────────────────
REM
REM  --onefile
REM      Packs everything into a single .exe.
REM
REM  --windowed
REM      Hides the console window behind the Tkinter GUI.
REM      Remove this flag for debug output during testing.
REM
REM  --add-data "source;dest"
REM      Bundles Stockfish into the exe.
REM      At runtime, get_stockfish_path() reads from sys._MEIPASS\stockfish\.
REM
REM  --hidden-import / --collect-submodules
REM      Forces inclusion of chess sub-modules PyInstaller might miss.
REM
REM  v1.3.1 additions:
REM      game_statistics and pgn_annotator are pure Python — no extra
REM      hidden imports needed. PyInstaller detects them via the import
REM      statements in explain_my_move.py automatically.
REM
REM  OPTIONAL ICON -- uncomment if you have a .ico file:
REM      --icon "chess.ico" ^

pyinstaller ^
    --onefile ^
    --windowed ^
    --add-data "%STOCKFISH_RELATIVE%;stockfish" ^
    --hidden-import chess ^
    --hidden-import chess.engine ^
    --hidden-import chess.pgn ^
    --hidden-import chess.svg ^
    --hidden-import game_statistics ^
    --hidden-import pgn_annotator ^
    --collect-submodules chess ^
    --name "%APP_NAME%" ^
    %ENTRY%

REM ── Result ──────────────────────────────────────────────────────────────────

echo.
IF EXIST "dist\%APP_NAME%.exe" (
    echo ===============================================================
    echo    BUILD SUCCESSFUL
    echo    Output:  dist\%APP_NAME%.exe
    echo ===============================================================
    echo.
    echo    The executable is fully self-contained.
    echo    Copy dist\%APP_NAME%.exe to any Windows machine and run it.
    echo    No Python, no Stockfish, no extra files needed.
    echo.
    echo    NOTE: test_suite.py was NOT bundled — run it separately
    echo    from your dev environment:  python test_suite.py
    echo.
) ELSE (
    echo ===============================================================
    echo    BUILD FAILED  --  check the output above for errors
    echo ===============================================================
    echo.
    echo    Common causes and fixes:
    echo.
    echo    1. PyInstaller not installed
    echo           pip install pyinstaller
    echo.
    echo    2. python-chess not installed
    echo           pip install python-chess
    echo.
    echo    3. Antivirus blocking the build
    echo           Temporarily disable real-time protection and retry.
    echo.
    echo    4. Wrong Stockfish path
    echo           Edit the STOCKFISH_RELATIVE variable at the top of this file.
    echo.
    echo    5. Missing source file
    echo           All 7 .py files must be in the same folder as this script.
    echo           (explain_my_move, engine_interface, engine_config,
    echo            explanation_engine, output_formatter,
    echo            game_statistics, pgn_annotator)
    echo.
)

ENDLOCAL
pause
