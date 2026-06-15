"""GUI RAG case library routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.services.rag_case_library import RagCaseLibrary

router = APIRouter(tags=["gui-rag"])


def get_rag_case_library() -> RagCaseLibrary:
    """Dependency hook for the user-filled RAG case folder."""
    return RagCaseLibrary()


@router.get("/cases")
async def list_rag_cases(
    library: RagCaseLibrary = Depends(get_rag_case_library),
) -> dict[str, Any]:
    """List structured RAG cases."""
    return {
        "root": str(library.root),
        "cases": library.scan_cases(),
        "manifest_path": str(library.manifest_path),
        "index_path": str(library.index_path),
    }


@router.post("/cases/{case_id}/validate")
async def validate_rag_case(
    case_id: str,
    library: RagCaseLibrary = Depends(get_rag_case_library),
) -> dict[str, Any]:
    """Validate one RAG case folder."""
    try:
        return library.validate_case(case_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="非法 case_id") from exc


@router.post("/index/rebuild")
async def rebuild_rag_index(
    library: RagCaseLibrary = Depends(get_rag_case_library),
) -> dict[str, Any]:
    """Rebuild manifest and lightweight keyword index."""
    manifest = library.write_manifest()
    index = library.build_keyword_index()
    return {
        **index,
        "manifest_path": str(library.manifest_path),
        "index_path": str(library.index_path),
        "valid_case_count": sum(1 for case in manifest["cases"] if case["status"] == "valid"),
    }


@router.get("/guide")
async def get_rag_guide() -> dict[str, Any]:
    """Return the required RAG case folder contract for the GUI."""
    return {
        "root": "data/rag_cases",
        "required_files": ["problem", "paper"],
        "accepted_suffixes": [".pdf", ".md", ".txt", ".docx"],
        "optional_paths": ["data/", "notes.md"],
        "example": [
            "case-id/",
            "  problem.pdf",
            "  paper.pdf",
            "  data/",
            "  notes.md",
        ],
    }
