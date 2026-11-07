
def detect_shortages(data):
    """
    Identify branch-SKU combinations where stock
    is below the minimum stock level.
    """

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
    """
    Identify branch-SKU combinations where stock
    is above the maximum stock level.
    """

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
