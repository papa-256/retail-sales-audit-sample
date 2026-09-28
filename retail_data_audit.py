"""Reproducible, read-only audit of UCI's Online Retail workbook."""

import argparse
import hashlib
import json
import zipfile
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd


SOURCE = "https://archive.ics.uci.edu/dataset/352/online+retail"
ZIP_URL = "https://archive.ics.uci.edu/static/public/352/online%2Bretail.zip"
MEMBER = "Online Retail.xlsx"
CENT = Decimal("0.01")
COLUMNS = ["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country"]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def line_cents(quantity, price):
    if pd.isna(quantity) or pd.isna(price):
        return None
    q, p = Decimal(str(quantity)), Decimal(str(price))
    if not q.is_finite() or not p.is_finite() or q != q.to_integral_value():
        raise ValueError("This dataset requires finite prices and integer quantities")
    return int((q * p / CENT).quantize(0, rounding=ROUND_HALF_UP))


def money(cents):
    return f"{'-' if cents < 0 else ''}£{abs(cents) / 100:,.2f}"


def audit(source):
    original_hash = sha256(source)
    with zipfile.ZipFile(source) as archive:
        members = archive.infolist()
        if len(members) != 1 or members[0].filename != MEMBER or members[0].file_size > 100_000_000:
            raise ValueError("Unexpected ZIP contents or workbook size")
        with archive.open(MEMBER) as stream:
            df = pd.read_excel(stream, engine="openpyxl")
    if list(df.columns) != COLUMNS:
        raise ValueError(f"Unexpected columns: {list(df.columns)}")
    if sha256(source) != original_hash:
        raise RuntimeError("Source changed during audit")

    n = len(df)
    qty = pd.to_numeric(df.Quantity, errors="coerce")
    price = pd.to_numeric(df.UnitPrice, errors="coerce")
    dates = pd.to_datetime(df.InvoiceDate, errors="coerce")
    invoice = df.InvoiceNo.astype("string")
    cancelled = invoice.str.startswith("C", na=False)
    complete_amount = qty.notna() & price.notna()
    eligible = complete_amount & (price > 0) & (qty != 0)
    cents = [line_cents(q, p) for q, p in zip(qty, price)]
    raw = sum(x for x in cents if x is not None)
    net = sum(cents[i] for i in range(n) if eligible.iat[i])
    gross = sum(cents[i] for i in range(n) if eligible.iat[i] and qty.iat[i] > 0)
    offsets = sum(cents[i] for i in range(n) if eligible.iat[i] and qty.iat[i] < 0)
    excluded = sum(cents[i] for i in range(n) if complete_amount.iat[i] and not eligible.iat[i])

    monthly = {}
    for i in range(n):
        if eligible.iat[i] and pd.notna(dates.iat[i]):
            key = dates.iat[i].strftime("%Y-%m")
            slot = monthly.setdefault(key, {"rows": 0, "net_cents": 0})
            slot["rows"] += 1
            slot["net_cents"] += cents[i]

    # Independent controls: partition all rows by eligibility, then regroup eligible
    # amounts by invoice number rather than by month.
    invoice_totals = {}
    for i in range(n):
        if eligible.iat[i]:
            key = str(invoice.iat[i])
            invoice_totals[key] = invoice_totals.get(key, 0) + cents[i]
    assert len(cents) == n
    assert int(eligible.sum()) + int((~eligible).sum()) == n
    assert raw == net + excluded
    assert net == gross + offsets == sum(invoice_totals.values())
    assert sum(x["rows"] for x in monthly.values()) == int((eligible & dates.notna()).sum())
    assert sum(x["net_cents"] for x in monthly.values()) == sum(cents[i] for i in range(n) if eligible.iat[i] and pd.notna(dates.iat[i]))

    result = {
        "source": SOURCE,
        "download_url": ZIP_URL,
        "doi": "10.24432/C5BW33",
        "license": "CC BY 4.0",
        "author": "Daqing Chen",
        "source_zip_sha256": original_hash,
        "source_zip_bytes": source.stat().st_size,
        "workbook_member": MEMBER,
        "workbook_bytes": members[0].file_size,
        "rows": n,
        "date_min": str(dates.min()),
        "date_max": str(dates.max()),
        "missing_by_column": {col: int(df[col].isna().sum()) for col in COLUMNS},
        "exact_duplicate_rows": int(df.duplicated().sum()),
        "cancel_prefix_rows": int(cancelled.sum()),
        "negative_quantity_rows": int((qty < 0).sum()),
        "zero_quantity_rows": int((qty == 0).sum()),
        "nonpositive_price_rows": int((price <= 0).sum()),
        "quantity_abs_over_1000_rows": int((qty.abs() > 1000).sum()),
        "eligible_rows": int(eligible.sum()),
        "raw_line_amount_cents": raw,
        "eligible_net_cents": net,
        "positive_sales_cents": gross,
        "negative_quantity_offsets_cents": offsets,
        "excluded_amount_cents": excluded,
        "monthly_eligible": dict(sorted(monthly.items())),
        "checks": {"source_unchanged": True, "row_partition": True, "amount_partition": True, "invoice_reconciliation": True, "monthly_reconciliation": True},
    }
    return result


