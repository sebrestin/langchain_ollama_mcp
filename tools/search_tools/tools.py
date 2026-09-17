import base64
import json
import random
import re
import time
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Statuses worth another attempt: throttling and transient server-side faults.
RETRIABLE_STATUS = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3


class BackendError(Exception):
    """A search engine could not be reached, or refused to serve results."""


def _describe(exc: BaseException | None) -> str:
    """Render an exception for a tool result.

    urllib3 can surface a dropped connection as ProtocolError(None), whose
    str() is the useless literal "None", so fall back to the type name.
    """
    detail = str(exc) if exc is not None else ""
    if not detail or detail == "None":
        return type(exc).__name__ if exc is not None else "unknown error"
    return detail


def _request(method: str, url: str, **kwargs) -> requests.Response:
    """Send a request, retrying dropped connections and throttling responses.

    Search engines rate-limit by IP, and they do it by resetting the TCP
    connection as often as by answering with a status code, so a bare
    ConnectionResetError has to be treated as a retriable throttle.
    """
    kwargs.setdefault("headers", HEADERS)
    kwargs.setdefault("timeout", 15)

    last_error = None
    for attempt in range(MAX_ATTEMPTS):
        if attempt:
            time.sleep(2 ** attempt + random.uniform(0, 0.5))
        try:
            response = requests.request(method, url, **kwargs)
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_error = exc
            continue

        if response.status_code in RETRIABLE_STATUS:
            last_error = requests.HTTPError(
                f"{response.status_code} {response.reason} for url: {url}"
            )
            continue

        response.raise_for_status()
        return response

    raise BackendError(f"{_describe(last_error)} (after {MAX_ATTEMPTS} attempts)")


def _is_challenge(response: requests.Response) -> bool:
    """Tell a challenge or captcha page apart from a page with no matches.

    Both parse to zero results, but they mean opposite things: one is the
    engine refusing us, the other is an answer. DuckDuckGo serves its
    challenge with a 200-range status, so the body has to be inspected.
    """
    body = response.text.lower()
    return (
        response.status_code == 202
        or "anomaly" in body
        or "<title>captcha" in body
        or "unusual traffic" in body
    )


def _search_duckduckgo(query: str, num_results: int) -> list[dict]:
    """Search DuckDuckGo's server-rendered HTML endpoint."""
    response = _request(
        "GET",
        "https://html.duckduckgo.com/html/",
        params={"q": query},
        headers={**HEADERS, "Referer": "https://duckduckgo.com/"},
    )

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    for result in soup.find_all("div", class_="result"):
        title_elem = result.find("a", class_="result__a")
        if not title_elem:
            continue

        title = title_elem.get_text(strip=True)

        # DuckDuckGo wraps URLs in a redirect - extract the actual URL
        href = title_elem.get("href", "")
        if "uddg=" in href:
            match = re.search(r"uddg=([^&]+)", href)
            if match:
                href = unquote(match.group(1))

        if not href or not title:
            continue

        snippet_elem = result.find("a", class_="result__snippet")
        results.append({
            "title": title,
            "url": href,
            "description": snippet_elem.get_text(strip=True) if snippet_elem else "",
        })

        if len(results) >= num_results:
            break

    if not results and _is_challenge(response):
        raise BackendError("served a challenge page instead of results (rate limited)")

    return results


def _unwrap_bing_url(href: str) -> str:
    """Recover the destination URL from a bing.com/ck/a tracking redirect."""
    if "bing.com/ck/a" not in href:
        return href

    wrapped = parse_qs(urlparse(href).query).get("u", [""])[0]
    if not wrapped.startswith("a1"):
        return href

    payload = wrapped[2:]
    payload += "=" * (-len(payload) % 4)
    try:
        return base64.urlsafe_b64decode(payload).decode("utf-8", "replace")
    except ValueError:
        return href


def _search_bing(query: str, num_results: int) -> list[dict]:
    """Search Bing's HTML results page, used when DuckDuckGo blocks us."""
    response = _request(
        "GET",
        "https://www.bing.com/search",
        params={"q": query, "setlang": "en"},
    )

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    for item in soup.select("li.b_algo"):
        heading = item.find("h2") or item
        link = heading.find("a")
        if not link:
            continue

        title = link.get_text(strip=True)
        url = _unwrap_bing_url(link.get("href", ""))
        if not title or not url.startswith("http"):
            continue

        snippet_elem = item.find("p")
        results.append({
            "title": title,
            "url": url,
            "description": snippet_elem.get_text(strip=True) if snippet_elem else "",
        })

        if len(results) >= num_results:
            break

    if not results and _is_challenge(response):
        raise BackendError("served a challenge page instead of results (rate limited)")

    return results


BACKENDS = (
    ("DuckDuckGo", _search_duckduckgo),
    ("Bing", _search_bing),
)


def web_search(query: str, num_results: int = 10) -> list[dict]:
    """Search the web for a query and return the results.

    Queries DuckDuckGo's HTML endpoint, falling back to Bing when DuckDuckGo
    is unreachable or rate-limits the caller. Both return server-rendered
    results that can be parsed without JavaScript.

    :param query: The search query string
    :type query: str
    :param num_results: Number of results to return (default: 10)
    :type num_results: int

    :return: List of search results with title, url, and description, or a
             single entry with an 'error' key if every engine failed
    """
    failures = []

    for name, backend in BACKENDS:
        try:
            results = backend(query, num_results)
        except (BackendError, requests.RequestException) as exc:
            failures.append(f"{name} failed: {_describe(exc)}")
            continue
        except Exception as exc:
            failures.append(f"{name} failed: {_describe(exc)}")
            continue

        if results:
            return results

        failures.append(f"{name} returned no matches")

    # Every engine answered, none had anything: that is an answer, not a fault.
    if all(failure.endswith("no matches") for failure in failures):
        return []

    return [{"error": "Search failed. " + "; ".join(failures)}]


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
    try:
        response = _request("GET", url)

        content_type = response.headers.get("Content-Type", "").lower()

        # Without a charset in the header, requests falls back to ISO-8859-1 as
        # the HTTP spec demands, which mangles the many pages that are really
        # UTF-8. Sniff the body instead.
        if "charset=" not in content_type:
            response.encoding = response.apparent_encoding or response.encoding

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

    except (BackendError, requests.RequestException) as e:
        return {"error": f"Request failed: {_describe(e)}", "url": url}
    except Exception as e:
        return {"error": _describe(e), "url": url}


if __name__ == "__main__":
    results = web_search("what is the dollar/euro ratio", 5)
    print(f"Found {len(results)} results:\n")
    for i, r in enumerate(results, 1):
        if r.get("error"):
            print(f"{i}. ERROR: {r['error']}")
            continue
        print(f"{i}. {r.get('title')}")
        print(f"   URL: {r.get('url')}")
        if r.get('description'):
            print(f"   {r.get('description')[:100]}...")
        print()

    if results and not results[0].get("error"):
        print("\nFetching content from first result...")
        print(results[0]['url'])
        content = fetch_url(results[0]['url'])
        if content.get('error'):
            print(f"Error: {content['error']}")
        else:
            print(f"\nTitle: {content.get('title', 'N/A')}")
            print(f"Content preview:\n{content.get('content', '')[:500]}")
