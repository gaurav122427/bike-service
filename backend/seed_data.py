"""
Seed script — inserts realistic bike service records for testing.
Run: python seed_data.py
"""
import asyncio
import random
from datetime import datetime, timedelta, timezone
from database import AsyncSessionLocal, init_db
from models import Customer, Bike, Service
from sqlalchemy import select

# ── Realistic Indian data ────────────────────────────────────────────────────

CUSTOMERS = [
    ("Rajesh Kumar",      "9876543210"),
    ("Priya Sharma",      "9845012345"),
    ("Mohammed Irfan",    "9912345678"),
    ("Sunita Patil",      "9823456789"),
    ("Arvind Nair",       "9754321098"),
    ("Deepika Reddy",     "9687654321"),
    ("Suresh Yadav",      "9765432109"),
    ("Kavitha Menon",     "9934567890"),
    ("Ramesh Gupta",      "9811234567"),
    ("Anita Joshi",       "9900112233"),
    ("Vikram Singh",      "9988776655"),
    ("Latha Krishnan",    "9776655443"),
    ("Nikhil Desai",      "9654321987"),
    ("Pooja Iyer",        "9543219876"),
    ("Santosh Bhosale",   "9432198765"),
]

BIKES = [
    # (bike_number, bike_model)
    ("MH12AB1234", "Honda Activa 6G"),
    ("MH14CD5678", "TVS Jupiter Classic"),
    ("MH04EF9012", "Bajaj Pulsar NS200"),
    ("KA05GH3456", "Royal Enfield Classic 350"),
    ("KA03IJ7890", "Hero Splendor Plus"),
    ("TN09KL2345", "Yamaha FZ-S V3"),
    ("TN22MN6789", "Honda CB Shine"),
    ("DL08OP1357", "Suzuki Access 125"),
    ("DL10QR2468", "TVS Apache RTR 160"),
    ("AP28ST3579", "Bajaj Dominar 400"),
    ("AP16UV4680", "Hero HF Deluxe"),
    ("GJ01WX5791", "Honda Dio"),
    ("GJ05YZ6802", "Yamaha Ray-ZR 125"),
    ("RJ14PQ7913", "Royal Enfield Meteor 350"),
    ("UP80RS8024", "Bajaj Platina 110"),
]

SERVICE_TYPES = [
    ("General Service", lambda: round(random.uniform(400, 800), 0)),
    ("Oil Change & Filter Replacement", lambda: round(random.uniform(350, 600), 0)),
    ("Brake Pad Replacement (Front & Rear)", lambda: round(random.uniform(600, 1200), 0)),
    ("Chain Cleaning & Lubrication", lambda: round(random.uniform(200, 400), 0)),
    ("Tyre Puncture Repair", lambda: round(random.uniform(100, 250), 0)),
    ("Carburetor Cleaning & Tuning", lambda: round(random.uniform(500, 900), 0)),
    ("Battery Replacement", lambda: round(random.uniform(800, 1800), 0)),
    ("Full Body Wash & Polish", lambda: round(random.uniform(300, 600), 0)),
    ("Spark Plug Replacement", lambda: round(random.uniform(150, 350), 0)),
    ("Clutch Cable & Throttle Cable Replacement", lambda: round(random.uniform(400, 700), 0)),
    ("Engine Overhaul", lambda: round(random.uniform(2500, 5000), 0)),
    ("Suspension Fork Oil Change", lambda: round(random.uniform(600, 1000), 0)),
    ("Rear Shock Absorber Replacement", lambda: round(random.uniform(1200, 2500), 0)),
    ("Fuel Injector Cleaning (FI Models)", lambda: round(random.uniform(700, 1200), 0)),
    ("Coolant Flush & Refill", lambda: round(random.uniform(400, 800), 0)),
    ("Headlight & Indicator Bulb Replacement", lambda: round(random.uniform(200, 500), 0)),
    ("Air Filter Cleaning", lambda: round(random.uniform(150, 300), 0)),
    ("Full Service with Wheel Alignment", lambda: round(random.uniform(1200, 2000), 0)),
]


def random_date(months_back: int) -> datetime:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=months_back * 30)
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


async def seed():
    await init_db()

    async with AsyncSessionLocal() as db:
        # Check if data already exists
        existing = await db.scalar(select(Customer).limit(1))
        if existing:
            print("Database already has data. Clearing and re-seeding...")
            await db.execute(__import__("sqlalchemy").delete(Service.__table__))
            await db.execute(__import__("sqlalchemy").delete(Bike.__table__))
            await db.execute(__import__("sqlalchemy").delete(Customer.__table__))
            await db.commit()

        print("Seeding customers, bikes, and services...")

        created_customers = []
        for name, phone in CUSTOMERS:
            c = Customer(name=name, phone=phone)
            db.add(c)
            created_customers.append(c)
        await db.flush()

        created_bikes = []
        for i, (bike_number, bike_model) in enumerate(BIKES):
            customer = created_customers[i % len(created_customers)]
            b = Bike(
                bike_number=bike_number,
                bike_model=bike_model,
                customer_id=customer.id,
                visit_count=0,
            )
            db.add(b)
            created_bikes.append((b, customer))
        await db.flush()

        # Generate service history — each bike gets 2-8 visits spread over 18 months
        service_count = 0
        for bike, owner in created_bikes:
            num_visits = random.randint(2, 8)
            for _ in range(num_visits):
                svc_type, cost_fn = random.choice(SERVICE_TYPES)
                s = Service(
                    bike_id=bike.id,
                    customer_id=owner.id,
                    service_date=random_date(18),
                    service_details=svc_type,
                    cost=cost_fn(),
                )
                db.add(s)
                bike.visit_count += 1
                service_count += 1

        await db.commit()
        print(f"  ✓ {len(CUSTOMERS)} customers")
        print(f"  ✓ {len(BIKES)} bikes")
        print(f"  ✓ {service_count} service records")
        print("\nDone! Refresh the dashboard to see the data.")


if __name__ == "__main__":
    asyncio.run(seed())
