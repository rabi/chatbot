"""Configuration settings for the RCA chatbot application."""

from dataclasses import dataclass
import os

# Constants for values we don't want to expose to the user
SUGGESTED_MINIMUM_SIMILARITY_THRESHOLD = 0.3


# pylint: disable=too-many-instance-attributes,too-few-public-methods
@dataclass(frozen=True)
class Config:
    """Configuration class for the RCA chatbot."""
    generation_llm_api_url: str
    generation_llm_api_key: str
    embeddings_llm_api_url: str
    embeddings_llm_api_key: str
    embeddings_llm_max_context: int
    generative_model: str
    embeddings_model: str
    default_temperature: float
    default_max_tokens: int
    default_top_p: float
    default_n: int
    auth_database_url: str
    vectordb_url: str
    vectordb_api_key: str
    vectordb_port: int
    vectordb_collection_name: str
    search_instruction: str
    search_similarity_threshold: float
    search_top_n: int
    system_prompt: str
    prompt_header: str
    welcome_message: str

    @classmethod
    def from_env(cls) -> 'Config':
        """Create Config instance from environment variables."""
        return cls(
            generation_llm_api_url=os.environ.get(
                "GENERATION_LLM_API_URL", "http://localhost:8000/v1"),
            generation_llm_api_key=os.environ.get(
                "GENERATION_LLM_API_KEY", ""),
            embeddings_llm_api_url=os.environ.get(
                "EMBEDDINGS_LLM_API_URL", "http://localhost:8000/v1"),
            embeddings_llm_api_key=os.environ.get(
                "EMBEDDINGS_LLM_API_KEY", ""),
            embeddings_llm_max_context=int(os.environ.get(
                "EMBEDDINGS_LLM_MAX_CONTEXT",
                8192,
            )),
            generative_model=os.environ.get(
                "GENERATION_LLM_MODEL_NAME",
                'mistralai/Mistral-7B-Instruct-v0.3'),
            embeddings_model=os.environ.get(
                "EMBEDDINGS_LLM_MODEL_NAME", 'BAAI/bge-m3'),
            default_temperature=float(
                os.environ.get("DEFAULT_MODEL_TEMPERATURE", 0.7)),
            default_max_tokens=int(
                os.environ.get("DEFAULT_MODEL_MAX_TOKENS", 1024)),
            default_top_p=float(
                os.environ.get("DEFAULT_MODEL_TOP_P", 1)),
            default_n=int(os.environ.get("DEFAULT_MODEL_N", 1)),
            auth_database_url=os.environ.get(
                "AUTH_DATABASE_URL",
                "postgresql://<username>:<password>@localhost:5432/users"),
            vectordb_url=os.environ.get(
                "VECTORDB_URL", "http://localhost:6333"),
            vectordb_api_key=os.environ.get("VECTORDB_API_KEY", ""),
            vectordb_port=int(os.environ.get("VECTORDB_PORT", 6333)),
            vectordb_collection_name=os.environ.get(
                "VECTORDB_COLLECTION_NAME", 'rca-knowledge-base'),
            search_instruction=os.environ.get(
                "SEARCH_INSTRUCTION",
                "Represent this sentence for searching relevant passages: "),
            search_similarity_threshold=float(
                os.environ.get("SEARCH_SIMILARITY_THRESHOLD", 0.8)),
            search_top_n=int(os.environ.get("SEARCH_TOP_N", 5)),
            system_prompt=os.environ.get(
                "SYSTEM_PROMPT",
                "# Purpose\n"
                "You are a Continuous Integration (CI) assistant. Your task "
                "is to help users diagnose CI failures, perform Root Cause "
                "Analysis (RCA) and suggest potential fixes. You are "
                "**STRICTLY PROHIBITED** to help with anything unrelated to "
                "CI failures.\n\n"

                "## Instructions:\n"
                "1. If the user **provides** a CI failure or a description "
                "of one in the conversation:\n"
                "   - You **MUST** provide:\n"
                "       - A reason why you believe the failure occurred.\n"
                "       - Potential steps that could help resolve the "
                "issue.\n\n"

                "2. If the user **does not provide** a CI failure or a "
                "description of one in the conversation:\n"
                "   - You **MUST** ask the user to provide a CI failure or a "
                "description of a failure you can analyze.\n\n"

                "## Response Format:\n"
                "1. When the user **does** provide a CI failure in the "
                "conversation:\n"
                "**Root Cause of the Failure:**\n"
                "{{ RCA explanation }}\n\n"

                "**Steps to Resolve:**\n"
                "{{ steps to resolve }}\n\n"

                "{{ RCA explanation }} = This is a placeholder for your "
                "response. Use it to explain the root cause of the failure.\n"
                "{{ steps to resolve }} = This is a placeholder for your "
                "response. Use it to explain the steps required to resolve "
                "the failure.\n\n"

                "2. When the user **does not** provide a CI failure in "
                "the conversation:\n"
                "{{ purpose explanation }}\n\n"

                "{{ purpose explanation }} = placeholder for your response. "
                "Use it to explain to the user your purpose and to ask them"
                "to provide a CI failure or a description of one.\n\n"

                "## Rules to Follow:\n"
                "- Follow these guidelines when generating your response:\n"
                "   - Keep responses **concise**, **accurate**, and "
                "**relevant** to the user's request.\n"
                "   - Use bullet points where appropriate.\n\n"

                "## Structure of the data\n"
                "Each piece of information follows this structure:\n\n"

                "---\n"
                "kind: {{ kind value }}\n"
                "text: {{ text value }}\n"
                "score: {{ score value }}\n"
                "---\n\n"

                "{{ kind value }} = describes the Jira ticket section (e.g., "
                "comment, summary, description, ...) from which the piece of "
                "information was taken.\n"
                "{{ text value }} = describes the actual content taken from "
                "the Jira ticket\n"
                "{{ score value }} = is the similarity score calculated for "
                "the user input\n\n"

                "## Additional information\n"
                "- When NO value could be obtained for <kind value>, "
                "<text value>, or <score value>, expect the \"NO VALUE\" "
                "string.\n"
                "- When NO tickets were found related to the user input, "
                "then expect: \"NO relevant Jira tickets found.\" string.\n"
                "- When Jira tickets **ARE** discovered but the user input "
                "does not describe a CI failure, you MUST explain your "
                "purpose and ask the user to provide a CI failure "
                "description. **Nothing else!**\n"
                "- Do not include placeholders defined with {{}} in your "
                "response.\n"),
            welcome_message=os.environ.get(
                "WELCOME_MESSAGE",
                "I am your CI assistant. I will help you with your RCA."),
            prompt_header=os.environ.get(
                "CONTEXT_HEADER",
                "Here is the text with the information from the Jira "
                "tickets:\n")
        )


# Initialize the configuration
config = Config.from_env()
