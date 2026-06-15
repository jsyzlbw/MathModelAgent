"""Structured RAG case library tests."""

from pathlib import Path

from app.services.rag_case_library import RagCaseLibrary


def test_rag_case_library_empty_root_returns_no_cases(tmp_path: Path) -> None:
    library = RagCaseLibrary(tmp_path / "rag_cases")

    assert library.scan_cases() == []


def test_rag_case_library_valid_case_has_manifest_and_hashes(tmp_path: Path) -> None:
    case_dir = tmp_path / "rag_cases" / "case-a"
    case_dir.mkdir(parents=True)
    (case_dir / "problem.pdf").write_bytes(b"problem")
    (case_dir / "paper.pdf").write_bytes(b"paper")
    (case_dir / "notes.md").write_text("AHP TOPSIS notes", encoding="utf-8")
    (case_dir / ".hidden").write_text("ignore", encoding="utf-8")

    library = RagCaseLibrary(tmp_path / "rag_cases")
    cases = library.scan_cases()
    manifest = library.write_manifest()

    assert cases[0]["case_id"] == "case-a"
    assert cases[0]["status"] == "valid"
    assert cases[0]["issues"] == []
    assert "problem.pdf" in {item["path"] for item in manifest["cases"][0]["files"]}
    assert ".hidden" not in {item["path"] for item in manifest["cases"][0]["files"]}
    assert all(item["sha256"] for item in manifest["cases"][0]["files"])


def test_rag_case_library_invalid_case_reports_missing_required_files(
    tmp_path: Path,
) -> None:
    case_dir = tmp_path / "rag_cases" / "case-b"
    case_dir.mkdir(parents=True)
    (case_dir / "notes.md").write_text("notes only", encoding="utf-8")

    result = RagCaseLibrary(tmp_path / "rag_cases").validate_case("case-b")

    assert result["status"] == "invalid"
    assert "missing_problem_file" in result["issues"]
    assert "missing_paper_file" in result["issues"]


def test_rag_case_library_builds_keyword_index(tmp_path: Path) -> None:
    case_dir = tmp_path / "rag_cases" / "case-c"
    case_dir.mkdir(parents=True)
    (case_dir / "problem.md").write_text("forecast demand", encoding="utf-8")
    (case_dir / "paper.md").write_text("ARIMA regression forecast", encoding="utf-8")

    index = RagCaseLibrary(tmp_path / "rag_cases").build_keyword_index()

    assert index["case_count"] == 1
    assert "forecast" in index["cases"][0]["keywords"]
    assert "arima" in index["cases"][0]["keywords"]
