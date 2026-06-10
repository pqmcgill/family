from tests.base import FamTest
from famlib import chores


class TestChores(FamTest):
    def test_touch_creates_then_learns_cadence(self):
        chores.touch(self.con, "manual", "laundry: towels", "2026-06-01")
        r = self.con.execute("SELECT * FROM chore_memory").fetchone()
        self.assertEqual((r["times_done"], r["cadence_days"]), (1, None))
        chores.touch(self.con, "manual", "laundry: towels", "2026-06-08")
        r = self.con.execute("SELECT * FROM chore_memory").fetchone()
        self.assertEqual(r["cadence_days"], 7.0)  # first interval becomes cadence
        chores.touch(self.con, "manual", "laundry: towels", "2026-06-11")
        r = self.con.execute("SELECT * FROM chore_memory").fetchone()
        self.assertEqual(r["cadence_days"], 5.0)  # blend: 0.5*7 + 0.5*3
        self.assertEqual(r["last_done"], "2026-06-11")

    def test_set_cadence_declares_explicitly(self):
        chores.touch(self.con, "manual", "bedding", "2026-06-01")
        chores.set_cadence(self.con, "manual", "bedding", 14)
        r = self.con.execute("SELECT * FROM chore_memory").fetchone()
        self.assertEqual(r["cadence_days"], 14.0)

    def test_set_cadence_unknown_chore_fails(self):
        with self.assertRaises(SystemExit):
            chores.set_cadence(self.con, "manual", "ghost", 7)

    def test_neglected_flags_only_past_threshold(self):
        chores.touch(self.con, "manual", "bedding", "2026-05-01")
        chores.set_cadence(self.con, "manual", "bedding", 14)
        chores.touch(self.con, "manual", "dishes", "2026-06-05")
        chores.set_cadence(self.con, "manual", "dishes", 1)
        flagged = chores.neglected(self.con, "2026-06-06")
        names = [f["name"] for f in flagged]
        self.assertIn("bedding", names)       # 36 days > 14*1.5
        self.assertNotIn("dishes", names)     # 1 day  <= 1.5

    def test_no_cadence_means_no_flag(self):
        chores.touch(self.con, "manual", "new thing", "2026-01-01")
        self.assertEqual(chores.neglected(self.con, "2026-06-06"), [])

    def test_backdated_touch_does_not_regress_last_done(self):
        chores.touch(self.con, "manual", "towels", "2026-06-08")
        chores.touch(self.con, "manual", "towels", "2026-06-15")
        chores.touch(self.con, "manual", "towels", "2026-06-01")  # backdated
        r = self.con.execute("SELECT * FROM chore_memory").fetchone()
        self.assertEqual(r["last_done"], "2026-06-15")
        self.assertEqual(r["cadence_days"], 7.0)  # unchanged by backdate
        self.assertEqual(r["times_done"], 3)      # still counted

    def test_empty_name_refused(self):
        with self.assertRaises(SystemExit):
            chores.touch(self.con, "manual", "  ", "2026-06-01")

    def test_nonpositive_cadence_refused(self):
        chores.touch(self.con, "manual", "bedding", "2026-06-01")
        with self.assertRaises(SystemExit):
            chores.set_cadence(self.con, "manual", "bedding", -7)

    def test_never_done_flagged_after_grace(self):
        from famlib import standing
        standing.add(self.con, "manual", "mop floors", kind="chore",
                     today="2026-05-20")
        flags = chores.never_done(self.con, "2026-06-06")
        self.assertEqual([f["title"] for f in flags], ["mop floors"])
        self.assertEqual(flags[0]["days"], 17)

    def test_never_done_quiet_within_grace(self):
        from famlib import standing
        standing.add(self.con, "manual", "mop floors", kind="chore",
                     today="2026-06-01")
        self.assertEqual(chores.never_done(self.con, "2026-06-06"), [])

    def test_done_chore_not_in_never_done(self):
        from famlib import standing
        standing.add(self.con, "manual", "mop floors", kind="chore",
                     today="2026-05-01")
        chores.touch(self.con, "manual", "mop floors", "2026-06-01")
        self.assertEqual(chores.never_done(self.con, "2026-06-06"), [])

    def test_paused_chore_not_in_never_done(self):
        from famlib import standing
        s = standing.add(self.con, "manual", "mop floors", kind="chore",
                         today="2026-05-01")
        standing.set_status(self.con, "manual", s["id"], "paused")
        self.assertEqual(chores.never_done(self.con, "2026-06-06"), [])
