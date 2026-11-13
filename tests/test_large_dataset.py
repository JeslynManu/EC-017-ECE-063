
import time
import unittest

from src.replenishment import (
    detect_shortages,
    detect_surpluses,
    allocate_transfers
)


class TestLargeDataset(unittest.TestCase):

    def setUp(self):

        self.branches = {
            f"B{i:02d}": f"Branch {i}"
            for i in range(1, 7)
        }

        self.skus = {
            f"SKU{i:03d}": {
                "unit_cost": 50.0,
                "pack_size": 5
            }
            for i in range(1, 81)
        }

        self.data = {
            "branches": self.branches,
            "sku_master": self.skus,
            "limits": {},
            "stock": {},
            "distances": {}
        }

        # Generate 480 branch-SKU combinations
        for branch_index, branch in enumerate(self.branches):

            for sku_index, sku in enumerate(self.skus):

                key = (branch, sku)

                self.data["limits"][key] = {
                    "min_stock": 20,
                    "max_stock": 100
                }

                pattern = (branch_index + sku_index) % 3

                if pattern == 0:
                    quantity = 10       # Shortage

                elif pattern == 1:
                    quantity = 60       # Normal stock

                else:
                    quantity = 120      # Surplus

                self.data["stock"][key] = quantity

        # Generate distances between all branches
        branch_list = list(self.branches)

        for i in range(len(branch_list)):

            for j in range(i + 1, len(branch_list)):

                branch1 = branch_list[i]
                branch2 = branch_list[j]

                distance = float((j - i) * 100)

                self.data["distances"][
                    (branch1, branch2)
                ] = distance

                self.data["distances"][
                    (branch2, branch1)
                ] = distance

    def test_dataset_contains_480_combinations(self):

        self.assertEqual(len(self.data["stock"]), 480)

        self.assertEqual(len(self.data["limits"]), 480)

    def test_every_combination_has_stock_and_limits(self):

        self.assertEqual(
            set(self.data["stock"]),
            set(self.data["limits"])
        )

    def test_shortages_and_surpluses_are_detected(self):

        shortages = detect_shortages(self.data)

        surpluses = detect_surpluses(self.data)

        self.assertGreater(len(shortages), 0)

        self.assertGreater(len(surpluses), 0)

    def test_shortages_and_surpluses_do_not_overlap(self):

        shortages = detect_shortages(self.data)

        surpluses = detect_surpluses(self.data)

        shortage_keys = {
            (item["branch_id"], item["sku_code"])
            for item in shortages
        }

        surplus_keys = {
            (item["branch_id"], item["sku_code"])
            for item in surpluses
        }

        self.assertTrue(
            shortage_keys.isdisjoint(surplus_keys)
        )

    def test_transfer_allocation_on_large_dataset(self):

        shortages = detect_shortages(self.data)

        start = time.perf_counter()

        transfers, remaining_needs, updated_stock = (
            allocate_transfers(self.data, shortages)
        )

        elapsed = time.perf_counter() - start

        self.assertIsInstance(transfers, list)

        self.assertIsInstance(remaining_needs, list)

        self.assertIsInstance(updated_stock, dict)

        self.assertGreater(len(transfers), 0)

        print(
            f"\nLarge dataset transfer allocation time: "
            f"{elapsed:.6f} seconds"
        )

    def test_transfer_quantities_are_full_packs(self):

        shortages = detect_shortages(self.data)

        transfers, remaining_needs, updated_stock = (
            allocate_transfers(self.data, shortages)
        )

        for transfer in transfers:

            sku = transfer["sku_code"]

            pack_size = self.skus[sku]["pack_size"]

            self.assertGreater(transfer["quantity"], 0)

            self.assertEqual(
                transfer["quantity"] % pack_size,
                0
            )

    def test_transfer_sources_and_destinations_are_valid(self):

        shortages = detect_shortages(self.data)

        transfers, remaining_needs, updated_stock = (
            allocate_transfers(self.data, shortages)
        )

        for transfer in transfers:

            self.assertIn(
                transfer["source"],
                self.branches
            )

            self.assertIn(
                transfer["destination"],
                self.branches
            )

            self.assertNotEqual(
                transfer["source"],
                transfer["destination"]
            )

    def test_updated_stock_is_never_negative(self):

        shortages = detect_shortages(self.data)

        transfers, remaining_needs, updated_stock = (
            allocate_transfers(self.data, shortages)
        )

        for quantity in updated_stock.values():

            self.assertGreaterEqual(quantity, 0)

    def test_remaining_needs_are_non_negative(self):

        shortages = detect_shortages(self.data)

        transfers, remaining_needs, updated_stock = (
            allocate_transfers(self.data, shortages)
        )

        for item in remaining_needs:

            self.assertGreaterEqual(
                item["remaining_need"],
                0
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