def report(r):
    missing = ", ".join(f"{k} {v:,}" for k, v in r["missing_by_column"].items() if v)
    months = "\n".join(f"| {month} | {item['rows']:,} | {money(item['net_cents'])} |" for month, item in r["monthly_eligible"].items())
    return f"""# UCI Online Retail: reproducible data quality audit

**Public portfolio sample; no client data or paid-client claim.** Source: [UCI Online Retail]({SOURCE}), Daqing Chen, DOI [10.24432/C5BW33](https://doi.org/10.24432/C5BW33), CC BY 4.0. The source covers {r['rows']:,} transaction lines from {r['date_min']} to {r['date_max']}. ZIP SHA-256: `{r['source_zip_sha256']}`. Workbook inside ZIP: `{MEMBER}` ({r['workbook_bytes']:,} bytes).

## Run

```powershell
New-Item -ItemType Directory -Force work/retail_sample | Out-Null
if (-not (Test-Path work/retail_sample/online_retail.zip)) {{ Invoke-WebRequest '{ZIP_URL}' -OutFile work/retail_sample/online_retail.zip }}
python retail_data_audit.py --source work/retail_sample/online_retail.zip --out-dir YOUR_NEW_EMPTY_DIRECTORY
```

Requires Python with pandas and openpyxl. The script opens the workbook inside the ZIP without extracting or editing it, verifies the source hash before and after, and creates JSON and Markdown with exclusive file creation. Use a new directory for each rerun.

## Findings

| Check | Count |
| --- | ---: |
| Source rows | {r['rows']:,} |
| Missing values | {missing or 'none'} |
| Exact duplicate rows (flagged, retained) | {r['exact_duplicate_rows']:,} |
| Invoice numbers beginning C | {r['cancel_prefix_rows']:,} |
| Negative quantity rows | {r['negative_quantity_rows']:,} |
| Zero quantity rows | {r['zero_quantity_rows']:,} |
| Nonpositive unit price rows | {r['nonpositive_price_rows']:,} |
| Absolute quantity above 1,000 (review flag) | {r['quantity_abs_over_1000_rows']:,} |
| Positive-price, nonzero-quantity analysis rows | {r['eligible_rows']:,} |

| Amount definition | GBP |
| --- | ---: |
| All numeric source lines, quantity × unit price | {money(r['raw_line_amount_cents'])} |
| Analysis net: positive-price, nonzero-quantity lines | {money(r['eligible_net_cents'])} |
| Positive-quantity sales component | {money(r['positive_sales_cents'])} |
| Negative-quantity offset component | {money(r['negative_quantity_offsets_cents'])} |
| Excluded line amount (raw minus analysis net) | {money(r['excluded_amount_cents'])} |

The positive and negative components sum to the analysis net. The excluded amount reconciles that net to the raw source amount. Each line is rounded to pence using decimal half-up arithmetic before summing. Missing CustomerID is left missing. Exact duplicate lines are retained because the columns do not provide a unique line key. Cancel-prefixed invoices and negative quantities remain in the net; neither proves the reason for an individual return. Nonpositive prices and zero quantities remain in the source and are only excluded from the stated analysis net. Quantity above 1,000 is a review flag, not a deletion rule.

## Monthly analysis totals

| Month | Analysis rows | Net GBP |
| --- | ---: | ---: |
{months}

December 2011 ends on 9 December, so its total must not be compared as a full month. These are transaction-line amounts, not profit, realized cash, or verified refunds. All assertions passed: source unchanged, row and amount partitions, and independent invoice and monthly reconciliations.

中文摘要：这是公开数据的作品样本，并非客户项目或已获得收入。保留取消单、负数量、重复行与缺失客户编号；正价非零数量行的净额与正销售、负数量冲销逐分核对。2011 年 12 月仅含前 9 天，不能按完整月份比较。
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--source", type=Path, help="Downloaded UCI ZIP; never modified")
    parser.add_argument("--out-dir", type=Path, help="New output directory")
    args = parser.parse_args()
    if args.self_check:
        assert line_cents(2, "1.255") == 251
        assert line_cents(-1, "1.255") == -126
        assert line_cents(None, 1) is None
        for q, p in ((1.5, 2), (1, float("inf"))):
            try:
                line_cents(q, p)
            except ValueError:
                pass
            else:
                raise AssertionError("Invalid numeric value was accepted")
        print("Money rounding and input validation checks passed")
        return
    if args.source is None or args.out_dir is None:
        parser.error("--source and --out-dir are required unless using --self-check")
    source = args.source.resolve(strict=True)
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    for name in ("retail_data_audit.json", "retail_data_audit.md"):
        target = out / name
        if target.exists() or target == source:
            parser.error(f"Refusing to overwrite {target}")
    r = audit(source)
    (out / "retail_data_audit.json").open("x", encoding="utf-8").write(json.dumps(r, indent=2, ensure_ascii=False) + "\n")
    (out / "retail_data_audit.md").open("x", encoding="utf-8").write(report(r))
    print(f"Audited {r['rows']:,} rows; net GBP {r['eligible_net_cents'] / 100:,.2f}; checks passed; reports in {out}")


if __name__ == "__main__":
    main()
