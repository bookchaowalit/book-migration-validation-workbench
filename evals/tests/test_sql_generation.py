import pathlib
import sys
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "reconciliation-core" / "src"))

from reconciliation_core.reconcile import generate_sql  # noqa: E402

try:
    import duckdb
except ImportError:  # pragma: no cover - duckdb is a declared dependency
    duckdb = None


class SqlGenerationTests(unittest.TestCase):
    def test_real_world_headers_are_quoted_not_rejected(self) -> None:
        sql = generate_sql(
            "legacy",
            "target",
            "Account No",
            "เลขบัญชี",
            {"Account No": "เลขบัญชี", 'Name "legal"': "name.full"},
        )
        self.assertIn('l."Account No"', sql)
        self.assertIn('t."เลขบัญชี"', sql)
        self.assertIn('l."Name ""legal"""', sql)
        self.assertIn('t."name.full"', sql)

    def test_quote_escaping_prevents_breaking_out_of_identifier(self) -> None:
        hostile = 'x" AS a; DROP TABLE legacy; --'
        sql = generate_sql("legacy", "target", "id", "id", {"id": "id", hostile: "y"})
        self.assertIn('"x"" AS a; DROP TABLE legacy; --"', sql)

    def test_table_names_stay_strict(self) -> None:
        for bad in ("legacy;drop", "legacy table", 'a"b', ""):
            with self.subTest(table=bad):
                with self.assertRaisesRegex(ValueError, "identifiers"):
                    generate_sql(bad, "target", "id", "id", {})
        self.assertIn('"main"."legacy"', generate_sql("main.legacy", "target", "id", "id", {}))

    def test_blank_long_or_control_column_names_are_rejected(self) -> None:
        for bad in ("", "   ", "a\nb", "a\x00b", "c" * 129):
            with self.subTest(column=repr(bad)[:20]):
                with self.assertRaisesRegex(ValueError, "column identifiers"):
                    generate_sql("legacy", "target", bad, "id", {})

    @unittest.skipIf(duckdb is None, "duckdb not installed")
    def test_generated_sql_executes_and_finds_differences(self) -> None:
        con = duckdb.connect()
        con.execute('CREATE TABLE legacy ("Account No" VARCHAR, "Customer ""Name""" VARCHAR)')
        con.execute('CREATE TABLE target ("เลขบัญชี" VARCHAR, "name" VARCHAR)')
        con.execute("INSERT INTO legacy VALUES ('1', 'a'), ('2', 'b'), ('3', 'c')")
        con.execute("INSERT INTO target VALUES ('1', 'a'), ('2', 'B'), ('4', 'd')")
        sql = generate_sql(
            "legacy", "target", "Account No", "เลขบัญชี",
            {"Account No": "เลขบัญชี", 'Customer "Name"': "name"},
        )
        rows = sorted(con.execute(sql).fetchall(), key=lambda row: (row[0] or "", row[1] or ""))
        self.assertEqual(rows, [(None, "4"), ("2", "2"), ("3", None)])


if __name__ == "__main__":
    unittest.main()
