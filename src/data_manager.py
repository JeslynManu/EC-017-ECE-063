
import csv
from pathlib import Path
from datetime import date

# Locate the data folder
DATA_FOLDER = Path(__file__).resolve().parent.parent / "data"


def read_csv(filename):
    """Read a CSV file and return rows as dictionaries."""

    filepath = DATA_FOLDER / filename

    if not filepath.exists():
        raise FileNotFoundError(f"Missing input file: {filename}")

    with open(filepath, "r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError(f"{filename} is empty or has no header.")

        return list(reader)


def required_value(row, column, filename):
    """Check that a required CSV field is not empty."""

    value = row.get(column)

    if value is None or not value.strip():
        raise ValueError(
            f"{filename}: Missing value in column '{column}'."
        )

    return value.strip()


def load_branches():
    """Load branch IDs and names."""

    rows = read_csv("branches.csv")
    branches = {}

    for row in rows:
        branch_id = required_value(row, "branch_id", "branches.csv")
        branch_name = required_value(row, "branch_name", "branches.csv")

        if branch_id in branches:
            raise ValueError(f"Duplicate branch ID: {branch_id}")

        branches[branch_id] = branch_name

    return branches


def load_distances():
    """Load distances and make them accessible in both directions."""

    rows = read_csv("distances.csv")
    distances = {}
    seen_pairs = set()

    for row in rows:
        branch1 = required_value(row, "from_branch", "distances.csv")
        branch2 = required_value(row, "to_branch", "distances.csv")

        distance = float(
            required_value(row, "distance_km", "distances.csv")
        )

        if branch1 == branch2:
            raise ValueError("A branch cannot have a distance to itself.")

        pair = frozenset((branch1, branch2))

        if pair in seen_pairs:
            raise ValueError(
                f"Duplicate distance pair: {branch1}, {branch2}"
            )

        if distance < 0:
            raise ValueError("Distance cannot be negative.")

        seen_pairs.add(pair)

        distances[(branch1, branch2)] = distance
        distances[(branch2, branch1)] = distance

    return distances


def load_sku_master():
    """Load product costs and pack sizes."""

    rows = read_csv("sku_master.csv")
    sku_master = {}

    for row in rows:
        sku = required_value(row, "sku_code", "sku_master.csv")

        if sku in sku_master:
            raise ValueError(f"Duplicate SKU code: {sku}")

        unit_cost = float(
            required_value(row, "unit_cost", "sku_master.csv")
        )

        pack_size = int(
            required_value(row, "pack_size", "sku_master.csv")
        )

        if unit_cost < 0:
            raise ValueError(f"Negative unit cost: {sku}")

        if pack_size <= 0:
            raise ValueError(f"Invalid pack size: {sku}")

        sku_master[sku] = {
            "unit_cost": unit_cost,
            "pack_size": pack_size
        }

    return sku_master


def load_limits():
    """Load minimum and maximum stock limits."""

    rows = read_csv("branch_sku_limits.csv")
    limits = {}

    for row in rows:
        key = (
            required_value(row, "branch_id", "branch_sku_limits.csv"),
            required_value(row, "sku_code", "branch_sku_limits.csv")
        )

        if key in limits:
            raise ValueError(f"Duplicate stock limit entry: {key}")

        minimum = int(
            required_value(row, "min_stock", "branch_sku_limits.csv")
        )

        maximum = int(
            required_value(row, "max_stock", "branch_sku_limits.csv")
        )

        if minimum < 0:
            raise ValueError(f"Negative minimum stock: {key}")

        if maximum < minimum:
            raise ValueError(f"Maximum stock below minimum: {key}")

        limits[key] = {
            "min_stock": minimum,
            "max_stock": maximum
        }

    return limits


def load_stock():
    """Load current stock quantities and detect duplicates."""

    rows = read_csv("stock.csv")
    stock = {}

    for row in rows:
        key = (
            required_value(row, "branch_id", "stock.csv"),
            required_value(row, "sku_code", "stock.csv")
        )

        if key in stock:
            raise ValueError(f"Duplicate stock entry: {key}")

        quantity = int(
            required_value(row, "quantity", "stock.csv")
        )

        if quantity < 0:
            raise ValueError(f"Negative stock quantity: {key}")

        stock[key] = quantity

    return stock


def load_sales():
    """Load sales history for each branch and product."""

    rows = read_csv("sales.csv")
    sales = {}
    seen_dates = set()

    for row in rows:
        key = (
            required_value(row, "branch_id", "sales.csv"),
            required_value(row, "sku_code", "sales.csv")
        )

        raw_date = required_value(row, "date", "sales.csv")

        try:
            sale_date = date.fromisoformat(raw_date)
        except ValueError:
            raise ValueError(
                f"Invalid sales date: {raw_date}. Use YYYY-MM-DD."
            )

        date_key = (key, sale_date)

        if date_key in seen_dates:
            raise ValueError(
                f"Duplicate sales date: {sale_date} for {key}"
            )

        seen_dates.add(date_key)

        quantity = int(
            required_value(row, "quantity_sold", "sales.csv")
        )

        if quantity < 0:
            raise ValueError(f"Negative sales quantity: {key}")

        if key not in sales:
            sales[key] = []

        sales[key].append({
            "date": raw_date,
            "quantity_sold": quantity
        })

    # Keep sales records in chronological order
    for records in sales.values():
        records.sort(key=lambda item: item["date"])

    return sales


def load_reorders():
    """Load existing supplier reorder records."""

    rows = read_csv("reorders.csv")
    reorders = {}

    for row in rows:
        key = (
            required_value(row, "branch_id", "reorders.csv"),
            required_value(row, "sku_code", "reorders.csv")
        )

        quantity = int(
            required_value(row, "reorder_quantity", "reorders.csv")
        )

        status = required_value(
            row, "status", "reorders.csv"
        ).upper()

        if quantity < 0:
            raise ValueError(f"Negative reorder quantity: {key}")

        if status not in ("OPEN", "CLOSED"):
            raise ValueError(f"Invalid reorder status: {key}")

        if key not in reorders:
            reorders[key] = []

        reorders[key].append({
            "reorder_quantity": quantity,
            "status": status
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
    """Validate the loaded project data and cross-file references."""

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

    # 4. Check stock and limits consistency
    if set(stock.keys()) != set(limits.keys()):
        errors.append("Stock and limits entries do not match.")

    # 5. Validate distances
    for (branch1, branch2), distance in distances.items():

        if branch1 not in branches or branch2 not in branches:
            errors.append(
                f"Unknown branch in distance: {branch1}, {branch2}"
            )

        if distance < 0:
            errors.append(
                f"Negative distance: {branch1}, {branch2}"
            )

    # 6. Validate sales records
    for key, records in sales.items():

        branch, sku = key

        if branch not in branches or sku not in sku_master:
            errors.append(f"Invalid sales entry: {key}")

        for record in records:

            if record["quantity_sold"] < 0:
                errors.append(f"Negative sales quantity: {key}")

            try:
                date.fromisoformat(record["date"])
            except ValueError:
                errors.append(f"Invalid sales date: {key}")

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
