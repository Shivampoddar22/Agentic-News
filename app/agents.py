import os
import httpx
import trafilatura
from typing import List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.models import ArticleSummary

# --- Agent Configuration ---

# Initialize the Gemini model for summarization
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)

# Initialize the Tavily Search Tool for finding articles
search_tool = TavilySearchResults(max_results=5)

# --- 1. Search Agent ---

def search_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Searches for relevant articles based on the query.
    """
    print("---🔎 SEARCHING---")
    query = state['query']
    try:
        search_results = search_tool.invoke({"query": query})
        urls = [result['url'] for result in search_results]
        print(f"Found {len(urls)} URLs.")
        return {"urls": urls}
    except Exception as e:
        print(f"Error during search: {e}")
        return {"urls": []}

# --- 2. Scrape Agent ---

def scrape_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Scrapes content from a list of URLs in parallel.
    Includes fallback mechanism.
    """
    print("---🕸️ SCRAPING---")
    urls = state.get('urls', [])
    scraped_data = []

    async def fetch_and_scrape(client, url):
        try:
            response = await client.get(url, timeout=15.0, follow_redirects=True)
            response.raise_for_status() # Raise an exception for bad status codes
            
            # Trafilatura extracts the main content
            content = trafilatura.extract(response.text, include_comments=False, include_tables=False)
            
            if content and len(content) > 300: # Basic quality check
                print(f"Successfully scraped: {url}")
                return {"url": url, "content": content}
            else:
                print(f"Failed to extract sufficient content from: {url}")
                return None
        except httpx.HTTPStatusError as e:
            print(f"HTTP error for {url}: {e.response.status_code}")
            return None # Fallback for HTTP errors
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None # Generic fallback

    async def main_scraper(urls_to_scrape):
        async with httpx.AsyncClient() as client:
            tasks = [fetch_and_scrape(client, url) for url in urls_to_scrape]
            results = await asyncio.gather(*tasks)
            return [res for res in results if res]

    import asyncio
    scraped_results = asyncio.run(main_scraper(urls))
    
    return {"scraped_articles": scraped_results}

# --- 3. Summarize Agent ---

def summarize_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Summarizes each scraped article using Gemini-1.5-flash.
    Processes summaries in parallel.
    """
    print("---✍️ SUMMARIZING---")
    articles = state.get('scraped_articles', [])
    
    # Structured output parser
    parser = JsonOutputParser(pydantic_object=ArticleSummary)

    prompt = ChatPromptTemplate.from_template(
        """
        You are an expert news analyst. Based on the following article content from the source URL provided,
        generate a concise summary and three key bullet points.

        **Instructions:**
        1. The summary should be neutral, informative, and no more than 3 sentences.
        2. The bullet points should highlight the most critical pieces of information.
        3. Respond ONLY with the JSON object as specified in the format instructions.

        **Source URL:** {source}

        **Article Content:**
        {content}

        **Format Instructions:**
        {format_instructions}
        """
    )
    
    # Create a chain for each article
    summarizer_chain = prompt | llm | parser

    # Process articles in a batch for efficiency
    summaries = summarizer_chain.batch(
        [
            {"source": article['url'], "content": article['content'], "format_instructions": parser.get_format_instructions()}
            for article in articles
        ],
        {"max_concurrency": 4} # Adjust concurrency as needed
    )

    # Convert Pydantic objects back to dicts for state compatibility
    summaries_as_dicts = [s.dict() for s in summaries]
    
    print(f"Generated {len(summaries_as_dicts)} summaries.")
    return {"summaries": summaries_as_dicts}

# --- 4. Aggregate Agent (Final Step) ---

def aggregate_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    A simple aggregator to format the final output.
    This can be expanded for more complex analysis (e.g., identifying trends).
    """
    print("---✅ AGGREGATING---")
    summaries = state.get('summaries', [])
    return {"final_digest": summaries}