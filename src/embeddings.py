"""Embedding generation and vector search functionality."""
import chainlit as cl
from openai import AsyncOpenAI, OpenAIError
from qdrant_client.http.exceptions import ApiException

from config import config
from vectordb import vector_store

# Initialize embedding LLM client
emb_llm = AsyncOpenAI(
    base_url=config.embeddings_llm_api_url,
    organization='',
    api_key=config.embeddings_llm_api_key
)


async def generate_embedding(text, model_name=config.embeddings_model):
    """Generate embeddings for the given text using the specified model."""
    try:
        embedding_response = await emb_llm.embeddings.create(
            model=model_name,
            input=text,
            encoding_format='float'
        )

        if not embedding_response:
            cl.logger.error("Failed to get embeddings: " +
                            "No response from model %s", model_name)
            return None
        if not embedding_response.data or len(embedding_response.data) == 0:
            cl.logger.error("Failed to get embeddings: " +
                            "Empty response for model %s", model_name)
            return None

        return embedding_response.data[0].embedding
    except OpenAIError as e:
        cl.logger.error("Error generating embeddings: %s", str(e))
        return None


async def search_similar_content(
        search_string, model_name=config.embeddings_model,
        top_n=config.search_top_n,
        similarity_threshold=config.search_similarity_threshold):
    """
    Search for similar content in the vector database.

    Args:
        search_string: The query to search for
        model_name: The model to use for creating embeddings
        top_n: Maximum number of results to return
        similarity_threshold: Minimum similarity score threshold

    Returns:
        List of search results with text and metadata
    """
    try:
        embedding = await generate_embedding(search_string, model_name)
        if embedding is None:
            return []

        # Search vector database using the embedding
        results = vector_store.search(embedding, top_n,
                                      similarity_threshold)
        return results
    except (ApiException, OpenAIError, ValueError, KeyError) as e:
        cl.logger.error("Error in search_similar_content: %s", str(e))
        return []


async def db_lookup(search_string, model_name=config.embeddings_model,
                    search_top_n=config.search_top_n,
                    search_sensitive=config.search_similarity_threshold):
    """
    Legacy compatibility wrapper for search_similar_content.
    Search the vector database for relevant content based on the input query.
    """
    search_query = config.search_instruction + search_string
    return await search_similar_content(
        search_query, model_name, search_top_n, search_sensitive
    )
