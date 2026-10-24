"""Tests for the pure parts of probe_fabric.py.  python -m unittest discover -s scripts"""

import unittest

from probe_fabric import note_status, verdict_of


def failed(*errors):
    return {"ok": False, "errors": [{"number": n, "message": m} for n, m in errors]}


class NoteStatus(unittest.TestCase):
    def test_endpoint_only_run_is_never_fully_probed(self):
        self.assertEqual(note_status(True, [], [], "sql_analytics_endpoint"), "partly_probed")

    def test_warehouse_run_with_full_proof_is_probed(self):
        self.assertEqual(note_status(True, [], [], "warehouse"), "probed")

    def test_any_refuted_claim_keeps_the_note_unprobed(self):
        self.assertEqual(note_status(True, ["c1"], [], "warehouse"), "unprobed")

    def test_partial_proof_caps_the_note(self):
        self.assertEqual(note_status(True, [], ["c2"], "warehouse"), "partly_probed")


class Verdict(unittest.TestCase):
    def test_not_supported_must_name_the_function(self):
        about_dbo = failed((15871, "FUNCTION 'dbo' is not supported."))
        self.assertEqual(verdict_of(about_dbo, "NEXT VALUE FOR"), "unclassified")
        self.assertEqual(verdict_of(failed((15871, "FUNCTION 'RAND' is not supported.")), "RAND"), "not_supported")

    def test_wrong_argument_count_means_it_exists(self):
        self.assertEqual(verdict_of(failed((174, "The len function requires 1 argument(s).")), "LEN"), "exists")

    def test_not_recognized_tries_the_next_form(self):
        self.assertIsNone(verdict_of(failed((195, "'NOPE' is not a recognized built-in function name.")), "NOPE"))


if __name__ == "__main__":
    unittest.main()
