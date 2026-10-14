"""Haalt de Deense marktprijzen (DKK) uit dk.boxrstore.com en schrijft een
koppelbestand voor Channable (join op variant-id).

price_dkk      -> g:price      (normale prijs: compare_at als die hoger is, anders prijs)
sale_price_dkk -> g:sale_price (alleen gevuld als er korting is)
"""
import csv, json, sys, time, urllib.request

BASE = "https://dk.boxrstore.com/products.json?limit=250&page={}"
HEADERS = {
    "Cookie": "localization=DK; cart_currency=DKK",
    "Accept-Language": "da-DK",
    "User-Agent": "Mozilla/5.0 (feed-price-sync)",
}
OUT = sys.argv[1] if len(sys.argv) > 1 else "boxr-dk/prices-dkk.csv"


def fetch(page):
    for attempt in range(5):
        try:
            req = urllib.request.Request(BASE.format(page), headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)["products"]
        except Exception as e:  # 429 / tijdelijke fout: even wachten
            print(f"pagina {page} poging {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(10 * (attempt + 1))
    raise SystemExit(f"pagina {page} niet op te halen")


rows, page = [], 1
while True:
    products = fetch(page)
    if not products:
        break
    for p in products:
        for v in p["variants"]:
            price = float(v["price"])
            compare = float(v["compare_at_price"] or 0)
            if compare > price:
                rows.append([v["id"], f"{compare:.2f}", f"{price:.2f}", p["handle"]])
            else:
                rows.append([v["id"], f"{price:.2f}", "", p["handle"]])
    page += 1
    time.sleep(1)

# sanity check: zonder DK-markt geeft de shop EUR-bedragen (< 150), DKK ligt veel hoger
probe = [float(r[1]) for r in rows if "kob-2-fa-3" in r[3]]
if not rows or not probe or max(probe) < 150:
    raise SystemExit(f"geen DKK-prijzen ontvangen (2+3 = {probe[:1]}), bestand niet overschreven")

rows.sort(key=lambda r: r[0])
with open(OUT, "w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["id", "price_dkk", "sale_price_dkk", "dk_handle"])
    w.writerows(rows)
print(f"{len(rows)} varianten geschreven naar {OUT}")
