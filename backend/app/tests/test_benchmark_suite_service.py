"""Benchmark smoke suite tests."""

from pathlib import Path


def test_benchmark_suite_runs_smoke_and_writes_reports(tmp_path: Path) -> None:
    from app.services.benchmark_suite_service import BenchmarkSuiteService

    report = BenchmarkSuiteService(tmp_path).run_smoke()

    assert report["status"] == "passed"
    assert {
        "res.md",
        "paper/claim_plan.json",
        "artifact_registry.json",
        "review/paper_qa_report.json",
        "exports/submission_package.zip",
    }.issubset({check["path"] for check in report["checks"]})
    assert (tmp_path / "benchmarks" / "latest_report.json").exists()
    assert (tmp_path / "benchmarks" / "latest_report.md").exists()
