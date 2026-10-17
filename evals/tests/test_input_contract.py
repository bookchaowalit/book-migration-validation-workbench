import io
import unittest
import zipfile
from unittest import mock

from migration_input import input_contract
from migration_input.input_contract import (
    INPUT_CONTRACT_VERSION,
    DatasetInputError,
    DatasetTooLarge,
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


def xlsx_from_rows(*rows: str) -> bytes:
    worksheet = (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(rows)}</sheetData></worksheet>"
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)
    return output.getvalue()


def excel_column(number: int) -> str:
    letters = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


class InputContractTests(unittest.TestCase):
    def test_csv_is_normalized_with_metadata_and_safe_filename(self) -> None:
        payload = "account_no,customer_name\nA-001,สมชาย ทดสอบ\n".encode()
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
        self.assertEqual(
            dataset.rows, [{"account_no": "A-001", "customer_name": "สมชาย ทดสอบ"}]
        )

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
        self.assertNotEqual(
            first, configuration_fingerprint({"key": "other", "mapping": {"a": "b"}})
        )

    @unittest.skipUnless(
        __import__("importlib").util.find_spec("pyarrow"), "PyArrow is optional"
    )
    def test_parquet_is_supported_when_optional_runtime_is_available(self) -> None:
        import pyarrow as pa
        from pyarrow import parquet

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


class DatasetShapeLimitTests(unittest.TestCase):
    def test_default_limits_are_documented_values(self) -> None:
        self.assertEqual(input_contract.MAX_DATASET_ROWS, 200_000)
        self.assertEqual(input_contract.MAX_DATASET_COLUMNS, 500)

    def test_csv_row_limit(self) -> None:
        with mock.patch.object(input_contract, "MAX_DATASET_ROWS", 3):
            self.assertEqual(read_dataset_bytes(b"id\n1\n2\n3\n", "a.csv").row_count, 3)
            with self.assertRaises(DatasetTooLarge):
                read_dataset_bytes(b"id\n1\n2\n3\n4\n", "a.csv")

    def test_column_limit_for_csv_and_tsv(self) -> None:
        with mock.patch.object(input_contract, "MAX_DATASET_COLUMNS", 2):
            read_dataset_bytes(b"a,b\n1,2\n", "a.csv")
            with self.assertRaises(DatasetTooLarge):
                read_dataset_bytes(b"a,b,c\n1,2,3\n", "a.csv")
            with self.assertRaises(DatasetTooLarge):
                read_dataset_bytes(b"a\tb\tc\n1\t2\t3\n", "a.tsv")

    def test_xlsx_row_limit_fails_while_parsing(self) -> None:
        with (
            mock.patch.object(input_contract, "MAX_DATASET_ROWS", 0),
            self.assertRaises(DatasetTooLarge),
        ):
            read_dataset_bytes(minimal_xlsx(), "sample.xlsx")

    def test_xlsx_column_limit_is_checked_before_dense_allocation(self) -> None:
        def guarded_range(width: int) -> range:
            self.assertLessEqual(
                width, 500, "Oversized XLSX row expanded before rejection"
            )
            return range(width)

        header = '<row r="1"><c r="A1" t="inlineStr"><is><t>id</t></is></c></row>'
        values = (
            't="inlineStr"><is><t>value</t></is>',
            't="b"><v>1</v>',
            "><v>7</v>",
            't="s"><v>999</v>',
            ">",
        )
        for column in ("SG", "XFD"):
            for row_number in (1, 2):
                for cell_value in values:
                    with self.subTest(
                        column=column, row=row_number, cell_value=cell_value
                    ):
                        row = f'<row r="{row_number}"><c r="{column}{row_number}" {cell_value}</c></row>'
                        payload = xlsx_from_rows(
                            *([header, row] if row_number == 2 else [row])
                        )
                        with (
                            mock.patch.object(
                                input_contract, "range", guarded_range, create=True
                            ),
                            self.assertRaisesRegex(DatasetTooLarge, "500 column limit"),
                        ):
                            read_dataset_bytes(payload, "sparse.xlsx")

    def test_xlsx_accepts_exactly_500_columns_with_normal_cell_types(self) -> None:
        headers = "".join(
            f'<c r="{excel_column(column)}1" t="inlineStr"><is><t>field_{column}</t></is></c>'
            for column in range(1, 501)
        )
        payload = xlsx_from_rows(
            f'<row r="1">{headers}</row>',
            '<row r="2"><c r="A2" t="inlineStr"><is><t>record</t></is></c>'
            '<c r="B2"><v>7</v></c><c r="C2"/><c r="SF2" t="b"><v>1</v></c></row>',
        )
        dataset = read_dataset_bytes(payload, "boundary.xlsx")
        self.assertEqual(len(dataset.fields), 500)
        self.assertEqual(dataset.row_count, 1)
        self.assertEqual(dataset.rows[0]["field_1"], "record")
        self.assertEqual(dataset.rows[0]["field_2"], "7")
        self.assertEqual(dataset.rows[0]["field_3"], "")
        self.assertEqual(dataset.rows[0]["field_500"], "TRUE")

    def test_invalid_excel_geometry_is_not_a_dataset_size_error(self) -> None:
        for reference in ("XFE1", "ZZZZZZZ1", "A0", "A-1"):
            with self.subTest(reference=reference):
                payload = xlsx_from_rows(f'<row r="1"><c r="{reference}"/></row>')
                with self.assertRaises(DatasetInputError) as raised:
                    read_dataset_bytes(payload, "invalid.xlsx")
                self.assertNotIsInstance(raised.exception, DatasetTooLarge)

    def test_too_large_is_still_a_dataset_input_error(self) -> None:
        self.assertTrue(issubclass(DatasetTooLarge, DatasetInputError))
