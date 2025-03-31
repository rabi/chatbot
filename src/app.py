"""
Chainlit-based chatbot for Root Cause Analysis assistance with RAG capabilities.
"""

from typing import List, Dict, Any

import config
import db_clients
import llm_clients

# Third-party libs
import chainlit as cl
from chainlit.input_widget import Select, Switch, Slider
from openai import OpenAIError
from pymongo.errors import ConnectionFailure, PyMongoError
from qdrant_client.http.exceptions import ApiException


async def db_lookup(
    search_string: str,
    model_name: str,
    search_top_n: int = 5,
    search_sensitive: float = 0.8
) -> List[Dict[str, Any]]:
    """
    Search the vector database for relevant content based on the input query.

    Args:
        search_string: The query to search for
        model_name: The model to use for creating embeddings
        search_top_n: Maximum number of results to return
        search_sensitive: Minimum similarity score threshold

    Returns:
        List of search results with text and metadata
    """
    results = []

    try:
        cl.logger.debug("Creating embeddings with %s", config.emb_llm_api_url)
        embedding_response = await llm_clients.emb_llm.embeddings.create(
            model=model_name,
            input=search_string,
            encoding_format="float"
        )

        if not embedding_response or not embedding_response.data:
            cl.logger.error("Failed to get embeddings for model %s", model_name)
            return results

        embedding = embedding_response.data[0].embedding
        search_results = db_clients.vectordb_client.search(
            collection_name=config.vectordb_collection_name,
            query_vector=embedding,
            limit=search_top_n
        )

        return [
            {"score": res.score, "url": res.payload["url"]}
            for res in search_results
            if res.score >= search_sensitive
        ]

    except (ApiException, OpenAIError, ValueError, KeyError) as e:
        cl.logger.error("Error in db_lookup: %s", str(e))
        return results

def filter_search_results(search_results: List[Dict[str, Any]]) -> str:
    """Format search results into a readable string."""
    if not search_results:
        return "No relevant results found."

    filtered = [
        f"🔗 {res['url']}, Similarity Score: {res.get('score', 0)}"
        for res in search_results
        if res.get("score", 0) >= 0.8
    ]

    return "Top similar bugs:\n" + "\n".join(filtered) if filtered else "No highly relevant results found."

# Chat Handlers
@cl.on_chat_start
async def init_chat():
    """Initialize the chat session with default settings and UI elements."""
    settings = await cl.ChatSettings(
        [
            Select(
                id="model",
                label="Chat - Model",
                values=[config.generative_model],
                initial_index=0,
            ),
            Slider(
                id="temperature",
                label="Model Temperature",
                initial=config.default_temperature,
                min=0,
                max=1,
                step=0.1,
            ),
            Slider(
                id="max_tokens",
                label="Max Tokens",
                initial=config.default_max_tokens,
                min=1,
                max=1024,
                step=1,
            ),
            Switch(id="stream", label="Stream a response", initial=True)
        ]
    ).send()
    cl.user_session.set("model_settings", settings)

@cl.action_callback("feedback")
async def on_action(action: cl.Action):
    """Handle user feedback on chat responses."""
    if not db_clients.db_available or not db_clients.collection:
        cl.logger.warning("MongoDB is not available - feedback will not be saved")
        return

    try:
        await db_clients.collection.update_one(
            {"message_id": action.forId},
            {"$set": {"feedback": action.payload.get("feedback")}}
        )
    except PyMongoError as e:
        cl.logger.error("Failed to save feedback: %s", str(e))

async def generate_response(
    message_history: List[Dict[str, str]],
    model_settings: Dict[str, Any],
    response_msg: cl.Message
):
    """Generate AI response based on message history and model settings."""
    if model_settings["stream"]:
        async for stream_resp in await llm_clients.gen_llm.chat.completions.create(
            messages=message_history,
            **model_settings
        ):
            if stream_resp.choices and stream_resp.choices[0].delta.content:
                await response_msg.stream_token(stream_resp.choices[0].delta.content)
    else:
        response = await llm_clients.gen_llm.chat.completions.create(
            messages=message_history,
            **model_settings
        )
        response_msg.content = response.choices[0].message.content

async def save_conversation(
    user_message: cl.Message,
    response_msg: cl.Message,
    model_settings: Dict[str, Any],
):
    """Save conversation data to database."""
    if not db_clients.db_available or not db_clients.collection:
        cl.logger.warning("MongoDB is not available - conversation data will not be saved")
        return

    try:
        record = {
            "conversation_id": cl.user_session.get("id"),
            "create_at": response_msg.created_at,
            "message_id": response_msg.id,
            "prompt": user_message.content,
            "model_reply": response_msg.content,
            "settings": model_settings,
            "feedback": None
        }
        await db_clients.collection.insert_one(record)
    except PyMongoError as e:
        cl.logger.error("Failed to save conversation data: %s", str(e))

@cl.on_message
async def main(message: cl.Message):
    """Main message handler for processing user input and generating responses."""
    model_settings = cl.user_session.get("model_settings")
    response_msg = cl.Message(
        content="",
        actions=[
            cl.Action(name="feedback", label="Affirmative", payload={"feedback": "positive"}),
            cl.Action(name="feedback", label="Negative", payload={"feedback": "negative"})
        ]
    )

    # Perform search and add context
    search_results = await db_lookup(
        config.SEARCH_INSTRUCTION + message.content,
        config.embeddings_model
    )
    if search_results:
        message.content += f"\n\nContext:\n{filter_search_results(search_results)}"

    # Generate response
    message_history = [
        {"role": "system", "content": "You are an CI assistant. You help with CI failures and help define RCA."},
        {"role": "user", "content": message.content}
    ]

    await generate_response(message_history, model_settings, response_msg)
    await save_conversation(message, response_msg, model_settings)
    await response_msg.send()
