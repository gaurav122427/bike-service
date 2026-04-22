"""
Production import script for JOB LOG 1.xlsx
Uses raw asyncpg for reliable bulk insert without connection timeouts.

Usage:
    python import_excel.py                        # imports JOB LOG 1.xlsx
    python import_excel.py --file other.xlsx      # imports a different file
    python import_excel.py --dry-run              # preview without writing
"""

import argparse
import asyncio
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import asyncpg
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()

# ── Constants ────────────────────────────────────────────────────────────────

DATA_SHEETS = ["Nov'25", "Dec'25", "Jan'26", "Feb'26", "Mar'26", "Apr'26"]
WALK_IN_REG = "WALK-IN"

# ── Build a plain psql:// DSN from the asyncpg URL ───────────────────────────

def build_dsn() -> str:
    raw = os.getenv("DATABASE_URL", "")
    # Convert postgresql+asyncpg:// → postgresql://
    raw = raw.replace("postgresql+asyncpg://", "postgresql://")
    # Convert ?ssl=require → handled via connect kwargs, strip from DSN
    if "?" in raw:
        raw = raw.split("?")[0]
    return raw


# ── Normalisation helpers ─────────────────────────────────────────────────────

def nn(val):
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

def safe_str(val):
    v = nn(val)
    return str(v).strip() if v is not None else None

def clean_bike_number(raw):
    if pd.isna(raw) or str(raw).strip() in ("", "nan", "NaT"):
        return WALK_IN_REG
    return re.sub(r"\s+", "", str(raw).strip().upper())

def clean_phone(raw):
    if pd.isna(raw):
        return None
    try:
        num = str(int(float(str(raw).strip())))
        return num if len(num) >= 7 else None
    except (ValueError, OverflowError):
        return None

def clean_name(raw):
    if pd.isna(raw) or str(raw).strip().lower() in ("nan", ""):
        return None
    return str(raw).strip().title()

def clean_chassis(raw):
    if pd.isna(raw) or str(raw).strip() in ("", "nan"):
        return None
    return str(raw).strip().upper()

def clean_km(raw):
    try:
        v = float(raw)
        return int(v) if not np.isnan(v) and v > 0 else None
    except (TypeError, ValueError):
        return None

def clean_bool(raw):
    if pd.isna(raw):
        return None
    return str(raw).strip().upper() in ("YES", "Y", "TRUE", "1")

def clean_incentive(raw):
    if pd.isna(raw) or str(raw).strip().lower() in ("nan", ""):
        return None
    return str(raw).strip()

def normalise_payment(raw):
    if pd.isna(raw):
        return "Unknown"
    s = str(raw).strip().lower()
    has_cash   = bool(re.search(r"\bcash\b", s))
    has_online = bool(re.search(r"\bonline\b", s))
    has_card   = bool(re.search(r"\bcard\b", s))
    active = sum([has_cash, has_online, has_card])
    if active > 1: return "Mixed"
    if has_online: return "Online"
    if has_card:   return "Card"
    if has_cash:   return "Cash"
    return "Unknown"

def clean_cost(raw):
    try:
        v = float(str(raw).replace(",", "").strip())
        return max(v, 0.0)
    except (TypeError, ValueError):
        return 0.0


# ── Sheet reader ──────────────────────────────────────────────────────────────

def read_sheet(xl, sheet):
    raw = pd.read_excel(xl, sheet_name=sheet, header=None)
    hdr_row = 0
    for i, row in raw.iterrows():
        vals = {str(v).strip() for v in row.values}
        if "Date" in vals or "Reg No." in vals:
            hdr_row = i
            break
    df = pd.read_excel(xl, sheet_name=sheet, header=hdr_row)
    rename_map = {}
    for col in df.columns:
        s = str(col).strip()
        if s == "Date":                       rename_map[col] = "date"
        elif s == "Reg No.":                  rename_map[col] = "reg_no"
        elif s == "Name":                     rename_map[col] = "name"
        elif s in ("Mobile No.", "Unnamed: 3"): rename_map[col] = "phone"
        elif s == "Chachis No.":              rename_map[col] = "chassis_no"
        elif s == "K. M.":                    rename_map[col] = "km"
        elif s == "J/C (Y/N)":               rename_map[col] = "job_card"
        elif s == "Work Done":                rename_map[col] = "work_done"
        elif s == "Amount":                   rename_map[col] = "amount"
        elif s == "MODE OF PAYMNET":          rename_map[col] = "payment"
        elif s == "Deepak Incentive":         rename_map[col] = "mechanic_incentive"
        elif s == "Incentive Given":          rename_map[col] = "incentive_paid"
    df = df.rename(columns=rename_map)
    for col in ["date","reg_no","name","phone","chassis_no","km","job_card",
                "work_done","amount","payment","mechanic_incentive","incentive_paid"]:
        if col not in df.columns:
            df[col] = None
    df = df[df["date"].notna()].copy()
    df["_sheet"] = sheet
    return df


