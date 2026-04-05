"""Tests for the chunker module."""

from pathlib import Path

from vector_store.chunker import chunk_file


def _write(tmp_path: Path, rel: str, content: str) -> Path:
    """Write a file at a relative path under tmp_path and return its full path."""
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return p


# --- Checkin chunking ---


def test_checkin_splits_by_domain(tmp_path):
    path = _write(tmp_path, "data/weeks/2026-W14/checkins/mon.md", """\
# Monday, 2026-03-30

## Homeschool
- No school today

## Laundry
- Darks: moved to dryer

## Meals
- Groceries: no
- Dinner: leftovers
""")
    chunks = chunk_file(path)
    assert len(chunks) == 3
    domains = {c["domain"] for c in chunks}
    assert domains == {"homeschool", "laundry", "meals"}


def test_checkin_metadata(tmp_path):
    path = _write(tmp_path, "data/weeks/2026-W14/checkins/thu.md", """\
# Thursday

## Homeschool
- Yes
""")
    chunks = chunk_file(path)
    assert len(chunks) == 1
    c = chunks[0]
    assert c["type"] == "checkin"
    assert c["domain"] == "homeschool"
    assert "2026-W14" in c["date"]
    assert "thu" in c["date"]
    assert c["source_file"] == str(path)


def test_checkin_skips_empty_sections(tmp_path):
    path = _write(tmp_path, "data/weeks/2026-W14/checkins/wed.md", """\
# Wednesday

## Homeschool
- Yes

## Laundry

## Meals
- Dinner: pizza
""")
    chunks = chunk_file(path)
    domains = {c["domain"] for c in chunks}
    assert "laundry" not in domains
    assert len(chunks) == 2


# --- Plan chunking ---


def test_plan_splits_sections(tmp_path):
    path = _write(tmp_path, "data/weeks/2026-W14/plan.md", """\
# Caregiver's Checklist

- [ ] Math (x3)
- [ ] Laundry

# Calendar View

## Monday
- Co-op 9-12

# Partner's Insights

Good week ahead. Personal time is overdue.
""")
    chunks = chunk_file(path)
    types = {c["type"] for c in chunks}
    assert "plan_checklist" in types
    assert "plan_calendar" in types
    assert "plan_insights" in types


def test_plan_date_from_week_folder(tmp_path):
    path = _write(tmp_path, "data/weeks/2026-W15/plan.md", """\
# Caregiver's Checklist

- [ ] stuff
""")
    chunks = chunk_file(path)
    assert chunks[0]["date"] == "2026-W15"


# --- current.yaml chunking ---


def test_current_yaml_splits_by_key(tmp_path):
    path = _write(tmp_path, "data/state/current.yaml", """\
last_done:
  homeschool: "2026-03-28"
  chores:
    decluttering: "2026-03-27"

laundry_pipeline:
  darks: { stage: dry, last_completed: "2026-03-25" }

weekly_one_offs:
  - task: "Call dentist"
    owner: patrick
    added: "2026-03-29"
    done: false
""")
    chunks = chunk_file(path)
    assert len(chunks) == 3
    keys = {c["domain"] for c in chunks}
    assert keys == {"last_done", "laundry_pipeline", "weekly_one_offs"}
    assert all(c["type"] == "state" for c in chunks)


def test_current_yaml_text_is_readable(tmp_path):
    path = _write(tmp_path, "data/state/current.yaml", """\
weekly_one_offs:
  - task: "Call dentist"
    done: false
""")
    chunks = chunk_file(path)
    assert "Call dentist" in chunks[0]["text"]


# --- Coverage chunking ---


def test_coverage_splits_by_standard(tmp_path):
    path = _write(tmp_path, "data/edu/coverage.yaml", """\
standards:
  K.NS.1:
    status: mastered
    last_touched: "2026-02-15"
    source: baseline
  2.G.3:
    status: introduced
    last_touched: "2026-03-20"
    source: activity
""")
    chunks = chunk_file(path)
    assert len(chunks) == 2
    ids = {c["id"] for c in chunks}
    assert any("K.NS.1" in i for i in ids)
    assert any("2.G.3" in i for i in ids)


def test_coverage_infers_subject(tmp_path):
    path = _write(tmp_path, "data/edu/coverage.yaml", """\
standards:
  K.NS.1:
    status: mastered
  2.RF.1:
    status: introduced
  1-PS4-1:
    status: practiced
""")
    chunks = chunk_file(path)
    domains = {c["id"].split("::")[-1]: c["domain"] for c in chunks}
    assert domains["K.NS.1"] == "math"
    assert domains["2.RF.1"] == "ela"
    assert domains["1-PS4-1"] == "science"


