"""Configuration settings for the RCA chatbot application."""
import os


# pylint: disable=too-many-instance-attributes,too-few-public-methods
class Config:
    """Configuration class for the RCA chatbot."""

    def __init__(self):
        self.load_env_variables()

    def load_env_variables(self):
        """Load environment variables."""
        self.generation_llm_api_url = os.environ.get("GENERATION_LLM_API_URL")
        self.generation_llm_api_key = os.environ.get("GENERATION_LLM_API_KEY")
        self.embeddings_llm_api_url = os.environ.get(
            "EMBEDDINGS_LLM_API_URL")
        self.embeddings_llm_api_key = os.environ.get(
            "EMBEDDINGS_LLM_API_KEY")
        self.generative_model = os.environ.get(
            "DEFAULT_MODEL_NAME", 'Mistral-7B-Instruct-v0.2')
        self.embeddings_model = os.environ.get(
            "DEFAULT_EMBEDDINGS_MODEL", 'bge-large-en-v1.5')
        self.default_temperature = float(
            os.environ.get("DEFAULT_MODEL_TEMPERATURE", 0.7))
        self.default_max_tokens = int(
            os.environ.get("DEFAULT_MODEL_MAX_TOKENS", 1024))
        self.default_top_p = float(
            os.environ.get("DEFAULT_MODEL_TOP_P", 1))
        self.default_n = int(os.environ.get("DEFAULT_MODEL_N", 1))
        self.auth_database_url = os.environ.get("AUTH_DATABASE_URL")
        self.vectordb_url = os.environ.get("VECTORDB_URL")
        self.vectordb_api_key = os.environ.get("VECTORDB_API_KEY")
        self.vectordb_port = int(os.environ.get("VECTORDB_PORT", 6333))
        self.vectordb_collection_name = os.environ.get(
            "VECTORDB_COLLECTION_NAME", 'rca-knowledge-base')
        self.search_instruction = os.environ.get(
            "SEARCH_INSTRUCTION",
            "Represent this sentence for searching relevant passages: "
        )
        self.search_similarity_threshold = float(
            os.environ.get("SEARCH_SIMILARITY_THRESHOLD", 0.8))
        self.search_top_n = int(
            os.environ.get("SEARCH_TOP_N", 5))
        self.system_prompt = os.environ.get(
            "SYSTEM_PROMPT",
            "You are a CI assistant. You help with CI failures " +
            "and help define RCA."
        )
        self.welcome_message = os.environ.get(
            "WELCOME_MESSAGE",
            "I am your CI assistant. I will help you with your RCA."
        )


# Initialize the configuration
config = Config()
