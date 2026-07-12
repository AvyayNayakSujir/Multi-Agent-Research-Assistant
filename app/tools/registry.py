from app.tools.scraper_tool import scrape_url
from app.tools.tavily_tool import search_web

# A minimal single point of import mapping tool names to execution functions
TOOLS = {
    "web_search": search_web,
    "scrape_url": scrape_url,
}
