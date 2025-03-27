"""
Chainlit-based chatbot for Root Cause Analysis assistance with RAG
capabilities.
"""
# Standard libs
import os

# Third-party libs
try:
    from openai import AsyncOpenAI
    import chainlit as cl
    from chainlit.input_widget import Select, Switch, Slider
    from pymongo import MongoClient
    from qdrant_client import QdrantClient
except ImportError as e:
    print(f"Error importing required libraries: {e}")
    print("openai chainlit pymongo qdrant-client")
    raise

SEARCH_INSTRUCTION = "Represent this sentence " \
                "for searching relevant passages: "
LOGO_URL = "https://www.redhat.com/rhdc/managed-files/" \
            "Asset-Red_Hat-Logo_page-General-This-RGB.svg"

llm_api_url = os.environ.get("LLM_API_URL", 'http://<changeme>/v1')
llm_api_key = os.environ.get("LLM_API_KEY")
generative_model = os.environ.get("DEFAULT_MODEL_NAME",
                                  'Mistral-7B-Instruct-v0.2')
embeddings_model = os.environ.get("DEFAULT_EMBEDDINGS_MODEL",
                                  'bge-large-en-v1.5')

default_temperature = os.environ.get("DEFAULT_MODEL_TEMPERATURE", 0.7)
default_max_tokens = os.environ.get("DEFAULT_MODEL_MAX_TOKENS", 1024)
default_top_p = os.environ.get("DEFAULT_MODEL_TOP_P", 1)
default_n = os.environ.get("DEFAULT_MODEL_N", 1)

db_url = os.environ.get("DB_URL",
                        'mongodb://mongoadmin:<changeme>@<changeme>:27017/')
default_db_name = os.environ.get("DEFAULT_DB_NAME", 'conversations')
default_collection_name = os.environ.get("DEFAULT_COLLECTION_NAME",
                                         'debug-collection')
vectordb_url = os.environ.get("VECTORDB_URL", '<changeme>')

# Vector Storage client
vectordb_client = QdrantClient(vectordb_url, port=6333)
vectordb_collection_name = os.environ.get("VECTORDB_COLLECTION_NAME",
                                          'all-jira-tickets')

# Message history storage
db_client = MongoClient(db_url)
conv_db = db_client[default_db_name]
collection = conv_db[default_collection_name]

llm = AsyncOpenAI(
    base_url=llm_api_url,
    organization='',
    api_key=llm_api_key)


async def db_lookup(search_string: str,
                    model_name: str, search_top_n: int = 5,
                    search_sensitive: float = 0.8) -> list:
    """
    Search the vector database for relevant content based on the input query.
    Args:
        search_string: The query to search for
        embedding_model: The model to use for creating embeddings
        search_top_n: Maximum number of results to return
        search_sensitive: Minimum similarity score threshold
    Returns:
        List of search results with text and metadata
    """
    results = []
    embedding = await llm.embeddings.create(model=model_name,
                                            input=search_string,
                                            encoding_format='float')
    embedding = embedding.data[0].embedding
    search_results = vectordb_client.search(
        collection_name=vectordb_collection_name,
        query_vector=embedding,
        limit=search_top_n)
    for res in search_results:
        if res.score >= search_sensitive:
            results.append(
                {
                    "score": res.score,
                    "url": res.payload['url']
                })
    return results


@cl.on_chat_start
async def init_chat():
    """
    Initialize the chat session with default settings and user interface
    elements.
    Sets up model selection, parameters, and initial message history.
    """
    settings = await cl.ChatSettings(
        [
            Select(
                id="model",
                label="Chat - Model",
                values=[generative_model],
                initial_index=0,
            ),
            Slider(
                id="temperature",
                label="Model Temperature",
                initial=default_temperature,
                min=0,
                max=1,
                step=0.1,
            ),
            Slider(
                id="max_tokens",
                label="Max Tokens",
                initial=default_max_tokens,
                min=1,
                max=1024,
                step=1,
            ),
            Switch(id="stream", label="Stream a response", initial=True)
            ]
    ).send()
    cl.user_session.set("model_settings", settings)
    await cl.Avatar(
        name="OpenStack",
        url=LOGO_URL,
    ).send()


@cl.action_callback("feedback")
async def on_action(action):
    """
    Handle user feedback on chat responses.
    Updates the database with the feedback value.
    """
    filter_msg = {"message_id": action.forId}
    value = {"$set": {"feedback": action.value}}
    collection.update_one(filter_msg, value)


@cl.on_message
async def main(message: cl.Message):
    """
    Main message handler that processes user input, searches for context,
    and generates AI responses.
    """
    model_settings = cl.user_session.get("model_settings")
    message_history = [{"role": "system",
                        "content": "Your name is Openstack. "
                        "Help to investigate the issue"}]
    message_history.append({"role": "user", "content": message.content})

    actions = [
            cl.Action(name="feedback", value="positive",
                      label="Affirmative", description="Positive feedback"),
            cl.Action(name="feedback", value="negative",
                      label="Negative", description="Negative feedback")
        ]
    msg = cl.Message(content="", actions=actions)

    if model_settings['stream']:
        async for stream_resp in await llm.chat.completions.create(
            messages=message_history, **model_settings
        ):
            if token := stream_resp.choices[0].delta.content or "":
                await msg.stream_token(token)
    else:
        content = await llm.chat.completions.create(
            messages=message_history, **model_settings)
        msg.content = content.choices[0].message.content

    # Searching
    search_query = SEARCH_INSTRUCTION + message.content
    search_summ_message = SEARCH_INSTRUCTION + msg.content

    search_results_query = await db_lookup(search_query, embeddings_model)
    search_results_sum = await db_lookup(search_summ_message, embeddings_model)

    all_search_results = search_results_query + search_results_sum
    search_results = sorted(all_search_results, key=lambda x: x['score'],
                            reverse=True)

    search_message = ""
    for result in search_results:
        score = result.get('score', 0)
        if score >= 0.8:
            search_message += f'🔗 {result["url"]}, Similarity Score: {score}\n'
    if search_message != "":
        await cl.Message(content="Top similar bugs:\n" + search_message).send()

    user_id = cl.user_session.get("id")

    record = {
        "conversation_id": user_id,
        "create_at": msg.created_at,
        "message_id": msg.id,
        "prompt": message.content,
        "search_results": search_results,
        "model_reply": msg.content,
        "settings": model_settings,
        "feedback": None
    }
    collection.insert_one(record)
    await msg.send()
