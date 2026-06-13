"""Typed Retrieval with MMR – Stage 3 of the resume generation pipeline.

Performs separate Qdrant queries filtered by entry_type (WORK_EXPERIENCE, PROJECT, OSS),
applies score threshold to filter low-relevance noise, and deduplicates by work_entry_id
to ensure diversity across projects.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from app.models.work_entry import EntryType
from app.services.qdrant_service import qdrant_service

logger = logging.getLogger(__name__)


@dataclass
class RetrievedEntry:
    """A structured context entry from retrieval, ready for bullet generation."""

    work_entry_id: str
    title: str
    company: str
    role: str
    entry_type: str
    priority: int
    project_summary: str
    skills: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    impact: list[str] = field(default_factory=list)
    domain: str = ""
    score: float = 0.0

    def to_context_str(self) -> str:
        """Format as a clean context string for the bullet generator."""
        lines = [f"Title: {self.title}"]
        if self.company:
            lines.append(f"Company: {self.company}")
        if self.role:
            lines.append(f"Role: {self.role}")
        if self.project_summary:
            lines.append(f"Summary: {self.project_summary}")
        if self.skills:
            lines.append(f"Skills: {', '.join(self.skills)}")
        if self.technologies:
            # Deduplicate with skills
            unique_tech = [t for t in self.technologies if t not in self.skills]
            if unique_tech:
                lines.append(f"Technologies: {', '.join(unique_tech)}")
        if self.impact:
            lines.append(f"Impact: {'; '.join(self.impact)}")
        return "\n".join(lines)


@dataclass
class RetrievalResult:
    """Combined results from typed retrieval."""

    work_entries: list[RetrievedEntry] = field(default_factory=list)
    project_entries: list[RetrievedEntry] = field(default_factory=list)
    oss_entries: list[RetrievedEntry] = field(default_factory=list)

    @property
    def all_entries(self) -> list[RetrievedEntry]:
        return self.work_entries + self.project_entries + self.oss_entries

    @property
    def total_count(self) -> int:
        return len(self.all_entries)


def _apply_mmr(results: list, max_per_entry: int = 2) -> list:
    """Apply Maximal Marginal Relevance-like deduplication.

    Keeps at most `max_per_entry` chunks per work_entry_id,
    prioritizing higher-scoring chunks.
    """
    seen_counts: dict[str, int] = {}
    filtered = []

    # Results should already be sorted by score (descending)
    for r in results:
        entry_id = r.payload.get("work_entry_id", r.payload.get("project_id", ""))
        current_count = seen_counts.get(entry_id, 0)

        if current_count < max_per_entry:
            filtered.append(r)
            seen_counts[entry_id] = current_count + 1

    return filtered


def _merge_chunks_to_entries(chunks: list) -> list[RetrievedEntry]:
    """Merge multiple chunks from the same work_entry into a single RetrievedEntry.

    Combines skills, technologies, and impact from all chunks of the same entry.
    Uses the highest-scoring chunk's score.
    """
    entries_map: dict[str, RetrievedEntry] = {}

    for chunk in chunks:
        payload = chunk.payload
        entry_id = payload.get("work_entry_id", payload.get("project_id", ""))

        if entry_id not in entries_map:
            entries_map[entry_id] = RetrievedEntry(
                work_entry_id=entry_id,
                title=payload.get("title", ""),
                company=payload.get("company", ""),
                role=payload.get("role", ""),
                entry_type=payload.get("entry_type", "project"),
                priority=payload.get("priority", 3),
                project_summary=payload.get("project_summary", ""),
                skills=list(payload.get("skills", [])),
                technologies=list(payload.get("technologies", [])),
                impact=list(payload.get("impact", [])),
                domain=payload.get("domain", ""),
                score=getattr(chunk, "score", 0) or 0,
            )
        else:
            # Merge additional data from this chunk
            existing = entries_map[entry_id]
            for skill in payload.get("skills", []):
                if skill not in existing.skills:
                    existing.skills.append(skill)
            for tech in payload.get("technologies", []):
                if tech not in existing.technologies:
                    existing.technologies.append(tech)
            for imp in payload.get("impact", []):
                if imp not in existing.impact:
                    existing.impact.append(imp)
            # Keep the higher score
            chunk_score = getattr(chunk, "score", 0) or 0
            if chunk_score > existing.score:
                existing.score = chunk_score
            # Use the richer summary
            chunk_summary = payload.get("project_summary", "")
            if chunk_summary and len(chunk_summary) > len(existing.project_summary):
                existing.project_summary = chunk_summary

    # Sort by score descending
    return sorted(entries_map.values(), key=lambda e: e.score, reverse=True)


class TypedRetriever:
    """Performs typed retrieval: separate queries per entry_type with MMR."""

    SCORE_THRESHOLD = 0.45

    def __init__(self):
        pass

    def retrieve(
        self,
        query_vector: list[float],
        sparse_indices: Optional[list[int]] = None,
        sparse_values: Optional[list[float]] = None,
        work_top_k: int = 5,
        project_top_k: int = 6,
        oss_top_k: int = 3,
    ) -> RetrievalResult:
        """Retrieve work entries from Qdrant, filtered by type.

        Args:
            query_vector: Dense embedding of the job description.
            sparse_indices: BM25 sparse vector indices (optional).
            sparse_values: BM25 sparse vector values (optional).
            work_top_k: Max work experience chunks to retrieve.
            project_top_k: Max project chunks to retrieve.
            oss_top_k: Max OSS chunks to retrieve.

        Returns:
            RetrievalResult with typed entries, deduplicated and merged.
        """
        result = RetrievalResult()

        # Retrieve per type
        for entry_type, top_k, target_list_attr in [
            (EntryType.WORK_EXPERIENCE, work_top_k, "work_entries"),
            (EntryType.PROJECT, project_top_k, "project_entries"),
            (EntryType.OSS, oss_top_k, "oss_entries"),
        ]:
            try:
                chunks = qdrant_service.search_filtered(
                    query_vector=query_vector,
                    top_k=top_k * 2,  # Over-fetch for MMR
                    entry_type=entry_type.value,
                    score_threshold=self.SCORE_THRESHOLD,
                    sparse_indices=sparse_indices,
                    sparse_values=sparse_values,
                )

                # Apply MMR deduplication
                deduped = _apply_mmr(chunks, max_per_entry=2)[:top_k]

                # Merge chunks into entries
                entries = _merge_chunks_to_entries(deduped)
                setattr(result, target_list_attr, entries)

                logger.info(f"Retrieved {len(entries)} {entry_type.value} entries "
                            f"from {len(chunks)} chunks")

            except Exception as e:
                logger.warning(f"Typed retrieval failed for {entry_type.value}: {e}")
                # Fall through — empty list for this type

        # If typed retrieval returned nothing, fall back to unfiltered search
        if result.total_count == 0:
            logger.warning("Typed retrieval returned no results — falling back to unfiltered search")
            try:
                all_chunks = qdrant_service.search(
                    query_vector=query_vector,
                    top_k=15,
                    sparse_indices=sparse_indices,
                    sparse_values=sparse_values,
                )
                deduped = _apply_mmr(all_chunks, max_per_entry=2)
                all_entries = _merge_chunks_to_entries(deduped)

                # Distribute to type buckets
                for entry in all_entries:
                    if entry.entry_type == "work_experience":
                        result.work_entries.append(entry)
                    elif entry.entry_type == "oss":
                        result.oss_entries.append(entry)
                    else:
                        result.project_entries.append(entry)

                logger.info(f"Unfiltered fallback: {result.total_count} entries")

            except Exception as e:
                logger.error(f"Unfiltered retrieval also failed: {e}")

        return result
