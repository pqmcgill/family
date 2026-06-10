import os
import unittest
from tests.base import FamTest
from famlib import dates


class TestSchema(FamTest):
    def test_tables_exist(self):
        names = {r[0] for r in self.con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        for t in ["people", "todos", "calendar", "standing", "weeks",
                  "week_entries", "chore_memory", "pulses", "journal",
                  "journal_fts", "observations", "events"]:
            self.assertIn(t, names)

    def test_db_lives_under_fam_home(self):
        from famlib import db
        self.assertTrue(str(db.db_path()).startswith(os.environ["FAM_HOME"]))

    def test_connect_is_idempotent(self):
        from famlib import db
        con2 = db.connect()  # second connect must not fail on CREATE
        con2.close()

    def test_journal_fts_roundtrip(self):
        with self.con:
            self.con.execute(
                "INSERT INTO journal(date, session, kind, text)"
                " VALUES ('2026-06-06', 'nightly', 'summary', 'we fixed the gutters')")
        hit = self.con.execute(
            "SELECT rowid FROM journal_fts WHERE journal_fts MATCH 'gutters'").fetchone()
        self.assertIsNotNone(hit)
        with self.con:
            self.con.execute("DELETE FROM journal")
        self.assertIsNone(self.con.execute(
            "SELECT rowid FROM journal_fts WHERE journal_fts MATCH 'gutters'").fetchone())


class TestDates(unittest.TestCase):
    def test_parse_rejects_garbage(self):
        with self.assertRaises(SystemExit):
            dates.parse("06/06/2026")

    def test_week_start_is_monday(self):
        self.assertEqual(dates.week_start("2026-06-06"), "2026-06-01")  # Sat -> Mon
        self.assertEqual(dates.week_start("2026-06-01"), "2026-06-01")  # Mon -> itself

    def test_days_until(self):
        self.assertEqual(dates.days_until("2026-06-06", "2026-06-20"), 14)

    def test_add_days(self):
        self.assertEqual(dates.add_days("2026-06-06", -7), "2026-05-30")

    def test_parse_time(self):
        self.assertEqual(dates.parse_time("16:00"), "16:00")
        self.assertIsNone(dates.parse_time(None))
        for bad in ("25:00", "9:00", "banana"):
            with self.assertRaises(SystemExit):
                dates.parse_time(bad)


class TestDow(FamTest):
    def test_dow_names_weekday(self):
        self.assertEqual(dates.dow("2026-06-08"), "mon")
        self.assertEqual(dates.dow("2026-06-10"), "wed")
        self.assertEqual(dates.dow("2026-06-14"), "sun")


class TestMigration(unittest.TestCase):
    def test_connect_adds_day_column_to_old_week_entries(self):
        import pathlib
        import sqlite3
        import tempfile
        from famlib import db
        with tempfile.TemporaryDirectory() as tmp:
            prior = os.environ.get("FAM_HOME")
            os.environ["FAM_HOME"] = tmp
            try:
                d = pathlib.Path(tmp) / "data"
                d.mkdir()
                raw = sqlite3.connect(str(d / "family.db"))
                raw.execute(
                    "CREATE TABLE week_entries(id INTEGER PRIMARY KEY,"
                    " week_id INTEGER NOT NULL, kind TEXT NOT NULL,"
                    " title TEXT NOT NULL, owner_id INTEGER,"
                    " standing_id INTEGER,"
                    " status TEXT NOT NULL DEFAULT 'pending',"
                    " note TEXT, done_date TEXT)")
                raw.commit()
                raw.close()
                con = db.connect()
                cols = {r["name"] for r in con.execute(
                    "PRAGMA table_info(week_entries)")}
                self.assertIn("day", cols)
                self.assertIn("todo_id", cols)
                self.assertIn("stage", cols)
                self.assertIn("stage_date", cols)
                con.close()
            finally:
                if prior is None:
                    os.environ.pop("FAM_HOME", None)
                else:
                    os.environ["FAM_HOME"] = prior


class TestRollover(unittest.TestCase):
    def test_evening_is_today(self):
        from datetime import datetime
        self.assertEqual(dates.effective_today(datetime(2026, 6, 10, 22, 30)),
                         "2026-06-10")

    def test_before_4am_counts_as_previous_night(self):
        from datetime import datetime
        self.assertEqual(dates.effective_today(datetime(2026, 6, 11, 0, 30)),
                         "2026-06-10")
        self.assertEqual(dates.effective_today(datetime(2026, 6, 11, 3, 59)),
                         "2026-06-10")

    def test_4am_boundary_is_new_day(self):
        from datetime import datetime
        self.assertEqual(dates.effective_today(datetime(2026, 6, 11, 4, 0)),
                         "2026-06-11")

    def test_today_uses_rollover(self):
        # today() must route through effective_today, not date.today()
        import famlib.dates as d
        self.assertEqual(d.today(), d.effective_today())
