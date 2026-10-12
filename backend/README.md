# ABC Technologies Support API

The backend is a FastAPI application backed by one SQLite database at
`backend/ecommerce.db`. Database initialization is automatic at startup.

## Start the backend

```powershell
cd backend
python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

Start only one Uvicorn process on port `8000`.

## Start the frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

The frontend uses `http://localhost:8000` unless `VITE_API_URL` is set.

## Runtime design

Order, billing, refund, and tracking requests use authenticated customer-scoped
database operations first. The local LLM is reserved for general explanations
and non-deterministic support questions, keeping routine operations responsive
on low-memory hardware.
