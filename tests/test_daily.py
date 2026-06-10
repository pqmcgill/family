from tests.base import FamTest
from famlib import daily, events


class TestDaily(FamTest):
    def test_schema_tables_exist(self):
        names = {r["name"] for r in self.con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertIn("daily_habits", names)
        self.assertIn("daily_log", names)

    def test_tables_in_events_allowlist(self):
        self.assertIn("daily_habits", events.TABLES)
        self.assertIn("daily_log", events.TABLES)

    def test_add_habit_creates_row_and_event(self):
        row = daily.add_habit(self.con, "manual", "spending review",
                              today="2026-06-08")
        self.assertEqual(row["name"], "spending review")
        self.assertEqual(row["status"], "active")
        self.assertEqual(row["created"], "2026-06-08")
        ev = self.con.execute(
            "SELECT * FROM events WHERE entity='daily_habits'").fetchone()
        self.assertEqual(ev["action"], "add")

    def test_add_duplicate_name_refused(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        with self.assertRaises(SystemExit):
            daily.add_habit(self.con, "manual", "spending review",
                            today="2026-06-09")

    def test_add_empty_name_refused(self):
        with self.assertRaises(SystemExit):
            daily.add_habit(self.con, "manual", "   ", today="2026-06-08")

    def test_list_habits(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        names = [h["name"] for h in daily.list_habits(self.con)]
        self.assertEqual(names, ["spending review"])

    def test_log_inserts_row_and_event(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        row = daily.log(self.con, "nightly", "spending review",
                        date="2026-06-08", note="reviewed")
        self.assertEqual(row["date"], "2026-06-08")
        self.assertEqual(row["note"], "reviewed")
        n = self.con.execute("SELECT COUNT(*) AS n FROM daily_log").fetchone()
        self.assertEqual(n["n"], 1)
        ev = self.con.execute(
            "SELECT * FROM events WHERE entity='daily_log'").fetchone()
        self.assertEqual(ev["action"], "log")

    def test_log_idempotent_per_night(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        daily.log(self.con, "nightly", "spending review", date="2026-06-08")
        daily.log(self.con, "nightly", "spending review", date="2026-06-08",
                  note="updated")
        rows = self.con.execute("SELECT * FROM daily_log").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["note"], "updated")

    def test_relog_without_note_preserves_existing(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        daily.log(self.con, "nightly", "spending review", date="2026-06-08",
                  note="first")
        daily.log(self.con, "nightly", "spending review", date="2026-06-08")
        row = self.con.execute("SELECT * FROM daily_log").fetchone()
        self.assertEqual(row["note"], "first")  # not wiped to NULL

    def test_log_unknown_habit_refused(self):
        with self.assertRaises(SystemExit):
            daily.log(self.con, "nightly", "ghost", date="2026-06-08")

    def test_log_retired_habit_refused(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        daily.retire_habit(self.con, "manual", "spending review")
        with self.assertRaises(SystemExit):
            daily.log(self.con, "nightly", "spending review",
                      date="2026-06-08")

    def test_retire_habit(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        row = daily.retire_habit(self.con, "manual", "spending review")
        self.assertEqual(row["status"], "retired")

    def test_retire_unknown_refused(self):
        with self.assertRaises(SystemExit):
            daily.retire_habit(self.con, "manual", "ghost")

    def test_retire_already_retired_refused(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        daily.retire_habit(self.con, "manual", "spending review")
        with self.assertRaises(SystemExit):
            daily.retire_habit(self.con, "manual", "spending review")

    def test_neglect_created_today_logged(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        daily.log(self.con, "nightly", "spending review", date="2026-06-08")
        f = daily.neglect(self.con, "2026-06-08")[0]
        self.assertTrue(f["logged_today"])
        self.assertEqual(f["miss_streak"], 0)
        self.assertEqual(f["total_missed"], 0)
        self.assertEqual(f["elapsed"], 0)

    def test_neglect_created_today_not_logged_has_grace(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        f = daily.neglect(self.con, "2026-06-08")[0]
        self.assertFalse(f["logged_today"])
        self.assertEqual(f["miss_streak"], 0)
        self.assertEqual(f["total_missed"], 0)

    def test_neglect_counts_streak_and_total(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-01")
        daily.log(self.con, "nightly", "spending review", date="2026-06-02")
        daily.log(self.con, "nightly", "spending review", date="2026-06-05")
        f = daily.neglect(self.con, "2026-06-08")[0]
        self.assertEqual(f["elapsed"], 7)
        self.assertEqual(f["total_missed"], 5)
        self.assertEqual(f["miss_streak"], 2)
        self.assertFalse(f["logged_today"])

    def test_neglect_never_logged_streak_equals_elapsed(self):
        # created 3 days before today, zero logs
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-05")
        f = daily.neglect(self.con, "2026-06-08")[0]
        self.assertEqual(f["elapsed"], 3)        # 05,06,07
        self.assertEqual(f["total_missed"], 3)
        self.assertEqual(f["miss_streak"], 3)    # streak stops at created, not negative
        self.assertFalse(f["logged_today"])

    def test_neglect_skips_retired(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-01")
        daily.retire_habit(self.con, "manual", "spending review")
        self.assertEqual(daily.neglect(self.con, "2026-06-08"), [])

    def test_undo_reverses_log(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        daily.log(self.con, "nightly", "spending review", date="2026-06-08")
        events.undo(self.con, 1)
        n = self.con.execute("SELECT COUNT(*) AS n FROM daily_log").fetchone()
        self.assertEqual(n["n"], 0)

    def test_undo_reverses_add(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        events.undo(self.con, 1)
        n = self.con.execute(
            "SELECT COUNT(*) AS n FROM daily_habits").fetchone()
        self.assertEqual(n["n"], 0)

    def test_check_replays_clean(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        daily.log(self.con, "nightly", "spending review", date="2026-06-08")
        self.assertEqual(events.check(self.con), [])

    def test_streaks_counts_consecutive_nights(self):
        daily.add_habit(self.con, "manual", "tidy", today="2026-06-01")
        for d in ("2026-06-02", "2026-06-03", "2026-06-04"):
            daily.log(self.con, "nightly", "tidy", date=d)
        self.assertEqual(daily.streaks(self.con, "2026-06-04"),
                         [{"name": "tidy", "nights": 3}])

    def test_streak_ending_yesterday_still_counts(self):
        daily.add_habit(self.con, "manual", "tidy", today="2026-06-01")
        for d in ("2026-06-02", "2026-06-03"):
            daily.log(self.con, "nightly", "tidy", date=d)
        self.assertEqual(daily.streaks(self.con, "2026-06-04"),
                         [{"name": "tidy", "nights": 2}])

    def test_single_night_or_broken_streak_not_reported(self):
        daily.add_habit(self.con, "manual", "tidy", today="2026-06-01")
        daily.log(self.con, "nightly", "tidy", date="2026-06-02")
        self.assertEqual(daily.streaks(self.con, "2026-06-02"), [])
        daily.log(self.con, "nightly", "tidy", date="2026-06-04")
        self.assertEqual(daily.streaks(self.con, "2026-06-06"), [])
