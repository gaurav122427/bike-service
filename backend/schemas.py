from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional


class ServiceCreate(BaseModel):
    customer_name: str
    phone: Optional[str] = None
    bike_number: str
    bike_model: Optional[str] = None
    service_date: datetime
    service_details: str
    cost: float
    chassis_number: Optional[str] = None
    odometer_km: Optional[int] = None
    job_card: Optional[bool] = None
    payment_mode: Optional[str] = None
    mechanic_incentive: Optional[bool] = None
    incentive_paid: Optional[str] = None

    @field_validator("bike_number")
    @classmethod
    def normalize_bike_number(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        return v.strip()


class ServiceOut(BaseModel):
    id: int
    service_date: datetime
    service_details: str
    cost: float
    bike_number: str
    bike_model: Optional[str] = None
    customer_name: str
    phone: Optional[str] = None

    model_config = {"from_attributes": True}


class BikeHistory(BaseModel):
    bike_number: str
    bike_model: Optional[str] = None
    customer_name: str
    phone: Optional[str] = None
    total_visits: int
    service_history: list[ServiceOut]


class MonthlyData(BaseModel):
    month: str
    count: int
    revenue: float


class DashboardStats(BaseModel):
    total_services: int
    monthly_services: int
    total_customers: int
    total_revenue: float
    monthly_revenue: float
    monthly_graph: list[MonthlyData]


class ServiceResponse(BaseModel):
    message: str
    service_id: int
    is_new_bike: bool
    visit_count: int


class ServiceListItem(BaseModel):
    id: int
    service_date: datetime
    service_details: str
    cost: float
    bike_number: str
    bike_model: Optional[str] = None
    chassis_number: Optional[str] = None
    customer_name: str
    phone: Optional[str] = None
    visit_count: int
    odometer_km: Optional[int] = None
    job_card: Optional[bool] = None
    payment_mode: Optional[str] = None
    mechanic_incentive: Optional[bool] = None
    incentive_paid: Optional[str] = None

    model_config = {"from_attributes": True}


class ServiceListResponse(BaseModel):
    services: list[ServiceListItem]
    total_count: int
    total_revenue: float
    available_months: list[str]
