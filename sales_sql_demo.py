"""SQLite sales summaries for the UCI Online Retail portfolio sample.

Uses retail_data_audit.py for the agreed line-level penny rounding. This is a
public-data work sample, not a paid client deliverable or a revenue claim.
"""

import argparse
import json
import sqlite3
import zipfile
from pathlib import Path

import pandas as pd

from retail_data_audit import COLUMNS, MEMBER, line_cents, sha256


def connect():
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE sales (month TEXT, country TEXT, stock_code TEXT, quantity INTEGER, line_cents INTEGER, eligible INTEGER)")
    return db


def summaries(db):
    where = "WHERE eligible = 1"
    monthly = db.execute(
        f"SELECT month, COUNT(*), SUM(line_cents) FROM sales {where} GROUP BY month ORDER BY month"
    ).fetchall()
    countries = db.execute(
        f"SELECT country, COUNT(*), SUM(line_cents) FROM sales {where} GROUP BY country ORDER BY SUM(line_cents) DESC LIMIT 5"
    ).fetchall()
    products = db.execute(
        f"SELECT stock_code, COUNT(*), SUM(line_cents) FROM sales {where} GROUP BY stock_code ORDER BY SUM(line_cents) DESC LIMIT 5"
    ).fetchall()
    totals = db.execute(
        "SELECT COUNT(*), SUM(eligible), SUM(line_cents), "
        "SUM(CASE WHEN eligible = 1 THEN line_cents ELSE 0 END), "
        "SUM(CASE WHEN eligible = 1 AND quantity > 0 THEN line_cents ELSE 0 END), "
        "SUM(CASE WHEN eligible = 1 AND quantity < 0 THEN line_cents ELSE 0 END) FROM sales"
    ).fetchone()
    return monthly, countries, products, totals


def self_check():
    with connect() as db:
        db.executemany("INSERT INTO sales VALUES (?,?,?,?,?,?)", [
            ("2026-01", "A", "X", 2, 251, 1),
            ("2026-01", "A", "X", -1, -126, 1),
            ("2026-02", "B", "Y", 1, 0, 0),
        ])
        monthly, _, _, totals = summaries(db)
        assert monthly == [("2026-01", 2, 125)]
        assert totals == (3, 2, 125, 125, 251, -126)
    print("SQLite signed-amount and eligibility checks passed")


def run(source, audit_path):
    baseline = json.loads(audit_path.read_text(encoding="utf-8"))
    source_hash = sha256(source)
    if source_hash != baseline["source_zip_sha256"]:
        raise ValueError("Source ZIP does not match the audited public sample")
    with zipfile.ZipFile(source) as archive:
        members = archive.infolist()
        if len(members) != 1 or members[0].filename != MEMBER or members[0].file_size > 100_000_000:
            raise ValueError("Unexpected ZIP contents or workbook size")
        with archive.open(MEMBER) as stream:
            data = pd.read_excel(stream, engine="openpyxl")
    if list(data.columns) != COLUMNS or len(data) != baseline["rows"]:
        raise ValueError("Workbook schema or row count differs from the audit")

    def rows():
        for item in data.itertuples(index=False):
            quantity = int(item.Quantity)
            price = item.UnitPrice
            yield (
                item.InvoiceDate.strftime("%Y-%m"),
                item.Country,
                str(item.StockCode),
                quantity,
                line_cents(quantity, price),
                int(price > 0 and quantity != 0),
            )

    with connect() as db:
        db.executemany("INSERT INTO sales VALUES (?,?,?,?,?,?)", rows())
        monthly, countries, products, totals = summaries(db)
    if sha256(source) != source_hash:
        raise RuntimeError("Source ZIP changed during analysis")
    row_count, eligible_count, raw, net, gross, offsets = totals
    expected_months = baseline["monthly_eligible"]
    assert row_count == baseline["rows"]
    assert eligible_count == baseline["eligible_rows"]
    assert raw == baseline["raw_line_amount_cents"]
    assert net == baseline["eligible_net_cents"]
    assert gross == baseline["positive_sales_cents"]
    assert offsets == baseline["negative_quantity_offsets_cents"]
    assert net == gross + offsets
    assert raw - net == baseline["excluded_amount_cents"]
    assert {m: {"rows": n, "net_cents": v} for m, n, v in monthly} == expected_months
    return {
        "source": baseline["source"],
        "source_zip_sha256": source_hash,
        "scope": "Public UCI sample; signed line amounts rounded to pence in Python before integer SQL aggregation",
        "rows": row_count,
        "eligible_rows": eligible_count,
        "raw_line_amount_cents": raw,
        "eligible_net_cents": net,
        "positive_sales_cents": gross,
        "negative_quantity_offsets_cents": offsets,
        "monthly": [{"month": m, "rows": n, "net_cents": v} for m, n, v in monthly],
        "top_five_countries_by_net_cents": [{"country": c, "rows": n, "net_cents": v} for c, n, v in countries],
        "top_five_stock_codes_by_net_cents": [{"stock_code": s, "rows": n, "net_cents": v} for s, n, v in products],
        "checks": {"source_unchanged": True, "rows_and_amounts_match_independent_audit": True, "monthly_matches_independent_audit": True},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--audit", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.self_check:
        self_check()
        return
    if not all((args.source, args.audit, args.out)):
        parser.error("--source, --audit and --out are required")
    if args.out.exists():
        parser.error(f"Refusing to overwrite {args.out}")
    result = run(args.source.resolve(strict=True), args.audit.resolve(strict=True))
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(f"SQL summarized {result['rows']:,} rows; net GBP {result['eligible_net_cents']/100:,.2f}; reconciled to original audit")


if __name__ == "__main__":
    main()
