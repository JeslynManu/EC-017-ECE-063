
def detect_shortages(data):
    """Identify branches where stock is below minimum."""

    shortages = []

    for key, current_stock in data["stock"].items():
        limits = data["limits"][key]

        minimum = limits["min_stock"]
        maximum = limits["max_stock"]

        if current_stock < minimum:
            shortage_quantity = maximum - current_stock

            shortages.append({
                "branch_id": key[0],
                "sku_code": key[1],
                "current_stock": current_stock,
                "min_stock": minimum,
                "max_stock": maximum,
                "shortage_quantity": shortage_quantity
            })

    return shortages


def detect_surpluses(data):
    """Identify branches where stock is above maximum."""

    surpluses = []

    for key, current_stock in data["stock"].items():
        limits = data["limits"][key]

        minimum = limits["min_stock"]
        maximum = limits["max_stock"]

        if current_stock > maximum:
            surplus_quantity = current_stock - maximum

            surpluses.append({
                "branch_id": key[0],
                "sku_code": key[1],
                "current_stock": current_stock,
                "min_stock": minimum,
                "max_stock": maximum,
                "surplus_quantity": surplus_quantity
            })

    return surpluses


def analyse_stock(data):
    """Run shortage and surplus detection."""

    shortages = detect_shortages(data)
    surpluses = detect_surpluses(data)

    return shortages, surpluses


def allocate_transfers(data, shortages):
    """Allocate surplus stock to shortage branches."""

    updated_stock = data["stock"].copy()

    transfers = []
    remaining_needs = []

    for shortage in shortages:

        destination = shortage["branch_id"]
        sku = shortage["sku_code"]
        remaining_need = shortage["shortage_quantity"]

        pack_size = data["sku_master"][sku]["pack_size"]
        unit_cost = data["sku_master"][sku]["unit_cost"]

        candidates = []

        for (source, source_sku), quantity in updated_stock.items():

            if source_sku != sku or source == destination:
                continue

            source_max = data["limits"][(source, sku)]["max_stock"]
            available_surplus = quantity - source_max

            if available_surplus > 0:

                distance = data["distances"].get(
                    (destination, source),
                    float("inf")
                )

                candidates.append({
                    "branch_id": source,
                    "distance": distance,
                    "available": available_surplus
                })

        candidates.sort(
            key=lambda item: (
                item["distance"],
                item["branch_id"]
            )
        )

        for candidate in candidates:

            if remaining_need <= 0:
                break

            source = candidate["branch_id"]
            available = candidate["available"]

            possible_quantity = min(
                available,
                remaining_need
            )

            transfer_quantity = (
                possible_quantity // pack_size
            ) * pack_size

            if transfer_quantity <= 0:
                continue

            transfer_value = transfer_quantity * unit_cost

            # Reject only when BOTH conditions are true
            if (
                transfer_value < 500
                and candidate["distance"] > 50
            ):
                continue

            updated_stock[(source, sku)] -= transfer_quantity
            updated_stock[(destination, sku)] += transfer_quantity

            remaining_need -= transfer_quantity

            transfers.append({
                "source": source,
                "destination": destination,
                "sku_code": sku,
                "quantity": transfer_quantity,
                "distance": candidate["distance"],
                "transfer_value": transfer_value
            })

        remaining_needs.append({
            "branch_id": destination,
            "sku_code": sku,
            "remaining_need": remaining_need
        })

    return transfers, remaining_needs, updated_stock


def calculate_average_daily_sales(data):
    """Calculate average daily sales over seven days."""

    averages = {}

    for key, records in data["sales"].items():

        total_sales = sum(
            record["quantity_sold"]
            for record in records
        )

        averages[key] = total_sales / 7

    return averages


def calculate_days_of_cover(data, average_sales):
    """Calculate how many days current stock will last."""

    days_of_cover = {}

    for key, quantity in data["stock"].items():

        average = average_sales.get(key, 0)

        if average == 0:
            days_of_cover[key] = float("inf")
        else:
            days_of_cover[key] = quantity / average

    return days_of_cover


def identify_fast_movers(average_sales):
    """Identify products selling more than 20 units per day."""

    fast_movers = []

    for key, average in average_sales.items():

        if average > 20:
            fast_movers.append(key)

    return fast_movers


def prioritise_shortages(shortages, days_of_cover):
    """Prioritise shortages by lowest days of cover."""

    return sorted(
        shortages,
        key=lambda item: (
            days_of_cover.get(
                (item["branch_id"], item["sku_code"]),
                float("inf")
            ),
            item["branch_id"]
        )
    )


def apply_fast_mover_limits(data, average_sales):
    """Double minimum stock for fast movers for this run only."""

    adjusted_limits = {
        key: values.copy()
        for key, values in data["limits"].items()
    }

    for key, average in average_sales.items():

        if average > 20 and key in adjusted_limits:
            adjusted_limits[key]["min_stock"] *= 2

    return adjusted_limits
