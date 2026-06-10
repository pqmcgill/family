from tests.base import FamTest
from famlib import people, standing, weeks


class TestWeeks(FamTest):
    def setUp(self):
        super().setUp()
        people.add(self.con, "manual", "P1", "adult")
        people.add(self.con, "manual", "P2", "adult")
        standing.add(self.con, "manual", "laundry: towels", kind="chore",
                     grp="laundry", owner="P1", today="2026-06-01")
        standing.add(self.con, "manual", "groceries", kind="chore",
                     owner="P2", today="2026-06-01")
        standing.add(self.con, "manual", "K1 swim", kind="commitment",
                     day="tue", time="16:00", today="2026-06-01")

    def test_new_week_drafts_from_active_standing_chores_only(self):
        wid, start = weeks.new_week(self.con, "weekly", today="2026-06-06")
        self.assertEqual(start, "2026-06-01")
        entries = weeks.entries(self.con, wid)
        self.assertEqual([e["title"] for e in entries],
                         ["laundry: towels", "groceries"])  # no commitment
        self.assertTrue(all(e["standing_id"] for e in entries))

    def test_paused_standing_not_drafted(self):
        s = standing.list_items(self.con, kind="chore")[0]
        standing.set_status(self.con, "manual", s["id"], "paused")
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-06")
        self.assertEqual([e["title"] for e in weeks.entries(self.con, wid)],
                         ["laundry: towels"])

    def test_duplicate_week_fails(self):
        weeks.new_week(self.con, "weekly", today="2026-06-06")
        with self.assertRaises(SystemExit):
            weeks.new_week(self.con, "weekly", today="2026-06-06")

    def test_add_variable_entry(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-06")
        e = weeks.add_entry(self.con, "weekly", wid, kind="personal",
                            title="P2 pottery night", owner="P2")
        self.assertEqual((e["kind"], e["standing_id"]), ("personal", None))

    def test_entry_done_touches_chore_memory(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-06")
        entry = weeks.entries(self.con, wid)[0]
        weeks.entry_done(self.con, "nightly", entry["id"], date="2026-06-03")
        r = self.con.execute(
            "SELECT * FROM chore_memory WHERE name='laundry: towels'").fetchone()
        self.assertEqual(r["last_done"], "2026-06-03")

    def test_personal_entry_done_does_not_touch_chores(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-06")
        e = weeks.add_entry(self.con, "weekly", wid, kind="personal",
                            title="gym", owner="P1")
        weeks.entry_done(self.con, "nightly", e["id"], date="2026-06-03")
        self.assertIsNone(self.con.execute(
            "SELECT * FROM chore_memory WHERE name='gym'").fetchone())

    def test_skip_does_not_alter_standing(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-06")
        entry = weeks.entries(self.con, wid)[0]
        weeks.entry_skip(self.con, "nightly", entry["id"])
        s = self.con.execute("SELECT status FROM standing WHERE id=?",
                             (entry["standing_id"],)).fetchone()
        self.assertEqual(s["status"], "active")

    def test_week_for_finds_current(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-06")
        self.assertEqual(weeks.week_for(self.con, "2026-06-04")["id"], wid)
        self.assertIsNone(weeks.week_for(self.con, "2026-06-10"))

    def test_done_entry_cannot_be_remarked(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-06")
        entry = weeks.entries(self.con, wid)[0]
        weeks.entry_done(self.con, "nightly", entry["id"], date="2026-06-03")
        with self.assertRaises(SystemExit):
            weeks.entry_done(self.con, "nightly", entry["id"],
                             date="2026-06-04")
        with self.assertRaises(SystemExit):
            weeks.entry_skip(self.con, "nightly", entry["id"])

    def test_skipped_entry_can_still_be_done(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-06")
        entry = weeks.entries(self.con, wid)[0]
        weeks.entry_skip(self.con, "nightly", entry["id"])
        after = weeks.entry_done(self.con, "nightly", entry["id"],
                                 date="2026-06-06")
        self.assertEqual(after["status"], "done")

    def test_set_note_on_existing_entry(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-06")
        entry = weeks.entries(self.con, wid)[0]
        after = weeks.set_note(self.con, "weekly", entry["id"], "wed")
        self.assertEqual(after["note"], "wed")
        refreshed = [e for e in weeks.entries(self.con, wid)
                     if e["id"] == entry["id"]][0]
        self.assertEqual(refreshed["note"], "wed")

    def test_set_note_missing_entry_fails(self):
        with self.assertRaises(SystemExit):
            weeks.set_note(self.con, "weekly", 999, "wed")


    def test_new_week_blocked_by_prior_pending_entries(self):
        weeks.new_week(self.con, "weekly", today="2026-06-06")
        with self.assertRaises(SystemExit) as cm:
            weeks.new_week(self.con, "weekly", start="2026-06-08",
                           today="2026-06-07")
        msg = str(cm.exception)
        self.assertIn("pending", msg)
        self.assertIn("laundry: towels", msg)
        self.assertIn("groceries", msg)

    def test_new_week_allowed_once_prior_week_dispositioned(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-06")
        es = weeks.entries(self.con, wid)
        weeks.entry_done(self.con, "x", es[0]["id"], date="2026-06-02")
        weeks.entry_skip(self.con, "x", es[1]["id"])
        wid2, start2 = weeks.new_week(self.con, "weekly", start="2026-06-08",
                                      today="2026-06-07")
        self.assertEqual(start2, "2026-06-08")

    def test_first_week_not_blocked(self):
        wid, start = weeks.new_week(self.con, "weekly", today="2026-06-06")
        self.assertEqual(start, "2026-06-01")

    def _disposition_all(self, wid, skip_title, date):
        for e in weeks.entries(self.con, wid):
            if e["title"] == skip_title:
                weeks.entry_skip(self.con, "x", e["id"])
            else:
                weeks.entry_done(self.con, "x", e["id"], date=date)

    def test_skip_streak_after_two_skipped_weeks(self):
        w1, _ = weeks.new_week(self.con, "weekly", today="2026-06-01")
        self._disposition_all(w1, "groceries", "2026-06-02")
        w2, _ = weeks.new_week(self.con, "weekly", start="2026-06-08",
                               today="2026-06-07")
        self._disposition_all(w2, "groceries", "2026-06-09")
        streaks = weeks.skip_streaks(self.con)
        self.assertEqual([(s["title"], s["weeks_skipped"]) for s in streaks],
                         [("groceries", 2)])

    def test_single_skip_not_flagged(self):
        w1, _ = weeks.new_week(self.con, "weekly", today="2026-06-01")
        self._disposition_all(w1, "groceries", "2026-06-02")
        self.assertEqual(weeks.skip_streaks(self.con), [])

    def test_done_resets_skip_streak(self):
        w1, _ = weeks.new_week(self.con, "weekly", today="2026-06-01")
        self._disposition_all(w1, "groceries", "2026-06-02")
        w2, _ = weeks.new_week(self.con, "weekly", start="2026-06-08",
                               today="2026-06-07")
        self._disposition_all(w2, "laundry: towels", "2026-06-09")
        self.assertEqual(weeks.skip_streaks(self.con), [])

    def test_pending_current_week_does_not_break_streak(self):
        w1, _ = weeks.new_week(self.con, "weekly", today="2026-06-01")
        self._disposition_all(w1, "groceries", "2026-06-02")
        w2, _ = weeks.new_week(self.con, "weekly", start="2026-06-08",
                               today="2026-06-07")
        self._disposition_all(w2, "groceries", "2026-06-09")
        weeks.new_week(self.con, "weekly", start="2026-06-15",
                       today="2026-06-14")  # groceries pending now
        streaks = weeks.skip_streaks(self.con)
        self.assertEqual([(s["title"], s["weeks_skipped"]) for s in streaks],
                         [("groceries", 2)])

    def test_set_day_on_entry(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-06")
        entry = weeks.entries(self.con, wid)[0]
        after = weeks.set_day(self.con, "weekly", entry["id"], "wed")
        self.assertEqual(after["day"], "wed")

    def test_set_day_rejects_garbage(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-06")
        entry = weeks.entries(self.con, wid)[0]
        with self.assertRaises(SystemExit):
            weeks.set_day(self.con, "weekly", entry["id"], "wednesday")

    def test_set_day_missing_entry_fails(self):
        with self.assertRaises(SystemExit):
            weeks.set_day(self.con, "weekly", 999, "wed")

    def test_add_entry_with_day(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-06")
        e = weeks.add_entry(self.con, "weekly", wid, kind="oneoff",
                            title="fix gate", day="sat")
        self.assertEqual(e["day"], "sat")
        with self.assertRaises(SystemExit):
            weeks.add_entry(self.con, "weekly", wid, kind="oneoff",
                            title="bad day", day="caturday")

    def test_entry_linked_to_todo_cascades_on_done(self):
        from famlib import todos
        t = todos.add(self.con, "manual", "reset attic", today="2026-06-01")
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-01")
        e = weeks.add_entry(self.con, "weekly", wid, kind="oneoff",
                            title="reset attic", todo_id=t["id"])
        self.assertEqual(e["todo_id"], t["id"])
        weeks.entry_done(self.con, "x", e["id"], date="2026-06-02")
        row = self.con.execute("SELECT status, resolved FROM todos WHERE id=?",
                               (t["id"],)).fetchone()
        self.assertEqual((row["status"], row["resolved"]),
                         ("done", "2026-06-02"))

    def test_add_entry_rejects_missing_or_resolved_todo(self):
        from famlib import todos
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-01")
        with self.assertRaises(SystemExit):
            weeks.add_entry(self.con, "weekly", wid, kind="oneoff",
                            title="ghost", todo_id=999)
        t = todos.add(self.con, "manual", "already handled",
                      today="2026-06-01")
        todos.done(self.con, "manual", t["id"], today="2026-06-01")
        with self.assertRaises(SystemExit):
            weeks.add_entry(self.con, "weekly", wid, kind="oneoff",
                            title="already handled", todo_id=t["id"])

    def test_entry_done_tolerates_already_done_todo(self):
        from famlib import todos
        t = todos.add(self.con, "manual", "reset attic", today="2026-06-01")
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-01")
        e = weeks.add_entry(self.con, "weekly", wid, kind="oneoff",
                            title="reset attic", todo_id=t["id"])
        todos.done(self.con, "manual", t["id"], today="2026-06-01")
        after = weeks.entry_done(self.con, "x", e["id"], date="2026-06-02")
        self.assertEqual(after["status"], "done")

    def test_link_existing_entry_to_todo(self):
        from famlib import todos
        t = todos.add(self.con, "manual", "reset attic", today="2026-06-01")
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-01")
        e = weeks.add_entry(self.con, "weekly", wid, kind="oneoff",
                            title="reset attic")
        after = weeks.set_todo(self.con, "manual", e["id"], t["id"])
        self.assertEqual(after["todo_id"], t["id"])
        weeks.entry_done(self.con, "x", e["id"], date="2026-06-02")
        row = self.con.execute("SELECT status FROM todos WHERE id=?",
                               (t["id"],)).fetchone()
        self.assertEqual(row["status"], "done")

    def test_link_rejects_resolved_todo(self):
        from famlib import todos
        t = todos.add(self.con, "manual", "x", today="2026-06-01")
        todos.done(self.con, "manual", t["id"], today="2026-06-01")
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-01")
        e = weeks.add_entry(self.con, "weekly", wid, kind="oneoff", title="x")
        with self.assertRaises(SystemExit):
            weeks.set_todo(self.con, "manual", e["id"], t["id"])

    def test_set_stage_tracks_stage_and_date(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-01")
        e = weeks.entries(self.con, wid)[0]
        after = weeks.set_stage(self.con, "nightly", e["id"], "dry",
                                date="2026-06-02")
        self.assertEqual(after["stage"], "dry")
        self.assertEqual(after["stage_date"], "2026-06-02")

    def test_set_stage_rejects_garbage_and_done_entries(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-01")
        e = weeks.entries(self.con, wid)[0]
        with self.assertRaises(SystemExit):
            weeks.set_stage(self.con, "nightly", e["id"], "soak")
        with self.assertRaises(SystemExit):
            weeks.set_stage(self.con, "nightly", 999, "dry")
        weeks.entry_done(self.con, "x", e["id"], date="2026-06-02")
        with self.assertRaises(SystemExit):
            weeks.set_stage(self.con, "nightly", e["id"], "dry")

    def test_stuck_stages_flags_old_pending_only(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-01")
        es = weeks.entries(self.con, wid)
        weeks.set_stage(self.con, "x", es[0]["id"], "dry", date="2026-06-01")
        weeks.set_stage(self.con, "x", es[1]["id"], "wash", date="2026-06-03")
        stuck = weeks.stuck_stages(self.con, "2026-06-03")
        self.assertEqual([(s["title"], s["stage"], s["days"]) for s in stuck],
                         [(es[0]["title"], "dry", 2)])
        weeks.entry_done(self.con, "x", es[0]["id"], date="2026-06-03")
        self.assertEqual(weeks.stuck_stages(self.con, "2026-06-03"), [])
