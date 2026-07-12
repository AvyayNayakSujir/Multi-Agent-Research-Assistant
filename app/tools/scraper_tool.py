import requests
from bs4 import BeautifulSoup

from app.core.logging import get_logger

logger = get_logger(__name__)


def scrape_url(url: str, timeout: int = 10) -> dict:
    """Fetch content from the given URL and extract cleaned, visible text.

    Strips script, style, noscript, iframe, svg, head, and boilerplate tags
    like nav, footer, header, aside. Caps the visible text length to 8000 characters,
    truncating cleanly at a word boundary to avoid partial words.

    Args:
        url: The HTTP/HTTPS web URL to scrape.
        timeout: Request timeout duration in seconds.

    Returns:
        A dictionary containing:
        - 'url': The scraped URL.
        - 'title': The page title (or None if unavailable).
        - 'text': Extracted clean text content.
        - 'success': A boolean indicating if the operation succeeded.
    """
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=timeout)

        if response.status_code != 200:
            logger.warning(
                f"Failed to scrape '{url}': HTTP status code {response.status_code}"
            )
            return {"url": url, "title": None, "text": "", "success": False}

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract title before decomposing structural elements (like head)
        title = soup.title.string.strip() if soup.title and soup.title.string else None

        # Strip scripting, formatting, and structural metadata tags
        for element in soup(["script", "style", "noscript", "iframe", "svg", "head"]):
            element.decompose()

        # Strip standard navigation and structural boilerplate tags
        for element in soup(["nav", "footer", "header", "aside"]):
            element.decompose()

        # Extract visible text blocks
        text = soup.get_text(separator="\n")

        # Clean whitespace and filter empty lines
        lines = [line.strip() for line in text.splitlines()]
        chunks = [line for line in lines if line]
        cleaned_text = "\n".join(chunks)

        # Cap text length to ~8,000 characters
        max_length = 8000
        if len(cleaned_text) > max_length:
            truncated = cleaned_text[:max_length]
            # Truncate cleanly at a word boundary
            last_space = truncated.rfind(" ")
            if last_space != -1 and (max_length - last_space) < 50:
                truncated = truncated[:last_space]
            cleaned_text = truncated.strip() + "..."

        return {"url": url, "title": title, "text": cleaned_text, "success": True}

    except requests.RequestException as exc:
        logger.warning(
            f"Network error or timeout occurred while scraping '{url}': {str(exc)}"
        )
        return {"url": url, "title": None, "text": "", "success": False}
    except Exception as exc:
        logger.error(f"Unexpected programming error while scraping '{url}': {str(exc)}")
        raise
