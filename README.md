# BikeService Pro

A full-stack Bike Service Management Dashboard for tracking customer bikes, service history, and business analytics.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Tailwind CSS, Recharts, Vite |
| Backend | FastAPI (Python), async SQLAlchemy |
| Database | PostgreSQL (Neon / Supabase) |
| Deployment | Vercel (frontend), Render (backend) |

## Features

- **Dashboard** — Total services, monthly services, total customers, revenue stats, monthly bar chart
- **Add Service** — Form to log service entries with smart bike linking (auto-creates or links existing bike)
- **Search** — Lookup full service history by bike registration number
- **CSV Export** — Download all service records as a CSV file
- **Auto Visit Counter** — Each service increments the bike's total visit count
- **Mobile Friendly** — Responsive layout with collapsible sidebar

## Project Structure

```
Bike SAAS/
├── backend/
│   ├── main.py            # FastAPI app, API routes, CORS
│   ├── models.py          # SQLAlchemy ORM models (Customer, Bike, Service)
│   ├── schemas.py         # Pydantic v2 request/response schemas
│   ├── crud.py            # Async database operations
│   ├── database.py        # Async engine, session factory, DB init
│   ├── import_data.py     # CLI script to import existing CSV/Excel data
│   ├── requirements.txt
│   └── render.yaml        # Render deployment config
└── frontend/
    ├── src/
    │   ├── pages/
    │   │   ├── Dashboard.jsx
    │   │   ├── AddService.jsx
    │   │   └── Search.jsx
    │   ├── components/
    │   │   ├── Sidebar.jsx
    │   │   ├── StatCard.jsx
    │   │   └── MonthlyChart.jsx
    │   └── api/index.js   # Axios API client
    ├── vercel.json         # SPA rewrite rule for Vercel
    └── vite.config.js
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/add-service` | Add a new service record |
| `GET` | `/dashboard` | Get stats and monthly graph data |
| `GET` | `/bike/{bike_number}` | Get customer details + full service history |
| `GET` | `/export-csv` | Download all data as CSV |
| `GET` | `/health` | Health check |

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL database (local or cloud)

### Backend

```bash
cd backend
cp .env.example .env
# Edit .env and set your DATABASE_URL
pip install -r requirements.txt
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.  
Interactive docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
cp .env.example .env
# Edit .env: VITE_API_URL=http://localhost:8000
npm install
npm run dev
```

The app will be available at `http://localhost:5173`.

## Environment Variables

### Backend — `backend/.env`

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/bikeservice
FRONTEND_URL=http://localhost:5173
```

### Frontend — `frontend/.env`

```env
VITE_API_URL=http://localhost:8000
```

## Importing Existing Data

Use the included import script to seed the database from a CSV or Excel file.

```bash
cd backend
python import_data.py --file your_data.csv
python import_data.py --file your_data.xlsx
```

**Required columns** (case-insensitive):

| Column | Format |
|---|---|
| `customer_name` | Text |
| `phone` | Text |
| `bike_number` | Text |
| `bike_model` | Text |
| `service_date` | `YYYY-MM-DD` or `DD/MM/YYYY` |
| `service_details` | Text |
| `cost` | Number |

## Deployment

### Database — Neon or Supabase

1. Create a free PostgreSQL database on [Neon](https://neon.tech) or [Supabase](https://supabase.com)
2. Copy the connection string
3. Append `?ssl=require` if not already included
4. Use the `postgresql+asyncpg://...` format for the `DATABASE_URL`

The database tables are created automatically on first startup.

### Backend — Render

1. Push the `backend/` folder to a GitHub repo
2. Create a new **Web Service** on [Render](https://render.com)
3. Set the following:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables:
   - `DATABASE_URL` — your Neon/Supabase connection string
   - `FRONTEND_URL` — your Vercel frontend URL (e.g. `https://your-app.vercel.app`)

### Frontend — Vercel

1. Push the `frontend/` folder to a GitHub repo
2. Import the project on [Vercel](https://vercel.com)
3. Set the environment variable:
   - `VITE_API_URL` — your Render backend URL (e.g. `https://your-api.onrender.com`)
4. Deploy — the `vercel.json` SPA rewrite is already configured

## Database Schema

```
customers
  id, name, phone, created_at

bikes
  id, bike_number (indexed), bike_model, visit_count, customer_id, created_at

services
  id, bike_id, customer_id, service_date, service_details, cost, created_at
```

## Performance Notes

- All FastAPI routes are fully `async`
- `idx_bike_number` index on the `bikes` table for fast lookups
- SQLAlchemy connection pool: 10 connections, 20 overflow
- Frontend JS split into separate vendor and charts chunks for faster initial load
- CSV export streams directly from the database
