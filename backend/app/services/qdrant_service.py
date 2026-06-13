"""Qdrant vector database service – collection management, upsert, and search."""

import logging
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Distance, PointStruct, VectorParams, Filter, SparseVectorParams, Prefetch, FusionQuery, Fusion, SparseVector

from app.config import settings

logger = logging.getLogger(__name__)


class QdrantService:
    """Manages Qdrant collections and vector operations."""

    COLLECTION_NAME = "work_chunks"

    def __init__(self):
        self._client = None

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            if settings.qdrant_url and settings.qdrant_api_key:
                self._client = QdrantClient(
                    url=settings.qdrant_url,
                    api_key=settings.qdrant_api_key,
                )
            else:
                # Local persistent storage
                import os
                os.makedirs("local_qdrant", exist_ok=True)
                logger.info("Using persistent local Qdrant storage.")
                self._client = QdrantClient(path="local_qdrant")
        return self._client

    def ensure_collection(self, vector_size: int) -> None:
        """Create the work_chunks collection if it doesn't exist."""
        try:
            info = self.client.get_collection(self.COLLECTION_NAME)
            # check dimension of dense vector
            existing_dim = info.config.params.vectors.get("dense").size if isinstance(info.config.params.vectors, dict) else info.config.params.vectors.size
            if existing_dim != vector_size:
                logger.warning(
                    f"Collection dimension mismatch: existing={existing_dim}, "
                    f"expected={vector_size}. Re-ingestion may be required."
                )
            return
        except (UnexpectedResponse, Exception):
            pass

        self.client.create_collection(
            collection_name=self.COLLECTION_NAME,
            vectors_config={
                "dense": VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,
                )
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams()
            }
        )
        logger.info(f"Created Qdrant hybrid collection '{self.COLLECTION_NAME}' with dense_dim={vector_size}")

    def check_dimension_mismatch(self, expected_dim: int) -> Optional[dict]:
        """Check if the current collection dimension matches the expected dimension."""
        try:
            info = self.client.get_collection(self.COLLECTION_NAME)
            existing_dim = info.config.params.vectors.get("dense").size if isinstance(info.config.params.vectors, dict) else info.config.params.vectors.size
            if existing_dim != expected_dim:
                return {
                    "existing_dim": existing_dim,
                    "expected_dim": expected_dim,
                    "message": (
                        f"Current collection uses {existing_dim}-dim vectors, "
                        f"but active embedding provider produces {expected_dim}-dim vectors. "
                        f"Re-ingestion required to use the new provider."
                    ),
                }
        except Exception:
            pass
        return None

    def upsert_vectors(self, points: list[PointStruct]) -> None:
        """Batch upsert vectors into the collection."""
        if not points:
            return
        self.client.upsert(
            collection_name=self.COLLECTION_NAME,
            points=points,
        )
        logger.info(f"Upserted {len(points)} vectors to Qdrant")

    def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        score_threshold: float = 0.0,
        sparse_indices: list[int] = None,
        sparse_values: list[float] = None,
    ) -> list:
        """Search for similar vectors using hybrid search if sparse vector is provided."""
        
        # Determine if we should use hybrid search
        if sparse_indices is not None and sparse_values is not None:
            return self.client.query_points(
                collection_name=self.COLLECTION_NAME,
                prefetch=[
                    Prefetch(
                        query=query_vector,
                        using="dense",
                        limit=top_k,
                    ),
                    Prefetch(
                        query=SparseVector(indices=sparse_indices, values=sparse_values),
                        using="sparse",
                        limit=top_k,
                    )
                ],
                query=FusionQuery(fusion=Fusion.RRF),
                limit=top_k,
            ).points
        else:
            # Fallback to dense-only if sparse is unavailable
            return self.client.query_points(
                collection_name=self.COLLECTION_NAME,
                query=query_vector,
                using="dense",
                limit=top_k,
                score_threshold=score_threshold,
            ).points

    def search_filtered(
        self,
        query_vector: list[float],
        top_k: int = 10,
        entry_type: str = None,
        score_threshold: float = 0.45,
        sparse_indices: list[int] = None,
        sparse_values: list[float] = None,
    ) -> list:
        """Search for similar vectors with payload filtering by entry_type.

        Uses hybrid search if sparse vector is provided, otherwise dense-only.
        """
        from qdrant_client.models import FieldCondition, MatchValue

        # Build filter
        must_conditions = []
        if entry_type:
            must_conditions.append(
                FieldCondition(key="entry_type", match=MatchValue(value=entry_type))
            )
        query_filter = Filter(must=must_conditions) if must_conditions else None

        if sparse_indices is not None and sparse_values is not None:
            return self.client.query_points(
                collection_name=self.COLLECTION_NAME,
                prefetch=[
                    Prefetch(
                        query=query_vector,
                        using="dense",
                        limit=top_k,
                        filter=query_filter,
                    ),
                    Prefetch(
                        query=SparseVector(indices=sparse_indices, values=sparse_values),
                        using="sparse",
                        limit=top_k,
                        filter=query_filter,
                    )
                ],
                query=FusionQuery(fusion=Fusion.RRF),
                limit=top_k,
                filter=query_filter,
            ).points
        else:
            return self.client.query_points(
                collection_name=self.COLLECTION_NAME,
                query=query_vector,
                using="dense",
                limit=top_k,
                score_threshold=score_threshold,
                filter=query_filter,
            ).points

    def delete_points(self, point_ids: list[str]) -> None:
        """Delete specific points from the collection."""
        if not point_ids:
            return
        self.client.delete(
            collection_name=self.COLLECTION_NAME,
            points_selector=point_ids,
        )
        logger.info(f"Deleted {len(point_ids)} points from Qdrant")

    def delete_collection(self) -> None:
        """Delete the entire collection (for re-ingestion)."""
        try:
            self.client.delete_collection(self.COLLECTION_NAME)
            logger.info(f"Deleted Qdrant collection '{self.COLLECTION_NAME}'")
        except Exception:
            logger.warning(f"Collection '{self.COLLECTION_NAME}' did not exist")

    def get_collection_info(self) -> Optional[dict]:
        """Get collection metadata including vector count and dimension."""
        try:
            info = self.client.get_collection(self.COLLECTION_NAME)
            return {
                "vector_count": info.points_count,
                "vector_size": info.config.params.vectors.size,
            }
        except Exception:
            return None


# Module-level singleton
qdrant_service = QdrantService()
