"""Chunked local vector retrieval for the structured RAG case library."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.rag_case_library import RagCaseLibrary


TEXT_SUFFIXES = {".md", ".txt", ".csv", ".json", ".tex"}
VECTOR_DIM = 64


class RagVectorIndexService:
    """Build and query a deterministic local vector index for RAG cases."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.chunks_path = self.root / ".rag_chunks.jsonl"
        self.vectors_path = self.root / ".rag_vectors.jsonl"
        self.retrieval_log_path = self.root / ".rag_retrieval_log.jsonl"

    def rebuild(self) -> dict[str, Any]:
        """Rebuild chunk and vector files from valid case text files."""
        self.root.mkdir(parents=True, exist_ok=True)
        chunks = self._build_chunks()
        vectors = [
            {
                "chunk_id": chunk["chunk_id"],
                "embedding": self._embed(chunk["text"]),
            }
            for chunk in chunks
        ]
        self._write_jsonl(self.chunks_path, chunks)
        self._write_jsonl(self.vectors_path, vectors)
        return {
            "version": 1,
            "status": "ready",
            "generated_at": self._now(),
            "chunk_count": len(chunks),
            "vector_count": len(vectors),
            "chunks_path": str(self.chunks_path),
            "vectors_path": str(self.vectors_path),
        }

    def query(
        self,
        query_text: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Retrieve top matching chunks and append a retrieval log entry."""
        if not self.chunks_path.exists() or not self.vectors_path.exists():
            self.rebuild()
        chunks = self._read_jsonl(self.chunks_path)
        vector_by_id = {
            item["chunk_id"]: item["embedding"] for item in self._read_jsonl(self.vectors_path)
        }
        query_embedding = self._embed(query_text)
        query_terms = set(self._tokens(query_text))
        scored = []
        for chunk in chunks:
            if filters and filters.get("case_id") and chunk["case_id"] != filters["case_id"]:
                continue
            embedding = vector_by_id.get(chunk["chunk_id"])
            if not embedding:
                continue
            lexical_bonus = self._lexical_bonus(query_terms, set(self._tokens(chunk["text"])))
            score = self._cosine(query_embedding, embedding) + lexical_bonus
            scored.append({**chunk, "score": round(score, 6)})

        hits = sorted(scored, key=lambda item: item["score"], reverse=True)[: max(top_k, 1)]
        result = {
            "query": query_text,
            "top_k": top_k,
            "hit_count": len(hits),
            "hits": hits,
            "retrieval_log_path": str(self.retrieval_log_path),
        }
        self._append_retrieval_log(result)
        return result

    def _build_chunks(self) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []
        library = RagCaseLibrary(self.root)
        for case in library.scan_cases():
            if case["status"] != "valid":
                continue
            case_dir = self.root / case["case_id"]
            for file_info in case.get("files", []):
                source = case_dir / file_info["path"]
                if source.suffix.lower() not in TEXT_SUFFIXES:
                    continue
                text = source.read_text(encoding="utf-8", errors="ignore")
                for index, chunk_text in enumerate(self._chunk_text(text)):
                    chunk_id = self._chunk_id(case["case_id"], file_info["path"], index)
                    chunks.append(
                        {
                            "case_id": case["case_id"],
                            "chunk_id": chunk_id,
                            "source_path": file_info["path"],
                            "text": chunk_text,
                            "metadata": {
                                "chunk_index": index,
                                "char_count": len(chunk_text),
                                "sha256": file_info.get("sha256", ""),
                            },
                        }
                    )
        return chunks

    @staticmethod
    def _chunk_text(text: str, max_chars: int = 1200) -> list[str]:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
        chunks: list[str] = []
        for paragraph in paragraphs or [text.strip()]:
            while len(paragraph) > max_chars:
                chunks.append(paragraph[:max_chars].strip())
                paragraph = paragraph[max_chars:].strip()
            if paragraph:
                chunks.append(paragraph)
        return chunks

    @staticmethod
    def _chunk_id(case_id: str, source_path: str, index: int) -> str:
        digest = hashlib.sha1(f"{case_id}:{source_path}:{index}".encode()).hexdigest()[:12]
        return f"chunk-{digest}"

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return [token.lower() for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text)]

    @classmethod
    def _embed(cls, text: str) -> list[float]:
        vector = [0.0] * VECTOR_DIM
        for token in cls._tokens(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:2], "big") % VECTOR_DIM
            sign = 1.0 if digest[2] % 2 == 0 else -1.0
            vector[bucket] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [round(value / norm, 8) for value in vector]

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        return sum(a * b for a, b in zip(left, right, strict=False))

    @staticmethod
    def _lexical_bonus(query_terms: set[str], chunk_terms: set[str]) -> float:
        if not query_terms:
            return 0.0
        return 0.25 * (len(query_terms & chunk_terms) / len(query_terms))

    @staticmethod
    def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            for row in rows:
                file.write(json.dumps(row, ensure_ascii=False) + "\n")

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _append_retrieval_log(self, result: dict[str, Any]) -> None:
        self.retrieval_log_path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "timestamp": self._now(),
            "query": result["query"],
            "top_k": result["top_k"],
            "hit_count": result["hit_count"],
            "hits": [
                {
                    "case_id": hit["case_id"],
                    "chunk_id": hit["chunk_id"],
                    "source_path": hit["source_path"],
                    "score": hit["score"],
                }
                for hit in result["hits"]
            ],
        }
        with self.retrieval_log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
