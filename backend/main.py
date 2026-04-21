from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import io
import os

from database import get_db, init_db, engine
from sqlalchemy import text
from schemas import ServiceCreate, ServiceResponse, DashboardStats, BikeHistory, ServiceListResponse
from typing import Optional
from auth import (
    ADMIN_USERNAME, ADMIN_PASSWORD_HASH,
    verify_password, create_access_token, get_current_user,
)
import crud

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Kwick Automobiles API",
    version="1.0.0",
    lifespan=lifespan,
)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/test-db")
async def test_db():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "Connected to Neon DB"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username != ADMIN_USERNAME or not verify_password(
        form_data.password, ADMIN_PASSWORD_HASH
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = create_access_token(form_data.username)
    return {"access_token": token, "token_type": "bearer"}


@app.post("/add-service", response_model=ServiceResponse)
async def add_service(
    data: ServiceCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    service, is_new_bike, visit_count = await crud.add_service(db, data)
    return ServiceResponse(
        message="Service added successfully",
        service_id=service.id,
        is_new_bike=is_new_bike,
        visit_count=visit_count,
    )


@app.get("/dashboard", response_model=DashboardStats)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    return await crud.get_dashboard_stats(db)


@app.get("/services", response_model=ServiceListResponse)
async def get_services(
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    return await crud.get_services(db, month, year)


@app.get("/bike/{bike_number}", response_model=BikeHistory)
async def get_bike(
    bike_number: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    result = await crud.get_bike_history(db, bike_number)
    if not result:
        raise HTTPException(status_code=404, detail="Bike not found")
    return result


@app.get("/export-csv")
async def export_csv(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    csv_data = await crud.export_csv(db)
    return StreamingResponse(
        io.StringIO(csv_data),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bike_services.csv"},
    )
