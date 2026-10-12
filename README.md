# ABC Technologies

An existing full-stack demonstration store and customer-support assistant using FastAPI, SQLAlchemy/SQLite, LangGraph/LangChain, optional local Ollama, React, and Vite.

## Requirements

- Windows 10/11, Python 3.11+, Node.js 18+, npm
- Ollama is optional for startup and database-backed features. The configured model defaults to `llama3.2:1b`.

## Quick Start (Windows)

1. Install backend dependencies in the existing project environment and frontend packages once:

```powershell
cd C:\Users\user\Desktop\project
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend
npm install
cd ..
```

2. Copy `backend\.env.example` to `backend\.env`; replace `ABC_AUTH_SECRET` with a long random local secret. Copy `frontend\.env.example` to `frontend\.env` if the API URL differs from the default.
3. Run `start.bat`. It refuses to launch when ports 8000 or 4173 are already occupied, opens backend/frontend in separate windows, and polls readiness instead of assuming process launch means the services are ready.
4. Open http://127.0.0.1:4173. The API defaults to http://127.0.0.1:8000, `/health` is liveness, and `/ready` reports database and optional Ollama/model readiness.

Manual startup is also available:

```powershell
cd C:\Users\user\Desktop\project\backend
..\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8000
```

```powershell
cd C:\Users\user\Desktop\project\frontend
npm run dev
```

Run `check.bat` for dependency/import/database checks, live health/readiness when the API is running, frontend production build, and optional Ollama/model diagnostics. It does not reset the database.

## Configuration

Backend settings are in `backend\.env.example`: `DATABASE_URL`, `ABC_AUTH_SECRET`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SECONDS`, CORS origins, 24-hour cancellation window, 12-hour refund-request window, and demo tracking thresholds. Frontend settings are in `frontend\.env.example`: `VITE_API_BASE_URL` and optionally `VITE_PORT` (default 4173).

Refund eligibility uses this application's configured 12-hour demonstration request window; it is not a universal e-commerce policy. Demo payment receipts and refund requests are simulated records and do not contact a bank or return funds.

## Recovery

- **Port occupied:** `start.bat` stops without killing processes. Inspect the listener yourself, stop only the process you recognize, or adjust the corresponding port and Vite/API URL settings.
- **Python packages missing:** activate/create the project `.venv`, then install `backend\requirements.txt`.
- **Frontend packages missing:** run `npm install` under `frontend`.
- **Database problem:** inspect the backend startup error and `backend\ecommerce.db` permissions/locks. Initialization preserves the existing file and fails with an explicit schema message instead of deleting data. Back up the SQLite file before manual repairs.
- **Ollama unavailable/model missing:** start Ollama and run `ollama pull llama3.2:1b`, or set `OLLAMA_MODEL` to an installed model. `/ready` reports degraded AI readiness while database/product operations remain available.

## Security and Demo Limitations

Login issues a signed seven-day bearer token; protected customer routes also require the matching `X-Customer-Id`. The local fallback signing secret is for development only; production must set a strong `ABC_AUTH_SECRET`. Product browsing is public; customer records/actions are scoped. Support escalation creates an internal demo ticket and does not contact a live human. No real payment processor or refund reversal is integrated.
