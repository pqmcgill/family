from tests.base import FamTest
from famlib import people, standing


class TestStanding(FamTest):
    def setUp(self):
        super().setUp()
        people.add(self.con, "manual", "P1", "adult")

    def test_add_chore_with_group(self):
        row = standing.add(self.con, "manual", "laundry: K1 clothes",
                           kind="chore", grp="laundry", owner="P1",
                           today="2026-06-06")
        self.assertEqual((row["kind"], row["grp"], row["status"]),
                         ("chore", "laundry", "active"))

    def test_add_commitment_with_day_time(self):
        row = standing.add(self.con, "manual", "K1 swim class",
                           kind="commitment", day="tue", time="16:00",
                           today="2026-06-06")
        self.assertEqual((row["day"], row["time"]), ("tue", "16:00"))

    def test_add_rejects_bad_kind_and_day(self):
        with self.assertRaises(SystemExit):
            standing.add(self.con, "manual", "x", kind="ritual",
                         today="2026-06-06")
        with self.assertRaises(SystemExit):
            standing.add(self.con, "manual", "x", kind="commitment",
                         day="someday", today="2026-06-06")

    def test_pause_resume_retire(self):
        row = standing.add(self.con, "manual", "x", kind="chore",
                           today="2026-06-06")
        self.assertEqual(
            standing.set_status(self.con, "manual", row["id"], "paused")["status"],
            "paused")
        self.assertEqual(
            standing.set_status(self.con, "manual", row["id"], "active")["status"],
            "active")
        self.assertEqual(
            standing.set_status(self.con, "manual", row["id"], "retired")["status"],
            "retired")

    def test_list_active_filters(self):
        a = standing.add(self.con, "manual", "a", kind="chore", today="2026-06-06")
        standing.add(self.con, "manual", "b", kind="chore", today="2026-06-06")
        standing.set_status(self.con, "manual", a["id"], "retired")
        self.assertEqual(
            [s["title"] for s in standing.list_items(self.con, status="active")],
            ["b"])
        self.assertEqual(len(standing.list_items(self.con)), 2)

    def test_bad_time_refused(self):
        with self.assertRaises(SystemExit):
            standing.add(self.con, "manual", "x", kind="commitment",
                         day="tue", time="25:99", today="2026-06-06")

    def test_same_status_noop_refused(self):
        row = standing.add(self.con, "manual", "x", kind="chore",
                           today="2026-06-06")
        with self.assertRaises(SystemExit):
            standing.set_status(self.con, "manual", row["id"], "active")

    def test_grp_normalized(self):
        row = standing.add(self.con, "manual", "towels", kind="chore",
                           grp="  Laundry ", today="2026-06-06")
        self.assertEqual(row["grp"], "laundry")
