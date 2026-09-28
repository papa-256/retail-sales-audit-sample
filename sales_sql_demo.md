# Public sales SQL work sample

This is a self-initiated portfolio sample using [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail) (Daqing Chen, DOI 10.24432/C5BW33, CC BY 4.0). It contains no client data and represents no paid engagement or earned revenue.

`sales_sql_demo.py` loads the workbook into an in-memory SQLite table, then uses SQL to summarize eligible transaction lines by month, country and stock code. The existing `retail_data_audit.py` computes each signed line amount with decimal half-up penny rounding before SQL aggregation. Eligibility means positive unit price and nonzero quantity; negative quantities remain as offsets. The original rows and duplicate lines are retained.

```powershell
python sales_sql_demo.py --self-check
python sales_sql_demo.py --source YOUR_DOWNLOADED_ZIP.zip --audit retail_data_audit.json --out YOUR_NEW_RESULT.json
```

Requires Python, pandas and openpyxl. Download the source ZIP using the URL in `retail_data_audit.py`; its SHA-256 must match `retail_data_audit.json`. The script refuses to overwrite an existing result.

The full run processed **541,909** lines, with **539,392** analysis-eligible lines. SQL returned an eligible signed net of **£9,769,872.05** across 13 calendar months. Source hash, row count, eligible count, raw/eligible/positive/negative amounts and every monthly row count and amount match the separately generated audit. The current result is in `sales_sql_demo.json`.

The top stock-code list is **not** a verified ranking of merchandise products: codes may include postage or other charges. The United Kingdom dominates the country totals in this dataset, so country comparisons also need context. December 2011 ends on 9 December and is not a full month. These are transaction-line amounts, not cash receipts, profit or proven refunds. Any client database would require its own schema, SQL dialect and agreed definitions for revenue, returns, regions and products before applying these queries.
