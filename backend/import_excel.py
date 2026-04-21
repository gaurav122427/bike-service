"""
Production import script for JOB LOG 1.xlsx
Reads all 6 monthly sheets, cleans data, and loads into PostgreSQL.

Usage:
    python import_excel.py                        # imports JOB LOG 1.xlsx
    python import_excel.py --file other.xlsx      # imports a different file
    python import_excel.py --dry-run              # preview without writing
"""

import argparse
import asyncio
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import numpy as np
from sqlalchemy import delete, select, text
from dotenv import load_dotenv

load_dotenv()

from database import AsyncSessionLocal, engine, init_db
from models import Customer, Bike, Service

# ── Utilities ────────────────────────────────────────────────────────────────

def nn(val):
    """Return None if val is any flavour of NaN/NaT/None, else val unchanged."""
    if val is None:
        return None
    if isinstance(val, float) and np.isnan(val):
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    return val


def safe_str(val) -> str | None:
    v = nn(val)
    return str(v).strip() if v is not None else None


# ── Constants ────────────────────────────────────────────────────────────────

DATA_SHEETS = ["Nov'25", "Dec'25", "Jan'26", "Feb'26", "Mar'26", "Apr'26"]
WALK_IN_REG = "WALK-IN"          # placeholder for rows with no registration number

# ── Normalisation helpers ─────────────────────────────────────────────────────

def clean_bike_number(raw) -> str:
    if pd.isna(raw) or str(raw).strip() in ("", "nan", "NaT"):
        return WALK_IN_REG
    return re.sub(r"\s+", "", str(raw).strip().upper())


def clean_phone(raw) -> str | None:
    if pd.isna(raw):
        return None
    # Excel stores phone as float (9876543210.0) → strip decimal
    try:
        num = str(int(float(str(raw).strip())))
        return num if len(num) >= 7 else None
    except (ValueError, OverflowError):
        return None


def clean_name(raw) -> str | None:
    if pd.isna(raw) or str(raw).strip().lower() in ("nan", ""):
        return None
    return str(raw).strip().title()


def clean_chassis(raw) -> str | None:
    if pd.isna(raw) or str(raw).strip() in ("", "nan"):
        return None
    return str(raw).strip().upper()


def clean_km(raw) -> int | None:
    try:
        v = float(raw)
        return int(v) if not np.isnan(v) and v > 0 else None
    except (TypeError, ValueError):
        return None


def clean_bool(raw) -> bool | None:
    if pd.isna(raw):
        return None
    return str(raw).strip().upper() in ("YES", "Y", "TRUE", "1")


def clean_incentive(raw) -> str | None:
    if pd.isna(raw) or str(raw).strip().lower() in ("nan", ""):
        return None
    return str(raw).strip()


def normalise_payment(raw) -> str:
    """
    Collapse the messy payment strings into four canonical values:
    Cash | Online | Card | Mixed
    """
    if pd.isna(raw):
        return "Unknown"
    s = str(raw).strip().lower()
    has_cash   = bool(re.search(r"\bcash\b", s))
    has_online = bool(re.search(r"\bonline\b", s))
    has_card   = bool(re.search(r"\bcard\b", s))

    active = sum([has_cash, has_online, has_card])
    if active > 1:
        return "Mixed"
    if has_online:
        return "Online"
    if has_card:
        return "Card"
    if has_cash:
        return "Cash"
    return "Unknown"


def clean_cost(raw) -> float:
    try:
        v = float(str(raw).replace(",", "").strip())
        return max(v, 0.0)
    except (TypeError, ValueError):
        return 0.0


# ── Sheet reader ──────────────────────────────────────────────────────────────

