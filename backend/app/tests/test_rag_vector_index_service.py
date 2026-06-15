"""RAG vector index service tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.routers.rag_router import get_rag_case_library
from app.services.rag_case_library import RagCaseLibrary


def _make_valid_case(root: Path, case_id: str, problem: str, paper: str) -> Path:
    case_dir = root / case_id
    case_dir.mkdir(parents=True)
    (case_dir / "problem.md").write_text(problem, encoding="utf-8")
    (case_dir / "paper.md").write_text(paper, encoding="utf-8")
    return case_dir


def test_rag_vector_index_builds_chunks_and_retrieves(tmp_path: Path) -> None:
    from app.services.rag_vector_index_service import RagVectorIndexService

    root = tmp_path / "rag_cases"
    _make_valid_case(
        root,
        "case-water",
        "Optimize water allocation.",
        "Linear programming model for water allocation.",
    )

    service = RagVectorIndexService(root)
    index = service.rebuild()
    hits = service.query("water programming", top_k=2)

    assert index["chunk_count"] >= 2
    assert hits["hits"][0]["case_id"] == "case-water"
    assert hits["hits"][0]["chunk_id"]
    assert hits["hits"][0]["source_path"] in {"problem.md", "paper.md"}
    assert root.joinpath(".rag_chunks.jsonl").exists()
    assert root.joinpath(".rag_vectors.jsonl").exists()
    assert root.joinpath(".rag_retrieval_log.jsonl").exists()


def test_rag_vector_api_rebuilds_and_queries(tmp_path: Path) -> None:
    root = tmp_path / "rag_cases"
    _make_valid_case(
        root,
        "case-energy",
        "Forecast energy demand.",
        "ARIMA and regression for energy demand forecasting.",
    )

    def override_library() -> RagCaseLibrary:
        return RagCaseLibrary(root)

    app.dependency_overrides[get_rag_case_library] = override_library
    client = TestClient(app)

    rebuild_response = client.post("/api/gui/rag/vector/rebuild")
    query_response = client.post(
        "/api/gui/rag/query",
        json={"query": "energy forecast", "top_k": 3},
    )

    assert rebuild_response.status_code == 200
    assert rebuild_response.json()["chunk_count"] >= 2
    assert query_response.status_code == 200
    assert query_response.json()["hits"][0]["case_id"] == "case-energy"

    app.dependency_overrides.clear()
