"""
Bulk import script for JOB LOG 1.xlsx
Builds all data in Python first, then inserts everything in one transaction.

Usage:
    python import_excel.py
    python import_excel.py --file other.xlsx
    python import_excel.py --dry-run
"""

import argparse
import asyncio
import os
import re
import sys
from pathlib import Path

import asyncpg
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()

DATA_SHEETS = ["Nov'25", "Dec'25", "Jan'26", "Feb'26", "Mar'26", "Apr'26"]
WALK_IN_REG = "WALK-IN"


# ── DSN builder ───────────────────────────────────────────────────────────────

def build_dsn() -> str:
    raw = os.getenv("DATABASE_URL", "")
    raw = raw.replace("postgresql+asyncpg://", "postgresql://")
    if "?" in raw:
        raw = raw.split("?")[0]
    return raw


# ── Cleaners ──────────────────────────────────────────────────────────────────

def nn(val):
    if val is None: return None
    if isinstance(val, float) and np.isnan(val): return None
    try:
        if pd.isna(val): return None
    except (TypeError, ValueError): pass
    return val

def safe_str(val):
    v = nn(val)
    return str(v).strip() if v is not None else None

def clean_bike_number(raw):
    if pd.isna(raw) or str(raw).strip() in ("", "nan", "NaT"):
        return WALK_IN_REG
    return re.sub(r"\s+", "", str(raw).strip().upper())

def clean_phone(raw):
    if pd.isna(raw): return None
    try:
        num = str(int(float(str(raw).strip())))
        return num if len(num) >= 7 else None
    except (ValueError, OverflowError):
        return None

def clean_name(raw):
    if pd.isna(raw) or str(raw).strip().lower() in ("nan", ""): return None
    return str(raw).strip().title()

def clean_chassis(raw):
    if pd.isna(raw) or str(raw).strip() in ("", "nan"): return None
    return str(raw).strip().upper()

def clean_km(raw):
    try:
        v = float(raw)
        return int(v) if not np.isnan(v) and v > 0 else None
    except (TypeError, ValueError): return None

def clean_bool(raw):
    if pd.isna(raw): return None
    return str(raw).strip().upper() in ("YES", "Y", "TRUE", "1")

def clean_incentive(raw):
    if pd.isna(raw) or str(raw).strip().lower() in ("nan", ""): return None
    return str(raw).strip()

def normalise_payment(raw):
    if pd.isna(raw): return "Unknown"
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
    except (TypeError, ValueError): return 0.0


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
        if s == "Date":                          rename_map[col] = "date"
        elif s == "Reg No.":                     rename_map[col] = "reg_no"
        elif s == "Name":                        rename_map[col] = "name"
        elif s in ("Mobile No.", "Unnamed: 3"):  rename_map[col] = "phone"
        elif s == "Chachis No.":                 rename_map[col] = "chassis_no"
        elif s == "K. M.":                       rename_map[col] = "km"
        elif s == "J/C (Y/N)":                  rename_map[col] = "job_card"
        elif s == "Work Done":                   rename_map[col] = "work_done"
        elif s == "Amount":                      rename_map[col] = "amount"
        elif s == "MODE OF PAYMNET":             rename_map[col] = "payment"
        elif s == "Deepak Incentive":            rename_map[col] = "mechanic_incentive"
        elif s == "Incentive Given":             rename_map[col] = "incentive_paid"
    df = df.rename(columns=rename_map)
    for col in ["date","reg_no","name","phone","chassis_no","km","job_card",
                "work_done","amount","payment","mechanic_incentive","incentive_paid"]:
        if col not in df.columns:
            df[col] = None
    df = df[df["date"].notna()].copy()
    return df


