"""AI-assisted synthetic dry run; not evidence of a human operator trial.

Uses only the two checked-in Thai fixture files and the pure core. No HTTP,
credentials, external inputs, database connections or file writes.
"""

import hashlib
import json
from pathlib import Path

from migration_privacy.redaction import REDACTED, redact_result
from reconciliation_core.reconcile import read_csv_text, reconcile


def main() -> None:
    fixtures = (
        Path(__file__).resolve().parents[1]
        / "apps/api/src/migration_validation_api/sample_data"
    )
    inputs = {}
    datasets = []
    for name in ("thai_customers_legacy.csv", "thai_customers_target.csv"):
        content = (fixtures / name).read_bytes()
        inputs[name] = hashlib.sha256(content).hexdigest()
        datasets.append(read_csv_text(content.decode("utf-8")))
    (legacy_fields, legacy), (target_fields, target) = datasets
    mapping = {field: field for field in legacy_fields}

    def run(profile, reviews=None):
        return reconcile(
            legacy_fields,
            legacy,
            target_fields,
            target,
            "account_no",
            "account_no",
            mapping,
            profile,
            reviews,
        )

    generic = run("generic")
    thai = run("thai_customer")
    assert generic["summary"]["matched"] == 0
    assert generic["summary"]["counts"]["value_mismatch"] == 2
    assert thai["summary"]["matched"] == 1
    assert thai["summary"]["counts"]["value_mismatch"] == 1
    evidence = {item["key"]: item for item in thai["evidence"]}
    assert evidence["TH-001"]["status"] == "match"
    assert evidence["TH-001"]["legacy"]["phone"] == "0810000001"
    assert evidence["TH-001"]["target"]["phone"] == "081-000-0001"
    assert evidence["TH-002"]["mismatches"][0]["legacy_field"] == "customer_name"
    assert all(item["review_status"] == "unreviewed" for item in thai["evidence"])

    # A simulated decision is deliberately Needs review, never human approval.
    evidence_id = evidence["TH-002"]["evidence_id"]
    reviewed = run("thai_customer", {evidence_id: "needs-review"})
    assert (
        next(
            item for item in reviewed["evidence"] if item["evidence_id"] == evidence_id
        )["review_status"]
        == "needs-review"
    )
    redacted = redact_result(
        reviewed,
        legacy_key="account_no",
        target_key="account_no",
        fields=("account_no", "customer_name", "phone"),
    )
    for item in redacted["evidence"]:
        assert item["key"] == REDACTED
        for side in ("legacy", "target"):
            for field in ("account_no", "customer_name", "phone"):
                assert item[side][field] == REDACTED
    assert evidence["TH-002"]["legacy"]["customer_name"] == "สุดา ตัวอย่าง"
    print(
        json.dumps(
            {
                "mode": "AI-assisted synthetic dry run",
                "human_operator_completion": False,
                "inputs_sha256": inputs,
                "generic_summary": generic["summary"],
                "thai_summary": thai["summary"],
                "checks": [
                    "raw evidence preserved",
                    "name mismatch remains",
                    "review survives rerun",
                    "selected evidence fields redacted",
                ],
                "result": "passed",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
