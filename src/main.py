
from data_manager import load_data, validate_data
from replenishment import analyse_stock

# Load project data
data = load_data()

# Validate data
is_valid, messages = validate_data(data)

if not is_valid:
    print("DATA VALIDATION FAILED")
    for message in messages:
        print(message)
    raise SystemExit

print("\n===== DATA LOADING SUCCESSFUL =====")

# Analyse stock
shortages, surpluses = analyse_stock(data)

# Display shortages
print("\n===== SHORTAGE REPORT =====")

for item in shortages:
    print(
        f"Branch: {item['branch_id']} | "
        f"SKU: {item['sku_code']} | "
        f"Current: {item['current_stock']} | "
        f"Required: {item['shortage_quantity']}"
    )

# Display surpluses
print("\n===== SURPLUS REPORT =====")

for item in surpluses:
    print(
        f"Branch: {item['branch_id']} | "
        f"SKU: {item['sku_code']} | "
        f"Current: {item['current_stock']} | "
        f"Available: {item['surplus_quantity']}"
    )

print("\nStock analysis completed!")