# --- Activity log chunking ---


def test_activity_log_splits_by_entry(tmp_path):
    path = _write(tmp_path, "data/edu/activity-log/2026-03-20.md", """\
## Block tower building
Built a tall tower, sorted blocks by shape and color.
Standards: K.G.1, K.G.2

## Story time
Read three books, discussed characters.
Standards: K.RC.1
""")
    chunks = chunk_file(path)
    assert len(chunks) == 2
    assert all(c["type"] == "activity" for c in chunks)
    assert all(c["domain"] == "education" for c in chunks)
    assert chunks[0]["date"] == "2026-03-20"


def test_activity_log_with_title_heading(tmp_path):
    """A # title heading before ## entries creates an extra chunk for the preamble."""
    path = _write(tmp_path, "data/edu/activity-log/2026-03-20.md", """\
# Activities — 2026-03-20

## Block tower building
Built a tall tower.
""")
    chunks = chunk_file(path)
    # The # heading preamble + the ## entry
    assert len(chunks) == 2


# --- Standards chunking ---


def test_standards_splits_by_standard(tmp_path):
    path = _write(tmp_path, "standards/indiana/math-k.yaml", """\
subject: math
grade: K
version: "2023"
domains:
  NS:
    name: Number Sense
    standards:
      K.NS.1:
        description: "Count to at least 100 by ones and tens."
        essential: true
      K.NS.2:
        description: "Write whole numbers from 0 to 20."
        essential: false
  CA:
    name: Computation and Algebraic Thinking
    standards:
      K.CA.1:
        description: "Solve real-world problems involving addition and subtraction within 10."
        essential: true
""")
    chunks = chunk_file(path)
    assert len(chunks) == 3
    assert all(c["type"] == "standard" for c in chunks)
    assert all(c["domain"] == "math" for c in chunks)


def test_standards_text_includes_context(tmp_path):
    path = _write(tmp_path, "standards/indiana/math-1.yaml", """\
subject: math
grade: 1
version: "2023"
domains:
  NS:
    name: Number Sense
    standards:
      1.NS.1:
        description: "Count to 120 starting at any number."
        essential: true
""")
    chunks = chunk_file(path)
    c = chunks[0]
    assert "1.NS.1" in c["text"]
    assert "Count to 120" in c["text"]
    assert "(Essential)" in c["text"]
    assert "Number Sense" in c["text"]
    assert "Grade: 1" in c["text"]


def test_standards_includes_sub_standards(tmp_path):
    path = _write(tmp_path, "standards/indiana/ela-2.yaml", """\
subject: ela
grade: 2
version: "2023"
domains:
  W:
    name: Writing
    standards:
      2.W.4:
        description: "Write narratives that:"
        essential: true
        sub_standards:
          2.W.4a:
            description: "Include a beginning"
          2.W.4b:
            description: "Use temporal words"
""")
    chunks = chunk_file(path)
    assert len(chunks) == 1
    assert "2.W.4a: Include a beginning" in chunks[0]["text"]
    assert "2.W.4b: Use temporal words" in chunks[0]["text"]


def test_standards_includes_science_fields(tmp_path):
    path = _write(tmp_path, "standards/indiana/science-1.yaml", """\
subject: science
grade: 1
version: "2023"
domains:
  PS4:
    name: Waves
    standards:
      1-PS4-1:
        description: "Plan and conduct investigations about vibrating materials."
        essential: true
        clarification: "Examples include tuning forks."
        practice: "SEP.3"
        core_idea: "PS4.A"
        crosscutting: "CC.2"
""")
    chunks = chunk_file(path)
    c = chunks[0]
    assert "clarification: Examples include tuning forks" in c["text"]
    assert "practice: SEP.3" in c["text"]


# --- Generic fallback ---


def test_generic_for_unknown_file(tmp_path):
    path = _write(tmp_path, "data/some/random.md", "Just some content here.")
    chunks = chunk_file(path)
    assert len(chunks) == 1
    assert chunks[0]["type"] == "generic"


def test_empty_file_returns_no_chunks(tmp_path):
    path = _write(tmp_path, "data/empty.md", "")
    chunks = chunk_file(path)
    assert chunks == []


# --- Date extraction ---


def test_date_from_activity_log_filename(tmp_path):
    path = _write(tmp_path, "data/edu/activity-log/2026-04-01.md", """\
## Did math
Counted to 100.
""")
    chunks = chunk_file(path)
    assert chunks[0]["date"] == "2026-04-01"
