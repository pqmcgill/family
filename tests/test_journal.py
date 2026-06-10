import os
import pathlib
from tests.base import FamTest
from famlib import journal


class TestJournal(FamTest):
    def test_add_and_search(self):
        journal.add(self.con, "nightly", session="nightly", kind="summary",
                    text="we talked about the gutters and laundry",
                    date="2026-06-06")
        hits = journal.search(self.con, "gutters")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["date"], "2026-06-06")

    def test_add_stores_text_verbatim_and_returns_row(self):
        row = journal.add(
            self.con, "capture", session="capture", kind="transcript",
            text="P1 said he would do it", date="2026-06-06")
        self.assertEqual(row["text"], "P1 said he would do it")
        self.assertEqual(row["session"], "capture")

    def test_bad_session_or_kind_fails(self):
        with self.assertRaises(SystemExit):
            journal.add(self.con, "x", session="daily", kind="summary",
                        text="t", date="2026-06-06")
        with self.assertRaises(SystemExit):
            journal.add(self.con, "x", session="nightly", kind="poem",
                        text="t", date="2026-06-06")

    def test_search_no_hits(self):
        self.assertEqual(journal.search(self.con, "unicorn"), [])

    def test_search_handles_quotes(self):
        journal.add(self.con, "x", session="nightly", kind="summary",
                    text='she said "maybe later"', date="2026-06-06")
        self.assertEqual(len(journal.search(self.con, 'maybe "later')), 1)

    def test_empty_text_refused(self):
        for bad in (None, "", "   "):
            with self.assertRaises(SystemExit):
                journal.add(self.con, "x", session="nightly", kind="summary",
                            text=bad, date="2026-06-06")

    def test_list_entries_full_text_ordered_by_date(self):
        long_text = "gutters " + "y" * 300
        journal.add(self.con, "weekly", session="weekly", kind="summary",
                    text=long_text, date="2026-06-05")
        journal.add(self.con, "nightly", session="nightly", kind="summary",
                    text="second entry", date="2026-06-06")
        rows = journal.list_entries(self.con)
        self.assertEqual([r["text"] for r in rows],
                         [long_text, "second entry"])

    def test_list_entries_days_filter(self):
        journal.add(self.con, "nightly", session="nightly", kind="summary",
                    text="old", date="2026-06-01")
        journal.add(self.con, "nightly", session="nightly", kind="summary",
                    text="recent", date="2026-06-06")
        rows = journal.list_entries(self.con, days=3, today="2026-06-07")
        self.assertEqual([r["text"] for r in rows], ["recent"])

    def test_last_session_date(self):
        journal.add(self.con, "nightly", session="nightly", kind="summary",
                    text="a", date="2026-06-03")
        journal.add(self.con, "nightly", session="nightly", kind="summary",
                    text="b", date="2026-06-05")
        self.assertEqual(journal.last_session_date(self.con, "nightly"),
                         "2026-06-05")
        self.assertIsNone(journal.last_session_date(self.con, "weekly"))
