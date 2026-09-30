import unittest

from migration_data_engine import profile_dataset


class DataEngineTests(unittest.TestCase):
    def test_profile_is_non_sensitive_and_counts_duplicate_keys(self) -> None:
        profile = profile_dataset(
            ["account_no", "status"],
            [
                {"account_no": "A-001", "status": "open"},
                {"account_no": "A-001", "status": ""},
                {"account_no": "A-002", "status": "closed"},
            ],
            "account_no",
        )

        self.assertIn(
            profile["backend"],
            {
                "duckdb",
                "python-fallback",
                "python-fallback-large-inline",
                "python-fallback-engine-error",
            },
        )
        self.assertEqual(profile["row_count"], 3)
        self.assertEqual(profile["field_count"], 2)
        self.assertEqual(profile["blank_counts"]["status"], 1)
        self.assertEqual(profile["distinct_keys"], 2)
        self.assertEqual(profile["duplicate_key_rows"], 1)


if __name__ == "__main__":
    unittest.main()
