
import os
import asyncio
import requests

from tavily import TavilyClient, AsyncTavilyClient
from open_deep_research.state import Section
from langsmith import traceable

tavily_client = TavilyClient()
tavily_async_client = AsyncTavilyClient()

def get_config_value(value):
    """
    Helper function to handle both string and enum cases of configuration values
    """
    return value if isinstance(value, str) else value.value

def deduplicate_and_format_sources(search_response, max_tokens_per_source, include_raw_content=True):
    """
    Takes a list of search responses and formats them into a readable string.
    Limits the raw_content to approximately max_tokens_per_source.
 
    Args:
        search_responses: List of search response dicts, each containing:
            - query: str
            - results: List of dicts with fields:
                - title: str
                - url: str
                - content: str
                - score: float
                - raw_content: str|None
        max_tokens_per_source: int
        include_raw_content: bool
            
    Returns:
        str: Formatted string with deduplicated sources
    """
     # Collect all results
    sources_list = []
    for response in search_response:
        sources_list.extend(response['results'])
    
    # Deduplicate by URL
    unique_sources = {source['url']: source for source in sources_list}

    # Format output
    formatted_text = "Sources:\n\n"
    for i, source in enumerate(unique_sources.values(), 1):
        formatted_text += f"Source {source['title']}:\n===\n"
        formatted_text += f"URL: {source['url']}\n===\n"
        formatted_text += f"Most relevant content from source: {source['content']}\n===\n"
        if include_raw_content:
            # Using rough estimate of 4 characters per token
            char_limit = max_tokens_per_source * 4
            # Handle None raw_content
            raw_content = source.get('raw_content', '')
            if raw_content is None:
                raw_content = ''
                print(f"Warning: No raw_content found for source {source['url']}")
            if len(raw_content) > char_limit:
                raw_content = raw_content[:char_limit] + "... [truncated]"
            formatted_text += f"Full source content limited to {max_tokens_per_source} tokens: {raw_content}\n\n"
                
    return formatted_text.strip()

def format_sections(sections: list[Section]) -> str:
    """ Format a list of sections into a string """
    formatted_str = ""
    for idx, section in enumerate(sections, 1):
        formatted_str += f"""
{'='*60}
Section {idx}: {section.name}
{'='*60}
Description:
{section.description}
Requires Research: 
{section.research}

Content:
{section.content if section.content else '[Not yet written]'}

"""
    return formatted_str

@traceable
async def tavily_search_async(search_queries):
    """
    Performs concurrent web searches using the Tavily API.

    Args:
        search_queries (List[SearchQuery]): List of search queries to process

    Returns:
            List[dict]: List of search responses from Tavily API, one per query. Each response has format:
                {
                    'query': str, # The original search query
                    'follow_up_questions': None,      
                    'answer': None,
                    'images': list,
                    'results': [                     # List of search results
                        {
                            'title': str,            # Title of the webpage
                            'url': str,              # URL of the result
                            'content': str,          # Summary/snippet of content
                            'score': float,          # Relevance score
                            'raw_content': str|None  # Full page content if available
                        },
                        ...
                    ]
                }
    """
    
    search_tasks = []
    for query in search_queries:
            search_tasks.append(
                tavily_async_client.search(
                    query,
                    max_results=5,
                    include_raw_content=True,
                    topic="general"
                )
            )

    # Execute all searches concurrently
    search_docs = await asyncio.gather(*search_tasks)

    return search_docs