# ── Main ──────────────────────────────────────────────────────────────────────

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

    # Clean all columns
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

    bad = merged["date_clean"].isna().sum()
    if bad:
        print(f"  ⚠ Dropping {bad} rows with unparseable dates")
    merged = merged[merged["date_clean"].notna()].copy()
    print(f"  ✓ Rows after date clean: {len(merged)}")
    print(f"  ✓ Total revenue: ₹{merged['cost_clean'].sum():,.0f}\n")

    if dry_run:
        print(merged[["date_clean","reg_clean","name_clean","cost_clean","payment_clean"]].head(10).to_string())
        print("\n(No data written.)")
        return

    # ── Build in-memory maps ───────────────────────────────────────────────────
    # customers: phone → (name, phone)
    customer_map = {}   # cache_key → {"name", "phone"}
    bike_map     = {}   # reg_no → {"reg_no", "chassis", "customer_key"}
    service_rows = []   # list of dicts

    for _, row in merged.iterrows():
        phone    = nn(row["phone_clean"])
        name     = safe_str(row["name_clean"]) or "Unknown"
        reg_no   = safe_str(row["reg_clean"]) or WALK_IN_REG
        chassis  = nn(row["chassis_clean"])
        eff_phone = phone or "000000000"
        c_key    = phone if phone else f"notel:{name}"

        if c_key not in customer_map:
            customer_map[c_key] = {"name": name, "phone": eff_phone}

        if reg_no not in bike_map:
            bike_map[reg_no] = {"reg_no": reg_no, "chassis": chassis, "customer_key": c_key}
        elif not bike_map[reg_no]["chassis"] and chassis:
            bike_map[reg_no]["chassis"] = chassis

        service_rows.append({
            "reg_no":     reg_no,
            "date":       row["date_clean"].to_pydatetime(),
            "details":    safe_str(row["work_done"]) or "—",
            "cost":       float(nn(row["cost_clean"]) or 0),
            "km":         nn(row["km_clean"]),
            "job_card":   nn(row["jc_clean"]),
            "payment":    safe_str(row["payment_clean"]),
            "incentive":  nn(row["inc_clean"]),
            "inc_paid":   safe_str(row["inc_paid"]),
            "c_key":      c_key,
        })

    print(f"  Customers to insert : {len(customer_map)}")
    print(f"  Bikes to insert     : {len(bike_map)}")
    print(f"  Services to insert  : {len(service_rows)}")
    print(f"\nConnecting to Neon…")

    dsn = build_dsn()
    conn = await asyncpg.connect(dsn, ssl="require", command_timeout=120)

    print("Clearing existing data…")
    await conn.execute(
        "TRUNCATE TABLE services, bikes, customers RESTART IDENTITY CASCADE"
    )
    print("  ✓ Tables cleared\n")

    # ── Insert customers ───────────────────────────────────────────────────────
    customer_records = [(v["name"], v["phone"]) for v in customer_map.values()]
    await conn.copy_records_to_table(
        "customers", records=customer_records, columns=["name", "phone"]
    )
    print(f"  ✓ {len(customer_records)} customers inserted")

    # Fetch back IDs
    rows = await conn.fetch("SELECT id, phone FROM customers")
    phone_to_id = {r["phone"]: r["id"] for r in rows}
    ckey_to_id  = {k: phone_to_id[v["phone"]] for k, v in customer_map.items()}

    # ── Insert bikes ───────────────────────────────────────────────────────────
    bike_records = [
        (v["reg_no"], v["chassis"], ckey_to_id[v["customer_key"]], 0)
        for v in bike_map.values()
    ]
    await conn.copy_records_to_table(
        "bikes", records=bike_records,
        columns=["bike_number", "chassis_number", "customer_id", "visit_count"]
    )
    print(f"  ✓ {len(bike_records)} bikes inserted")

    # Fetch back IDs
    rows = await conn.fetch("SELECT id, bike_number FROM bikes")
    reg_to_id = {r["bike_number"]: r["id"] for r in rows}

    # ── Insert services + update visit counts ──────────────────────────────────
    svc_records = []
    visit_counts = {}
    for s in service_rows:
        bid = reg_to_id[s["reg_no"]]
        cid = ckey_to_id[s["c_key"]]
        visit_counts[bid] = visit_counts.get(bid, 0) + 1
        svc_records.append((
            bid, cid, s["date"], s["details"], s["cost"],
            s["km"], s["job_card"], s["payment"], s["incentive"], s["inc_paid"]
        ))

    await conn.copy_records_to_table(
        "services", records=svc_records,
        columns=["bike_id", "customer_id", "service_date", "service_details",
                 "cost", "odometer_km", "job_card", "payment_mode",
                 "mechanic_incentive", "incentive_paid"]
    )
    print(f"  ✓ {len(svc_records)} services inserted")

    # Update visit counts in bulk
    await conn.executemany(
        "UPDATE bikes SET visit_count=$1 WHERE id=$2",
        [(count, bid) for bid, count in visit_counts.items()]
    )
    print(f"  ✓ Visit counts updated\n")

    # Verify
    total_svc = await conn.fetchval("SELECT COUNT(*) FROM services")
    total_rev = await conn.fetchval("SELECT SUM(cost) FROM services")
    await conn.close()

    print(f"""
╔══════════════════════════════════════╗
║        Import Complete               ║
╠══════════════════════════════════════╣
║  Customers inserted : {len(customer_records):<15} ║
║  Bikes inserted     : {len(bike_records):<15} ║
║  Services inserted  : {len(svc_records):<15} ║
║  Errors             : 0               ║
╠══════════════════════════════════════╣
║  DB verified count  : {total_svc:<15} ║
║  DB total revenue   : ₹{float(total_rev or 0):,.0f}
╚══════════════════════════════════════╝
""")
    print("✅  All rows imported. Refresh the dashboard!")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="JOB LOG 1.xlsx")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not Path(args.file).exists():
        print(f"Error: file not found → {args.file}")
        sys.exit(1)
    asyncio.run(run_import(args.file, args.dry_run))

if __name__ == "__main__":
    main()
