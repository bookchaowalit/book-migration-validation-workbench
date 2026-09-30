import base64
import io
import sys
import unittest
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
for relative in (
    "packages/reconciliation-core/src",
    "packages/data-engine/src",
    "connectors/file-input/src",
    "packages/privacy/src",
    "packages/audit/src",
    "apps/api/src",
):
    sys.path.insert(0, str(PROJECT_ROOT / relative))

from migration_input.input_contract import DatasetInputError, read_dataset_bytes  # noqa: E402

try:
    from fastapi.testclient import TestClient

    from migration_validation_api.server import MAX_BODY_BYTES, app
except ImportError:  # pragma: no cover - fastapi/httpx are needed for API tests
    TestClient = None


def xlsx_with_cell(reference: str) -> bytes:
    worksheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
        f'<row r="1"><c r="{reference}" t="inlineStr"><is><t>id</t></is></c></row>'
        "</sheetData></worksheet>"
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)
    return output.getvalue()


class XlsxHardeningTests(unittest.TestCase):
    def test_column_reference_beyond_excel_limit_is_rejected(self) -> None:
        for reference in ("XFE1", "ZZZZZZZ1"):
            with self.subTest(reference=reference):
                with self.assertRaises(DatasetInputError):
                    read_dataset_bytes(xlsx_with_cell(reference), "data.xlsx")

    def test_valid_reference_is_accepted(self) -> None:
        dataset = read_dataset_bytes(xlsx_with_cell("A1"), "data.xlsx")
        self.assertEqual(dataset.fields, ["id"])

    def test_corrupted_part_is_a_dataset_error(self) -> None:
        payload = bytearray(xlsx_with_cell("A1"))
        marker = payload.find(b"<sheetData>")
        payload[marker + 1] ^= 0x01  # stored entry: flip a byte so the CRC fails
        with self.assertRaises(DatasetInputError):
            read_dataset_bytes(bytes(payload), "data.xlsx")


@unittest.skipIf(TestClient is None, "fastapi test client (httpx) not installed")
class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health_and_profiles(self) -> None:
        self.assertEqual(self.client.get("/api/health").json()["status"], "ok")
        self.assertIn("profiles", self.client.get("/api/normalization-profiles").json())

    def test_fixture_route_blocks_traversal(self) -> None:
        self.assertEqual(self.client.get("/fixtures/legacy_customers.csv").status_code, 200)
        for path in ("/fixtures/../pyproject.toml", "/fixtures/%2e%2e/pyproject.toml",
                     "/fixtures/%2e%2e%2fpyproject.toml", "/fixtures/missing.csv"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_reconcile_with_spaced_and_thai_headers(self) -> None:
        response = self.client.post(
            "/api/reconcile",
            json={
                "legacy_csv": "Account No,Customer Name\n1,a\n2,b\n",
                "target_csv": "Account No,ชื่อลูกค้า\n1,a\n3,c\n",
                "legacy_key": "Account No",
                "target_key": "Account No",
                "mapping": {"Customer Name": "ชื่อลูกค้า"},
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertIn('l."Customer Name"', body["sql"])
        self.assertIn("configuration_fingerprint", body)
        self.assertIn("audit_package", body)

    def test_reconcile_with_fixture_files_base64(self) -> None:
        legacy = (PROJECT_ROOT / "evals/fixtures/legacy_customers.csv").read_bytes()
        target = (PROJECT_ROOT / "evals/fixtures/new_customers.csv").read_bytes()
        response = self.client.post(
            "/api/reconcile",
            json={
                "legacy_file_base64": base64.b64encode(legacy).decode(),
                "legacy_filename": "legacy.csv",
                "target_file_base64": base64.b64encode(target).decode(),
                "target_filename": "target.csv",
                "legacy_key": "account_no",
                "target_key": "account_no",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)

    def test_bad_inputs_return_structured_errors(self) -> None:
        cases = [
            ({"legacy_csv": "id\n1\n", "target_csv": "id\n1\n", "legacy_key": "nope", "target_key": "id"}, 400),
            ({"legacy_file_base64": "***", "legacy_filename": "a.csv", "target_csv": "id\n1\n"}, 400),
            ({"legacy_csv": "id\n1\n", "target_csv": "id\n1\n", "legacy_key": "id", "target_key": "id",
              "legacy_table": "t;drop"}, 400),
            ({"legacy_csv": "id\n1\n", "target_csv": "id\n1\n", "fuzzy_threshold": 2}, 422),
        ]
        for payload, status in cases:
            with self.subTest(payload=payload):
                response = self.client.post("/api/reconcile", json=payload)
                self.assertEqual(response.status_code, status)
                self.assertIn("error", response.json())

    def test_inspect_strips_directory_parts_from_filenames(self) -> None:
        response = self.client.post(
            "/api/inspect",
            json={"filename": "../../etc/passwd.csv", "content_base64": base64.b64encode(b"id\n1\n").decode()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("..", str(response.json()["input"]))
        bad = self.client.post("/api/inspect", json={"filename": "..", "content_base64": "aWQK"})
        self.assertEqual(bad.status_code, 400)

    def test_size_guard(self) -> None:
        response = self.client.post(
            "/api/inspect", content=b"{}",
            headers={"Content-Type": "application/json", "Content-Length": str(MAX_BODY_BYTES + 1)},
        )
        self.assertEqual(response.status_code, 413)

    def test_cors_allows_only_local_origins(self) -> None:
        allowed = self.client.options(
            "/api/health", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"}
        )
        self.assertEqual(allowed.headers.get("access-control-allow-origin"), "http://localhost:3000")
        denied = self.client.options(
            "/api/health", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"}
        )
        self.assertNotEqual(denied.headers.get("access-control-allow-origin"), "https://evil.example")


if __name__ == "__main__":
    unittest.main()
