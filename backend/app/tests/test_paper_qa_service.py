"""Paper formatting QA service tests."""

from pathlib import Path

from app.services.planning_service import PlanningService


COMPLETE_DRAFT = """# Draft

## Abstract

Claim-aware summary.

## Introduction

Context.

## Assumptions

Assumptions.

## Model

- [claim:model] Model selected.

## Results

- [claim:result] Result available.

## Limitations

Limitations.

## Conclusion

Conclusion.
"""


def test_paper_qa_service_writes_reports_and_detects_missing_sections(
    tmp_path: Path,
) -> None:
    from app.services.paper_qa_service import PaperQAService

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "res.md").write_text("# Draft\n\n## Abstract\n\nNo claim.", encoding="utf-8")

    report = PaperQAService(workspace).run()

    assert report["status"] == "issues_found"
    assert any(issue["code"] == "missing_section" for issue in report["issues"])
    assert workspace.joinpath("review", "paper_qa_report.json").exists()
    assert workspace.joinpath("review", "paper_qa_report.md").exists()


def test_paper_qa_service_accepts_complete_claim_aware_draft(tmp_path: Path) -> None:
    from app.services.paper_qa_service import PaperQAService

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "res.md").write_text(COMPLETE_DRAFT, encoding="utf-8")

    report = PaperQAService(workspace).run()

    assert not any(issue["severity"] == "error" for issue in report["issues"])


def test_paper_qa_service_flags_long_lines(tmp_path: Path) -> None:
    from app.services.paper_qa_service import PaperQAService

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "res.md").write_text(COMPLETE_DRAFT + ("x" * 220), encoding="utf-8")

    report = PaperQAService(workspace).run()

    assert any(issue["code"] == "long_line" for issue in report["issues"])


def test_pipeline_writes_paper_qa_reports(tmp_path: Path) -> None:
    from app.services.pipeline_service import PipelineService

    workspace = tmp_path / "workspace"
    (workspace / "input" / "problem").mkdir(parents=True)
    (workspace / "input" / "problem" / "problem.txt").write_text(
        "Optimize allocation.",
        encoding="utf-8",
    )
    PlanningService(workspace).create_plan(problem_text="Optimize allocation.")

    PipelineService(workspace, task_id="qa-pipeline").run()

    assert workspace.joinpath("review", "paper_qa_report.json").exists()
    assert workspace.joinpath("review", "paper_qa_report.md").exists()
