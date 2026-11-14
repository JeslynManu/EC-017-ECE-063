
import unittest
from src.data_manager import load_data, validate_data


class TestDataManagement(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.data = load_data()

    def test_data_loads_successfully(self):
        self.assertIsNotNone(self.data)

    def test_all_required_data_sections_exist(self):
        expected = {
            "branches", "distances", "sku_master",
            "limits", "stock", "sales", "reorders"
        }
        self.assertEqual(set(self.data.keys()), expected)

    def test_branch_data_loaded(self):
        self.assertGreater(len(self.data["branches"]), 0)

    def test_stock_and_limits_are_consistent(self):
        self.assertEqual(
            set(self.data["stock"].keys()),
            set(self.data["limits"].keys())
        )

    def test_data_validation_passes(self):
        is_valid, messages = validate_data(self.data)
        self.assertTrue(is_valid, messages)


if __name__ == "__main__":
    unittest.main()
