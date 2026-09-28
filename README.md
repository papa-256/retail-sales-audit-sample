# UCI Online Retail: reproducible data quality audit

**Public portfolio sample; no client data or paid-client claim.** Source: [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail), Daqing Chen, DOI [10.24432/C5BW33](https://doi.org/10.24432/C5BW33), CC BY 4.0. The source covers 541,909 transaction lines from 2010-12-01 08:26:00 to 2011-12-09 12:50:00. ZIP SHA-256: `f5385cbb54bbebf7196389109c6b0621faab0c304e3702548165e71c84aede8b`. Workbook inside ZIP: `Online Retail.xlsx` (23,715,344 bytes).

## Run

```powershell
New-Item -ItemType Directory -Force work/retail_sample | Out-Null
if (-not (Test-Path work/retail_sample/online_retail.zip)) { Invoke-WebRequest 'https://archive.ics.uci.edu/static/public/352/online%2Bretail.zip' -OutFile work/retail_sample/online_retail.zip }
python retail_data_audit.py --source work/retail_sample/online_retail.zip --out-dir YOUR_NEW_EMPTY_DIRECTORY
```

Requires Python with pandas and openpyxl. The script opens the workbook inside the ZIP without extracting or editing it, verifies the source hash before and after, and creates JSON and Markdown with exclusive file creation. Use a new directory for each rerun.

## Findings

| Check | Count |
| --- | ---: |
| Source rows | 541,909 |
| Missing values | Description 1,454, CustomerID 135,080 |
| Exact duplicate rows (flagged, retained) | 5,268 |
| Invoice numbers beginning C | 9,288 |
| Negative quantity rows | 10,624 |
| Zero quantity rows | 0 |
| Nonpositive unit price rows | 2,517 |
| Absolute quantity above 1,000 (review flag) | 174 |
| Positive-price, nonzero-quantity analysis rows | 539,392 |

| Amount definition | GBP |
| --- | ---: |
| All numeric source lines, quantity × unit price | £9,747,747.93 |
| Analysis net: positive-price, nonzero-quantity lines | £9,769,872.05 |
| Positive-quantity sales component | £10,666,684.54 |
| Negative-quantity offset component | -£896,812.49 |
| Excluded line amount (raw minus analysis net) | -£22,124.12 |

The positive and negative components sum to the analysis net. The excluded amount reconciles that net to the raw source amount. Each line is rounded to pence using decimal half-up arithmetic before summing. Missing CustomerID is left missing. Exact duplicate lines are retained because the columns do not provide a unique line key. Cancel-prefixed invoices and negative quantities remain in the net; neither proves the reason for an individual return. Nonpositive prices and zero quantities remain in the source and are only excluded from the stated analysis net. Quantity above 1,000 is a review flag, not a deletion rule.

## Monthly analysis totals

| Month | Analysis rows | Net GBP |
| --- | ---: | ---: |
| 2010-12 | 42,208 | £748,957.02 |
| 2011-01 | 35,007 | £560,000.26 |
| 2011-02 | 27,580 | £498,062.65 |
| 2011-03 | 36,502 | £683,267.08 |
| 2011-04 | 29,655 | £493,207.12 |
| 2011-05 | 36,785 | £723,333.51 |
| 2011-06 | 36,688 | £691,123.12 |
| 2011-07 | 39,330 | £681,300.11 |
| 2011-08 | 35,151 | £704,804.63 |
| 2011-09 | 50,066 | £1,019,687.62 |
| 2011-10 | 60,504 | £1,070,704.67 |
| 2011-11 | 84,445 | £1,461,756.25 |
| 2011-12 | 25,471 | £433,668.01 |

December 2011 ends on 9 December, so its total must not be compared as a full month. These are transaction-line amounts, not profit, realized cash, or verified refunds. All assertions passed: source unchanged, row and amount partitions, and independent invoice and monthly reconciliations.

中文摘要：这是公开数据的作品样本，并非客户项目或已获得收入。保留取消单、负数量、重复行与缺失客户编号；正价非零数量行的净额与正销售、负数量冲销逐分核对。2011 年 12 月仅含前 9 天，不能按完整月份比较。

## SQL companion sample

`sales_sql_demo.py` loads the same public workbook into an in-memory SQLite table and uses SQL to group signed transaction amounts by month, country and stock code. The 541,909-row result reconciles to the independent Python audit down to each monthly penny. Read `sales_sql_demo.md` for the run command and limits, and `sales_sql_demo.json` for the full result. The stock-code list is not a verified ranking of merchandise products; it can contain charges. This remains a self-initiated public-data example, not a customer project.

## Request a scoped CSV/XLSX cleanup

Reference scope: **USD 75** for one dataset supplied as up to two CSV/XLSX files, at most 500,000 rows in total and 20 columns. After the inputs, cleaning rules and schedule are agreed, the proposed delivery is two working days: a cleaned export, runnable Python notebook, quality/change log, up to three exploratory charts and a short findings summary. One correction round within the agreed scope is included. External paid APIs and ongoing maintenance are outside this offer.

For a scope request, open a GitHub issue with the file format, approximate row/column counts, the three questions you want answered and your deadline. **Issues are public: do not upload private datasets, personal records, credentials or confidential links.** Data transfer, availability, final terms and payment method must be agreed separately before any order starts. An inquiry is not an accepted order; no payment is requested at this stage.

The work uses AI-assisted coding and executable checks. Missing values, duplicate-looking transactions and returns are handled under agreed rules, not silently discarded. This public UCI sample demonstrates the approach; it is not a paid-client testimonial or a guarantee of business outcomes.

中文：可在 GitHub issue 中说明文件格式、约略行列数、需要解答的问题和交期，用于确认服务范围。请勿公开私人数据、账号密码或客户资料；实际接单、交期与付款方式另行确认。
