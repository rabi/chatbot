"""Vector database client for RAG operations."""

from typing import List
import chainlit as cl
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ApiException

from config import config


class VectorStore:
    """Abstract interface for vector storage and retrieval operations."""

    def search(
        self, embedding: List[float], top_n: int, similarity_threshold: float
    ) -> list:
        """
        Search for similar vectors in the database.

        Args:
            embedding: Vector embedding to search with
            top_n: Maximum number of results to return
            similarity_threshold: Minimum similarity score threshold

        Returns:
            List of search results with scores and metadata
        """
        raise NotImplementedError

    def get_collection_settings(self) -> tuple[list[str], int]:
        """
        Fetches collection names and determines the initial index.

        Returns:
            Tuple of collection names and the initial collection index
        """
        raise NotImplementedError


class QdrantVectorStore(VectorStore):
    """Qdrant implementation of VectorStore interface."""

    def __init__(self):
        """Initialize the vector database client."""
        self.client = QdrantClient(
            config.vectordb_url,
            api_key=config.vectordb_api_key,
            port=config.vectordb_port,
        )
        cl.logger.info("Qdrant client initialized successfully.")

    def get_collection_settings(self) -> tuple[list[str], int]:
        """Fetches collection names and determines the initial index."""
        collection_names = self._get_collections()
        initial_collection_index = 0
        if config.vectordb_collection_name in collection_names:
            initial_collection_index = collection_names.index(config.vectordb_collection_name)
        else:
            # Handle case where default collection might not exist (e.g., first run)
            # It's already added as the first element, so index 0 is correct.
            cl.logger.warning("Default collection %s not found in Qdrant. " +
                              "Using it as default anyway.", config.vectordb_collection_name)
        return collection_names, initial_collection_index

    def _get_collections(self) -> list[str]:
        """Fetches the list of collection names from Qdrant."""
        collections = [config.vectordb_collection_name]  # Start with the default
        try:
            qdrant_collections = self.client.get_collections().collections
            # Add fetched collections, avoiding duplicates
            for col in qdrant_collections:
                if col.name not in collections:
                    collections.append(col.name)
        except ApiException as e:
            cl.logger.error("Failed to connect to Qdrant to list collections: %s", str(e))
        return collections

    def search(
        self, embedding: List[float], top_n: int, similarity_threshold: float,
        collection_name: str = config.vectordb_collection_name,
    ) -> list:
        """
        Search for similar vectors in the database.

        Args:
            embedding: Vector embedding to search with
            top_n: Maximum number of results to return
            similarity_threshold: Minimum similarity score threshold

        Returns:
            List of search results with scores and metadata
        """
        results = []
        if self.client is None:
            cl.logger.error("Vector database client is not available")
            return results

        try:
            search_results = self.client.search(
                collection_name=collection_name,
                query_vector=embedding,
                limit=top_n,
            )

            for res in search_results:
                if res.score >= similarity_threshold:
                    results.append(
                        {
                            "score": res.score,
                            "url": res.payload["url"],
                            "kind": res.payload["kind"],
                            "text": res.payload["text"],
                            "components": res.payload["components"],
                        }
                    )
            return results
        except ApiException as e:
            cl.logger.error("Error in vector search: %s", str(e))
            return results


# Create singleton instance
vector_store = QdrantVectorStore()
