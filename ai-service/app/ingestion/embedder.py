"""
Local Embedding Service using HuggingFace all-MiniLM-L6-v2.

Generates dense 384-dimensional vector embeddings for text passages and document chunks
completely locally on CPU, without external API calls or network egress.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional
import numpy as np

from app.ingestion.chunker import DocumentChunk

DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384


@dataclass
class EmbeddedChunk:
    """Represents a document chunk with its dense vector embedding."""

    chunk_id: str
    doc_name: str
    page_number: int
    chunk_index: int
    text: str
    char_count: int
    doc_sha256: str
    chunk_sha256: str
    embedding: List[float]
    embedding_dim: int
    embedding_model: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation suitable for MongoDB Atlas insertion."""
        return asdict(self)


class LocalEmbeddingService:
    """
    Manages local embedding generation using sentence-transformers.
    Implements lazy model loading and singleton-style caching.
    """

    _instance: Optional["LocalEmbeddingService"] = None

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME):
        """
        Initialize the local embedding service.

        Args:
            model_name: HuggingFace model identifier (default: all-MiniLM-L6-v2).
        """
        self.model_name = model_name
        self.dimension = EMBEDDING_DIMENSION
        self._model = None

    @classmethod
    def get_instance(cls, model_name: str = DEFAULT_MODEL_NAME) -> "LocalEmbeddingService":
        """Singleton accessor to prevent reloading the model into memory multiple times."""
        if cls._instance is None:
            cls._instance = cls(model_name=model_name)
        return cls._instance

    @property
    def model(self):
        """Lazy loader for SentenceTransformer model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            print(f"Loading local embedding model: '{self.model_name}' (dim={self.dimension})...")
            self._model = SentenceTransformer(self.model_name)
            print(f"Model '{self.model_name}' loaded successfully.")
        return self._model

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding vector for a single string.

        Args:
            text: Input text string.

        Returns:
            List of 384 float values representing the normalized vector embedding.
        """
        if not text or not text.strip():
            # Return zero vector for empty strings
            return [0.0] * self.dimension

        vector = self.model.encode(text, normalize_embeddings=True)
        return vector.tolist() if isinstance(vector, np.ndarray) else list(vector)

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embedding vectors for a list of strings in batches.

        Args:
            texts: List of input strings.
            batch_size: Batch size for model inference.

        Returns:
            List of 384-dimensional float vector lists.
        """
        if not texts:
            return []

        clean_texts = [t if t and t.strip() else " " for t in texts]
        vectors = self.model.encode(
            clean_texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return [v.tolist() for v in vectors]

    def embed_chunks(
        self,
        chunks: List[DocumentChunk],
        batch_size: int = 32,
    ) -> List[EmbeddedChunk]:
        """
        Generate vector embeddings for a list of DocumentChunk instances.

        Args:
            chunks: List of DocumentChunk instances.
            batch_size: Batch size for batched inference.

        Returns:
            List of EmbeddedChunk instances enriched with vector embeddings.
        """
        if not chunks:
            return []

        texts = [chunk.text for chunk in chunks]
        embeddings = self.embed_batch(texts, batch_size=batch_size)

        embedded_chunks: List[EmbeddedChunk] = []
        for chunk, emb in zip(chunks, embeddings):
            embedded_chunk = EmbeddedChunk(
                chunk_id=chunk.chunk_id,
                doc_name=chunk.doc_name,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                char_count=chunk.char_count,
                doc_sha256=chunk.doc_sha256,
                chunk_sha256=chunk.chunk_sha256,
                embedding=emb,
                embedding_dim=len(emb),
                embedding_model=self.model_name,
                metadata=chunk.metadata,
            )
            embedded_chunks.append(embedded_chunk)

        return embedded_chunks

    @staticmethod
    def compute_similarity(vector_a: List[float], vector_b: List[float]) -> float:
        """
        Compute cosine similarity between two normalized vectors.

        Args:
            vector_a: First vector.
            vector_b: Second vector.

        Returns:
            Cosine similarity score between -1.0 and 1.0.
        """
        a = np.array(vector_a, dtype=np.float32)
        b = np.array(vector_b, dtype=np.float32)

        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        return float(np.dot(a, b) / (norm_a * norm_b))
