import unittest

from migration_privacy.redaction import REDACTED, default_redact_fields, redact_result


class RedactionTests(unittest.TestCase):
    def test_default_profile_selects_pii_like_fields_but_not_generic_ids(self) -> None:
        selected = default_redact_fields(
            ["account_no", "customer_name", "phone", "status"]
        )
        self.assertEqual(selected, {"customer_name", "phone"})

    def test_redaction_does_not_mutate_reconciliation_result(self) -> None:
        result = {
            "evidence": [
                {
                    "key": "A-001",
                    "legacy": {"account_no": "A-001", "customer_name": "สมชาย ทดสอบ"},
                    "target": {
                        "account_no": "A-001",
                        "customer_name": "สมชาย ทดสอบใหม่",
                    },
                    "mismatches": [
                        {
                            "legacy_field": "customer_name",
                            "target_field": "customer_name",
                            "legacy_value": "สมชาย ทดสอบ",
                            "target_value": "สมชาย ทดสอบใหม่",
                        }
                    ],
                    "match_candidates": [
                        {
                            "candidate_key": "A-009",
                            "target_key": "A-009",
                            "field_scores": [
                                {
                                    "source_field": "customer_name",
                                    "candidate_field": "customer_name",
                                    "score": 0.96,
                                }
                            ],
                        }
                    ],
                }
            ]
        }
        redacted = redact_result(
            result, legacy_key="account_no", target_key="account_no"
        )

        self.assertEqual(
            result["evidence"][0]["legacy"]["customer_name"], "สมชาย ทดสอบ"
        )
        self.assertEqual(redacted["evidence"][0]["legacy"]["customer_name"], REDACTED)
        self.assertEqual(redacted["evidence"][0]["target"]["customer_name"], REDACTED)
        self.assertEqual(
            redacted["evidence"][0]["mismatches"][0]["legacy_value"], REDACTED
        )
        self.assertEqual(
            redacted["evidence"][0]["match_candidates"][0]["candidate_key"], REDACTED
        )
        self.assertEqual(redacted["evidence"][0]["key"], "A-001")
        self.assertFalse(redacted["redaction"]["raw_values_included"])


if __name__ == "__main__":
    unittest.main()
