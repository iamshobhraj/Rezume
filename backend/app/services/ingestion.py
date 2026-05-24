"""Ingestion service – chunks project text, extracts metadata, embeds (dense + sparse), and stores."""

import json
import logging
import uuid

from qdrant_client.models import PointStruct, SparseVector
from sqlalchemy.orm import Session
from fastembed import SparseTextEmbedding

from app.models.project import Chunk, Project
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

    def ingest_project(self, project_id: str) -> int:
        """Ingest a project: chunk it, extract metadata, embed, and store.

        Args:
            project_id: The UUID of the Project to ingest.

        Returns:
            Number of chunks created.
        """
        project = self.db.query(Project).get(project_id)
        if project is None:
            raise ValueError(f"Project {project_id} not found")

        # Delete existing chunks for this project (re-ingestion)
        existing_chunks = self.db.query(Chunk).filter(Chunk.project_id == project_id).all()
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
        text_chunks = _split_text_into_chunks(project.raw_text)
        logger.info(f"Split project '{project.title}' into {len(text_chunks)} chunks")

        # Generate sparse embeddings all at once if model is loaded
        sparse_embs = None
        if sparse_model:
            try:
                sparse_embs = list(sparse_model.embed(text_chunks))
            except Exception as e:
                logger.warning(f"Sparse embedding failed: {e}")

        # Extract metadata via LLM at the project level (once per project)
        try:
            # Limit the raw text to first 50,000 characters to keep it token-friendly
            project_text_sample = project.raw_text[:50000]
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
            logger.warning(f"Metadata extraction failed for project '{project.title}': {e}")
            metadata = {"skills": [], "technologies": [], "impact": [], "domain": "", "summary": ""}

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

            # Create Qdrant point
            payload = {
                "project_id": project_id,
                "chunk_id": chunk_id,
                "title": project.title,
                "company": project.company or "",
                "role": project.role or "",
                "project_type": project.project_type,
                "priority": project.priority,
                **metadata,
            }
            points.append(PointStruct(id=point_id, vector=vector_dict, payload=payload))

            # Create DB chunk record
            db_chunk = Chunk(
                id=chunk_id,
                project_id=project_id,
                chunk_text=chunk_text,
                metadata_json=json.dumps(metadata),
                qdrant_point_id=point_id,
            )
            self.db.add(db_chunk)

        # Batch upsert to Qdrant
        if points:
            qdrant_service.upsert_vectors(points)

        self.db.commit()
        logger.info(f"Ingested {len(points)} chunks for project '{project.title}'")
        return len(points)

    def rebuild_all_embeddings(self) -> int:
        """Delete the Qdrant collection and re-ingest all projects."""
        qdrant_service.delete_collection()

        projects = self.db.query(Project).all()
        total = 0
        for project in projects:
            count = self.ingest_project(project.id)
            total += count

        logger.info(f"Rebuilt all embeddings: {total} chunks across {len(projects)} projects")
        return total

# Global singleton
ingestion_service = IngestionService(None, None) # Will be properly instantiated in routers
