@echo off
setlocal
REM ============================================================
REM  CampusLearn AI - starts database, backend and frontend
REM  Usage: double-click start_project.bat
REM ============================================================

set "ROOT=%~dp0"
set "PG_BIN=C:\Program Files\PostgreSQL\18\bin"
set "PGDATA=C:\Users\ragha\AppData\Local\Temp\opencode\pgdata"
set "PGLOG=%TEMP%\campuslearn_postgres.log"
set "PYTHONPATH=%ROOT%;%ROOT%backend"

REM ---------- 1. Database (PostgreSQL 18 on port 55432) ----------
if not exist "%PGDATA%\PG_VERSION" (
  echo [db] creating data directory...
  "%PG_BIN%\initdb.exe" -D "%PGDATA%" -U postgres -A trust > "%PGLOG%" 2>&1
)

"%PG_BIN%\pg_ctl.exe" -D "%PGDATA%" status >nul 2>&1
if errorlevel 1 (
  echo [db] starting PostgreSQL on 127.0.0.1:55432 ...
  "%PG_BIN%\pg_ctl.exe" -D "%PGDATA%" -l "%PGLOG%" -o "-p 55432 -h 127.0.0.1" start
) else (
  echo [db] PostgreSQL already running
)

echo [db] creating database if needed...
"%PG_BIN%\psql.exe" -h 127.0.0.1 -p 55432 -U postgres -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='ai_study_analyzer'" | findstr /i "1" >nul
if errorlevel 1 (
  "%PG_BIN%\psql.exe" -h 127.0.0.1 -p 55432 -U postgres -d postgres -c "CREATE DATABASE ai_study_analyzer"
)

echo [db] applying migrations...
cd /d "%ROOT%backend"
python -m alembic upgrade head

REM ---------- 2. Ollama (optional - the AI chat needs it) ----------
netstat -an | findstr ":11434" | findstr "LISTENING" >nul
if errorlevel 1 (
  where ollama >nul 2>&1
  if not errorlevel 1 (
    echo [llm] starting Ollama on port 11434 ...
    start "CampusLearn Ollama" /min cmd /c "ollama serve"
  )
)

REM ---------- 3. Backend (FastAPI on port 8000) ----------
echo [api] starting FastAPI on http://127.0.0.1:8000 ...
start "CampusLearn API" /min /D "%ROOT%backend" cmd /c "python -m uvicorn main:app --host 127.0.0.1 --port 8000"

REM ---------- 4. Frontend (Vite on port 5173) ----------
echo [web] starting Vite on http://127.0.0.1:5173 ...
start "CampusLearn Web" /min /D "%ROOT%frontend" cmd /c "npm run dev"

echo.
echo ------------------------------------------------------------
echo   Database : 127.0.0.1:55432   (ai_study_analyzer)
echo   Backend  : http://127.0.0.1:8000/health
echo   Frontend : http://localhost:5173
echo   Local-only demo: no public tunnel is created.
echo ------------------------------------------------------------
echo   The servers keep running after this window closes.
echo.

REM Give Vite a moment to bind, then open the login page in the
REM default browser (local-only - nothing is exposed publicly).
ping -n 6 127.0.0.1 >nul
netstat -an | findstr ":5173" | findstr "LISTENING" >nul
if errorlevel 1 (
  echo [web] Vite did not start on port 5173 - check the output above.
  pause
) else (
  start http://localhost:5173
)
