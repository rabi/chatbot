"""Text generation with large language models."""
from typing import TypedDict

import chainlit as cl
from openai import AsyncOpenAI, OpenAIError
from openai.types.chat import ChatCompletionMessageParam

from config import config

# Initialize generative LLM client
gen_llm = AsyncOpenAI(
    base_url=config.generation_llm_api_url,
    organization='',
    api_key=config.generation_llm_api_key,
)


class ModelSettings(TypedDict):
    """
    A dictionary type that defines the settings for a model.

    Attributes:
        model: The name of the model.
        temperature: The temperature to use for generation.
        max_tokens: The maximum number of tokens in the output.
    """
    model: str
    temperature: float
    max_tokens: int


async def get_response(user_message: cl.Message, response_msg: cl.Message,
                       model_settings: ModelSettings,
                       stream_response: bool = True) -> None:
    """Process the user's message and generate a response using the LLM.

    This function constructs the prompt from the LLM by compbining the system
    prompt with the user's input. It then sends the prepared message to the LLM
    for response generation.

    Args:
        user_message: The user's input message object.
        response_msg: The message object to populate with the LLM's
            generated response or an error message if something goes wrong.
        model_settings: A dictionary containing LLM configuration.
        stream_response: Indicates whether we want to stream the response or
            get the process in a single chunk.
    """
    message_history: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": config.system_prompt},
        {"role": "user", "content": user_message.content},
    ]

    try:
        if stream_response:
            async for stream_resp in await gen_llm.chat.completions.create(
                messages=message_history, stream=stream_response,
                **model_settings
            ):
                if stream_resp.choices and len(stream_resp.choices) > 0:
                    if token := stream_resp.choices[0].delta.content or "":
                        await response_msg.stream_token(token)
        else:
            response = await gen_llm.chat.completions.create(
                messages=message_history, stream=stream_response,
                **model_settings
            )
            response_msg.content = response.choices[0].message.content or ""
    except OpenAIError as e:
        cl.logger.error("Error in process_message_and_get_response: %s",
                        str(e))
        response_msg.content = (
            "I encountered an error while generating a response."
        )
