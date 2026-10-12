@echo off
setlocal
cd /d "%~dp0"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=4173"
set "PROJECT_FRONTEND=%~dp0frontend"
set "PROJECT_BACKEND=%~dp0backend"
if exist "backend\.env" for /f "usebackq tokens=1,* delims==" %%A in ("backend\.env") do if "%%A"=="API_PORT" set "BACKEND_PORT=%%B"
if exist "frontend\.env" for /f "usebackq tokens=1,* delims==" %%A in ("frontend\.env") do if "%%A"=="VITE_PORT" set "FRONTEND_PORT=%%B"

where node >nul 2>nul || (echo ERROR: Node.js is not installed or not on PATH.& exit /b 1)
where npm >nul 2>nul || (echo ERROR: npm is not installed or not on PATH.& exit /b 1)

powershell -NoProfile -Command "if($env:BACKEND_PORT -notmatch '^\d+$' -or [int]$env:BACKEND_PORT -lt 1 -or [int]$env:BACKEND_PORT -gt 65535){exit 2}; if (Get-NetTCPConnection -State Listen -LocalPort ([int]$env:BACKEND_PORT) -ErrorAction SilentlyContinue) { exit 1 }"
if errorlevel 2 (echo ERROR: API_PORT must be an integer between 1 and 65535.& exit /b 1)
if errorlevel 1 (echo ERROR: Backend port %BACKEND_PORT% is already in use. Stop the project server yourself or change the configured port.& exit /b 1)
set "FRONTEND_LISTENER="
for /f %%R in ('powershell -NoProfile -Command "if($env:FRONTEND_PORT -notmatch '^\d+$' -or [int]$env:FRONTEND_PORT -lt 1 -or [int]$env:FRONTEND_PORT -gt 65535){exit 2}; $port=[int]$env:FRONTEND_PORT; $c=Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue; if(-not $c){Write-Output FREE; exit 0}; $root=$env:PROJECT_FRONTEND; $p=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$c[0].OwningProcess); if($p.CommandLine -and $p.CommandLine.IndexOf($root,[StringComparison]::OrdinalIgnoreCase) -ge 0){try{$r=Invoke-WebRequest -Uri ('http://127.0.0.1:'+$port+'/') -TimeoutSec 2; if($r.StatusCode -eq 200){Write-Output PROJECT; exit 0}}catch{}}; exit 1"') do set "FRONTEND_LISTENER=%%R"
if errorlevel 2 (echo ERROR: VITE_PORT must be an integer between 1 and 65535.& exit /b 1)
if errorlevel 1 (echo ERROR: Frontend port %FRONTEND_PORT% is owned by another or unresponsive process. It was left untouched.& exit /b 1)

if exist ".venv\Scripts\python.exe" (
  set "PYTHON_CMD=..\.venv\Scripts\python.exe"
) else (
  where py >nul 2>nul || (echo ERROR: Python launcher not found. Create the project .venv or install Python 3.11+.& exit /b 1)
  set "PYTHON_CMD=py -3"
)
if not exist "frontend\node_modules\vite\bin\vite.js" (
  echo ERROR: Frontend dependencies are missing. Run: cd frontend ^&^& npm install
  exit /b 1
)

start "ABC Technologies Backend" /D "%PROJECT_BACKEND%" cmd /k "%PYTHON_CMD% -m uvicorn api:app --host 127.0.0.1 --port %BACKEND_PORT%"
if /i not "%FRONTEND_LISTENER%"=="PROJECT" start "ABC Technologies Frontend" /D "%PROJECT_FRONTEND%" cmd /k "npm run dev -- --host 127.0.0.1 --port %FRONTEND_PORT% --strictPort"
if /i "%FRONTEND_LISTENER%"=="PROJECT" echo Reusing the existing project Vite server on port %FRONTEND_PORT%.

echo Started service processes. Checking readiness; process launch alone is not treated as success.
powershell -NoProfile -Command "$port=[int]$env:BACKEND_PORT; $front=[int]$env:FRONTEND_PORT; $deadline=(Get-Date).AddSeconds(35); $b=$false; $f=$false; while((Get-Date) -lt $deadline){try{$r=Invoke-RestMethod -Uri ('http://127.0.0.1:'+$port+'/ready') -TimeoutSec 1; if($r.ready){$b=$true}}catch{}; try{$w=Invoke-WebRequest -Uri ('http://127.0.0.1:'+$front+'/') -TimeoutSec 1; if($w.StatusCode -eq 200){$f=$true}}catch{}; if($b -and $f){break}; Start-Sleep -Milliseconds 400}; if($b){Write-Host ('Backend database: ready at http://127.0.0.1:'+$port)}else{Write-Host 'Backend database: NOT READY; inspect the backend window and /ready'}; if($f){Write-Host ('Frontend: ready at http://127.0.0.1:'+$front)}else{Write-Host 'Frontend: NOT READY; inspect the frontend window'}; if(-not($b -and $f)){exit 1}"
if errorlevel 1 exit /b 1
endlocal