def read_sheet(xl: pd.ExcelFile, sheet: str) -> pd.DataFrame:
    """
    Reads one sheet, auto-detects the header row, and returns a normalised DataFrame.
    """
    raw = pd.read_excel(xl, sheet_name=sheet, header=None)

    # Find the row that contains 'Date' and 'Reg No.'
    hdr_row = 0
    for i, row in raw.iterrows():
        vals = {str(v).strip() for v in row.values}
        if "Date" in vals or "Reg No." in vals:
            hdr_row = i
            break

    df = pd.read_excel(xl, sheet_name=sheet, header=hdr_row)

    # Rename columns to canonical names
    rename_map = {}
    for col in df.columns:
        s = str(col).strip()
        if s in ("Date",):                    rename_map[col] = "date"
        elif s in ("Reg No.",):               rename_map[col] = "reg_no"
        elif s in ("Name",):                  rename_map[col] = "name"
        elif s in ("Mobile No.", "Unnamed: 3"): rename_map[col] = "phone"
        elif s in ("Chachis No.",):           rename_map[col] = "chassis_no"
        elif s in ("K. M.",):                 rename_map[col] = "km"
        elif s in ("J/C (Y/N)",):             rename_map[col] = "job_card"
        elif s in ("Work Done",):             rename_map[col] = "work_done"
        elif s in ("Amount",):                rename_map[col] = "amount"
        elif s in ("MODE OF PAYMNET",):       rename_map[col] = "payment"
        elif s in ("Deepak Incentive",):      rename_map[col] = "mechanic_incentive"
        elif s in ("Incentive Given",):       rename_map[col] = "incentive_paid"

    df = df.rename(columns=rename_map)

    # Ensure all required columns exist
    for col in ["date","reg_no","name","phone","chassis_no","km","job_card",
                "work_done","amount","payment","mechanic_incentive","incentive_paid"]:
        if col not in df.columns:
            df[col] = None

    # Drop rows with no date
    df = df[df["date"].notna()].copy()
    df["_sheet"] = sheet
    return df


# ── Main import ───────────────────────────────────────────────────────────────

