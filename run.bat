@echo off
REM ============================================================
REM  Modal analysis pipeline launcher
REM  Double-click this file, or run it from a cmd prompt.
REM ============================================================
setlocal
cd /d "%~dp0"

REM Use the py launcher's default (3.12, has mido); fall back to python on PATH.
where py >nul 2>&1 && (set "PY=py") || (set "PY=python")

:menu
echo.
echo  ===== countConfigs / modal analysis =====
echo   -- 57-mode detail + graphs (whole corpus) --
echo   1. Corpus report           -^> modes_corpus.csv + graphs\corpus_*.png
echo   2. Corpus report, normalized (compare shape, not level)
echo   3. Corpus report, duration-weighted
echo   9. Corpus report, PER BAR (fixed-unit, fairer proportions)
echo   4. Report custom composers...
echo.
echo   -- single-track inspector (piano-roll + detected modes) --
echo   7. Inspect a track...
echo.
echo   -- per-file family-summary metrics --
echo   5. Full corpus             -^> metrics.csv
echo   6. Custom composers (summary)...
echo.
echo   8. Install/upgrade dependencies
echo   0. Quit
echo.
set /p choice="  Choose: "

if "%choice%"=="1" ( %PY% report.py & goto done )
if "%choice%"=="2" ( %PY% report.py --normalize & goto done )
if "%choice%"=="3" ( %PY% report.py --weighted & goto done )
if "%choice%"=="9" ( %PY% report.py --unit bar & goto done )
if "%choice%"=="4" goto customreport
if "%choice%"=="7" goto inspect
if "%choice%"=="5" ( %PY% analyze.py --out metrics.csv & goto done )
if "%choice%"=="6" goto custom
if "%choice%"=="8" ( %PY% -m pip install -r requirements.txt & goto done )
if "%choice%"=="0" goto :eof
echo  Invalid choice.
goto menu

:custom
set /p comps="  Composer folder names (space-separated): "
%PY% analyze.py --composers %comps% --out metrics.csv
goto done

:customreport
set /p comps="  Composer folder names (space-separated): "
%PY% report.py --composers %comps%
goto done

:inspect
set /p trackfile="  MIDI file path (e.g. data\Clementi\sonatina op36 n1 1mov.mid): "
set /p barrange="  Bar range as 'START END' (blank = first 32): "
set /p indep="  Independent per-bar detection (no sticky)? y/N: "
set "opts="
if not "%barrange%"=="" set "opts=%opts% --bars %barrange%"
if /i "%indep%"=="y" set "opts=%opts% --independent"
%PY% inspect_track.py --file "%trackfile%"%opts%
goto done

:done
echo.
echo  Done.
pause
goto menu
