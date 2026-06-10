import sqlite3

from tests.base import FamTest
from famlib import events, people, time_log


class TestTimeLogSchema(FamTest):
    def test_table_exists_and_events_allowlisted(self):
        self.con.execute(
            "INSERT INTO time_log(date, kind, level, person_id, note)"
            " VALUES ('2026-06-06', 'personal', 'partial', NULL, NULL)")
        self.assertIn("time_log", events.TABLES)
        snap = events.snapshot(self.con, "time_log", 1)
        self.assertEqual(set(snap.keys()),
                         {"id", "date", "kind", "level", "person_id", "note"})
        self.assertEqual(snap["kind"], "personal")

    def test_kind_and_level_check_constraints(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute(
                "INSERT INTO time_log(date, kind) VALUES ('2026-06-06', 'nap')")
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute(
                "INSERT INTO time_log(date, kind, level)"
                " VALUES ('2026-06-06', 'personal', 'huge')")
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute("INSERT INTO time_log(kind) VALUES ('family')")


class TestTimeLogAdd(FamTest):
    def setUp(self):
        super().setUp()
        people.add(self.con, "manual", "P1", "adult")
        people.add(self.con, "manual", "K1", "kid")

    def test_personal_defaults_to_partial(self):
        row = time_log.add(self.con, "nightly", "personal", who="P1",
                           date="2026-06-06")
        self.assertEqual(row["level"], "partial")
        pid = self.con.execute(
            "SELECT id FROM people WHERE alias='P1'").fetchone()[0]
        self.assertEqual(row["person_id"], pid)

    def test_personal_full(self):
        row = time_log.add(self.con, "nightly", "personal", who="P1",
                           level="full", date="2026-06-06", note="long hike")
        self.assertEqual((row["level"], row["note"]), ("full", "long hike"))

    def test_personal_requires_person(self):
        with self.assertRaises(SystemExit):
            time_log.add(self.con, "nightly", "personal", date="2026-06-06")

    def test_personal_adults_only(self):
        with self.assertRaises(SystemExit):
            time_log.add(self.con, "nightly", "personal", who="K1",
                         date="2026-06-06")

    def test_personal_unknown_person(self):
        with self.assertRaises(SystemExit):
            time_log.add(self.con, "nightly", "personal", who="ghost",
                         date="2026-06-06")

    def test_couple_is_household_level(self):
        row = time_log.add(self.con, "nightly", "couple", date="2026-06-06")
        self.assertIsNone(row["person_id"])
        self.assertIsNone(row["level"])
        row = time_log.add(self.con, "nightly", "family", date="2026-06-06")
        self.assertIsNone(row["person_id"])
        self.assertIsNone(row["level"])

    def test_couple_refuses_person_and_level(self):
        with self.assertRaises(SystemExit):
            time_log.add(self.con, "nightly", "couple", who="P1",
                         date="2026-06-06")
        with self.assertRaises(SystemExit):
            time_log.add(self.con, "nightly", "family", level="full",
                         date="2026-06-06")

    def test_invalid_kind_and_level_and_date(self):
        with self.assertRaises(SystemExit):
            time_log.add(self.con, "nightly", "nap", date="2026-06-06")
        with self.assertRaises(SystemExit):
            time_log.add(self.con, "nightly", "personal", who="P1",
                         level="huge", date="2026-06-06")
        with self.assertRaises(SystemExit):
            time_log.add(self.con, "nightly", "personal", who="P1",
                         date="June 6th")

    def test_add_is_undoable(self):
        time_log.add(self.con, "nightly", "family", date="2026-06-06")
        events.undo(self.con)
        n = self.con.execute("SELECT COUNT(*) FROM time_log").fetchone()[0]
        self.assertEqual(n, 0)


class TestTimeLogRecent(FamTest):
    def setUp(self):
        super().setUp()
        people.add(self.con, "manual", "P1", "adult")

    def test_recent_window_and_alias_join(self):
        time_log.add(self.con, "nightly", "personal", who="P1",
                     date="2026-06-05")
        time_log.add(self.con, "nightly", "family", date="2026-05-01")
        rows = time_log.recent(self.con, "2026-06-06", days=14)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["alias"], "P1")

    def test_recent_newest_first_and_null_alias(self):
        time_log.add(self.con, "nightly", "couple", date="2026-06-01")
        time_log.add(self.con, "nightly", "family", date="2026-06-04")
        rows = time_log.recent(self.con, "2026-06-06", days=14)
        self.assertEqual([r["kind"] for r in rows], ["family", "couple"])
        self.assertIsNone(rows[0]["alias"])
