import unittest
from importlib.resources import files
from pathlib import Path

from reconciliation_core.reconcile import (
    generate_sql,
    read_csv_text,
    reconcile,
    suggest_mapping,
)

# Sample datasets ship as package data of migration_validation_api.
SAMPLE_DATA_ROOT = Path(str(files("migration_validation_api") / "sample_data"))


class ReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.legacy_csv = (SAMPLE_DATA_ROOT / "legacy_customers.csv").read_text()
        self.target_csv = (SAMPLE_DATA_ROOT / "new_customers.csv").read_text()
        self.legacy_fields, self.legacy_rows = read_csv_text(self.legacy_csv)
        self.target_fields, self.target_rows = read_csv_text(self.target_csv)

    def test_fixture_produces_explainable_statuses(self) -> None:
        result = reconcile(
            self.legacy_fields,
            self.legacy_rows,
            self.target_fields,
            self.target_rows,
            "account_no",
            "account_no",
            {
                "account_no": "account_no",
                "customer_name": "customer_name",
                "status": "status",
                "close_date": "closed_at",
            },
        )
        self.assertEqual(result["summary"]["records_checked"], 6)
        self.assertEqual(result["summary"]["matched"], 2)
        self.assertEqual(result["summary"]["counts"]["value_mismatch"], 1)
        self.assertEqual(result["summary"]["counts"]["missing_target"], 1)
        self.assertEqual(result["summary"]["counts"]["duplicate"], 2)
        self.assertEqual(result["summary"]["counts"]["missing_legacy"], 1)
        mismatch = next(item for item in result["evidence"] if item["status"] == "value_mismatch")
        self.assertEqual(mismatch["key"], "A-002")
        self.assertEqual(mismatch["mismatches"][0]["legacy_field"], "status")

    def test_blank_key_is_not_silently_dropped(self) -> None:
        fields, rows = read_csv_text("id,value\n,orphan\n")
        target_fields, target_rows = read_csv_text("id,value\n1,ok\n")
        result = reconcile(fields, rows, target_fields, target_rows, "id", "id", {"id": "id"})
        self.assertEqual(result["summary"]["counts"]["invalid_key"], 1)
        self.assertEqual(result["evidence"][0]["reason"], "Legacy key 'id' is blank")

    def test_mapping_suggestions_are_bounded(self) -> None:
        suggestions = suggest_mapping(["close_date", "customer_name"], ["closed_at", "customer_name"])
        self.assertEqual(suggestions[1]["target"], "customer_name")
        self.assertTrue(0 <= suggestions[0]["confidence"] <= 1)
        self.assertIn(suggestions[0]["method"], {"similar name", "exact normalized name"})

    def test_duplicate_headers_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "headers must be unique"):
            read_csv_text("id,ID\n1,2\n")

    def test_sql_is_read_only_and_quoted(self) -> None:
        sql = generate_sql(
            "legacy_customers",
            "new_customers",
            "account_no",
            "account_no",
            {"account_no": "account_no", "status": "status"},
        )
        self.assertIn("FULL OUTER JOIN", sql)
        self.assertIn('l."status"', sql)
        self.assertNotIn("INSERT", sql)
        with self.assertRaisesRegex(ValueError, "identifiers"):
            generate_sql("legacy;drop", "target", "id", "id", {"id": "id"})

    def test_thai_customer_profile_normalizes_values_but_preserves_raw_evidence(self) -> None:
        fields = ["account_no", "customer_name", "phone", "tax_id", "closed_date"]
        legacy_rows = [{
            "account_no": " 001 ",
            "customer_name": "นาย สมชาย",
            "phone": "+66 81-234-5678",
            "tax_id": "1-2345-67890-12-3",
            "closed_date": "17/04/2566",
        }]
        target_rows = [{
            "account_no": "001",
            "customer_name": "สมชาย",
            "phone": "0812345678",
            "tax_id": "1234567890123",
            "closed_date": "2023-04-17",
        }]

        result = reconcile(
            fields,
            legacy_rows,
            fields,
            target_rows,
            "account_no",
            "account_no",
            {field: field for field in fields},
            "thai_customer",
        )

        self.assertEqual(result["summary"]["matched"], 1)
        self.assertEqual(result["normalization"]["name"], "thai_customer")
        self.assertEqual(result["evidence"][0]["legacy"]["customer_name"], "นาย สมชาย")
        self.assertEqual(result["evidence"][0]["legacy"]["phone"], "+66 81-234-5678")

    def test_unknown_normalization_profile_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown normalization profile"):
            reconcile(
                ["id"],
                [{"id": "1"}],
                ["id"],
                [{"id": "1"}],
                "id",
                "id",
                None,
                "unsafe",
            )

    def test_fuzzy_candidate_is_advisory_and_never_auto_approved(self) -> None:
        fields = ["legacy_id", "customer_name", "status"]
        result = reconcile(
            fields,
            [{"legacy_id": "OLD-1", "customer_name": "Acme North", "status": "active"}],
            ["target_id", "customer_name", "status"],
            [{"target_id": "NEW-9", "customer_name": "Acme Nort", "status": "active"}],
            "legacy_id",
            "target_id",
            {"customer_name": "customer_name", "status": "status"},
        )

        evidence = result["evidence"][0]
        self.assertEqual(evidence["status"], "missing_target")
        self.assertEqual(evidence["match_candidates"][0]["target_key"], "NEW-9")
        self.assertGreater(evidence["match_candidates"][0]["score"], 0.9)
        self.assertFalse(evidence["match_candidates"][0]["auto_approved"])
        self.assertIn("human review", evidence["match_candidates"][0]["reason"])
        self.assertFalse(result["fuzzy_matching"]["auto_approval"])

    def test_fuzzy_configuration_can_be_disabled_and_is_bounded(self) -> None:
        fields = ["legacy_id", "customer_name", "status"]
        result = reconcile(
            fields,
            [{"legacy_id": "OLD-1", "customer_name": "Acme North", "status": "active"}],
            ["target_id", "customer_name", "status"],
            [{"target_id": "NEW-9", "customer_name": "Acme Nort", "status": "active"}],
            "legacy_id",
            "target_id",
            {"customer_name": "customer_name", "status": "status"},
            fuzzy_enabled=False,
        )

        self.assertFalse(result["fuzzy_matching"]["enabled"])
        self.assertEqual(result["evidence"][0]["match_candidates"], [])
        strict = reconcile(
            fields,
            [{"legacy_id": "OLD-1", "customer_name": "Acme North", "status": "active"}],
            ["target_id", "customer_name", "status"],
            [{"target_id": "NEW-9", "customer_name": "Acme Nort", "status": "active"}],
            "legacy_id",
            "target_id",
            {"customer_name": "customer_name", "status": "status"},
            fuzzy_threshold=1.0,
        )
        strict_candidate = strict["evidence"][0]["match_candidates"][0]
        self.assertLess(strict_candidate["score"], 1.0)
        self.assertIn("Below conservative review threshold", strict_candidate["reason"])
        with self.assertRaisesRegex(ValueError, "fuzzy_threshold"):
            reconcile(fields, [{"legacy_id": "1"}], ["target_id"], [{"target_id": "2"}], "legacy_id", "target_id", {}, fuzzy_threshold=1.1)
        with self.assertRaisesRegex(ValueError, "fuzzy_candidate_limit"):
            reconcile(fields, [{"legacy_id": "1"}], ["target_id"], [{"target_id": "2"}], "legacy_id", "target_id", {}, fuzzy_candidate_limit=6)

    def test_fuzzy_candidates_are_symmetric_for_target_only_records(self) -> None:
        result = reconcile(
            ["legacy_id", "customer_name", "status"],
            [{"legacy_id": "OLD-9", "customer_name": "Acme North", "status": "active"}],
            ["target_id", "customer_name", "status"],
            [{"target_id": "NEW-9", "customer_name": "Acme Nort", "status": "active"}],
            "legacy_id",
            "target_id",
            {"customer_name": "customer_name", "status": "status"},
        )

        target_only = next(item for item in result["evidence"] if item["status"] == "missing_legacy")
        self.assertEqual(target_only["match_candidates"][0]["candidate_key"], "OLD-9")
        self.assertFalse(target_only["match_candidates"][0]["auto_approved"])

    def test_review_statuses_are_keyed_to_evidence_and_summarized(self) -> None:
        result = reconcile(
            ["id", "name"],
            [{"id": "1", "name": "Acme"}],
            ["id", "name"],
            [{"id": "1", "name": "Acme"}],
            "id",
            "id",
            {"name": "name"},
        )
        evidence_id = result["evidence"][0]["evidence_id"]

        reviewed = reconcile(
            ["id", "name"],
            [{"id": "1", "name": "Acme"}],
            ["id", "name"],
            [{"id": "1", "name": "Acme"}],
            "id",
            "id",
            {"name": "name"},
            "generic",
            {evidence_id: "approved"},
        )

        self.assertEqual(reviewed["evidence"][0]["review_status"], "approved")
        self.assertEqual(reviewed["review_summary"]["approved"], 1)
        with self.assertRaisesRegex(ValueError, "Unknown review status"):
            reconcile(
                ["id"], [{"id": "1"}], ["id"], [{"id": "1"}],
                "id", "id", None, "generic", {evidence_id: "maybe"},
            )

class UnicodeHeaderAndRateTests(unittest.TestCase):
    def test_thai_headers_are_distinct_and_map_exactly(self) -> None:
        from reconciliation_core.reconcile import read_csv_text, suggest_mapping

        headers, _ = read_csv_text("รหัสลูกค้า,ชื่อ,เบอร์โทร\n1,a,b\n")
        self.assertEqual(headers, ["รหัสลูกค้า", "ชื่อ", "เบอร์โทร"])
        [suggestion] = suggest_mapping(["ชื่อ"], ["ที่อยู่", "ชื่อ"])
        self.assertEqual(suggestion["target"], "ชื่อ")
        self.assertEqual(suggestion["method"], "exact normalized name")

    def test_match_rate_is_not_100_with_exceptions(self) -> None:
        from reconciliation_core.reconcile import _display_rate

        self.assertEqual(_display_rate(9999, 10000), 99.9)
        self.assertEqual(_display_rate(10000, 10000), 100.0)
        self.assertEqual(_display_rate(1, 10000), 0.1)
        self.assertEqual(_display_rate(0, 0), 0.0)


if __name__ == "__main__":
    unittest.main()
