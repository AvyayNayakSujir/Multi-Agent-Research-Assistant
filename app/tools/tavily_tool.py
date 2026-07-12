import time

from tavily import TavilyClient
from tavily.errors import (
    InvalidAPIKeyError,
    MissingAPIKeyError,
    UsageLimitExceededError,
)

from app.core.config import settings
from app.core.logging import get_logger
from app.exceptions.custom_exceptions import ToolExecutionError

logger = get_logger(__name__)


def search_web(query: str, max_results: int = 5) -> list[dict]:
    """Search the web using the Tavily API.

    Retries transient failures (e.g. timeout, 5xx) up to 2 times with a short backoff.
    Fails fast immediately without retry on authorization or quota errors.

    Args:
        query: The search query string.
        max_results: The maximum number of search results to return.

    Returns:
        A list of dictionaries, each containing 'url', 'title', 'content', and 'score'.

    Raises:
        ToolExecutionError: If the search fails due to API errors, network issues, or authorization errors.
    """
    if not settings.TAVILY_API_KEY:
        raise ToolExecutionError("Tavily API Key is not configured in settings.")

    try:
        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
    except Exception as exc:
        raise ToolExecutionError(
            f"Failed to initialize Tavily client: {str(exc)}"
        ) from exc

    attempts = 2
    backoff = 1.0  # seconds

    for attempt in range(attempts):
        try:
            response = client.search(query=query, max_results=max_results)
            results = response.get("results", [])

            formatted_results = []
            for r in results:
                formatted_results.append(
                    {
                        "url": r.get("url", ""),
                        "title": r.get("title", ""),
                        "content": r.get("content", ""),
                        "score": r.get("score", 0.0),
                    }
                )

            logger.info(
                f"Tavily search for query '{query}' completed. Found {len(formatted_results)} results."
            )
            return formatted_results

        except (
            MissingAPIKeyError,
            InvalidAPIKeyError,
            UsageLimitExceededError,
        ) as auth_exc:
            logger.error(
                f"Non-retryable Tavily API error on attempt {attempt + 1}: {str(auth_exc)}"
            )
            raise ToolExecutionError(
                f"Tavily API authorization or usage limit error: {str(auth_exc)}"
            ) from auth_exc

        except Exception as exc:
            logger.warning(
                f"Tavily search attempt {attempt + 1}/{attempts} failed for query '{query}': {str(exc)}"
            )
            if attempt < attempts - 1:
                time.sleep(backoff)
            else:
                raise ToolExecutionError(
                    f"Tavily API search failed after {attempts} attempts: {str(exc)}"
                ) from exc

    raise ToolExecutionError(f"Tavily API search failed after {attempts} attempts.")
