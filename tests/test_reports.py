from tests.base import FamTest
from famlib import (calendar_items as cal, daily, people, pulses, reports,
                    standing, todos, weeks)
from famlib import time_log


class TestReports(FamTest):
    def setUp(self):
        super().setUp()
        people.add(self.con, "manual", "P1", "adult")
        people.add(self.con, "manual", "P2", "adult")

    def test_checkin_sections_have_counts(self):
        todos.add(self.con, "manual", "call plumber", today="2026-06-06")
        todos.add(self.con, "manual", "renew passport", due="2026-10-01",
                  today="2026-06-06")
        out = reports.checkin(self.con, "2026-06-06")
        self.assertIn("OPEN TODOS (2 of 2 shown)", out)
        self.assertIn("call plumber", out)
        self.assertIn("NO WEEK PLAN", out)

    def test_checkin_shows_week_plan_and_commitments(self):
        standing.add(self.con, "manual", "groceries", kind="chore",
                     owner="P1", today="2026-06-01")
        standing.add(self.con, "manual", "K-swim", kind="commitment",
                     day="tue", time="16:00", today="2026-06-01")
        weeks.new_week(self.con, "weekly", today="2026-06-06")
        out = reports.checkin(self.con, "2026-06-06")
        self.assertIn("WEEK PLAN", out)
        self.assertIn("groceries", out)
        self.assertIn("K-swim", out)
        self.assertIn("(1 of 1 shown)", out)

    def test_horizon_includes_far_future_and_undated_and_parked(self):
        todos.add(self.con, "manual", "far future", due="2027-01-15",
                  today="2026-06-06")
        todos.add(self.con, "manual", "undated thing", today="2026-06-06")
        t = todos.add(self.con, "manual", "parked thing", today="2026-06-06")
        todos.defer(self.con, "manual", t["id"])
        cal.add(self.con, "manual", "wedding", date="2026-12-12",
                today="2026-06-06")
        out = reports.horizon(self.con, "2026-06-06")
        self.assertIn("far future", out)
        self.assertIn("in 223 days", out)      # 2026-06-06 -> 2027-01-15
        self.assertIn("undated thing", out)
        self.assertIn("parked thing", out)
        self.assertIn("wedding", out)
        self.assertIn("DATED ITEMS (2 of 2 shown)", out)

    def test_fair_compares_adults(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-06")
        e1 = weeks.add_entry(self.con, "weekly", wid, kind="personal",
                             title="gym", owner="P1")
        weeks.add_entry(self.con, "weekly", wid, kind="personal",
                        title="pottery", owner="P2")
        weeks.entry_done(self.con, "nightly", e1["id"], date="2026-06-03")
        pulses.log(self.con, "nightly", "P1", 8, date="2026-06-05")
        pulses.log(self.con, "nightly", "P2", 4, date="2026-06-05")
        out = reports.fair(self.con, "2026-06-06", weeks_back=4)
        self.assertIn("P1: 1/1 personal blocks", out)
        self.assertIn("P2: 0/1 personal blocks", out)
        self.assertIn("avg pulse 8.0", out)
        self.assertIn("avg pulse 4.0", out)

    def test_overdue_calendar_never_vanishes(self):
        cal.add(self.con, "manual", "missed dentist", date="2026-06-01",
                today="2026-05-20")
        out = reports.checkin(self.con, "2026-06-06")
        self.assertIn("missed dentist", out)
        self.assertIn("UNRESOLVED CALENDAR", out)
        self.assertIn("(5 days ago)", out)
        hout = reports.horizon(self.con, "2026-06-06")
        self.assertIn("missed dentist", hout)

    def test_overdue_todo_reads_as_overdue(self):
        todos.add(self.con, "manual", "late thing", due="2026-06-01",
                  today="2026-05-20")
        out = reports.horizon(self.con, "2026-06-06")
        self.assertIn("overdue by 5 days", out)

    def test_recall_searches_structured_and_journal(self):
        from famlib import journal
        todos.add(self.con, "manual", "fix gutters", today="2026-06-06")
        journal.add(self.con, "nightly", session="nightly", kind="summary",
                    text="long chat about gutters", date="2026-06-05")
        out = reports.recall(self.con, "gutters")
        self.assertIn("fix gutters", out)
        self.assertIn("long chat about gutters", out)
        self.assertIn("TODOS (1 of 1 shown)", out)
        self.assertIn("JOURNAL (1 of 1 shown)", out)

    def test_drought_flags_adult_with_stale_personal_time(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-05-04")
        e = weeks.add_entry(self.con, "weekly", wid, kind="personal",
                            title="gym", owner="P1")
        weeks.entry_done(self.con, "nightly", e["id"], date="2026-05-05")
        out = reports.checkin(self.con, "2026-06-06")
        self.assertIn("PERSONAL TIME DROUGHT", out)
        self.assertIn("P1 — 32 days since last personal time", out)
        self.assertIn("P2 — no personal time on record (since 2026-05-04)", out)

    def test_drought_quiet_when_recent(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-01")
        for who in ("P1", "P2"):
            e = weeks.add_entry(self.con, "weekly", wid, kind="personal",
                                title="block", owner=who)
            weeks.entry_done(self.con, "nightly", e["id"], date="2026-06-05")
        out = reports.checkin(self.con, "2026-06-06")
        self.assertIn("PERSONAL TIME DROUGHT (0 of 0 shown)", out)

    def test_drought_silent_on_brand_new_system(self):
        out = reports.checkin(self.con, "2026-06-06")
        self.assertIn("PERSONAL TIME DROUGHT (0 of 0 shown)", out)

    def test_drought_appears_in_fair(self):
        weeks.new_week(self.con, "weekly", today="2026-05-04")
        out = reports.fair(self.con, "2026-06-06")
        self.assertIn("no personal time on record", out)


class TestTimeLogDroughts(TestReports):
    def test_adhoc_full_satisfies_full_drought(self):
        weeks.new_week(self.con, "weekly", today="2026-05-04")
        time_log.add(self.con, "nightly", "personal", who="P1", level="full",
                     date="2026-06-05")
        time_log.add(self.con, "nightly", "personal", who="P2", level="full",
                     date="2026-06-05")
        out = reports.checkin(self.con, "2026-06-06")
        self.assertIn("PERSONAL TIME DROUGHT (0 of 0 shown)", out)

    def test_adhoc_partial_does_not_satisfy_full_drought(self):
        weeks.new_week(self.con, "weekly", today="2026-05-04")
        time_log.add(self.con, "nightly", "personal", who="P1",
                     date="2026-06-05")  # partial
        out = reports.checkin(self.con, "2026-06-06")
        self.assertIn("P1 — no personal time on record (since 2026-05-04)",
                      out)

    def test_time_log_alone_starts_observation_horizon(self):
        # No weeks at all — a 40-day-old family log opens the horizon,
        # so adults with no personal time get flagged.
        time_log.add(self.con, "nightly", "family", date="2026-04-27")
        out = reports.checkin(self.con, "2026-06-06")
        self.assertIn("P1 — no personal time on record (since 2026-04-27)",
                      out)

    def test_dose_streak_flags_two_dry_days(self):
        weeks.new_week(self.con, "weekly", today="2026-06-01")
        time_log.add(self.con, "nightly", "personal", who="P1",
                     date="2026-06-04")  # 2 days before today -> flag
        time_log.add(self.con, "nightly", "personal", who="P2",
                     date="2026-06-05")  # yesterday -> quiet
        out = reports.checkin(self.con, "2026-06-06")
        self.assertIn("P1 — 2 days without any personal time", out)
        self.assertNotIn("P2 — ", out.split("PERSONAL TIME DROUGHT")[1]
                         .split("PULSES")[0])

    def test_dose_streak_counts_planned_entries_too(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-01")
        for who in ("P1", "P2"):
            e = weeks.add_entry(self.con, "weekly", wid, kind="personal",
                                title="block", owner=who)
            weeks.entry_done(self.con, "nightly", e["id"], date="2026-06-05")
        out = reports.checkin(self.con, "2026-06-06")
        self.assertNotIn("without any personal time", out)

    def test_couple_drought_at_31_days(self):
        time_log.add(self.con, "nightly", "couple", date="2026-05-06")
        out = reports.checkin(self.con, "2026-06-06")
        self.assertIn("couple — 31 days since last couple time", out)

    def test_couple_quiet_at_30_days(self):
        time_log.add(self.con, "nightly", "couple", date="2026-05-07")
        # keep family quiet so the section can be empty except family count
        time_log.add(self.con, "nightly", "family", date="2026-06-05")
        time_log.add(self.con, "nightly", "family", date="2026-06-04")
        out = reports.checkin(self.con, "2026-06-06")
        self.assertNotIn("since last couple time", out)

    def test_family_slipping_with_one_moment_in_window(self):
        weeks.new_week(self.con, "weekly", today="2026-05-04")
        time_log.add(self.con, "nightly", "family", date="2026-06-04")
        out = reports.checkin(self.con, "2026-06-06")
        self.assertIn("family — 1 of 2 family moments in last 7 days", out)

    def test_family_quiet_with_two_moments(self):
        weeks.new_week(self.con, "weekly", today="2026-05-04")
        time_log.add(self.con, "nightly", "family", date="2026-06-04")
        time_log.add(self.con, "nightly", "family", date="2026-06-05")
        out = reports.checkin(self.con, "2026-06-06")
        self.assertNotIn("family moments in last", out)

    def test_togetherness_grace_on_young_system(self):
        # horizon only 3 days old: family window (7d) and couple window
        # (30d) haven't elapsed -> no togetherness flags at all
        weeks.new_week(self.con, "weekly", today="2026-06-03")
        out = reports.checkin(self.con, "2026-06-06")
        self.assertIn("TOGETHERNESS (0 of 0 shown)", out)

    def test_fair_shows_adhoc_counts(self):
        time_log.add(self.con, "nightly", "personal", who="P1", level="full",
                     date="2026-06-03")
        time_log.add(self.con, "nightly", "personal", who="P1",
                     date="2026-06-04")
        time_log.add(self.con, "nightly", "personal", who="P1",
                     date="2026-06-05")
        out = reports.fair(self.con, "2026-06-06", weeks_back=4)
        self.assertIn("P1: 0/0 personal blocks done, 1 full + 2 partial"
                      " ad-hoc", out)
        self.assertIn("P2: 0/0 personal blocks done, 0 full + 0 partial"
                      " ad-hoc", out)

    def test_horizon_shows_time_log(self):
        time_log.add(self.con, "nightly", "personal", who="P1", level="full",
                     date="2026-06-03", note="trail run")
        time_log.add(self.con, "nightly", "couple", date="2026-06-01")
        out = reports.horizon(self.con, "2026-06-06")
        self.assertIn("TIME LOG (last 14 days) (2 of 2 shown)", out)
        self.assertIn("2026-06-03 personal (full)  @P1  (trail run)", out)
        self.assertIn("2026-06-01 couple", out)

    def test_checkin_shows_nightly_habits(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        out = reports.checkin(self.con, "2026-06-08")
        self.assertIn("NIGHTLY HABITS", out)
        self.assertIn("spending review — not yet logged tonight", out)
        daily.log(self.con, "nightly", "spending review", date="2026-06-08")
        out = reports.checkin(self.con, "2026-06-08")
        self.assertIn("spending review — ✓ logged tonight", out)

    def test_checkin_flags_missed_habit_streak(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-01")
        daily.log(self.con, "nightly", "spending review", date="2026-06-02")
        out = reports.checkin(self.con, "2026-06-08")
        self.assertIn("spending review — not yet tonight; MISSED", out)
        self.assertIn("nights running (", out)
        self.assertIn("nights since 2026-06-01)", out)

    def test_recall_journal_text_not_truncated(self):
        from famlib import journal
        long_text = "gutters " + "z" * 300
        journal.add(self.con, "nightly", session="nightly", kind="summary",
                    text=long_text, date="2026-06-05")
        out = reports.recall(self.con, "gutters")
        self.assertIn("z" * 300, out)

    def test_checkin_flags_session_gaps(self):
        from famlib import journal
        journal.add(self.con, "nightly", session="nightly", kind="summary",
                    text="n", date="2026-06-03")
        journal.add(self.con, "weekly", session="weekly", kind="summary",
                    text="w", date="2026-05-25")
        out = reports.checkin(self.con, "2026-06-06")
        self.assertIn("last nightly: 2026-06-03 (3 days ago)", out)
        self.assertIn("GAP: 2 nights unrecorded", out)
        self.assertIn("last weekly: 2026-05-25 (12 days ago)", out)
        self.assertIn("GAP: weekly review overdue", out)

    def test_checkin_session_banner_quiet_when_current(self):
        from famlib import journal
        journal.add(self.con, "nightly", session="nightly", kind="summary",
                    text="n", date="2026-06-05")
        journal.add(self.con, "weekly", session="weekly", kind="summary",
                    text="w", date="2026-06-01")
        out = reports.checkin(self.con, "2026-06-06")
        self.assertIn("last nightly: 2026-06-05 (1 day ago)", out)
        self.assertNotIn("GAP", out)

    def test_checkin_sessions_never_on_record(self):
        out = reports.checkin(self.con, "2026-06-06")
        self.assertIn("last nightly: never", out)
        self.assertIn("last weekly: never", out)

    def test_neglect_includes_never_done_and_skip_streaks(self):
        from famlib import standing, weeks as wk
        standing.add(self.con, "manual", "mop floors", kind="chore",
                     today="2026-04-01")
        w1, _ = wk.new_week(self.con, "weekly", today="2026-05-18")
        for e in wk.entries(self.con, w1):
            wk.entry_skip(self.con, "x", e["id"])
        w2, _ = wk.new_week(self.con, "weekly", start="2026-05-25",
                            today="2026-05-24")
        for e in wk.entries(self.con, w2):
            wk.entry_skip(self.con, "x", e["id"])
        out = reports.checkin(self.con, "2026-06-06")
        self.assertIn("mop floors — never done since added 2026-04-01", out)
        self.assertIn("mop floors — skipped 2 weeks running", out)

    def test_checkin_todays_targets_and_behind_plan(self):
        from famlib import standing, weeks as wk
        standing.add(self.con, "manual", "towels", kind="chore",
                     today="2026-06-01")
        standing.add(self.con, "manual", "groceries", kind="chore",
                     today="2026-06-01")
        wid, _ = wk.new_week(self.con, "weekly", today="2026-06-01")
        es = wk.entries(self.con, wid)
        wk.set_day(self.con, "weekly", es[0]["id"], "wed")
        wk.set_day(self.con, "weekly", es[1]["id"], "tue")
        e3 = wk.add_entry(self.con, "weekly", wid, kind="oneoff",
                          title="no day assigned")
        out = reports.checkin(self.con, "2026-06-03")  # a wednesday
        self.assertIn("TODAY'S TARGETS (wed)", out)
        self.assertIn(es[0]["title"], out.split("TODAY'S TARGETS")[1]
                      .split("BEHIND PLAN")[0])
        self.assertIn("BEHIND PLAN", out)
        self.assertIn("%s  @-  (planned tue)" % es[1]["title"],
                      out.split("BEHIND PLAN")[1].split("NO DAY ASSIGNED")[0])
        self.assertIn("NO DAY ASSIGNED", out)
        self.assertIn("no day assigned", out)

    def test_horizon_includes_pending_week_plan(self):
        from famlib import standing, weeks as wk
        standing.add(self.con, "manual", "towels", kind="chore",
                     today="2026-06-01")
        wid, _ = wk.new_week(self.con, "weekly", today="2026-06-01")
        es = wk.entries(self.con, wid)
        wk.set_day(self.con, "weekly", es[0]["id"], "tue")
        out = reports.horizon(self.con, "2026-06-03")
        self.assertIn("WEEK PLAN PENDING", out)
        self.assertIn(es[0]["title"], out)
        self.assertIn("day tue", out)

    def test_today_report(self):
        from famlib import daily, journal, standing, todos as td, weeks as wk
        journal.add(self.con, "nightly", session="nightly", kind="summary",
                    text="n", date="2026-06-02")
        standing.add(self.con, "manual", "towels", kind="chore",
                     today="2026-06-01")
        standing.add(self.con, "manual", "groceries", kind="chore",
                     today="2026-06-01")
        wid, _ = wk.new_week(self.con, "weekly", today="2026-06-01")
        es = wk.entries(self.con, wid)
        wk.set_day(self.con, "weekly", es[0]["id"], "wed")
        wk.set_day(self.con, "weekly", es[1]["id"], "mon")
        td.add(self.con, "manual", "due thing", due="2026-06-03",
               today="2026-06-01")
        daily.add_habit(self.con, "manual", "tidy", today="2026-06-01")
        out = reports.today_report(self.con, "2026-06-03")
        self.assertIn("TODAY — 2026-06-03 (wed)", out)
        self.assertIn("last nightly: 2026-06-02 (1 day ago)", out)
        self.assertIn("TODAY'S TARGETS (wed)", out)
        self.assertIn(es[0]["title"], out)
        self.assertIn("BEHIND PLAN", out)
        self.assertIn("due thing", out)
        self.assertIn("tidy", out)

    def test_checkin_flags_stuck_stage_and_shows_stage(self):
        from famlib import standing, weeks as wk
        standing.add(self.con, "manual", "towels", kind="chore",
                     today="2026-06-01")
        wid, _ = wk.new_week(self.con, "weekly", today="2026-06-01")
        e = wk.entries(self.con, wid)[0]
        wk.set_stage(self.con, "x", e["id"], "dry", date="2026-06-01")
        out = reports.checkin(self.con, "2026-06-04")
        self.assertIn("towels — stuck in dry for 3 days (since 2026-06-01)",
                      out)
        self.assertIn("[dry since 2026-06-01]", out)

    def test_week_rollup_line(self):
        from famlib import standing, weeks as wk
        standing.add(self.con, "manual", "towels", kind="chore",
                     today="2026-06-01")
        standing.add(self.con, "manual", "groceries", kind="chore",
                     today="2026-06-01")
        wid, _ = wk.new_week(self.con, "weekly", today="2026-06-01")
        es = wk.entries(self.con, wid)
        wk.set_day(self.con, "x", es[0]["id"], "mon")
        wk.entry_done(self.con, "x", es[0]["id"], date="2026-06-01")
        wk.add_entry(self.con, "weekly", wid, kind="oneoff", title="declutter",
                     day="tue")
        rollup = "WEEK: 1 of 3 done, 2 pending (1 unscheduled), 1 behind" \
                 " plan, 4 days left"
        out = reports.checkin(self.con, "2026-06-04")  # thursday
        self.assertIn(rollup, out)
        out2 = reports.today_report(self.con, "2026-06-04")
        self.assertIn(rollup, out2)

    def test_wins_section_celebrates(self):
        from famlib import chores, daily, standing, time_log, weeks as wk
        standing.add(self.con, "manual", "towels", kind="chore",
                     today="2026-06-01")
        wid, _ = wk.new_week(self.con, "weekly", today="2026-06-01")
        e = wk.entries(self.con, wid)[0]
        wk.entry_done(self.con, "x", e["id"], date="2026-06-02")
        chores.set_cadence(self.con, "manual", "towels", 7)
        daily.add_habit(self.con, "manual", "tidy", today="2026-06-01")
        for d in ("2026-06-02", "2026-06-03", "2026-06-04"):
            daily.log(self.con, "nightly", "tidy", date=d)
        time_log.add(self.con, "nightly", "personal", who="P1",
                     level="full", date="2026-06-01")
        time_log.add(self.con, "nightly", "family", date="2026-06-02")
        time_log.add(self.con, "nightly", "family", date="2026-06-03")
        out = reports.checkin(self.con, "2026-06-04")
        self.assertIn("WINS", out)
        win_block = out.split("WINS")[1].split("WEEK PLAN")[0]
        self.assertIn("1 plan item done this week", win_block)
        self.assertIn("tidy — 3 nights running", win_block)
        self.assertIn("towels — on rhythm (2 days since, ~7-day cadence)",
                      win_block)
        self.assertIn("P1 — full personal reset 3 days ago", win_block)
        self.assertIn("family time — 2 moments in last 7 days (target met)",
                      win_block)
        out2 = reports.today_report(self.con, "2026-06-04")
        self.assertIn("tidy — 3 nights running", out2)
