import io
import sys
import unittest
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "reconciliation-core" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "connectors" / "file-input" / "src"))

from migration_input.input_contract import (  # noqa: E402
    INPUT_CONTRACT_VERSION,
    DatasetInputError,
    configuration_fingerprint,
    read_dataset_bytes,
)


def minimal_xlsx() -> bytes:
    shared_strings = """<?xml version="1.0" encoding="UTF-8"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <si><t>account_no</t></si><si><t>customer_name</t></si><si><t>A-001</t></si><si><t>สมชาย ทดสอบ</t></si>
</sst>"""
    worksheet = """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>
  <row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>
  <row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2" t="s"><v>3</v></c></row>
</sheetData></worksheet>"""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/sharedStrings.xml", shared_strings)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)
    return output.getvalue()


class InputContractTests(unittest.TestCase):
    def test_csv_is_normalized_with_metadata_and_safe_filename(self) -> None:
        payload = "account_no,customer_name\nA-001,สมชาย ทดสอบ\n".encode("utf-8")
        dataset = read_dataset_bytes(payload, "../exports/customers.csv")

        self.assertEqual(dataset.source_format, "csv")
        self.assertEqual(dataset.filename, "customers.csv")
        self.assertEqual(dataset.fields, ["account_no", "customer_name"])
        self.assertEqual(dataset.rows[0]["customer_name"], "สมชาย ทดสอบ")
        self.assertEqual(dataset.metadata()["contract_version"], INPUT_CONTRACT_VERSION)
        self.assertEqual(dataset.metadata()["byte_size"], len(payload))
        self.assertEqual(len(dataset.content_sha256), 64)

    def test_xlsx_uses_the_same_canonical_shape(self) -> None:
        dataset = read_dataset_bytes(minimal_xlsx(), "customers.xlsx")

        self.assertEqual(dataset.source_format, "xlsx")
        self.assertEqual(dataset.fields, ["account_no", "customer_name"])
        self.assertEqual(dataset.rows, [{"account_no": "A-001", "customer_name": "สมชาย ทดสอบ"}])

    def test_tsv_and_invalid_format_behavior_are_explicit(self) -> None:
        dataset = read_dataset_bytes(b"id\tvalue\n1\tok\n", "records.tsv")
        self.assertEqual(dataset.fields, ["id", "value"])
        self.assertEqual(dataset.rows, [{"id": "1", "value": "ok"}])

        with self.assertRaisesRegex(DatasetInputError, "Supported input formats"):
            read_dataset_bytes(b"{}", "records.json")

    def test_configuration_fingerprint_is_order_independent(self) -> None:
        first = configuration_fingerprint({"mapping": {"a": "b"}, "key": "id"})
        second = configuration_fingerprint({"key": "id", "mapping": {"a": "b"}})
        self.assertEqual(first, second)
        self.assertNotEqual(first, configuration_fingerprint({"key": "other", "mapping": {"a": "b"}}))

    @unittest.skipUnless(__import__("importlib").util.find_spec("pyarrow"), "PyArrow is optional")
    def test_parquet_is_supported_when_optional_runtime_is_available(self) -> None:
        import pyarrow as pa
        import pyarrow.parquet as parquet

        output = io.BytesIO()
        parquet.write_table(pa.table({"id": ["1"], "value": ["ok"]}), output)
        dataset = read_dataset_bytes(output.getvalue(), "records.parquet")

        self.assertEqual(dataset.source_format, "parquet")
        self.assertEqual(dataset.fields, ["id", "value"])
        self.assertEqual(dataset.rows, [{"id": "1", "value": "ok"}])

    def test_malformed_xlsx_is_rejected(self) -> None:
        with self.assertRaisesRegex(DatasetInputError, "XLSX archive is invalid"):
            read_dataset_bytes(b"not-a-zip", "records.xlsx")


if __name__ == "__main__":
    unittest.main()
