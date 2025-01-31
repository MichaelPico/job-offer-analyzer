from typing import Optional
from bs4 import BeautifulSoup
import requests

@staticmethod
def fetch_page(url, headers: Optional[dict] = None) -> Optional[str]:
    """Fetch the webpage content."""
    if headers is None: # Default headers to imitate a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching the page: {e}")
        return None
        
@staticmethod
def _get_text(node: BeautifulSoup, selector: str) -> str:
    """Extract text from a node using a selector."""
    element = node.select_one(selector)
    return element.text.strip() if element else ''

@staticmethod
def _get_href(node: BeautifulSoup, selector: str) -> str:
    """Extract href attribute from a node using a selector."""
    element = node.select_one(selector)
    return element.get('href', '') if element else ''