"""
MongoDB Atlas Database Connection and Vector Search Manager.

Manages connections to MongoDB Atlas, handles collection lifecycle for
document_fingerprints and document_chunks, and provides hybrid vector search
capabilities with automatic fallback.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
import numpy as np
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, OperationFailure, PyMongoError

from app.core.config import settings

if TYPE_CHECKING:
    from app.ingestion.embedder import EmbeddedChunk


class DatabaseManager:
    """Manages MongoDB Atlas database client, collections, indexes, and vector operations."""

    def __init__(
        self,
        uri: Optional[str] = None,
        db_name: Optional[str] = None,
        client: Optional[Any] = None,
    ):
        """
        Initialize DatabaseManager.

        Args:
            uri: MongoDB connection string (defaults to settings.MONGODB_URI).
            db_name: Database name (defaults to settings.MONGODB_DB_NAME).
            client: Optional pre-configured client (useful for injecting mongomock in tests).
        """
        self.uri = uri or settings.MONGODB_URI
        self.db_name = db_name or settings.MONGODB_DB_NAME
        self.vector_index_name = settings.VECTOR_INDEX_NAME

        if client is not None:
            self.client = client
        elif self.uri:
            try:
                self.client = MongoClient(
                    self.uri,
                    serverSelectionTimeoutMS=2000,
                    connectTimeoutMS=2000,
                    socketTimeoutMS=5000,
                    maxPoolSize=50,
                    minPoolSize=5,
                    retryWrites=True,
                )
                # Quick probe to test connectivity; fallback if network is restricted
                self.client.admin.command("ping")
            except Exception:
                import mongomock
                self.client = mongomock.MongoClient()
        else:
            # Fallback to in-memory mongomock when no URI is provided
            import mongomock
            self.client = mongomock.MongoClient()

        self.db: Database = self.client.get_database(self.db_name)
        self.fingerprints_col: Collection = self.db.get_collection("document_fingerprints")
        self.chunks_col: Collection = self.db.get_collection("document_chunks")
        self.checkpoints_col: Collection = self.db.get_collection("conversation_checkpoints")

    def ping(self) -> bool:
        """Verify database connectivity."""
        try:
            self.client.admin.command("ping")
            return True
        except Exception:
            return False

    def init_indexes(self) -> None:
        """Create required standard indexes for efficient lookup and idempotency."""
        try:
            # Fingerprints collection indexes
            self.fingerprints_col.create_index([("doc_name", ASCENDING)], unique=True)
            self.fingerprints_col.create_index([("doc_sha256", ASCENDING)])

            # Chunks collection indexes
            self.chunks_col.create_index([("chunk_id", ASCENDING)], unique=True)
            self.chunks_col.create_index([("doc_name", ASCENDING)])
            self.chunks_col.create_index([("doc_sha256", ASCENDING)])
            self.chunks_col.create_index([("page_number", ASCENDING)])

            # Conversation Checkpoints indexes (Day 13)
            self.checkpoints_col.create_index([("thread_id", ASCENDING)])
            self.checkpoints_col.create_index([("thread_id", ASCENDING), ("turn_index", ASCENDING)])
            self.checkpoints_col.create_index([("created_at", DESCENDING)])
        except (OperationFailure, PyMongoError, Exception) as err:
            # Some mock implementations or restricted environments skip index creation
            pass

    # =========================================================================
    # Fingerprint Management (Idempotency Engine)
    # =========================================================================

    def get_fingerprint(self, doc_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored fingerprint record for a document by name."""
        return self.fingerprints_col.find_one({"doc_name": doc_name})

    def is_document_unchanged(self, doc_name: str, doc_sha256: str) -> bool:
        """
        Check if a document has already been ingested with the identical SHA-256 hash.

        Args:
            doc_name: PDF filename (e.g. "Company_HR_and_Work_Rules.pdf").
            doc_sha256: 64-character SHA-256 checksum string.

        Returns:
            True if the document exists in MongoDB with the same hash, False otherwise.
        """
        record = self.get_fingerprint(doc_name)
        if not record:
            return False
        return record.get("doc_sha256") == doc_sha256

    def save_fingerprint(
        self,
        doc_name: str,
        doc_sha256: str,
        total_pages: int,
        chunk_count: int,
    ) -> None:
        """
        Save or update a document's fingerprint registry entry.

        Args:
            doc_name: PDF filename.
            doc_sha256: File checksum.
            total_pages: Extracted page count.
            chunk_count: Number of chunks generated and stored.
        """
        now = datetime.now(timezone.utc).isoformat()
        self.fingerprints_col.update_one(
            {"doc_name": doc_name},
            {
                "$set": {
                    "doc_name": doc_name,
                    "doc_sha256": doc_sha256,
                    "total_pages": total_pages,
                    "chunk_count": chunk_count,
                    "ingested_at": now,
                    "status": "indexed",
                }
            },
            upsert=True,
        )

    # =========================================================================
    # Document Chunk Management
    # =========================================================================

    def delete_chunks_by_document(self, doc_name: str) -> int:
        """
        Remove all stored chunks for a document (used when replacing updated documents).

        Args:
            doc_name: PDF filename.

        Returns:
            Count of deleted chunk documents.
        """
        result = self.chunks_col.delete_many({"doc_name": doc_name})
        return result.deleted_count

    def insert_chunks(self, chunks: List[Any]) -> int:
        """
        Bulk insert embedded chunks into MongoDB.

        Args:
            chunks: List of EmbeddedChunk instances or dictionary objects.

        Returns:
            Count of successfully inserted chunks.
        """
        if not chunks:
            return 0

        documents = [c.to_dict() if hasattr(c, "to_dict") else c for c in chunks]
        result = self.chunks_col.insert_many(documents, ordered=False)
        return len(result.inserted_ids)

    def get_chunks_by_document(self, doc_name: str) -> List[Dict[str, Any]]:
        """Retrieve all stored chunks for a specific document."""
        return list(self.chunks_col.find({"doc_name": doc_name}).sort("chunk_index", ASCENDING))

    def get_total_chunks(self) -> int:
        """Return total number of chunks indexed in the database."""
        return self.chunks_col.count_documents({})

    def get_all_fingerprints(self) -> List[Dict[str, Any]]:
        """Return list of all registered document fingerprints."""
        return list(self.fingerprints_col.find({}, {"_id": 0}))

    # =========================================================================
    # Vector Search & Semantic Retrieval
    # =========================================================================

    def vector_search(
        self,
        query_vector: List[float],
        limit: int = 5,
        doc_filter: Optional[str] = None,
        search_metric: str = "cosine",
        query_text: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute vector search for nearest chunks.

        Attempts MongoDB Atlas $vectorSearch aggregation pipeline first.
        If Atlas Vector Search index is not yet built or running on mock DB,
        seamlessly falls back to in-memory cosine similarity calculation.

        Args:
            query_vector: 384-dimensional query embedding.
            limit: Maximum number of closest chunks to return.
            doc_filter: Optional doc_name filter to restrict search to a single PDF.

        Returns:
            List of matching chunk documents with similarity 'score'.
        """
        # Try native MongoDB Atlas $vectorSearch pipeline
        try:
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": self.vector_index_name,
                        "path": "embedding",
                        "queryVector": query_vector,
                        "numCandidates": limit * 10,
                        "limit": limit,
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "chunk_id": 1,
                        "doc_name": 1,
                        "page_number": 1,
                        "chunk_index": 1,
                        "text": 1,
                        "char_count": 1,
                        "doc_sha256": 1,
                        "chunk_sha256": 1,
                        "score": {"$meta": "vectorSearchScore"},
                        "metadata": 1,
                    }
                },
            ]

            if doc_filter:
                pipeline[0]["$vectorSearch"]["filter"] = {"doc_name": {"$eq": doc_filter}}

            cursor = self.chunks_col.aggregate(pipeline)
            results = list(cursor)
            if results:
                return results
        except (OperationFailure, PyMongoError, NotImplementedError, Exception):
            # Fall back to in-memory calculation below
            pass

        # In-memory cosine similarity fallback
        filter_query = {"doc_name": doc_filter} if doc_filter else {}
        cursor = self.chunks_col.find(filter_query, {"_id": 0})

        q_vec = np.array(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0.0:
            return []

        scored_results: List[Dict[str, Any]] = []
        for doc in cursor:
            emb = doc.get("embedding")
            if not emb:
                continue

            d_vec = np.array(emb, dtype=np.float32)
            d_norm = np.linalg.norm(d_vec)
            if d_norm == 0.0:
                continue

            if search_metric == "dot":
                similarity = float(np.dot(q_vec / q_norm, d_vec / d_norm))
            elif search_metric == "euclidean":
                dist = float(np.linalg.norm(q_vec - d_vec))
                similarity = float(1.0 / (1.0 + dist))
            elif search_metric == "hybrid" and query_text:
                dense_sim = float(np.dot(q_vec, d_vec) / (q_norm * d_norm))
                import re
                q_words = set(re.findall(r"\w+", query_text.lower()))
                d_words = set(re.findall(r"\w+", doc.get("text", "").lower()))
                overlap = len(q_words.intersection(d_words)) / max(len(q_words), 1)
                similarity = float(0.75 * dense_sim + 0.25 * overlap)
            else:
                similarity = float(np.dot(q_vec, d_vec) / (q_norm * d_norm))

            doc_copy = dict(doc)
            doc_copy["score"] = similarity
            # Omit large raw vector from final search response for efficiency
            doc_copy.pop("embedding", None)
            scored_results.append(doc_copy)

        scored_results.sort(key=lambda x: x["score"], reverse=True)
        return scored_results[:limit]

    # =========================================================================
    # Conversation Checkpoint & Memory Operations (Day 13)
    # =========================================================================

    def save_checkpoint(self, thread_id: str, checkpoint_data: Dict[str, Any]) -> str:
        """
        Persist a conversation state checkpoint to MongoDB.

        Args:
            thread_id: Unique conversation thread identifier.
            checkpoint_data: State dictionary containing query, answer, entities, citations, and trace.

        Returns:
            The inserted document ID as a string.
        """
        doc = dict(checkpoint_data)
        doc["thread_id"] = thread_id
        if "created_at" not in doc:
            doc["created_at"] = datetime.now(timezone.utc).isoformat()

        res = self.checkpoints_col.insert_one(doc)
        return str(res.inserted_id)

    def get_latest_checkpoint(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the most recent checkpoint for a given thread_id.

        Args:
            thread_id: Conversation thread identifier.

        Returns:
            Dictionary representation of the latest state checkpoint or None.
        """
        record = self.checkpoints_col.find_one(
            {"thread_id": thread_id},
            {"_id": 0},
            sort=[("turn_index", DESCENDING), ("created_at", DESCENDING)],
        )
        return record

    def get_thread_history(self, thread_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieve chronological conversation turns for a given thread.

        Args:
            thread_id: Conversation thread identifier.
            limit: Maximum turns to return.

        Returns:
            List of conversation turn dictionaries in ascending chronological order.
        """
        cursor = self.checkpoints_col.find(
            {"thread_id": thread_id},
            {"_id": 0},
        ).sort("turn_index", ASCENDING).limit(limit)
        return list(cursor)

    def delete_thread(self, thread_id: str) -> int:
        """
        Delete all checkpoints and history associated with a conversation thread.

        Args:
            thread_id: Conversation thread identifier to clear.

        Returns:
            Count of deleted checkpoint records.
        """
        res = self.checkpoints_col.delete_many({"thread_id": thread_id})
        return res.deleted_count


_db_manager_instance: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    """Singleton provider for DatabaseManager instance."""
    global _db_manager_instance
    if _db_manager_instance is None:
        _db_manager_instance = DatabaseManager()
        _db_manager_instance.init_indexes()
    return _db_manager_instance
