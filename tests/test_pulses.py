from tests.base import FamTest
from famlib import people, pulses


class TestPulses(FamTest):
    def setUp(self):
        super().setUp()
        people.add(self.con, "manual", "P1", "adult")
        people.add(self.con, "manual", "K1", "kid")

    def test_log_basic(self):
        row = pulses.log(self.con, "nightly", "P1", 7, note="long day",
                         date="2026-06-06")
        self.assertEqual((row["rating"], row["note"]), (7, "long day"))

    def test_same_day_relog_overwrites(self):
        pulses.log(self.con, "nightly", "P1", 7, date="2026-06-06")
        pulses.log(self.con, "nightly", "P1", 4, date="2026-06-06")
        rows = self.con.execute("SELECT * FROM pulses").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["rating"], 4)

    def test_rating_bounds(self):
        for bad in (0, 11):
            with self.assertRaises(SystemExit):
                pulses.log(self.con, "nightly", "P1", bad, date="2026-06-06")

    def test_adults_only(self):
        with self.assertRaises(SystemExit):
            pulses.log(self.con, "nightly", "K1", 5, date="2026-06-06")

    def test_recent_window(self):
        pulses.log(self.con, "nightly", "P1", 5, date="2026-05-01")
        pulses.log(self.con, "nightly", "P1", 8, date="2026-06-05")
        recent = pulses.recent(self.con, "2026-06-06", days=7)
        self.assertEqual([r["rating"] for r in recent], [8])

    def test_bool_rating_refused(self):
        with self.assertRaises(SystemExit):
            pulses.log(self.con, "nightly", "P1", True, date="2026-06-06")

    def test_unknown_person_refused(self):
        with self.assertRaises(SystemExit):
            pulses.log(self.con, "nightly", "ghost", 5, date="2026-06-06")

    def test_recent_window_is_seven_days_inclusive_of_today(self):
        pulses.log(self.con, "nightly", "P1", 3, date="2026-05-31")  # 6 days ago: in
        pulses.log(self.con, "nightly", "P1", 9, date="2026-05-30")  # 7 days ago: out
        ratings = [r["rating"] for r in
                   pulses.recent(self.con, "2026-06-06", days=7)]
        self.assertEqual(ratings, [3])
