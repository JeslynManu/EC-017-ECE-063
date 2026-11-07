import csv
from pathlib import Path

DATA_FOLDER = Path(__file__).resolve().parent.parent / "data"

files = [
    "branches.csv",
    "distances.csv",
    "sku_master.csv",
    "branch_sku_limits.csv",
    "stock.csv",
    "sales.csv",
    "reorders.csv"
]

for filename in files:
    filepath = DATA_FOLDER / filename

    with open(filepath, "r", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    print(f"{filename}: {len(rows)} records loaded successfully")

print("\nAll CSV files tested!")