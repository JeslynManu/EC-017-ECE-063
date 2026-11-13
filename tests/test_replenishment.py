
import unittest

from src.replenishment import (
    detect_shortages,
    detect_surpluses,
    allocate_transfers,
    calculate_average_daily_sales,
    calculate_days_of_cover,
    identify_fast_movers,
    apply_fast_mover_limits
)

from src.reorder_manager import generate_reorders


class TestReplenishment(unittest.TestCase):

    def create_data(
        self,
        stock,
        limits,
        pack_size=10,
        unit_cost=10,
        distances=None,
        sales=None,
        reorders=None
    ):
        return {
            "stock": stock,
            "limits": limits,
            "sku_master": {
                "R001": {
                    "unit_cost": unit_cost,
                    "pack_size": pack_size
                }
            },
            "distances": distances or {},
            "sales": sales or {},
            "reorders": reorders or {}
        }

    # TEST 1: Stock exactly equal to minimum
    def test_stock_equal_to_minimum(self):

        data = self.create_data(
            {("B01", "R001"): 10},
            {("B01", "R001"): {
                "min_stock": 10,
                "max_stock": 20
            }}
        )

        self.assertEqual(detect_shortages(data), [])

    # TEST 2: Stock exactly equal to maximum
    def test_stock_equal_to_maximum(self):

        data = self.create_data(
            {("B01", "R001"): 20},
            {("B01", "R001"): {
                "min_stock": 10,
                "max_stock": 20
            }}
        )

        self.assertEqual(detect_surpluses(data), [])

    # TEST 3: Zero sales
    def test_zero_sales(self):

        data = self.create_data(
            {("B01", "R001"): 20},
            {("B01", "R001"): {
                "min_stock": 10,
                "max_stock": 30
            }}
        )

        average_sales = calculate_average_daily_sales(data)
        days = calculate_days_of_cover(data, average_sales)

        self.assertEqual(
            average_sales.get(("B01", "R001"), 0), 0
        )

        self.assertEqual(
            days[("B01", "R001")], float("inf")
        )

    # TEST 4: Competing shortages for the same surplus
    def test_competing_shortages(self):

        data = self.create_data(
            {
                ("B01", "R001"): 0,
                ("B02", "R001"): 0,
                ("B03", "R001"): 30
            },
            {
                ("B01", "R001"): {
                    "min_stock": 10, "max_stock": 20
                },
                ("B02", "R001"): {
                    "min_stock": 10, "max_stock": 20
                },
                ("B03", "R001"): {
                    "min_stock": 10, "max_stock": 10
                }
            },
            distances={
                ("B01", "B03"): 20,
                ("B02", "B03"): 30
            }
        )

        shortages = detect_shortages(data)

        transfers, remaining, updated = allocate_transfers(
            data, shortages
        )

        self.assertEqual(len(transfers), 1)
        self.assertEqual(transfers[0]["destination"], "B01")
        self.assertEqual(updated[("B03", "R001")], 10)
        self.assertEqual(remaining[1]["remaining_need"], 20)

    # TEST 5: Insufficient surplus and partial transfer
    def test_insufficient_surplus(self):

        data = self.create_data(
            {
                ("B01", "R001"): 0,
                ("B02", "R001"): 20
            },
            {
                ("B01", "R001"): {
                    "min_stock": 10, "max_stock": 20
                },
                ("B02", "R001"): {
                    "min_stock": 10, "max_stock": 10
                }
            },
            distances={("B01", "B02"): 20}
        )

        shortages = detect_shortages(data)

        transfers, remaining, updated = allocate_transfers(
            data, shortages
        )

        self.assertEqual(transfers[0]["quantity"], 10)
        self.assertEqual(remaining[0]["remaining_need"], 10)
        self.assertEqual(updated[("B02", "R001")], 10)

    # TEST 6: Surplus smaller than one pack
    def test_sub_pack_transfer(self):

        data = self.create_data(
            {
                ("B01", "R001"): 0,
                ("B02", "R001"): 19
            },
            {
                ("B01", "R001"): {
                    "min_stock": 10, "max_stock": 20
                },
                ("B02", "R001"): {
                    "min_stock": 10, "max_stock": 10
                }
            },
            distances={("B01", "B02"): 20}
        )

        shortages = detect_shortages(data)

        transfers, remaining, updated = allocate_transfers(
            data, shortages
        )

        self.assertEqual(len(transfers), 0)
        self.assertEqual(remaining[0]["remaining_need"], 20)
        self.assertEqual(updated[("B02", "R001")], 19)

    # TEST 7: Low-value transfer over 50 km
    def test_low_value_distant_transfer_rejected(self):

        data = self.create_data(
            {
                ("B01", "R001"): 0,
                ("B02", "R001"): 30
            },
            {
                ("B01", "R001"): {
                    "min_stock": 10, "max_stock": 20
                },
                ("B02", "R001"): {
                    "min_stock": 10, "max_stock": 10
                }
            },
            pack_size=10,
            unit_cost=10,
            distances={("B01", "B02"): 100}
        )

        shortages = detect_shortages(data)

        transfers, remaining, updated = allocate_transfers(
            data, shortages
        )

        self.assertEqual(len(transfers), 0)
        self.assertEqual(remaining[0]["remaining_need"], 20)
        self.assertEqual(updated[("B02", "R001")], 30)

    # TEST 8: Existing OPEN reorder must not be duplicated
    def test_open_reorder_skipped(self):

        data = self.create_data(
            {("B01", "R001"): 5},
            {("B01", "R001"): {
                "min_stock": 10,
                "max_stock": 20
            }},
            reorders={
                ("B01", "R001"): [
                    {
                        "reorder_quantity": 10,
                        "status": "OPEN"
                    }
                ]
            }
        )

        needs = [{
            "branch_id": "B01",
            "sku_code": "R001",
            "remaining_need": 15
        }]

        result = generate_reorders(data, needs)

        self.assertEqual(result, [])

    # TEST 9: Fast mover doubles minimum stock
    def test_fast_mover_minimum_doubled(self):

        key = ("B01", "R001")

        data = self.create_data(
            {key: 30},
            {key: {
                "min_stock": 10,
                "max_stock": 50
            }},
            sales={
                key: [
                    {"quantity_sold": 25}
                    for _ in range(7)
                ]
            }
        )

        averages = calculate_average_daily_sales(data)
        fast_movers = identify_fast_movers(averages)

        adjusted = apply_fast_mover_limits(data, averages)

        self.assertIn(key, fast_movers)
        self.assertEqual(adjusted[key]["min_stock"], 20)

        # Original minimum must remain unchanged
        self.assertEqual(data["limits"][key]["min_stock"], 10)

    # TEST 10: Equal-distance tie-breaker
    def test_equal_distance_tie_breaker(self):

        data = self.create_data(
            {
                ("B01", "R001"): 0,
                ("B02", "R001"): 30,
                ("B03", "R001"): 30
            },
            {
                ("B01", "R001"): {
                    "min_stock": 10, "max_stock": 20
                },
                ("B02", "R001"): {
                    "min_stock": 10, "max_stock": 10
                },
                ("B03", "R001"): {
                    "min_stock": 10, "max_stock": 10
                }
            },
            distances={
                ("B01", "B02"): 50,
                ("B01", "B03"): 50
            }
        )

        shortages = detect_shortages(data)

        transfers, remaining, updated = allocate_transfers(
            data, shortages
        )

        self.assertEqual(transfers[0]["source"], "B02")
        self.assertEqual(updated[("B02", "R001")], 10)
        self.assertEqual(updated[("B03", "R001")], 30)
        self.assertEqual(remaining[0]["remaining_need"], 0)

    # TEST 11: Transfer from multiple surplus branches
    def test_multiple_source_transfers(self):

        data = self.create_data(
            {
                ("B01", "R001"): 0,
                ("B02", "R001"): 30,
                ("B03", "R001"): 40
            },
            {
                ("B01", "R001"): {
                    "min_stock": 10, "max_stock": 40
                },
                ("B02", "R001"): {
                    "min_stock": 10, "max_stock": 10
                },
                ("B03", "R001"): {
                    "min_stock": 10, "max_stock": 10
                }
            },
            distances={
                ("B01", "B02"): 20,
                ("B01", "B03"): 40
            }
        )

        shortages = detect_shortages(data)

        transfers, remaining, updated = allocate_transfers(
            data, shortages
        )

        self.assertEqual(len(transfers), 2)

        self.assertEqual(transfers[0]["source"], "B02")
        self.assertEqual(transfers[0]["quantity"], 20)

        self.assertEqual(transfers[1]["source"], "B03")
        self.assertEqual(transfers[1]["quantity"], 20)

        self.assertEqual(remaining[0]["remaining_need"], 0)
        self.assertEqual(updated[("B02", "R001")], 10)
        self.assertEqual(updated[("B03", "R001")], 20)

    # TEST 12: Missing distance information
    def test_missing_distance_rejected(self):

        data = self.create_data(
            {
                ("B01", "R001"): 0,
                ("B02", "R001"): 30
            },
            {
                ("B01", "R001"): {
                    "min_stock": 10, "max_stock": 20
                },
                ("B02", "R001"): {
                    "min_stock": 10, "max_stock": 10
                }
            },
            pack_size=10,
            unit_cost=10,
            distances={}
        )

        shortages = detect_shortages(data)

        transfers, remaining, updated = allocate_transfers(
            data, shortages
        )

        self.assertEqual(len(transfers), 0)
        self.assertEqual(remaining[0]["remaining_need"], 20)
        self.assertEqual(updated[("B02", "R001")], 30)

    # TEST 13: Transfer value exactly ₹500 must be accepted
    def test_transfer_value_exactly_500(self):

        data = self.create_data(
            {
                ("B01", "R001"): 0,
                ("B02", "R001"): 30
            },
            {
                ("B01", "R001"): {
                    "min_stock": 10, "max_stock": 20
                },
                ("B02", "R001"): {
                    "min_stock": 10, "max_stock": 10
                }
            },
            pack_size=10,
            unit_cost=25,
            distances={("B01", "B02"): 100}
        )

        shortages = detect_shortages(data)

        transfers, remaining, updated = allocate_transfers(
            data, shortages
        )

        self.assertEqual(len(transfers), 1)
        self.assertEqual(transfers[0]["quantity"], 20)
        self.assertEqual(transfers[0]["transfer_value"], 500)
        self.assertEqual(remaining[0]["remaining_need"], 0)

    # TEST 14: Low-value transfer at exactly 50 km accepted
    def test_low_value_transfer_exactly_50_km(self):

        data = self.create_data(
            {
                ("B01", "R001"): 0,
                ("B02", "R001"): 30
            },
            {
                ("B01", "R001"): {
                    "min_stock": 10, "max_stock": 20
                },
                ("B02", "R001"): {
                    "min_stock": 10, "max_stock": 10
                }
            },
            pack_size=10,
            unit_cost=10,
            distances={("B01", "B02"): 50}
        )

        shortages = detect_shortages(data)

        transfers, remaining, updated = allocate_transfers(
            data, shortages
        )

        self.assertEqual(len(transfers), 1)
        self.assertEqual(transfers[0]["transfer_value"], 200)
        self.assertEqual(remaining[0]["remaining_need"], 0)

    # TEST 15: Low-value transfer beyond 50 km rejected
    def test_low_value_transfer_above_50_km(self):

        data = self.create_data(
            {
                ("B01", "R001"): 0,
                ("B02", "R001"): 30
            },
            {
                ("B01", "R001"): {
                    "min_stock": 10, "max_stock": 20
                },
                ("B02", "R001"): {
                    "min_stock": 10, "max_stock": 10
                }
            },
            pack_size=10,
            unit_cost=10,
            distances={("B01", "B02"): 51}
        )

        shortages = detect_shortages(data)

        transfers, remaining, updated = allocate_transfers(
            data, shortages
        )

        self.assertEqual(len(transfers), 0)
        self.assertEqual(remaining[0]["remaining_need"], 20)
        self.assertEqual(updated[("B02", "R001")], 30)


if __name__ == "__main__":
    unittest.main(verbosity=2)