@traceable
def perplexity_search(search_queries):
    """Search the web using the Perplexity API.
    
    Args:
        search_queries (List[SearchQuery]): List of search queries to process
  
    Returns:
        List[dict]: List of search responses from Perplexity API, one per query. Each response has format:
            {
                'query': str,                    # The original search query
                'follow_up_questions': None,      
                'answer': None,
                'images': list,
                'results': [                     # List of search results
                    {
                        'title': str,            # Title of the search result
                        'url': str,              # URL of the result
                        'content': str,          # Summary/snippet of content
                        'score': float,          # Relevance score
                        'raw_content': str|None  # Full content or None for secondary citations
                    },
                    ...
                ]
            }
    """

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {os.getenv('PERPLEXITY_API_KEY')}"
    }
    
    search_docs = []
    for query in search_queries:

        payload = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "system",
                    "content": "Search the web and provide factual information with sources."
                },
                {
                    "role": "user",
                    "content": query
                }
            ]
        }
        
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload
        )
        response.raise_for_status()  # Raise exception for bad status codes
        
        # Parse the response
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        citations = data.get("citations", ["https://perplexity.ai"])
        
        # Create results list for this query
        results = []
        
        # First citation gets the full content
        results.append({
            "title": f"Perplexity Search, Source 1",
            "url": citations[0],
            "content": content,
            "raw_content": content,
            "score": 1.0  # Adding score to match Tavily format
        })
        
        # Add additional citations without duplicating content
        for i, citation in enumerate(citations[1:], start=2):
            results.append({
                "title": f"Perplexity Search, Source {i}",
                "url": citation,
                "content": "See primary source for full content",
                "raw_content": None,
                "score": 0.5  # Lower score for secondary sources
            })
        
        # Format response to match Tavily structure
        search_docs.append({
            "query": query,
            "follow_up_questions": None,
            "answer": None,
            "images": [],
            "results": results
        })
    
    return search_docs

@traceable
def bing_search(search_queries: list[str]) -> list[dict]:
    """
    Searches Bing for each query in search_queries. Returns a list of search response dicts
    in a structure similar to tavily_search_async / perplexity_search:
    
    [
        {
            "query": str,  # The original search query
            "follow_up_questions": None,
            "answer": None,
            "images": [],
            "results": [
                {
                    "title": str,
                    "url": str,
                    "content": str,       # snippet
                    "score": float,       # a made-up relevance score
                    "raw_content": str|None
                },
                ...
            ]
        },
        ...
    ]
    """
    
    subscription_key = os.getenv("BING_API_KEY")
    if not subscription_key:
        raise ValueError("No BING_API_KEY found in environment variables.")
    
    search_url = "https://api.bing.microsoft.com/v7.0/search"
    
    headers = {
        "Ocp-Apim-Subscription-Key": subscription_key
    }
    
    results_list = []
    
    for query in search_queries:
        params = {
            "q": query,
            "textFormat": "HTML",
            "mkt": "en-US",          # or "zh-CN" if you prefer Chinese
            "freshness": "Day",
            "responseFilter": "webPages",
            "count": 10               # number of results you want
        }
        
        try:
            response = requests.get(search_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            # 解析返回数据
            # Bing 会把搜索结果放在 data["webPages"]["value"] 里
            web_pages = data.get("webPages", {}).get("value", [])
            
            # 构造与 tavily/perplexity 类似的结构
            bing_results = []
            for i, page in enumerate(web_pages):
                title = page.get("name", "No Title")
                url = page.get("url", "No URL")
                snippet = page.get("snippet", "No snippet")
                
                # 这里 raw_content 暂时也用 snippet
                # 如果想获取更多内容，需要调用 Bing 的 additional endpoints (不一定可行)
                raw_content = snippet
                
                # 给一个简单的“score”，可随意
                score = 1.0 - i * 0.1
                
                bing_results.append({
                    "title": title,
                    "url": url,
                    "content": snippet,
                    "score": score,
                    "raw_content": raw_content
                })
            
            # 组装成与 tavily/perplexity 一致的格式
            results_list.append({
                "query": query,
                "follow_up_questions": None,
                "answer": None,
                "images": [],
                "results": bing_results
            })
            
        except requests.RequestException as e:
            # 如果发生网络错误或 HTTP 错误，也返回一个空结果结构
            results_list.append({
                "query": query,
                "follow_up_questions": None,
                "answer": None,
                "images": [],
                "results": [
                    {
                        "title": "Bing Search Error",
                        "url": "",
                        "content": f"An error occurred: {e}",
                        "score": 0.0,
                        "raw_content": None
                    }
                ]
            })
    
    return results_list
