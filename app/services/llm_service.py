from langchain_groq import ChatGroq

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_llm(temperature: float = 0.0) -> ChatGroq:
    """Builds and returns a LangChain ChatGroq client.

    Logs the model name and temperature at DEBUG level.
    """
    logger.debug(
        f"Instantiating ChatGroq client with model='{settings.GROQ_MODEL}' and temperature={temperature}"
    )
    return ChatGroq(
        groq_api_key=settings.GROQ_API_KEY,
        model_name=settings.GROQ_MODEL,
        temperature=temperature,
    )
