import json
import unittest

from migration_audit import build_audit_package


class AuditPackageTests(unittest.TestCase):
    def test_package_is_stable_and_omits_raw_evidence_values(self) -> None:
        result = {
            "summary": {
                "records_checked": 1,
                "matched": 0,
                "exceptions": 1,
                "match_rate": 0.0,
                "counts": {"value_mismatch": 1},
            },
            "normalization": {"name": "generic"},
            "fuzzy_matching": {"enabled": True, "auto_approval": False},
            "review_summary": {"unreviewed": 1},
            "evidence": [
                {
                    "evidence_id": "value_mismatch:legacy-3:target-7",
                    "status": "value_mismatch",
                    "review_status": "unreviewed",
                    "key": "SECRET-ACCOUNT-42",
                    "reason": "1 mapped field(s) differ",
                    "legacy_row": 3,
                    "target_row": 7,
                    "legacy": {"account_no": "SECRET-ACCOUNT-42", "name": "Alice Raw"},
                    "target": {"account_no": "SECRET-ACCOUNT-42", "name": "Alice Changed"},
                    "mismatches": [
                        {
                            "legacy_field": "name",
                            "target_field": "name",
                            "legacy_value": "Alice Raw",
                            "target_value": "Alice Changed",
                        }
                    ],
                    "match_candidates": [
                        {
                            "candidate_key": "SECRET-ACCOUNT-43",
                            "row_number": 8,
                            "score": 0.91,
                            "threshold": 0.9,
                            "auto_approved": False,
                            "reason": "Human review required",
                            "field_scores": [{"source_field": "name", "candidate_field": "name", "score": 0.91}],
                        }
                    ],
                }
            ],
        }
        inputs = {
            "contract_version": "mvw.input.v1",
            "filename": "legacy.csv",
            "format": "csv",
            "fields": ["account_no", "name"],
            "row_count": 1,
            "byte_size": 12,
            "sha256": "legacy-hash",
        }

        package = build_audit_package(
            result,
            legacy_metadata=inputs,
            target_metadata={**inputs, "filename": "target.csv", "sha256": "target-hash"},
            legacy_key="account_no",
            target_key="account_no",
            legacy_table="legacy_customers",
            target_table="new_customers",
            mapping={"account_no": "account_no", "name": "name"},
            configuration_fingerprint="configuration-hash",
        )

        encoded = json.dumps(package, ensure_ascii=False, sort_keys=True)
        self.assertEqual(package["schema_version"], "mvw.audit.v1")
        self.assertEqual(package["rule_version"], "reconciliation-core@0.2.0")
        self.assertEqual(package["inputs"]["legacy"]["sha256"], "legacy-hash")
        self.assertEqual(package["fingerprints"]["configuration_sha256"], "configuration-hash")
        self.assertEqual(package["evidence"][0]["legacy_row"], 3)
        self.assertEqual(package["evidence"][0]["target_row"], 7)
        self.assertEqual(package["evidence"][0]["mismatch_fields"], [{"legacy_field": "name", "target_field": "name"}])
        self.assertFalse(package["privacy"]["raw_values_included"])
        for raw_value in ("SECRET-ACCOUNT-42", "SECRET-ACCOUNT-43", "Alice Raw", "Alice Changed"):
            self.assertNotIn(raw_value, encoded)
        self.assertNotIn("legacy", package["evidence"][0])
        self.assertNotIn("target", package["evidence"][0])

        repeat = build_audit_package(
            result,
            legacy_metadata=inputs,
            target_metadata={**inputs, "filename": "target.csv", "sha256": "target-hash"},
            legacy_key="account_no",
            target_key="account_no",
            legacy_table="legacy_customers",
            target_table="new_customers",
            mapping={"name": "name", "account_no": "account_no"},
            configuration_fingerprint="configuration-hash",
        )
        self.assertEqual(package, repeat)


if __name__ == "__main__":
    unittest.main()