# ── Main import ───────────────────────────────────────────────────────────────

async def run_import(file_path: str, dry_run: bool = False):
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Reading: {file_path}\n")

    xl = pd.ExcelFile(file_path)
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

    bad_dates = merged["date_clean"].isna().sum()
    if bad_dates:
        print(f"  ⚠ Dropping {bad_dates} rows with unparseable dates")
    merged = merged[merged["date_clean"].notna()].copy()

    before = len(merged)
    merged = merged.drop_duplicates(subset=["reg_clean", "date_clean", "work_done"], keep="first")
    dupes = before - len(merged)
    if dupes:
        print(f"  ✓ Removed {dupes} duplicate rows")

    print(f"  ✓ Clean rows to import: {len(merged)}\n")

    if dry_run:
        print(merged[["date_clean","reg_clean","name_clean","phone_clean",
                       "work_done","cost_clean","payment_clean"]].head(10).to_string())
        print("\n(No data was written to the database.)")
        return

    dsn = build_dsn()
    conn = await asyncpg.connect(dsn, ssl="require", command_timeout=60)

    print("Clearing existing data…")
    await conn.execute("TRUNCATE TABLE services, bikes, customers RESTART IDENTITY CASCADE")
    print("  ✓ Tables cleared\n")

    customer_cache = {}  # phone/key → id
    bike_cache     = {}  # reg_no → id

    inserted_customers = 0
    inserted_bikes     = 0
    inserted_services  = 0
    errors             = 0

    for idx, row in merged.iterrows():
        try:
            phone  = nn(row["phone_clean"])
            name   = safe_str(row["name_clean"]) or "Unknown"
            reg_no = safe_str(row["reg_clean"]) or WALK_IN_REG
            effective_phone = phone or "000000000"
            cache_key = phone if phone else f"notel:{name}"
            chassis = nn(row["chassis_clean"])

            async with conn.transaction():
                # ── Customer ──────────────────────────────────────────────────
                if cache_key in customer_cache:
                    customer_id = customer_cache[cache_key]
                else:
                    row_c = await conn.fetchrow(
                        "SELECT id FROM customers WHERE phone=$1", effective_phone
                    )
                    if row_c:
                        customer_id = row_c["id"]
                    else:
                        customer_id = await conn.fetchval(
                            "INSERT INTO customers(name, phone) VALUES($1,$2) RETURNING id",
                            name, effective_phone
                        )
                        inserted_customers += 1

                # ── Bike ──────────────────────────────────────────────────────
                if reg_no in bike_cache:
                    bike_id = bike_cache[reg_no]
                else:
                    row_b = await conn.fetchrow(
                        "SELECT id, chassis_number FROM bikes WHERE bike_number=$1", reg_no
                    )
                    if row_b:
                        bike_id = row_b["id"]
                        if not row_b["chassis_number"] and chassis:
                            await conn.execute(
                                "UPDATE bikes SET chassis_number=$1 WHERE id=$2", chassis, bike_id
                            )
                    else:
                        bike_id = await conn.fetchval(
                            "INSERT INTO bikes(bike_number, chassis_number, customer_id, visit_count) VALUES($1,$2,$3,0) RETURNING id",
                            reg_no, chassis, customer_id
                        )
                        inserted_bikes += 1

                # ── Service ───────────────────────────────────────────────────
                await conn.execute(
                    "UPDATE bikes SET visit_count = visit_count + 1 WHERE id=$1", bike_id
                )
                await conn.execute(
                    """INSERT INTO services
                       (bike_id, customer_id, service_date, service_details, cost,
                        odometer_km, job_card, payment_mode, mechanic_incentive, incentive_paid)
                       VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
                    bike_id, customer_id,
                    row["date_clean"].to_pydatetime(),
                    safe_str(row["work_done"]) or "—",
                    float(nn(row["cost_clean"]) or 0),
                    nn(row["km_clean"]),
                    nn(row["jc_clean"]),
                    safe_str(row["payment_clean"]),
                    nn(row["inc_clean"]),
                    safe_str(row["inc_paid"]),
                )

            # Only cache after successful transaction
            customer_cache[cache_key] = customer_id
            bike_cache[reg_no] = bike_id
            inserted_services += 1

            if inserted_services % 50 == 0:
                print(f"  … {inserted_services} services saved")

        except Exception as e:
            errors += 1
            print(f"  ✗ Row {idx}: {e!r} | reg={row.get('reg_clean')}")

    await conn.close()

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