async def run_import(file_path: str, dry_run: bool = False):
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Reading: {file_path}\n")
    await init_db()

    xl = pd.ExcelFile(file_path)

    # ── 1. Read & merge all sheets ────────────────────────────────────────────
    frames = []
    for sheet in DATA_SHEETS:
        if sheet not in xl.sheet_names:
            print(f"  ⚠ Sheet '{sheet}' not found — skipping")
            continue
        df = read_sheet(xl, sheet)
        frames.append(df)
        print(f"  ✓ Sheet '{sheet}': {len(df)} rows")

    merged = pd.concat(frames, ignore_index=True)
    print(f"\n  Total raw rows: {len(merged)}")

    # ── 2. Clean all columns ──────────────────────────────────────────────────
    merged["reg_clean"]     = merged["reg_no"].apply(clean_bike_number)
    merged["name_clean"]    = merged["name"].apply(clean_name)
    merged["phone_clean"]   = merged["phone"].apply(clean_phone)
    merged["chassis_clean"] = merged["chassis_no"].apply(clean_chassis)
    merged["km_clean"]      = merged["km"].apply(clean_km)
    merged["jc_clean"]      = merged["job_card"].apply(clean_bool)
    merged["cost_clean"]    = merged["amount"].apply(clean_cost)
    merged["payment_clean"] = merged["payment"].apply(normalise_payment)
    merged["inc_clean"]     = merged["mechanic_incentive"].apply(clean_bool)
    merged["inc_paid"]      = merged["incentive_paid"].apply(clean_incentive)
    merged["date_clean"]    = pd.to_datetime(merged["date"], errors="coerce").dt.tz_localize("UTC")

    # Drop rows where date failed to parse
    bad_dates = merged["date_clean"].isna().sum()
    if bad_dates:
        print(f"  ⚠ Dropping {bad_dates} rows with unparseable dates")
    merged = merged[merged["date_clean"].notna()].copy()

    # De-duplicate: same reg_no + same date + same work_done
    before = len(merged)
    merged = merged.drop_duplicates(subset=["reg_clean", "date_clean", "work_done"], keep="first")
    dupes_removed = before - len(merged)
    if dupes_removed:
        print(f"  ✓ Removed {dupes_removed} duplicate rows (same reg+date+work)")

    print(f"  ✓ Clean rows to import: {len(merged)}\n")

    if dry_run:
        print("=== DRY RUN — sample of cleaned data ===")
        print(merged[["date_clean","reg_clean","name_clean","phone_clean",
                       "work_done","cost_clean","payment_clean"]].head(10).to_string())
        print("\n(No data was written to the database.)")
        return

    # ── 3. Wipe existing data (FK order) ─────────────────────────────────────
    async with AsyncSessionLocal() as db:
        print("Clearing existing data…")
        await db.execute(delete(Service))
        await db.execute(delete(Bike))
        await db.execute(delete(Customer))
        # Reset sequences
        for seq in ("services_id_seq", "bikes_id_seq", "customers_id_seq"):
            await db.execute(text(f"ALTER SEQUENCE {seq} RESTART WITH 1"))
        await db.commit()
        print("  ✓ Tables cleared\n")

    # ── 4. Build lookup maps & insert ────────────────────────────────────────
    customer_cache: dict[str, Customer] = {}   # phone → Customer
    bike_cache:     dict[str, Bike] = {}        # reg_no → Bike

    inserted_customers = 0
    inserted_bikes     = 0
    inserted_services  = 0
    errors             = 0

    BATCH = 50

    async with AsyncSessionLocal() as db:

        for idx, row in merged.iterrows():
            # Use a savepoint so a single-row failure does NOT abort the session
            async with db.begin_nested():
                try:
                    # nn() sanitises any np.nan that pandas re-introduces after clean_*
                    phone  = nn(row["phone_clean"])   # str or None
                    name   = safe_str(row["name_clean"]) or "Unknown"
                    reg_no = safe_str(row["reg_clean"]) or WALK_IN_REG

                    # ── Customer ─────────────────────────────────────────────
                    if phone and phone in customer_cache:
                        customer = customer_cache[phone]
                    elif phone:
                        result = await db.execute(
                            select(Customer).where(Customer.phone == phone)
                        )
                        customer = result.scalar_one_or_none()
                        if not customer:
                            customer = Customer(name=name, phone=phone)
                            db.add(customer)
                            await db.flush()
                            inserted_customers += 1
                        customer_cache[phone] = customer
                    else:
                        # No phone — bucket walk-ins by name
                        cache_key = f"notel:{name}"
                        if cache_key in customer_cache:
                            customer = customer_cache[cache_key]
                        else:
                            customer = Customer(name=name, phone="000000000")
                            db.add(customer)
                            await db.flush()
                            inserted_customers += 1
                            customer_cache[cache_key] = customer

                    # ── Bike ─────────────────────────────────────────────────
                    if reg_no in bike_cache:
                        bike = bike_cache[reg_no]
                    else:
                        result = await db.execute(
                            select(Bike).where(Bike.bike_number == reg_no)
                        )
                        bike = result.scalar_one_or_none()
                        chassis = nn(row["chassis_clean"])
                        if not bike:
                            bike = Bike(
                                bike_number=reg_no,
                                bike_model=None,
                                chassis_number=chassis,
                                customer_id=customer.id,
                                visit_count=0,
                            )
                            db.add(bike)
                            await db.flush()
                            inserted_bikes += 1
                        else:
                            if not bike.chassis_number and chassis:
                                bike.chassis_number = chassis
                        bike_cache[reg_no] = bike

                    # ── Service ───────────────────────────────────────────────
                    bike.visit_count += 1

                    service = Service(
                        bike_id=bike.id,
                        customer_id=customer.id,
                        service_date=row["date_clean"],
                        service_details=safe_str(row["work_done"]) or "—",
                        cost=float(nn(row["cost_clean"]) or 0),
                        odometer_km=nn(row["km_clean"]),
                        job_card=nn(row["jc_clean"]),
                        payment_mode=safe_str(row["payment_clean"]),
                        mechanic_incentive=nn(row["inc_clean"]),
                        incentive_paid=safe_str(row["inc_paid"]),
                    )
                    db.add(service)
                    inserted_services += 1

                except Exception as e:
                    errors += 1
                    print(f"  ✗ Row {idx}: {e!r} | reg={row.get('reg_clean')} date={row.get('date_clean')}")
                    raise   # rolls back only this savepoint

            # Commit every BATCH rows
            if inserted_services > 0 and inserted_services % BATCH == 0:
                await db.commit()
                print(f"  … {inserted_services} services saved")

        await db.commit()

    # ── 5. Summary ────────────────────────────────────────────────────────────
    print(f"""
╔══════════════════════════════════════╗
║        Import Complete               ║
╠══════════════════════════════════════╣
║  Customers inserted : {inserted_customers:<15} ║
║  Bikes inserted     : {inserted_bikes:<15} ║
║  Services inserted  : {inserted_services:<15} ║
║  Errors             : {errors:<15} ║
╚══════════════════════════════════════╝
""")

    if errors:
        print("⚠  Some rows had errors — check output above.")
    else:
        print("✅  All rows imported successfully. Refresh the dashboard!")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Import bike service Excel log")
    parser.add_argument("--file", default="JOB LOG 1.xlsx", help="Path to Excel file")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    if not Path(args.file).exists():
        print(f"Error: file not found → {args.file}")
        sys.exit(1)

    asyncio.run(run_import(args.file, args.dry_run))


if __name__ == "__main__":
    main()
