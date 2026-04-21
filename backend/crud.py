from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from models import Customer, Bike, Service
from schemas import ServiceCreate
import csv
import io


async def get_or_create_customer(db: AsyncSession, name: str, phone: str | None) -> Customer:
    effective_phone = phone or "000000000"
    result = await db.execute(select(Customer).where(Customer.phone == effective_phone))
    customer = result.scalar_one_or_none()
    if customer:
        customer.name = name
        return customer
    customer = Customer(name=name, phone=effective_phone)
    db.add(customer)
    await db.flush()
    return customer


async def get_or_create_bike(
    db: AsyncSession, bike_number: str, bike_model: str, customer_id: int
) -> tuple[Bike, bool]:
    result = await db.execute(select(Bike).where(Bike.bike_number == bike_number))
    bike = result.scalar_one_or_none()
    is_new = False
    if not bike:
        bike = Bike(
            bike_number=bike_number,
            bike_model=bike_model,
            customer_id=customer_id,
            visit_count=0,
        )
        db.add(bike)
        await db.flush()
        is_new = True
    return bike, is_new


async def add_service(db: AsyncSession, data: ServiceCreate):
    customer = await get_or_create_customer(db, data.customer_name, data.phone)
    bike, is_new = await get_or_create_bike(
        db, data.bike_number, data.bike_model, customer.id
    )

    # Update chassis number if provided and not already set
    if data.chassis_number and not bike.chassis_number:
        bike.chassis_number = data.chassis_number.strip().upper()

    bike.visit_count += 1

    service = Service(
        bike_id=bike.id,
        customer_id=customer.id,
        service_date=data.service_date,
        service_details=data.service_details,
        cost=data.cost,
        odometer_km=data.odometer_km,
        job_card=data.job_card,
        payment_mode=data.payment_mode,
        mechanic_incentive=data.mechanic_incentive,
        incentive_paid=data.incentive_paid,
    )
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return service, is_new, bike.visit_count


async def get_dashboard_stats(db: AsyncSession):
    now = datetime.now(timezone.utc)
    current_month = now.month
    current_year = now.year

    total_services = await db.scalar(select(func.count(Service.id)))
    total_customers = await db.scalar(select(func.count(Customer.id)))
    total_revenue = await db.scalar(select(func.coalesce(func.sum(Service.cost), 0)))

    monthly_services = await db.scalar(
        select(func.count(Service.id)).where(
            extract("month", Service.service_date) == current_month,
            extract("year", Service.service_date) == current_year,
        )
    )
    monthly_revenue = await db.scalar(
        select(func.coalesce(func.sum(Service.cost), 0)).where(
            extract("month", Service.service_date) == current_month,
            extract("year", Service.service_date) == current_year,
        )
    )

    monthly_result = await db.execute(
        select(
            extract("year", Service.service_date).label("year"),
            extract("month", Service.service_date).label("month"),
            func.count(Service.id).label("count"),
            func.coalesce(func.sum(Service.cost), 0).label("revenue"),
        )
        .group_by("year", "month")
        .order_by("year", "month")
        .limit(12)
    )
    rows = monthly_result.all()

    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    monthly_graph = [
        {
            "month": f"{month_names[int(r.month) - 1]} {int(r.year)}",
            "count": r.count,
            "revenue": float(r.revenue),
        }
        for r in rows
    ]

    return {
        "total_services": total_services or 0,
        "monthly_services": monthly_services or 0,
        "total_customers": total_customers or 0,
        "total_revenue": float(total_revenue or 0),
        "monthly_revenue": float(monthly_revenue or 0),
        "monthly_graph": monthly_graph,
    }


async def get_bike_history(db: AsyncSession, bike_number: str):
    result = await db.execute(
        select(Bike)
        .options(selectinload(Bike.customer), selectinload(Bike.services).selectinload(Service.customer))
        .where(Bike.bike_number == bike_number.strip().upper())
    )
    bike = result.scalar_one_or_none()
    if not bike:
        return None

    history = [
        {
            "id": s.id,
            "service_date": s.service_date,
            "service_details": s.service_details,
            "cost": s.cost,
            "bike_number": bike.bike_number,
            "bike_model": bike.bike_model,
            "customer_name": bike.customer.name,
            "phone": bike.customer.phone,
        }
        for s in bike.services
    ]

    return {
        "bike_number": bike.bike_number,
        "bike_model": bike.bike_model,
        "customer_name": bike.customer.name,
        "phone": bike.customer.phone,
        "total_visits": bike.visit_count,
        "service_history": history,
    }


async def get_services(
    db: AsyncSession,
    month: int | None = None,
    year: int | None = None,
):
    base_query = (
        select(
            Service.id,
            Service.service_date,
            Service.service_details,
            Service.cost,
            Service.odometer_km,
            Service.job_card,
            Service.payment_mode,
            Service.mechanic_incentive,
            Service.incentive_paid,
            Bike.bike_number,
            Bike.bike_model,
            Bike.chassis_number,
            Bike.visit_count,
            Customer.name.label("customer_name"),
            Customer.phone,
        )
        .join(Bike, Service.bike_id == Bike.id)
        .join(Customer, Service.customer_id == Customer.id)
    )

    if month and year:
        base_query = base_query.where(
            extract("month", Service.service_date) == month,
            extract("year", Service.service_date) == year,
        )

    base_query = base_query.order_by(Service.service_date.desc())
    result = await db.execute(base_query)
    rows = result.all()

    services = [
        {
            "id": r.id,
            "service_date": r.service_date,
            "service_details": r.service_details,
            "cost": r.cost,
            "bike_number": r.bike_number,
            "bike_model": r.bike_model,
            "chassis_number": r.chassis_number,
            "customer_name": r.customer_name,
            "phone": r.phone,
            "visit_count": r.visit_count,
            "odometer_km": r.odometer_km,
            "job_card": r.job_card,
            "payment_mode": r.payment_mode,
            "mechanic_incentive": r.mechanic_incentive,
            "incentive_paid": r.incentive_paid,
        }
        for r in rows
    ]

    total_revenue = sum(s["cost"] for s in services)

    # Build available months list from all data
    months_result = await db.execute(
        select(
            extract("year", Service.service_date).label("year"),
            extract("month", Service.service_date).label("month"),
        )
        .distinct()
        .order_by(
            extract("year", Service.service_date).desc(),
            extract("month", Service.service_date).desc(),
        )
    )
    month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    available_months = [
        f"{month_names[int(r.month)-1]} {int(r.year)}"
        for r in months_result.all()
    ]

    return {
        "services": services,
        "total_count": len(services),
        "total_revenue": total_revenue,
        "available_months": available_months,
    }


async def export_csv(db: AsyncSession) -> str:
    result = await db.execute(
        select(
            Service.id,
            Service.service_date,
            Service.service_details,
            Service.cost,
            Bike.bike_number,
            Bike.bike_model,
            Bike.visit_count,
            Customer.name.label("customer_name"),
            Customer.phone,
        )
        .join(Bike, Service.bike_id == Bike.id)
        .join(Customer, Service.customer_id == Customer.id)
        .order_by(Service.service_date.desc())
    )
    rows = result.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Service ID", "Service Date", "Service Details", "Cost (₹)",
        "Bike Number", "Bike Model", "Total Visits",
        "Customer Name", "Phone",
    ])
    for row in rows:
        writer.writerow([
            row.id,
            row.service_date.strftime("%Y-%m-%d %H:%M") if row.service_date else "",
            row.service_details,
            row.cost,
            row.bike_number,
            row.bike_model,
            row.visit_count,
            row.customer_name,
            row.phone,
        ])
    return output.getvalue()
