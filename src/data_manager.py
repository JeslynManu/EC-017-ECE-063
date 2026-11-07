
import csv
from pathlib import Path

# Locate the data folder
DATA_FOLDER = Path(__file__).resolve().parent.parent / "data"


def read_csv(filename):
    """Read a CSV file and return rows as dictionaries."""
    filepath = DATA_FOLDER / filename

    with open(filepath, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader)


def load_branches():
    """Load branch IDs and names."""
    rows = read_csv("branches.csv")
    return {
        row["branch_id"]: row["branch_name"]
        for row in rows
    }


def load_distances():
    """Load distances and make them accessible in both directions."""
    rows = read_csv("distances.csv")
    distances = {}

    for row in rows:
        branch1 = row["from_branch"]
        branch2 = row["to_branch"]
        distance = float(row["distance_km"])

        distances[(branch1, branch2)] = distance
        distances[(branch2, branch1)] = distance

    return distances


def load_sku_master():
    """Load product costs and pack sizes."""
    rows = read_csv("sku_master.csv")

    return {
        row["sku_code"]: {
            "unit_cost": float(row["unit_cost"]),
            "pack_size": int(row["pack_size"])
        }
        for row in rows
    }


def load_limits():
    """Load minimum and maximum stock limits."""
    rows = read_csv("branch_sku_limits.csv")

    return {
        (row["branch_id"], row["sku_code"]): {
            "min_stock": int(row["min_stock"]),
            "max_stock": int(row["max_stock"])
        }
        for row in rows
    }


def load_stock():
    """Load current stock quantities."""
    rows = read_csv("stock.csv")

    return {
        (row["branch_id"], row["sku_code"]): int(row["quantity"])
        for row in rows
    }


def load_sales():
    """Load sales history for each branch and product."""
    rows = read_csv("sales.csv")
    sales = {}

    for row in rows:
        key = (row["branch_id"], row["sku_code"])

        if key not in sales:
            sales[key] = []

        sales[key].append({
            "date": row["date"],
            "quantity_sold": int(row["quantity_sold"])
        })

    return sales


def load_reorders():
    """Load existing supplier reorder records."""
    rows = read_csv("reorders.csv")
    reorders = {}

    for row in rows:
        key = (row["branch_id"], row["sku_code"])

        if key not in reorders:
            reorders[key] = []

        reorders[key].append({
            "reorder_quantity": int(row["reorder_quantity"]),
            "status": row["status"].strip().upper()
        })

    return reorders


def load_data():
    """Load all project data into one dictionary."""
    data = {
        "branches": load_branches(),
        "distances": load_distances(),
        "sku_master": load_sku_master(),
        "limits": load_limits(),
        "stock": load_stock(),
        "sales": load_sales(),
        "reorders": load_reorders()
    }

    return data



def validate_data(data):
    """Validate the loaded project data."""
    errors = []

    branches = data["branches"]
    sku_master = data["sku_master"]
    limits = data["limits"]
    stock = data["stock"]
    distances = data["distances"]
    sales = data["sales"]
    reorders = data["reorders"]

    # 1. Validate product information
    for sku, details in sku_master.items():
        if details["unit_cost"] < 0:
            errors.append(f"Negative unit cost: {sku}")

        if details["pack_size"] <= 0:
            errors.append(f"Invalid pack size: {sku}")

    # 2. Validate stock limits
    for key, values in limits.items():
        branch, sku = key

        if branch not in branches:
            errors.append(f"Unknown branch in limits: {branch}")

        if sku not in sku_master:
            errors.append(f"Unknown SKU in limits: {sku}")

        if values["min_stock"] < 0:
            errors.append(f"Negative minimum stock: {key}")

        if values["max_stock"] < values["min_stock"]:
            errors.append(f"Maximum below minimum: {key}")

    # 3. Validate stock quantities
    for key, quantity in stock.items():
        branch, sku = key

        if branch not in branches:
            errors.append(f"Unknown branch in stock: {branch}")

        if sku not in sku_master:
            errors.append(f"Unknown SKU in stock: {sku}")

        if quantity < 0:
            errors.append(f"Negative stock quantity: {key}")

    # 4. Check that stock and limits have matching entries
    if set(stock.keys()) != set(limits.keys()):
        errors.append("Stock and limits entries do not match.")

    # 5. Validate distances
    for (branch1, branch2), distance in distances.items():
        if branch1 not in branches or branch2 not in branches:
            errors.append(f"Unknown branch in distance: {branch1}, {branch2}")

        if distance < 0:
            errors.append(f"Negative distance: {branch1}, {branch2}")

    # 6. Validate sales records
    for key, records in sales.items():
        branch, sku = key

        if branch not in branches or sku not in sku_master:
            errors.append(f"Invalid sales entry: {key}")

        for record in records:
            if record["quantity_sold"] < 0:
                errors.append(f"Negative sales quantity: {key}")

    # 7. Validate reorder records
    for key, records in reorders.items():
        branch, sku = key

        if branch not in branches or sku not in sku_master:
            errors.append(f"Invalid reorder entry: {key}")

        for record in records:
            if record["reorder_quantity"] < 0:
                errors.append(f"Negative reorder quantity: {key}")

            if record["status"] not in ("OPEN", "CLOSED"):
                errors.append(f"Invalid reorder status: {key}")

    if errors:
        return False, errors

    return True, ["All data validations passed."]
