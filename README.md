# Store Health Report – UK Online Retailer

**Live report:** https://alikhokharak.github.io/finrows-store-report/

An e-commerce "store health" analysis of 1M+ real transactions from a UK online gift retailer (public **Online Retail II** dataset). It answers the questions a store owner actually asks: *Are we really growing? Where are customers leaking? Which products are costing us in refunds?*

## Key findings (Dec 2010 – Nov 2011 vs the 12 months before)

| | Result |
|---|---|
| Net sales | **+6.1%** (£9.75M) |
| Orders | **−4.0%**, so growth came only from bigger baskets (AOV +10.3%) |
| New customers, Jul–Nov | **−37.3%** (1,288 → 808) |
| Revenue concentration | Top 10% of customers = **60.3%** of revenue |
| At-risk VIPs | **416** regular buyers (avg 9 orders) quiet for ~105 days |
| Refund leaks | e.g. Pantry Chopping Board: **82.7%** of its sales refunded |

## What's inside

```
analysis/store_health.py   # cleaning + all aggregations (pandas)
analysis/build_report.py   # charts (matplotlib) + the HTML report
data/                      # aggregated tables used in the report (CSV)
docs/                      # the published web report (GitHub Pages)
```

## Method

- Removed postage, fees, manual adjustments and zero-price lines
- Removed one data-entry error: a 74,215-unit order cancelled 16 minutes later (Jan 2011)
- Refunds = invoices starting with "C"; net sales = gross sales − refunds
- Customer groups by recency and frequency as of 1 Dec 2011 (Champions, Loyal, At-risk VIPs, Cooling off, Lost)
- No cost data in the dataset, so the report covers revenue, not profit

## Reproduce

```bash
pip install -r requirements.txt
# download online_retail_II.csv from Kaggle (mashlyn/online-retail-ii-uci) or the .xlsx from UCI
python analysis/store_health.py path/to/online_retail_II.csv
python analysis/build_report.py
```

## Data source

Chen, D. (2012). *Online Retail II* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D. The raw file is not included in this repo.

---

Built by **Ali Usman** · Finrows · Business Data Analytics (Fintech), COMSATS University Islamabad
[LinkedIn](https://www.linkedin.com/in/ali-usman-5871b8342) · alikhokhar.ak1012@gmail.com
