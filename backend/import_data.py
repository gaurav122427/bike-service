"""
Data import script — run once to seed existing records.

Usage:
    pip install pandas openpyxl psycopg2-binary python-dotenv
    python import_data.py --file data.csv
    python import_data.py --file data.xlsx

Expected columns (case-insensitive):
    customer_name, phone, bike_number, bike_model,
    service_date (YYYY-MM-DD or DD/MM/YYYY), service_details, cost
"""

import argparse
import asyncio
import sys
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import select

load_dotenv()

from database import AsyncSessionLocal, init_db
from models import Customer, Bike, Service


def parse_date(value) -> datetime:
    if isinstance(value, datetime):
        return value
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {value}")


async def import_records(df: pd.DataFrame):
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    required = {"customer_name", "phone", "bike_number", "bike_model", "service_date", "service_details", "cost"}
    missing = required - set(df.columns)
    if missing:
        print(f"Missing columns: {missing}")
        sys.exit(1)

    await init_db()
    success = 0
    errors = 0

    async with AsyncSessionLocal() as db:
        for idx, row in df.iterrows():
            try:
                phone = str(row["phone"]).strip()
                bike_number = str(row["bike_number"]).strip().upper()

                # Customer
                result = await db.execute(select(Customer).where(Customer.phone == phone))
                customer = result.scalar_one_or_none()
                if not customer:
                    customer = Customer(name=str(row["customer_name"]).strip(), phone=phone)
                    db.add(customer)
                    await db.flush()

                # Bike
                result = await db.execute(select(Bike).where(Bike.bike_number == bike_number))
                bike = result.scalar_one_or_none()
                if not bike:
                    bike = Bike(
                        bike_number=bike_number,
                        bike_model=str(row["bike_model"]).strip(),
                        customer_id=customer.id,
                        visit_count=0,
                    )
                    db.add(bike)
                    await db.flush()

                bike.visit_count += 1

                service = Service(
                    bike_id=bike.id,
                    customer_id=customer.id,
                    service_date=parse_date(row["service_date"]),
                    service_details=str(row["service_details"]).strip(),
                    cost=float(row["cost"]),
                )
                db.add(service)
                success += 1

                if success % 100 == 0:
                    await db.commit()
                    print(f"  Imported {success} records...")

            except Exception as e:
                print(f"  Row {idx + 2} error: {e}")
                errors += 1

        await db.commit()

    print(f"\nDone. Imported: {success}, Errors: {errors}")


def main():
    parser = argparse.ArgumentParser(description="Import bike service data")
    parser.add_argument("--file", required=True, help="Path to CSV or Excel file")
    args = parser.parse_args()

    if args.file.endswith(".xlsx") or args.file.endswith(".xls"):
        df = pd.read_excel(args.file)
    else:
        df = pd.read_csv(args.file)

    print(f"Loaded {len(df)} rows from {args.file}")
    asyncio.run(import_records(df))


if __name__ == "__main__":
    main()
