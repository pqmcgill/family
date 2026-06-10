from tests.base import FamTest
from famlib import calendar_items as cal
from famlib import people


class TestCalendar(FamTest):
    def setUp(self):
        super().setUp()
        people.add(self.con, "manual", "K1", "kid")

    def test_add_requires_valid_date(self):
        with self.assertRaises(SystemExit):
            cal.add(self.con, "manual", "dentist", date="tomorrow",
                    today="2026-06-06")

    def test_add_full(self):
        row = cal.add(self.con, "manual", "swim class", date="2026-06-09",
                      time="16:00", who="K1", today="2026-06-06")
        self.assertEqual(row["status"], "scheduled")
        self.assertEqual(row["who_id"], 1)

    def test_cancel_and_done(self):
        row = cal.add(self.con, "manual", "x", date="2026-06-09",
                      today="2026-06-06")
        self.assertEqual(
            cal.cancel(self.con, "manual", row["id"])["status"], "cancelled")
        row2 = cal.add(self.con, "manual", "y", date="2026-06-09",
                       today="2026-06-06")
        self.assertEqual(
            cal.done(self.con, "manual", row2["id"])["status"], "done")

    def test_upcoming_window_and_all(self):
        cal.add(self.con, "manual", "near", date="2026-06-10", today="2026-06-06")
        cal.add(self.con, "manual", "far", date="2026-09-01", today="2026-06-06")
        cal.add(self.con, "manual", "past", date="2026-06-01", today="2026-06-06")
        near = cal.upcoming(self.con, "2026-06-06", days=14)
        self.assertEqual([r["title"] for r in near], ["near"])
        allfuture = cal.upcoming(self.con, "2026-06-06", days=None)
        self.assertEqual([r["title"] for r in allfuture], ["near", "far"])

    def test_terminal_status_transitions_refused(self):
        row = cal.add(self.con, "manual", "x", date="2026-06-09",
                      today="2026-06-06")
        cal.done(self.con, "manual", row["id"])
        with self.assertRaises(SystemExit):
            cal.cancel(self.con, "manual", row["id"])

    def test_bad_time_refused(self):
        with self.assertRaises(SystemExit):
            cal.add(self.con, "manual", "x", date="2026-06-09",
                    time="25:99", today="2026-06-06")
