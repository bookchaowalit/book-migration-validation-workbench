import pathlib
import sys
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "reconciliation-core" / "src"))

from reconciliation_core.normalization import (  # noqa: E402
    NormalizationProfileError,
    available_profiles,
    normalize_value,
)
from reconciliation_core.reconcile import reconcile  # noqa: E402


class NormalizationTests(unittest.TestCase):
    def test_registry_exposes_only_reviewed_profiles(self) -> None:
        self.assertEqual(
            [profile["name"] for profile in available_profiles()],
            ["generic", "thai_customer"],
        )
        with self.assertRaises(NormalizationProfileError):
            normalize_value("value", profile="unknown")

    def test_thai_customer_profile_normalizes_common_field_shapes(self) -> None:
        self.assertEqual(
            normalize_value("นาย  สมชาย  ทดสอบ", profile="thai_customer", field_name="customer_name"),
            "สมชาย ทดสอบ",
        )
        self.assertEqual(
            normalize_value("+66 81-000-0001", profile="thai_customer", field_name="phone"),
            "0810000001",
        )
        self.assertEqual(
            normalize_value("010-555-123-4567", profile="thai_customer", field_name="tax_id"),
            "0105551234567",
        )
        self.assertEqual(
            normalize_value("31/12/2567", profile="thai_customer", field_name="close_date"),
            "2024-12-31",
        )
        self.assertEqual(
            normalize_value("123/4 ถนนสุขุมวิท,\nเขตบางรัก", profile="thai_customer", field_name="address"),
            "123/4 ถนนสุขุมวิท เขตบางรัก",
        )

    def test_profile_matches_without_mutating_raw_evidence(self) -> None:
        legacy_rows = [
            {
                "phone": "081-000-0001",
                "customer_name": "นาย  สมชาย  ทดสอบ",
                "tax_id": "010-555-123-4567",
                "close_date": "31/12/2567",
                "address": "123/4 ถนนสุขุมวิท, เขตบางรัก",
            }
        ]
        target_rows = [
            {
                "phone": "+66 81 000 0001",
                "customer_name": "สมชาย ทดสอบ",
                "tax_id": "0105551234567",
                "close_date": "2024-12-31",
                "address": "123/4 ถนนสุขุมวิท เขตบางรัก",
            }
        ]
        result = reconcile(
            list(legacy_rows[0]),
            legacy_rows,
            list(target_rows[0]),
            target_rows,
            "phone",
            "phone",
            {"phone": "phone", "customer_name": "customer_name", "tax_id": "tax_id", "close_date": "close_date", "address": "address"},
            "thai_customer",
        )

        self.assertEqual(result["summary"]["matched"], 1)
        self.assertEqual(result["summary"]["counts"]["value_mismatch"], 0)
        self.assertEqual(result["normalization"]["name"], "thai_customer")
        self.assertTrue(result["normalization"]["raw_evidence_preserved"])
        self.assertEqual(result["evidence"][0]["legacy"]["customer_name"], "นาย  สมชาย  ทดสอบ")
        self.assertEqual(result["evidence"][0]["target"]["phone"], "+66 81 000 0001")


if __name__ == "__main__":
    unittest.main()
