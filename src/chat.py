"""Handler for chat messages and responses."""
import chainlit as cl

from generation import process_message_and_get_response
from embeddings import db_lookup
from conversation import conversation_store
from config import config


async def perform_search(user_content):
    """
    Perform search with user input.

    Args:
        user_content: User's input query

    Returns:
        List of unique search results sorted by relevance
    """
    search_results = []

    # Search based on user query first
    if user_content:
        search_query = config.search_instruction + user_content
        search_results_query = await db_lookup(search_query,
                                               config.embeddings_model)
        search_results.extend(search_results_query)

    # Remove duplicates (based on URL) and sort by score
    unique_results = {}
    for result in search_results:
        url = result.get('url')
        if url in unique_results:
            # Keep the result with higher score
            if result.get('score', 0) > unique_results[url].get('score', 0):
                unique_results[url] = result
        else:
            unique_results[url] = result

    return sorted(list(unique_results.values()),
                  key=lambda x: x.get('score', 0), reverse=True)


def search_results_for_context(search_results) -> str:
    """
    Format search results into a readable string.

    Args:
        search_results: List of search results

    Returns:
        Formatted string with search results
    """
    if not search_results:
        return "No relevant results found."

    filtered = [
        f"{res.get('text')}, Similarity Score: {res.get('score', 0)}"
        for res in search_results
    ]

    if filtered:
        return "\n".join(filtered)

    return "No highly relevant results found."


def append_searched_urls(search_results, resp):
    """
    Append search urls.

    Args:
        search_results: List of search results
        resp: The response message object to populate
    """
    search_message = ""
    for result in search_results:
        score = result.get('score', 0)
        search_message += f'🔗 {result["url"]}, Similarity Score: {score}\n'
    if search_message != "":
        resp.content += "\n\nTop similar bugs:\n" + search_message


async def handle_user_message(message: cl.Message):
    """
    Main handler for user messages.

    Args:
        message: The user's input message
    """
    model_settings = cl.user_session.get("model_settings")

    # Create response message with feedback actions
    actions = [
        cl.Action(name="feedback", label="Affirmative",
                  payload={"feedback": "positive"}),
        cl.Action(name="feedback", label="Negative",
                  payload={"feedback": "negative"})
    ]
    resp = cl.Message(content="", actions=actions)

    search_results = await perform_search(message.content)
    if search_results:
        message.content += (f"\n\nReply in the following context:"
                            f"\n{search_results_for_context(search_results)}")

    # Process user message and get AI response
    await process_message_and_get_response(message, resp, model_settings)

    # Extend response with searched jira urls
    append_searched_urls(search_results, resp)

    # Save conversation data
    user_id = cl.user_session.get("id")
    conversation_data = {
        "user_id": user_id,
        "user_message": message.content,
        "ai_response": resp.content,
        "model_settings": model_settings,
        "search_results": search_results
    }
    conversation_store.save(conversation_data)

    await resp.send()
