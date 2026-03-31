"""Tests for YAML schema validation."""

from pathlib import Path

import yaml

from ingest_standards.schema import validate_yaml_file


def _write_yaml(tmp_path: Path, name: str, data: dict) -> Path:
    path = tmp_path / name
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    return path


def _valid_math_k() -> dict:
    return {
        "subject": "math",
        "grade": "K",
        "version": "2023",
        "source": {
            "primary": "opensalt",
            "primary_url": "https://opensalt.net/...",
            "last_verified": "2026-03-31",
        },
        "standard_count": 2,
        "domains": {
            "NS": {
                "name": "Number Sense",
                "learning_outcome": "Students explore...",
                "standards": {
                    "K.NS.1": {
                        "description": "Count to at least 100.",
                        "essential": True,
                    },
                    "K.NS.2": {
                        "description": "Write whole numbers.",
                        "essential": False,
                    },
                },
            },
        },
    }


def test_valid_file_passes(tmp_path: Path) -> None:
    path = _write_yaml(tmp_path, "math-k.yaml", _valid_math_k())
    report = validate_yaml_file(path)
    assert report.passed, report.summary()


def test_missing_required_field(tmp_path: Path) -> None:
    data = _valid_math_k()
    del data["standard_count"]
    path = _write_yaml(tmp_path, "math-k.yaml", data)
    report = validate_yaml_file(path)
    assert not report.passed
    assert any("standard_count" in e.message for e in report.errors)


def test_invalid_subject(tmp_path: Path) -> None:
    data = _valid_math_k()
    data["subject"] = "art"
    path = _write_yaml(tmp_path, "art-k.yaml", data)
    report = validate_yaml_file(path)
    assert not report.passed


def test_malformed_code(tmp_path: Path) -> None:
    data = _valid_math_k()
    data["domains"]["NS"]["standards"]["KBAD1"] = {
        "description": "Bad code",
        "essential": False,
    }
    data["standard_count"] = 3
    path = _write_yaml(tmp_path, "math-k.yaml", data)
    report = validate_yaml_file(path)
    assert any("KBAD1" in e.path for e in report.errors)


def test_essential_in_description(tmp_path: Path) -> None:
    data = _valid_math_k()
    data["domains"]["NS"]["standards"]["K.NS.1"]["description"] = "Count to 100. (E)"
    path = _write_yaml(tmp_path, "math-k.yaml", data)
    report = validate_yaml_file(path)
    assert any("(E)" in e.message for e in report.errors)


def test_count_mismatch(tmp_path: Path) -> None:
    data = _valid_math_k()
    data["standard_count"] = 99
    path = _write_yaml(tmp_path, "math-k.yaml", data)
    report = validate_yaml_file(path)
    assert any("standard_count" in e.path for e in report.errors)


def test_science_requires_dimensions(tmp_path: Path) -> None:
    data = {
        "subject": "science",
        "grade": "1",
        "version": "2023",
        "source": {
            "primary": "IDOE PDF",
            "primary_url": "https://example.com",
            "last_verified": "2026-03-31",
        },
        "standard_count": 1,
        "domains": {
            "PS4": {
                "name": "Waves",
                "standards": {
                    "1-PS4-1": {
                        "description": "Plan and conduct investigations.",
                        # Missing practice, core_idea, crosscutting
                    },
                },
            },
        },
    }
    path = _write_yaml(tmp_path, "science-1.yaml", data)
    report = validate_yaml_file(path)
    assert not report.passed
    assert any("practice" in e.message for e in report.errors)


def test_science_invalid_sep(tmp_path: Path) -> None:
    data = {
        "subject": "science",
        "grade": "1",
        "version": "2023",
        "source": {
            "primary": "IDOE PDF",
            "primary_url": "https://example.com",
            "last_verified": "2026-03-31",
        },
        "standard_count": 1,
        "domains": {
            "PS4": {
                "name": "Waves",
                "standards": {
                    "1-PS4-1": {
                        "description": "Plan investigations.",
                        "practice": "SEP.99",
                        "core_idea": "PS4.A",
                        "crosscutting": "CC.2",
                    },
                },
            },
        },
    }
    path = _write_yaml(tmp_path, "science-1.yaml", data)
    report = validate_yaml_file(path)
    assert any("SEP.99" in e.message for e in report.errors)


def test_ela_sub_standards_counted(tmp_path: Path) -> None:
    data = {
        "subject": "ela",
        "grade": "2",
        "version": "2023",
        "source": {
            "primary": "IDOE PDF",
            "primary_url": "https://example.com",
            "last_verified": "2026-03-31",
        },
        "standard_count": 3,  # 1 plain + 2 sub-standards
        "domains": {
            "W": {
                "name": "Writing",
                "standards": {
                    "2.W.1": {
                        "description": "Write legibly.",
                        "essential": True,
                    },
                    "2.W.4": {
                        "description": "Write narratives that:",
                        "sub_standards": {
                            "2.W.4a": {"description": "Include a beginning;"},
                            "2.W.4b": {"description": "Provide an ending."},
                        },
                    },
                },
            },
        },
    }
    path = _write_yaml(tmp_path, "ela-2.yaml", data)
    report = validate_yaml_file(path)
    assert report.passed, report.summary()
