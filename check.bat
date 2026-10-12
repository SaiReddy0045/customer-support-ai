@echo off
setlocal
cd /d "%~dp0"
set "FAILED=0"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=4173"
set "OLLAMA_MODEL=llama3.2:1b"
if exist "backend\.env" for /f "usebackq tokens=1,* delims==" %%A in ("backend\.env") do (
  if "%%A"=="API_PORT" set "BACKEND_PORT=%%B"
  if "%%A"=="OLLAMA_MODEL" if not "%%B"=="" set "OLLAMA_MODEL=%%B"
)
if exist "frontend\.env" for /f "usebackq tokens=1,* delims==" %%A in ("frontend\.env") do if "%%A"=="VITE_PORT" set "FRONTEND_PORT=%%B"

if exist ".venv\Scripts\python.exe" (
  set "PYTHON=.venv\Scripts\python.exe"
) else (
  where py >nul 2>nul
  if errorlevel 1 (echo FAIL: Python 3.11+ is unavailable.& set "FAILED=1") else (set "PYTHON=py -3")
)
where npm >nul 2>nul
if errorlevel 1 (echo FAIL: npm is unavailable.& set "FAILED=1")

if not exist "backend\.env" echo INFO: backend\.env is absent; safe development defaults are active. Copy backend\.env.example to backend\.env to configure settings.
if not exist "frontend\.env" echo INFO: frontend\.env is absent; frontend defaults to http://127.0.0.1:8000.

if exist ".venv\Scripts\python.exe" (
  pushd backend
  ..\.venv\Scripts\python.exe -c "from database.db import SessionLocal; from sqlalchemy import text; db=SessionLocal(); db.execute(text('SELECT 1')); db.close(); print('PASS: database connection')"
  if errorlevel 1 set "FAILED=1"
  ..\.venv\Scripts\python.exe -c "import api, agents.intent_classifier, graph.workflow; print('PASS: backend imports')"
  if errorlevel 1 set "FAILED=1"
  popd
) else (
  echo SKIP: Direct database/import checks require the project .venv.
)

 powershell -NoProfile -Command "try{$r=Invoke-RestMethod 'http://127.0.0.1:%BACKEND_PORT%/health' -TimeoutSec 3; Write-Host ('API health: '+$r.status)}catch{Write-Host 'API health: not running; start it with start.bat or the documented uvicorn command.'; exit 1}"
if errorlevel 1 set "FAILED=1"
powershell -NoProfile -Command "try{$r=Invoke-RestMethod 'http://127.0.0.1:%BACKEND_PORT%/ready' -TimeoutSec 4; Write-Host ('API readiness: '+$r.status+'; database='+$r.dependencies.database+'; ollama='+$r.dependencies.ollama); if(-not $r.ready){exit 1}}catch{Write-Host 'API readiness: not available (backend is not running or database is unavailable).'; exit 1}"
if errorlevel 1 set "FAILED=1"
powershell -NoProfile -Command "try{$r=Invoke-WebRequest 'http://127.0.0.1:%BACKEND_PORT%/products' -TimeoutSec 3; Write-Host ('Product API: HTTP '+$r.StatusCode)}catch{Write-Host 'Product API: not reachable until the backend is running.'}"
if errorlevel 1 set "FAILED=1"
powershell -NoProfile -Command "try{$r=Invoke-WebRequest 'http://127.0.0.1:%FRONTEND_PORT%/' -TimeoutSec 3; Write-Host ('Frontend HTTP: '+$r.StatusCode)}catch{Write-Host 'Frontend HTTP: not running; start it with start.bat.'; exit 1}"
if errorlevel 1 set "FAILED=1"

if exist "frontend\node_modules\vite\bin\vite.js" (
  pushd frontend
  call npm run build
  if errorlevel 1 set "FAILED=1"
  popd
) else (
  echo FAIL: Frontend dependencies missing. Run: cd frontend ^&^& npm install
  set "FAILED=1"
)

powershell -NoProfile -Command "try{$tags=Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2; $model='%OLLAMA_MODEL%'; if($tags.models.name -contains $model){Write-Host ('PASS: Ollama model '+$model)}else{Write-Host ('WARN: Ollama is running but model '+$model+' is not listed; install it with ollama pull '+$model)}}catch{Write-Host 'WARN: Ollama unavailable. API/database and product browsing still work; AI answers will degrade gracefully.'}"

if "%FAILED%"=="1" (echo One or more required local checks failed.& exit /b 1)
echo Local diagnostics completed.
endlocal
