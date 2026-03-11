import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode, unquote
import re


def web_search(query: str, num_results: int = 10) -> list[dict]:
    """Search the web for a query and return the results.
    
    Uses DuckDuckGo HTML endpoint which returns server-rendered results
    that can be reliably parsed without JavaScript.
    
    :param query: The search query string
    :type query: str
    :param num_results: Number of results to return (default: 10)
    :type num_results: int
    
    :return: List of search results with title, url, and description
    """
    results = []
    
    session = requests.Session()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://duckduckgo.com/",
    }
    
    try:
        # DuckDuckGo HTML search endpoint
        url = f"https://html.duckduckgo.com/html/?q={urlencode({'q': query})[2:]}"
        
        response = session.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find all result containers
        for result in soup.find_all("div", class_="result"):
            # Extract title and URL
            title_elem = result.find("a", class_="result__a")
            if not title_elem:
                continue
            
            title = title_elem.get_text(strip=True)
            
            # DuckDuckGo wraps URLs in a redirect - extract the actual URL
            href = title_elem.get("href", "")
            if "uddg=" in href:
                # Extract the actual URL from the redirect
                match = re.search(r'uddg=([^&]+)', href)
                if match:
                    href = unquote(match.group(1))
            
            if not href or not title:
                continue
            
            # Extract description/snippet
            snippet_elem = result.find("a", class_="result__snippet")
            description = snippet_elem.get_text(strip=True) if snippet_elem else ""
            
            results.append({
                "title": title,
                "url": href,
                "description": description
            })
            
            if len(results) >= num_results:
                break
                    
    except requests.RequestException as e:
        return [{"error": f"Request failed: {str(e)}"}]
    except Exception as e:
        return [{"error": str(e)}]
    
    return results


def fetch_url(url: str, max_length: int = 10000) -> dict:
    """Fetch content from a URL and return the text content.
    
    Retrieves the webpage at the given URL and extracts readable text content.
    For HTML pages, it removes scripts, styles, and other non-content elements
    to provide clean, readable text.
    
    :param url: The URL to fetch content from
    :type url: str
    :param max_length: Maximum length of content to return (default: 10000 characters)
    :type max_length: int
    
    :return: Dictionary with 'url', 'title', 'content', and 'content_type' keys,
             or an 'error' key if the request fails
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        content_type = response.headers.get("Content-Type", "").lower()
        
        # Handle HTML content
        if "text/html" in content_type:
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract title
            title = ""
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)
            
            # Remove script and style elements
            for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                element.decompose()
            
            # Try to find main content area
            main_content = soup.find("main") or soup.find("article") or soup.find("body")
            
            if main_content:
                # Get text with proper spacing
                text = main_content.get_text(separator="\n", strip=True)
            else:
                text = soup.get_text(separator="\n", strip=True)
            
            # Clean up excessive whitespace
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = "\n".join(lines)
            
            # Truncate if needed
            if len(text) > max_length:
                text = text[:max_length] + "\n\n[Content truncated...]"
            
            return {
                "url": url,
                "title": title,
                "content": text,
                "content_type": "html"
            }
        
        # Handle plain text content
        elif "text/" in content_type:
            text = response.text
            if len(text) > max_length:
                text = text[:max_length] + "\n\n[Content truncated...]"
            
            return {
                "url": url,
                "title": "",
                "content": text,
                "content_type": "text"
            }
        
        # Handle JSON content
        elif "application/json" in content_type:
            import json
            text = json.dumps(response.json(), indent=2)
            if len(text) > max_length:
                text = text[:max_length] + "\n\n[Content truncated...]"
            
            return {
                "url": url,
                "title": "",
                "content": text,
                "content_type": "json"
            }
        
        # Other content types
        else:
            return {
                "url": url,
                "title": "",
                "content": f"[Binary or unsupported content type: {content_type}]",
                "content_type": content_type
            }
            
    except requests.RequestException as e:
        return {"error": f"Request failed: {str(e)}", "url": url}
    except Exception as e:
        return {"error": str(e), "url": url}


if __name__ == "__main__":
    results = web_search("what is the dollar/euro ration")
    print(f"Found {len(results)} results:\n")
    for i, r in enumerate(results, 1):
        print(f"{i}. {r.get('title')}")
        print(f"   URL: {r.get('url')}")
        if r.get('description'):
            print(f"   {r.get('description')[:100]}...")
        print()

    print("\nFetching content from first result...")
    print(results[0]['url'])
    content = fetch_url(results[0]['url'])
    if content.get('error'):
        print(f"Error: {content['error']}")
    else:
        print(f"\nTitle: {content.get('title', 'N/A')}")
        print(f"Content preview:\n{content.get('content', '')[:500]}")
    