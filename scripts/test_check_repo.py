"""Tests for the invented-name check in check_repo.py.  python -m unittest discover -s scripts"""

import unittest

from check_repo import SERVER, invented

NAMES = {"LEN", "DATEADD", "STRING_AGG", "@@VERSION", "OPENJSON"}


class InventedNames(unittest.TestCase):
    def test_candidates_and_keywords_pass(self):
        sql = "SELECT LEN(N'a'), STRING_AGG(x, ',') WITHIN GROUP (ORDER BY x), CAST(1 AS VARCHAR(10)) FROM (VALUES (1)) AS t(x)"
        self.assertEqual(invented(sql, NAMES | {"CAST"}), set())

    def test_an_unknown_function_is_reported(self):
        self.assertEqual(invented("SELECT DATE_ADD(day, 1, GETDATE())", NAMES), {"DATE_ADD", "GETDATE"})

    def test_qualified_objects_and_lowercase_aliases_are_not_functions(self):
        self.assertEqual(invented("SELECT * FROM sys.dm_exec_sessions() AS s(a), dbo.MyFn(1)", NAMES), set())

    def test_string_literals_and_type_methods_are_not_calls(self):
        self.assertEqual(invented("SELECT CAST('POINT(1 1)' AS geography), geography::Point(1, 1, 4326)", NAMES | {"CAST"}), set())

    def test_known_limit_lowercase_calls_are_not_checked(self):
        # Documented limit of invented(): lower case reads as an alias. Change this test if it is lifted.
        self.assertEqual(invented("SELECT date_add(day, 1, x)", NAMES), set())

    def test_server_name_is_detected(self):
        self.assertTrue(SERVER.search("abcdefghijklmnop-qrstuvwxyz012345.datawarehouse.fabric.microsoft.com"))


if __name__ == "__main__":
    unittest.main()
