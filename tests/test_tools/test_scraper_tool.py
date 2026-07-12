from unittest.mock import MagicMock, patch

import requests

from app.tools.scraper_tool import scrape_url


@patch("app.tools.scraper_tool.requests.get")
def test_scrape_url_success(mock_get):
    """Verify that scrapable HTML is fetched, parsed, stripped of boilerplate, and returned successfully."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = """
    <html>
        <head>
            <title>My Research Topic</title>
            <style>body { color: red; }</style>
            <script>console.log('hello');</script>
        </head>
        <body>
            <header>
                <nav><a href="/home">Home</a></nav>
            </header>
            <aside>Related Links</aside>
            <main>
                <h1>Main Headline</h1>
                <p>This is the important research text data.</p>
            </main>
            <footer>
                <p>Copyright 2026</p>
            </footer>
        </body>
    </html>
    """
    mock_get.return_value = mock_response

    result = scrape_url("https://example.com/research", timeout=5)

    assert result["success"] is True
    assert result["title"] == "My Research Topic"
    assert "Main Headline" in result["text"]
    assert "This is the important research text data." in result["text"]

    # Boilerplate and script/style content must not be present in extracted text
    assert "Home" not in result["text"]
    assert "Related Links" not in result["text"]
    assert "Copyright" not in result["text"]
    assert "hello" not in result["text"]
    assert "color: red" not in result["text"]
    assert result["url"] == "https://example.com/research"
    mock_get.assert_called_once_with(
        "https://example.com/research",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        },
        timeout=5,
    )


@patch("app.tools.scraper_tool.requests.get")
def test_scrape_url_non_200_returns_graceful_failure(mock_get):
    """Verify non-200 HTTP responses fail gracefully returning success=False."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response

    result = scrape_url("https://example.com/missing")

    assert result["success"] is False
    assert result["title"] is None
    assert result["text"] == ""
    assert result["url"] == "https://example.com/missing"


@patch("app.tools.scraper_tool.requests.get")
def test_scrape_url_network_error_returns_graceful_failure(mock_get):
    """Verify timeout/network exceptions fail gracefully returning success=False."""
    mock_get.side_effect = requests.Timeout("Connection timed out")

    result = scrape_url("https://example.com/timeout")

    assert result["success"] is False
    assert result["title"] is None
    assert result["text"] == ""
    assert result["url"] == "https://example.com/timeout"


@patch("app.tools.scraper_tool.requests.get")
def test_scrape_url_clean_truncation_cap(mock_get):
    """Verify text exceeding 8,000 chars is capped and cleanly truncated at word boundary."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    # Construct a string consisting of repetitive "word" tokens.
    # Each word is 4 chars + 1 space = 5 chars.
    # 2000 repetitions = 10000 characters.
    word_block = " ".join(["word" for _ in range(2000)])
    mock_response.text = f"<html><head><title>Long Content</title></head><body><p>{word_block}</p></body></html>"
    mock_get.return_value = mock_response

    result = scrape_url("https://example.com/long")

    assert result["success"] is True
    # The max text character cap is 8000. Plus 3 for '...' makes it 8003.
    assert len(result["text"]) <= 8003
    assert result["text"].endswith("...")

    # Stripping the ellipses should leave the text ending on a complete word
    content_without_ellipses = result["text"][:-3].strip()
    assert content_without_ellipses.endswith("word")
    assert not content_without_ellipses.endswith("wor")
