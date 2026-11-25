"""
Store Health Report – UK Online Retailer (Online Retail II)
Author: Ali Usman (Finrows)

Builds the aggregated tables in ../data from the raw transactions.

Raw data (not included in this repo):
  - Kaggle:  https://www.kaggle.com/datasets/mashlyn/online-retail-ii-uci  (online_retail_II.csv)
  - UCI:     https://archive.ics.uci.edu/dataset/502/online+retail+ii       (online_retail_II.xlsx)

Usage:
  python analysis/store_health.py path/to/online_retail_II.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "data"

# Non-product lines: postage, fees, manual adjustments, tests
NON_PRODUCT = ["POST", "DOT", "M", "BANK CHARGES", "AMAZONFEE", "ADJUST", "ADJUST2",
               "D", "CRUK", "C2", "PADS", "B", "TEST001", "TEST002", "S"]
# One data-entry error: a 74,215-unit order cancelled 16 minutes later (Jan 2011)
BAD_INVOICES = ["541431", "C541433"]
CUTOFF = "2011-12-01"           # drop the partial month of Dec 2011
YEAR_SPLIT = "2010-12-01"       # 12 months before vs last 12 months
REFERENCE_DATE = pd.Timestamp("2011-12-01")


def load(path: str) -> pd.DataFrame:
    if path.endswith(".xlsx"):
        df = pd.concat(pd.read_excel(path, sheet_name=None).values(), ignore_index=True)
    else:
        df = pd.read_csv(path, encoding="ISO-8859-1")
    df = df.rename(columns={"Customer ID": "CustomerID", "InvoiceNo": "Invoice", "UnitPrice": "Price"})
    df["Invoice"] = df["Invoice"].astype(str)
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df[~df.Invoice.isin(BAD_INVOICES)]
    df = df[~df.StockCode.astype(str).isin(NON_PRODUCT) & (df.Price > 0) & (df.InvoiceDate < CUTOFF)].copy()
    df["Line"] = df.Quantity * df.Price
    df["IsRefund"] = df.Invoice.str.startswith("C")
    df["Month"] = df.InvoiceDate.dt.strftime("%Y-%m")
    df["Period"] = np.where(df.InvoiceDate < YEAR_SPLIT, "Dec 2009 – Nov 2010", "Dec 2010 – Nov 2011")
    return df


def segment(r) -> str:
    if r.rec <= 60 and r.orders >= 5:
        return "Champions"
    if r.rec <= 60 and r.orders >= 2:
        return "Loyal / growing"
    if r.rec <= 60:
        return "Recent one-time buyers"
    if r.rec <= 180 and r.orders >= 5:
        return "At-risk VIPs"
    if r.rec <= 180:
        return "Cooling off"
    return "Lost (6+ months quiet)"


def main(path: str) -> None:
    df = clean(load(path))
    sales = df[~df.IsRefund & (df.Quantity > 0)]
    refunds = df[df.IsRefund]
    last = "Dec 2010 – Nov 2011"

    # 1. Yearly KPIs
    rows = []
    for p in ["Dec 2009 – Nov 2010", last]:
        s, r = sales[sales.Period == p], refunds[refunds.Period == p]
        gross, ref = s.Line.sum(), -r.Line.sum()
        rows.append(dict(period=p, gross_sales=round(gross), refunds=round(ref), net_sales=round(gross - ref),
                         orders=s.Invoice.nunique(), customers=int(s.CustomerID.nunique()),
                         avg_order_value=round(s.groupby("Invoice").Line.sum().mean(), 2),
                         refund_rate_pct=round(ref / gross * 100, 2)))
    pd.DataFrame(rows).to_csv(OUT / "yearly_kpis.csv", index=False)

    # 2. Monthly sales and refunds
    m = sales.groupby("Month").Line.sum().round()
    mr = (-refunds.groupby("Month").Line.sum()).round().reindex(m.index).fillna(0)
    pd.DataFrame({"month": m.index, "sales": m.values.astype(int), "refunds": mr.values.astype(int)}) \
        .to_csv(OUT / "monthly_sales.csv", index=False)

    # 3. Products (last 12 months)
    s2, r2 = sales[sales.Period == last], refunds[refunds.Period == last]
    prod = s2.groupby("Description").agg(revenue=("Line", "sum"), units=("Quantity", "sum")) \
        .sort_values("revenue", ascending=False)
    top = prod.head(10).reset_index().rename(columns={"Description": "product"})
    top["revenue"] = top.revenue.round().astype(int)
    top["units"] = top.units.astype(int)
    top.to_csv(OUT / "top_products.csv", index=False)

    rp = (-r2.groupby("Description").Line.sum()).sort_values(ascending=False).head(10)
    leaks = pd.DataFrame({"product": rp.index, "refunded": rp.values.round().astype(int),
                          "sales": prod.revenue.reindex(rp.index).fillna(0).round().astype(int).values})
    leaks["refund_pct"] = (leaks.refunded / leaks.sales.replace(0, np.nan) * 100).round(1)
    leaks.to_csv(OUT / "refund_leaks.csv", index=False)

    # 4. Customer groups (recency / frequency)
    known = sales.dropna(subset=["CustomerID"])
    cu = known.groupby("CustomerID").agg(rev=("Line", "sum"), orders=("Invoice", "nunique"),
                                         last=("InvoiceDate", "max"), first=("InvoiceDate", "min"))
    cu["rec"] = (REFERENCE_DATE - cu["last"]).dt.days
    cu["segment"] = cu.apply(segment, axis=1)
    months_active = ((cu["last"] - cu["first"]).dt.days / 30.4).clip(lower=1)
    cu["monthly_spend"] = cu.rev / months_active
    order = ["Champions", "Loyal / growing", "Recent one-time buyers", "At-risk VIPs", "Cooling off",
             "Lost (6+ months quiet)"]
    sg = cu.groupby("segment").agg(customers=("rev", "size"), two_year_revenue=("rev", "sum"),
                                   avg_orders=("orders", "mean"), avg_days_since_last_order=("rec", "mean"),
                                   monthly_spend_when_active=("monthly_spend", "sum")).reindex(order).reset_index()
    sg["two_year_revenue"] = sg.two_year_revenue.round().astype(int)
    sg["monthly_spend_when_active"] = sg.monthly_spend_when_active.round().astype(int)
    sg["avg_orders"] = sg.avg_orders.round(1)
    sg["avg_days_since_last_order"] = sg.avg_days_since_last_order.round().astype(int)
    sg.to_csv(OUT / "customer_segments.csv", index=False)

    # 5. Revenue concentration (last 12 months)
    cr = known[known.Period == last].groupby("CustomerID").Line.sum().sort_values(ascending=False)
    n, k = len(cr), int(len(cr) * 0.1)
    pd.DataFrame([
        {"group": "Top 10% of customers", "customers": k, "revenue_share_pct": round(cr.head(k).sum() / cr.sum() * 100, 1)},
        {"group": "Other 90%", "customers": n - k, "revenue_share_pct": round(cr.iloc[k:].sum() / cr.sum() * 100, 1)},
    ]).to_csv(OUT / "customer_concentration.csv", index=False)

    # 6. New customers per month (first purchase seen in the data)
    first = known.groupby("CustomerID").InvoiceDate.min().dt.strftime("%Y-%m").value_counts().sort_index()
    nc = pd.DataFrame({"month": first.index, "new_customers": first.values})
    nc[nc.month >= "2010-07"].to_csv(OUT / "new_customers.csv", index=False)

    print("Tables written to", OUT)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
