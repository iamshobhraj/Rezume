"""Ingestion service – chunks work entry text, extracts metadata, embeds (dense + sparse), and stores."""

import json
import logging
import uuid

from qdrant_client.models import PointStruct, SparseVector
from sqlalchemy.orm import Session
from fastembed import SparseTextEmbedding

from app.models.work_entry import Chunk, WorkEntry
from app.providers.manager import ProviderManager
from app.services.qdrant_service import qdrant_service

logger = logging.getLogger(__name__)

# Initialize local sparse embedding model for BM25
try:
    sparse_model = SparseTextEmbedding("Qdrant/bm25")
except Exception as e:
    logger.error(f"Failed to load SparseTextEmbedding: {e}")
    sparse_model = None

# Metadata extraction prompt
METADATA_EXTRACTION_PROMPT = """Analyze the following text description of an engineer's project or codebase.
Extract structured metadata as a JSON object with these keys:
- "skills": list of technical skills mentioned
- "technologies": list of technologies, frameworks, tools mentioned
- "impact": list of quantifiable impact statements (metrics, percentages, scale)
- "domain": the business/technical domain (e.g., "backend", "ML", "infrastructure")
- "summary": a one-sentence summary of the project

Respond ONLY with valid JSON, no other text.

Project description:
{project_text}
"""

# Resume-ready project summary prompt (Phase 3 enrichment)
PROJECT_SUMMARY_PROMPT = """Write a concise, resume-ready paragraph (2-3 sentences) summarizing this engineering project.
Focus on: what was built, key technologies used, and measurable impact/scale.
Use active voice and quantify where possible.

Project title: {title}
Company/Context: {company}
Role: {role}

Project description:
{project_text}

Respond ONLY with the paragraph, no other text.
"""


def _split_text_into_chunks(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    if len(words) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


class IngestionService:
    """Handles the ingestion pipeline: chunk → extract metadata → embed → store."""

    def __init__(self, db: Session, provider_manager: ProviderManager):
        self.db = db
        self.pm = provider_manager

    def ingest_project(self, entry_id: str) -> int:
        """Ingest a work entry: chunk it, extract metadata, embed, and store.

        Args:
            entry_id: The UUID of the WorkEntry to ingest.

        Returns:
            Number of chunks created.
        """
        entry = self.db.query(WorkEntry).get(entry_id)
        if entry is None:
            raise ValueError(f"WorkEntry {entry_id} not found")

        # Delete existing chunks for this entry (re-ingestion)
        existing_chunks = self.db.query(Chunk).filter(Chunk.work_entry_id == entry_id).all()
        existing_point_ids = [c.qdrant_point_id for c in existing_chunks if c.qdrant_point_id]
        if existing_point_ids:
            qdrant_service.delete_points(existing_point_ids)
        for chunk in existing_chunks:
            self.db.delete(chunk)
        self.db.flush()

        # Get embedding provider info for collection setup
        emb_provider = self.pm.get_active_embedding_provider()
        if emb_provider is None:
            raise RuntimeError("No active embedding provider configured")
        qdrant_service.ensure_collection(emb_provider.embedding_dim)

        # Split into chunks
        text_chunks = _split_text_into_chunks(entry.raw_text)
        logger.info(f"Split entry '{entry.title}' into {len(text_chunks)} chunks")

        # Generate sparse embeddings all at once if model is loaded
        sparse_embs = None
        if sparse_model:
            try:
                sparse_embs = list(sparse_model.embed(text_chunks))
            except Exception as e:
                logger.warning(f"Sparse embedding failed: {e}")

        # Extract metadata via LLM at the entry level (once per entry)
        try:
            # Limit the raw text to first 50,000 characters to keep it token-friendly
            project_text_sample = entry.raw_text[:50000]
            metadata_response = self.pm.generate(
                messages=[
                    {"role": "user", "content": METADATA_EXTRACTION_PROMPT.format(project_text=project_text_sample)}
                ],
                temperature=0.1,
                max_tokens=1024,
            )
            cleaned = metadata_response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
            metadata = json.loads(cleaned)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Metadata extraction failed for entry '{entry.title}': {e}")
            metadata = {"skills": [], "technologies": [], "impact": [], "domain": "", "summary": ""}

        # Generate resume-ready project summary (enriched context for generation)
        project_summary = ""
        try:
            summary_response = self.pm.generate(
                messages=[
                    {"role": "user", "content": PROJECT_SUMMARY_PROMPT.format(
                        title=entry.title,
                        company=entry.company or "Personal",
                        role=entry.role or "Engineer",
                        project_text=entry.raw_text[:10000],
                    )}
                ],
                temperature=0.2,
                max_tokens=256,
            )
            project_summary = summary_response.strip()
        except Exception as e:
            logger.warning(f"Project summary generation failed for '{entry.title}': {e}")
            project_summary = metadata.get("summary", "")

        points = []
        for i, chunk_text in enumerate(text_chunks):
            chunk_id = str(uuid.uuid4())
            point_id = str(uuid.uuid4())

            # Generate dense embedding
            dense_embedding = self.pm.embed_text(chunk_text)
            
            # Construct vectors dictionary
            vector_dict = {"dense": dense_embedding}
            if sparse_embs and i < len(sparse_embs):
                vector_dict["sparse"] = SparseVector(
                    indices=sparse_embs[i].indices.tolist(),
                    values=sparse_embs[i].values.tolist(),
                )

            # Create Qdrant point with entry_type in payload for filtered retrieval
            payload = {
                "work_entry_id": entry_id,
                "chunk_id": chunk_id,
                "title": entry.title,
                "company": entry.company or "",
                "role": entry.role or "",
                "entry_type": entry.entry_type.value if entry.entry_type else "project",
                "priority": entry.priority,
                "project_summary": project_summary,
                **metadata,
            }
            points.append(PointStruct(id=point_id, vector=vector_dict, payload=payload))

            # Create DB chunk record
            db_chunk = Chunk(
                id=chunk_id,
                work_entry_id=entry_id,
                chunk_text=chunk_text,
                metadata_json=json.dumps(metadata),
                qdrant_point_id=point_id,
            )
            self.db.add(db_chunk)

        # Batch upsert to Qdrant
        if points:
            qdrant_service.upsert_vectors(points)

        self.db.commit()
        logger.info(f"Ingested {len(points)} chunks for entry '{entry.title}'")
        return len(points)

    def rebuild_all_embeddings(self) -> int:
        """Delete the Qdrant collection and re-ingest all work entries."""
        qdrant_service.delete_collection()

        entries = self.db.query(WorkEntry).all()
        total = 0
        for entry in entries:
            count = self.ingest_project(entry.id)
            total += count

        logger.info(f"Rebuilt all embeddings: {total} chunks across {len(entries)} entries")
        return total

# Global singleton
ingestion_service = IngestionService(None, None) # Will be properly instantiated in routers
