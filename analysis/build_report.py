"""Builds the web report (docs/index.html + charts) from the tables in ../data."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D, DOCS = ROOT / "data", ROOT / "docs"
IMG = DOCS
IMG.mkdir(parents=True, exist_ok=True)

BLUE, TEAL, GREY, RED, INK = "#2563eb", "#0d9488", "#cbd5e1", "#dc2626", "#0f172a"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": "#94a3b8", "axes.labelcolor": INK,
                     "xtick.color": "#475569", "ytick.color": "#475569"})

k = pd.read_csv(D / "yearly_kpis.csv")
m = pd.read_csv(D / "monthly_sales.csv")
nc = pd.read_csv(D / "new_customers.csv")
sg = pd.read_csv(D / "customer_segments.csv")
cc = pd.read_csv(D / "customer_concentration.csv")
rl = pd.read_csv(D / "refund_leaks.csv")
tp = pd.read_csv(D / "top_products.csv")

prior, last = k.iloc[0], k.iloc[1]
chg = lambda c: (last[c] / prior[c] - 1) * 100
net_chg, ord_chg, aov_chg, cust_chg = chg("net_sales"), chg("orders"), chg("avg_order_value"), chg("customers")
ref_pts = last.refund_rate_pct - prior.refund_rate_pct
win = lambda y: nc[(nc.month >= f"{y}-07") & (nc.month <= f"{y}-11")].new_customers.sum()
nc10, nc11 = win(2010), win(2011)
nc_chg = (nc11 / nc10 - 1) * 100
risk = sg.set_index("segment").loc["At-risk VIPs"]
winback = risk.monthly_spend_when_active * 0.2
top10 = cc.set_index("group").loc["Top 10% of customers"]
pantry = rl.set_index("product").loc["PANTRY CHOPPING BOARD"]


def label(mo):
    return pd.to_datetime(mo).strftime("%b %y")


# Chart 1: monthly sales
fig, ax = plt.subplots(figsize=(9, 3.4), dpi=150)
colors = [BLUE if mo[5:] in ("09", "10", "11") else GREY for mo in m.month]
ax.bar(range(len(m)), m.sales / 1e6, color=colors)
ax.set_xticks(range(0, len(m), 3), [label(x) for x in m.month[::3]])
ax.set_ylabel("Gross sales (£ million)")
ax.grid(axis="y", color="#e2e8f0"); ax.set_axisbelow(True)
fig.tight_layout(); fig.savefig(IMG / "monthly_sales.png"); plt.close(fig)

# Chart 2: new customers
fig, ax = plt.subplots(figsize=(9, 3.2), dpi=150)
inwin = nc.month.str[5:].isin(["07", "08", "09", "10", "11"])
colors = [GREY if not w else (TEAL if mo < "2011" else BLUE) for mo, w in zip(nc.month, inwin)]
bars = ax.bar(range(len(nc)), nc.new_customers, color=colors)
for b, v, w in zip(bars, nc.new_customers, inwin):
    if w:
        ax.text(b.get_x() + b.get_width() / 2, v + 4, str(v), ha="center", fontsize=8, color="#475569")
ax.set_xticks(range(0, len(nc), 2), [label(x) for x in nc.month[::2]])
ax.set_ylabel("New customers")
ax.grid(axis="y", color="#e2e8f0"); ax.set_axisbelow(True)
fig.tight_layout(); fig.savefig(IMG / "new_customers.png"); plt.close(fig)

# Chart 3: customer groups
fig, ax = plt.subplots(figsize=(9, 3.4), dpi=150)
s = sg.iloc[::-1]
cols = [RED if x == "At-risk VIPs" else BLUE for x in s.segment]
ax.barh(s.segment, s.two_year_revenue / 1e6, color=cols)
for i, (v, n) in enumerate(zip(s.two_year_revenue, s.customers)):
    ax.text(v / 1e6 + 0.1, i, f"£{v/1e6:.2f}M · {n:,} customers", va="center", fontsize=9, color="#334155")
ax.set_xlabel("Two-year revenue (£ million)")
ax.set_xlim(0, s.two_year_revenue.max() / 1e6 * 1.45)
fig.tight_layout(); fig.savefig(IMG / "customer_groups.png"); plt.close(fig)


def sign(v, d=1, unit="%"):
    return f"{'+' if v > 0 else '−' if v < 0 else ''}{abs(v):.{d}f}{unit}"


def cls(v, good_up=True):
    return "good" if (v > 0) == good_up else "bad"


def rows(df, cols, fmt):
    out = []
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            text, klass = fmt.get(c, lambda x: (str(x), ""))(v)
            cells.append(f'<td class="{klass}">{text}</td>')
        out.append("<tr>" + "".join(cells) + "</tr>")
    return "\n".join(out)


gbp = lambda v: (f"£{v:,.0f}", "n")
leak_rows = rows(rl, ["product", "refunded", "sales", "refund_pct"],
                 {"product": lambda x: (x.title(), ""), "refunded": gbp, "sales": gbp,
                  "refund_pct": lambda x: (f"{x:.1f}%", "n hot" if x >= 25 else "n")})
top_rows = rows(tp, ["product", "revenue", "units"],
                {"product": lambda x: (x.title(), ""), "revenue": gbp, "units": lambda x: (f"{x:,}", "n")})

html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Store Health Report – UK Online Retailer | Finrows</title>
<meta name="description" content="Sample e-commerce store health report by Finrows on the public UCI Online Retail II dataset.">
<style>
:root{{--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--panel:#f8fafc;--blue:#2563eb;--good:#16a34a;--bad:#dc2626}}
*{{box-sizing:border-box}} body{{margin:0;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:#fff;line-height:1.55}}
.wrap{{max-width:980px;margin:0 auto;padding:32px 20px 60px}}
.brand{{font-size:12px;letter-spacing:.14em;font-weight:700;color:var(--blue);text-transform:uppercase}}
h1{{font-family:Georgia,serif;font-weight:400;font-size:clamp(28px,5vw,40px);line-height:1.15;margin:8px 0}}
.sub{{color:var(--muted);margin:0 0 22px}} .lead{{font-size:clamp(17px,2.4vw,20px);margin:0 0 26px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:30px}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}}
.card h3{{margin:0;font-size:12px;color:var(--muted);font-weight:600}} .big{{font-family:Georgia,serif;font-size:26px;margin:6px 0 2px}}
.chg{{font-size:13px;color:var(--muted)}} .good{{color:var(--good);font-weight:600}} .bad{{color:var(--bad);font-weight:600}}
h2{{font-size:20px;margin:36px 0 6px}} .note{{color:var(--muted);margin:0 0 12px}} .note b{{color:var(--ink)}}
img{{width:100%;height:auto;border:1px solid var(--line);border-radius:10px}}
.tw{{overflow-x:auto}} table{{width:100%;border-collapse:collapse;font-size:14px}}
th{{text-align:left;font-size:12px;color:var(--muted);border-bottom:1px solid var(--line);padding:6px 8px}} td{{border-bottom:1px solid var(--line);padding:7px 8px}}
td.n,th.n{{text-align:right;font-variant-numeric:tabular-nums}} td.hot{{color:var(--bad);font-weight:600}}
ol.recs{{list-style:none;padding:0;display:grid;gap:12px}} ol.recs li{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}}
ol.recs h4{{margin:0 0 4px}} .cta{{margin-top:30px;padding:18px;border-radius:12px;background:#eff6ff;border:1px solid #bfdbfe}}
details{{margin-top:22px;color:var(--muted)}} summary{{cursor:pointer;color:var(--ink)}} a{{color:var(--blue)}}
footer{{margin-top:30px;font-size:13px;color:var(--muted)}}
</style></head><body><div class="wrap">
<div class="brand">Finrows · Sample store health report</div>
<h1>UK online gift retailer: where growth came from, and where it is leaking</h1>
<p class="sub">Real, anonymised transactions of a UK online store (public UCI "Online Retail II" dataset). Last 12 months = Dec 2010 – Nov 2011, compared with the 12 months before. Amounts in GBP.</p>
<p class="lead">Net sales grew <b>{sign(net_chg)}</b>, but only because orders got bigger: the number of orders fell <b>{abs(ord_chg):.1f}%</b> and first-time customers in Jul–Nov fell <b>{abs(nc_chg):.1f}%</b>. The store now leans on a small group of loyal buyers, and <b>{int(risk.customers):,}</b> of its regulars have gone quiet.</p>

<div class="kpis">
<div class="card"><h3>Net sales (after refunds)</h3><div class="big">£{last.net_sales:,.0f}</div><div class="chg"><span class="{cls(net_chg)}">{sign(net_chg)}</span> vs prior 12 months</div></div>
<div class="card"><h3>Orders</h3><div class="big">{last.orders:,}</div><div class="chg"><span class="{cls(ord_chg)}">{sign(ord_chg)}</span> vs prior 12 months</div></div>
<div class="card"><h3>Average order value</h3><div class="big">£{last.avg_order_value:,.2f}</div><div class="chg"><span class="{cls(aov_chg)}">{sign(aov_chg)}</span> vs prior 12 months</div></div>
<div class="card"><h3>Known customers who ordered</h3><div class="big">{last.customers:,}</div><div class="chg"><span class="{cls(cust_chg)}">{sign(cust_chg)}</span> vs prior 12 months</div></div>
<div class="card"><h3>Refund rate</h3><div class="big">{last.refund_rate_pct:.2f}%</div><div class="chg"><span class="{cls(ref_pts, False)}">{sign(ref_pts, 2, ' pts')}</span> vs prior 12 months</div></div>
</div>

<h2>Monthly sales: a strong Sep–Nov peak both years</h2>
<p class="note">Gross sales by month; peak months in blue.</p>
<img src="monthly_sales.png" alt="Bar chart of monthly gross sales, Dec 2009 to Nov 2011">

<h2>Finding 1 · New customers are drying up</h2>
<p class="note">First-time buyers per month. Jul–Nov 2010 brought <b>{nc10:,}</b> new customers; the same months of 2011 brought <b>{nc11:,}</b>. Growth came from existing buyers spending more per order, which cannot last forever.</p>
<img src="new_customers.png" alt="Bar chart of new customers per month">

<h2>Finding 2 · Revenue depends on a few loyal buyers</h2>
<p class="note">The top 10% of customers (<b>{int(top10.customers):,}</b> accounts) brought <b>{top10.revenue_share_pct:.1f}%</b> of last year's revenue from known customers. Below: every customer grouped by how recently and how often they buy.</p>
<img src="customer_groups.png" alt="Horizontal bars of two-year revenue by customer group">

<h2>Finding 3 · Refund leaks by product</h2>
<p class="note">Products with the most money refunded in the last 12 months. A high refunded share usually points to a quality, packaging or description problem.</p>
<div class="tw"><table><thead><tr><th>Product</th><th class="n">Refunded</th><th class="n">Sales</th><th class="n">Refunded share</th></tr></thead><tbody>
{leak_rows}
</tbody></table></div>

<h2>Best sellers, last 12 months</h2>
<div class="tw"><table><thead><tr><th>Product</th><th class="n">Revenue</th><th class="n">Units</th></tr></thead><tbody>
{top_rows}
</tbody></table></div>

<h2>What we would do next</h2>
<ol class="recs">
<li><h4>1. Win back the at-risk VIPs</h4><b>{int(risk.customers):,}</b> customers who averaged <b>{risk.avg_orders:.1f}</b> orders have not ordered for about <b>{int(risk.avg_days_since_last_order)}</b> days. A personal email or call with a reorder offer is cheap. If 20% came back at their old pace, that is about <b>£{winback:,.0f}</b> a month.</li>
<li><h4>2. Fix new-customer acquisition before the next peak</h4>First-time buyers in Jul–Nov changed by <b>{sign(nc_chg)}</b>. Review ad spend, marketplace listings and the first-order offer, and track new customers every month.</li>
<li><h4>3. Protect the top 10%</h4>With <b>{top10.revenue_share_pct:.1f}%</b> of revenue coming from them, losing a few big wholesale buyers would hurt. Give them early access to the Christmas range and a named contact.</li>
<li><h4>4. Check the high-refund products</h4>For example, <b>{pantry.refund_pct:.1f}%</b> of Pantry Chopping Board sales were refunded. Fix the listing or the supplier, or drop the product.</li>
</ol>

<div class="cta"><b>Want this report for your own store or your agency's clients?</b><br>Finrows turns Shopify / e-commerce order exports into monthly reports like this one.<br>Contact Ali Usman · <a href="mailto:alikhokhar.ak1012@gmail.com">alikhokhar.ak1012@gmail.com</a> · <a href="https://www.linkedin.com/in/ali-usman-5871b8342">LinkedIn</a></div>

<details><summary>About the data and method</summary>
<p>Source: "Online Retail II", UCI Machine Learning Repository (Chen, 2012), also on Kaggle. A UK-based online gift-ware retailer whose customers are often wholesalers. Transactions 1 Dec 2009 – 30 Nov 2011 (the partial month of Dec 2011 is left out).</p>
<p>Cleaning: removed postage, bank charges, manual adjustments and zero-price lines; removed one data-entry error in Jan 2011 (a single 74,215-unit order cancelled 16 minutes later). Refunds are invoices starting with "C". Orders without a customer ID (about 15% of last year's sales) count in sales but not in customer figures. "New customers" = first purchase seen in this data. Customer groups use recency and order count as of 1 Dec 2011: Champions = ordered in the last 60 days with 5+ orders; At-risk VIPs = 61–180 days quiet with 5+ orders; Lost = quiet for more than 180 days. No cost data is available, so this report covers revenue, not profit.</p>
<p>Code and tables: <a href="https://github.com/alikhokharak/finrows-store-report">github.com/alikhokharak/finrows-store-report</a></p>
</details>
<footer>© Finrows · Built with Python (pandas, matplotlib)</footer>
</div></body></html>
"""
(DOCS / "index.html").write_text(html, encoding="utf-8")
print("Report written to", DOCS / "index.html")
