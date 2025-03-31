"""Storage implementations for conversation history and feedback."""
import chainlit as cl
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError

from config import config


class ConversationStore:
    """Abstract interface for conversation storage operations."""

    def save(self, conversation_data):
        """
        Save conversation data to storage.

        Args:
            conversation_data: Dictionary containing all conversation data
        """
        raise NotImplementedError

    def update_feedback(self, message_id, feedback_value):
        """
        Update feedback for a specific message.

        Args:
            message_id: ID of the message to update
            feedback_value: Feedback value to store

        Returns:
            bool: True if operation succeeded, False otherwise
        """
        raise NotImplementedError


class MongoDBConversationStore(ConversationStore):
    """MongoDB implementation of ConversationStore interface."""

    def __init__(self):
        self.client = None
        self.db = None
        self.collection = None
        self.available = False
        self.connect()

    def connect(self):
        """Establish connection to MongoDB."""
        try:
            self.client = MongoClient(config.db_url,
                                      serverSelectionTimeoutMS=5000)
            # Validate connection immediately
            self.client.admin.command('ping')
            self.db = self.client[config.default_db_name]
            self.collection = self.db[config.default_db_collection_name]
            self.available = True
            cl.logger.info("Successfully connected to MongoDB")
        except (ConnectionFailure, PyMongoError) as exception:
            cl.logger.error("Failed to connect to MongoDB: %s",
                            str(exception))
            self.client = None
            self.db = None
            self.collection = None
            self.available = False

    def save(self, conversation_data):
        """
        Save conversation data to database.

        Args:
            conversation_data: Dictionary containing all conversation data
        """
        if not self.available or self.collection is None:
            cl.logger.warning("MongoDB is not available - conversation data " +
                              "will not be saved")
            return

        try:
            self.collection.insert_one(conversation_data)
        except PyMongoError as e:
            cl.logger.error("Failed to save conversation data: %s", str(e))

    def update_feedback(self, message_id, feedback_value):
        """Update feedback for a message."""
        if not self.available or self.collection is None:
            cl.logger.warning("MongoDB is not available - feedback will " +
                              "not be saved")
            return False

        try:
            filter_msg = {"message_id": message_id}
            value = {"$set": {"feedback": feedback_value}}
            result = self.collection.update_one(filter_msg, value)
            return result.modified_count > 0
        except PyMongoError as e:
            cl.logger.error("Failed to save feedback: %s", str(e))
            return False


# Create singleton instance
conversation_store = MongoDBConversationStore()
