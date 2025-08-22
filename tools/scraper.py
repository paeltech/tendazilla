import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
import random
from urllib.parse import urljoin, urlparse
import json
import feedparser
from config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter for web scraping"""
    
    def __init__(self, requests_per_minute: int, delay_seconds: float):
        self.requests_per_minute = requests_per_minute
        self.delay_seconds = delay_seconds
        self.last_request_time = 0
    
    def wait_if_needed(self):
        """Wait if necessary to respect rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 60.0 / self.requests_per_minute
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last + random.uniform(0, self.delay_seconds)
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()

class TenderScraper:
    """Advanced tender scraper with multiple strategies and site-specific handling"""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(
            config.RATE_LIMIT_REQUESTS_PER_MINUTE,
            config.RATE_LIMIT_DELAY_SECONDS
        )
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def scrape_web(self, url: str, site_config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Scrapes tender listings from a specific portal URL using combined approach.
        Returns a list of structured tender opportunities.
        
        Args:
            url (str): The URL of the tender site to scrape
            site_config (Dict): Site-specific configuration from tender_sites.json
            
        Returns:
            List[Dict[str, Any]]: List of tender objects with structured data
        """
        try:
            logger.info(f"Starting scraping process for: {url}")
            
            # Apply rate limiting
            self.rate_limiter.wait_if_needed()
            
            # If site has API endpoint, try that first
            if site_config and site_config.get('api_url'):
                logger.info(f"Trying API endpoint: {site_config['api_url']}")
                api_tenders = self._scrape_with_api_endpoint(site_config['api_url'], url)
                if api_tenders:
                    logger.info(f"Successfully scraped {len(api_tenders)} tenders using API")
                    return self._post_process_tenders(api_tenders, url)
            
            # If site has RSS feed, try that next
            if site_config and site_config.get('rss_url'):
                logger.info(f"Trying RSS feed: {site_config['rss_url']}")
                rss_tenders = self._scrape_with_rss(site_config['rss_url'], url)
                if rss_tenders:
                    logger.info(f"Successfully scraped {len(rss_tenders)} tenders using RSS")
                    return self._post_process_tenders(rss_tenders, url)
            
            # Determine scraper strategy based on site configuration
            if site_config and site_config.get('scraper_type'):
                scraper_type = site_config['scraper_type']
                logger.info(f"Using specified scraper type: {scraper_type}")
                
                if scraper_type == 'playwright':
                    tenders = self._scrape_with_playwright(url)
                elif scraper_type == 'selenium':
                    tenders = self._scrape_with_selenium_fallback(url)
                elif scraper_type == 'requests':
                    tenders = self._scrape_with_requests(url)
                else:
                    # Fallback to default strategy
                    tenders = self._scrape_with_default_strategy(url)
                
                if tenders:
                    logger.info(f"Successfully scraped {len(tenders)} tenders using {scraper_type}")
                    return self._post_process_tenders(tenders, url)
            
            # If no specific strategy or it failed, try multiple scraping strategies
            strategies = [
                self._scrape_with_playwright,
                self._scrape_with_selenium_fallback,
                self._scrape_with_requests,
                self._scrape_with_api_endpoints
            ]
            
            for strategy in strategies:
                try:
                    logger.info(f"Trying strategy: {strategy.__name__}")
                    tenders = strategy(url)
                    if tenders:
                        logger.info(f"Successfully scraped {len(tenders)} tenders using {strategy.__name__}")
                        return self._post_process_tenders(tenders, url)
                    
                except Exception as e:
                    logger.warning(f"Strategy {strategy.__name__} failed: {str(e)}")
                    continue
            
            # If all strategies fail, return sample data in test mode
            if config.USE_SAMPLE_DATA:
                logger.info("All scraping strategies failed, returning sample data")
                return self._get_sample_tenders(url)
            
            logger.warning(f"Failed to scrape any tenders from {url}")
            return []
            
        except Exception as e:
            logger.error(f"Error in main scraping process for {url}: {str(e)}")
            return []
    
    def _scrape_with_playwright(self, url: str) -> List[Dict[str, Any]]:
        """Use Playwright for JavaScript-heavy sites"""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
                page = browser.new_page()
                
                # Set viewport and user agent
                page.set_viewport_size({"width": 1920, "height": 1080})
                page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                # Navigate to page with retry logic
                for attempt in range(config.SCRAPING_MAX_RETRIES):
                    try:
                        page.goto(url, wait_until='networkidle', timeout=config.SCRAPING_TIMEOUT * 1000)
                        break
                    except Exception as e:
                        if attempt == config.SCRAPING_MAX_RETRIES - 1:
                            raise e
                        logger.warning(f"Navigation attempt {attempt + 1} failed, retrying...")
                        time.sleep(2)
                
                # Wait for content to load
                time.sleep(3)
                
                # Try multiple selectors for tender elements - IMPROVED: better targeting
                tender_selectors = [
                    'table',  # Look for tables first (most reliable)
                    'tr',  # Look for table rows
                    '[class*="tender"]',
                    '[class*="opportunity"]',
                    '[class*="rfp"]',
                    '[class*="bid"]',
                    '[class*="procurement"]',
                    '.listing-item',
                    '.card',
                    '.tender-item',
                    '.opportunity-item',
                    '[class*="content"]',  # Look for content areas
                    '[class*="main"]'  # Look for main content areas
                ]
                
                tenders = []
                for selector in tender_selectors:
                    try:
                        elements = page.query_selector_all(selector)
                        if elements:
                            logger.info(f"Found {len(elements)} elements with selector: {selector}")
                            
                            # Special handling for tables
                            if selector == 'tr' or selector == 'table':
                                table_tenders = self._extract_tenders_from_table(page, selector)
                                if table_tenders:
                                    tenders.extend(table_tenders)
                                    logger.info(f"Extracted {len(table_tenders)} tenders from table structure")
                                    break
                            else:
                                # For non-table elements, be more selective
                                if selector in ['[class*="tender"]', '[class*="opportunity"]', '[class*="rfp"]']:
                                    # These are more likely to contain actual tender data
                                    for element in elements[:10]:  # Limit to first 10
                                        tender = self._extract_tender_data_dynamic(element, page)
                                        if tender and tender.get('title') and len(tender['title']) > 20:
                                            tenders.append(tender)
                                    
                                    if tenders:
                                        logger.info(f"Found {len(tenders)} tenders with {selector}")
                                        break
                                else:
                                    # For general content selectors, be more conservative
                                    continue
                            
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {str(e)}")
                        continue
                
                browser.close()
                return tenders
                
        except Exception as e:
            logger.error(f"Playwright scraping failed for {url}: {str(e)}")
            return []
    
    def _scrape_with_selenium_fallback(self, url: str) -> List[Dict[str, Any]]:
        """Fallback to Selenium if available"""
        try:
            # Try to import selenium
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(url)
            
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Look for tender elements
            tender_elements = driver.find_elements(By.CSS_SELECTOR, '[class*="tender"], [class*="opportunity"], [class*="rfp"], tr, .card')
            
            tenders = []
            for element in tender_elements[:20]:
                try:
                    tender = self._extract_tender_data_selenium(element, driver)
                    if tender and tender.get('title'):
                        tenders.append(tender)
                except Exception as e:
                    logger.debug(f"Error extracting from Selenium element: {str(e)}")
                    continue
            
            driver.quit()
            return tenders
            
        except ImportError:
            logger.debug("Selenium not available, skipping Selenium strategy")
            return []
        except Exception as e:
            logger.error(f"Selenium scraping failed for {url}: {str(e)}")
            return []
    
    def _scrape_with_requests(self, url: str) -> List[Dict[str, Any]]:
        """Use requests and BeautifulSoup for static content"""
        try:
            response = self.session.get(url, timeout=config.SCRAPING_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for tender patterns - IMPROVED: better table handling
            tenders = []
            
            # Strategy 1: Look for tables with tender data
            tables = soup.find_all('table')
            for table in tables:
                table_tenders = self._extract_tenders_from_static_table(table, url)
                if table_tenders:
                    tenders.extend(table_tenders)
                    logger.info(f"Found {len(table_tenders)} tenders in table")
            
            # Strategy 2: Look for tender elements with specific classes
            if not tenders:
                tender_elements = soup.find_all(['div', 'tr', 'li'], 
                    class_=re.compile(r'tender|opportunity|rfp|bid|procurement', re.I))
                
                for element in tender_elements[:20]:
                    tender = self._extract_tender_data_static(element, soup)
                    if tender and tender.get('title'):
                        tenders.append(tender)
            
            # Strategy 3: Fallback - look for elements containing tender-related text
            if not tenders:
                tender_elements = soup.find_all(text=re.compile(
                    r'tender|opportunity|rfp|bid|procurement', re.I))
                tender_elements = [elem.parent for elem in tender_elements if elem.parent]
                
                for element in tender_elements[:20]:
                    tender = self._extract_tender_data_static(element, soup)
                    if tender and tender.get('title'):
                        tenders.append(tender)
            
            # Strategy 4: Look for any structured data (JSON-LD, microdata)
            if not tenders:
                json_ld_scripts = soup.find_all('script', type='application/ld+json')
                for script in json_ld_scripts:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, dict) and data.get('@type') in ['Tender', 'RequestForProposal', 'Bid']:
                            tender = self._parse_structured_data(data, url)
                            if tender:
                                tenders.append(tender)
                    except:
                        continue
            
            return tenders
            
        except Exception as e:
            logger.error(f"Requests scraping failed for {url}: {str(e)}")
            return []
    
    def _scrape_with_api_endpoints(self, url: str) -> List[Dict[str, Any]]:
        """Try to find and use API endpoints for data"""
        try:
            # Special handling for known sites
            if 'nest.go.tz' in url:
                return self._scrape_nest_tanzania(url)
            elif 'finca.co.tz' in url:
                return self._scrape_finca_tanzania(url)
            
            # Try common API patterns
            api_patterns = [
                url.replace('/website/Tenders/index', '/api/tenders'),
                url.replace('/Public/Notice', '/api/notices'),
                url.replace('/tenders/', '/api/tenders/'),
                url + '/api/tenders',
                url + '/api/opportunities',
                url.replace('/tenders/published-tenders', '/api/tenders'),
                url.replace('/tenders/published-tenders', '/api/opportunities'),
                url.replace('/tenders/published-tenders', '/api/procurement')
            ]
            
            for api_url in api_patterns:
                try:
                    response = self.session.get(api_url, timeout=10)
                    if response.status_code == 200:
                        # Check if response is JSON
                        content_type = response.headers.get('content-type', '')
                        if 'application/json' in content_type or response.text.strip().startswith('{'):
                            try:
                                data = response.json()
                                if isinstance(data, list) and len(data) > 0:
                                    return self._parse_api_data(data, url)
                                elif isinstance(data, dict) and 'data' in data:
                                    return self._parse_api_data(data['data'], url)
                                elif isinstance(data, dict) and 'results' in data:
                                    return self._parse_api_data(data['results'], url)
                            except json.JSONDecodeError:
                                logger.debug(f"API endpoint {api_url} returned non-JSON content")
                                continue
                        else:
                            # Try to parse as HTML and look for embedded data
                            soup = BeautifulSoup(response.content, 'html.parser')
                            embedded_data = self._extract_embedded_data(soup, url)
                            if embedded_data:
                                return embedded_data
                except Exception as e:
                    logger.debug(f"API endpoint {api_url} failed: {str(e)}")
                    continue
            
            return []
            
        except Exception as e:
            logger.error(f"API scraping failed for {url}: {str(e)}")
            return []
    
    def _scrape_with_api_endpoint(self, api_url: str, source_url: str) -> List[Dict[str, Any]]:
        """Scrape tenders from a dedicated API endpoint"""
        try:
            logger.info(f"Scraping from API endpoint: {api_url}")
            
            # Try different HTTP methods and headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            # Try GET request first
            response = self.session.get(api_url, headers=headers, timeout=30)
            if response.status_code == 200:
                try:
                    data = response.json()
                    return self._parse_api_data(data, source_url)
                except json.JSONDecodeError:
                    logger.debug(f"API response is not JSON: {response.text[:200]}")
            
            # Try POST request if GET fails
            response = self.session.post(api_url, headers=headers, timeout=30)
            if response.status_code == 200:
                try:
                    data = response.json()
                    return self._parse_api_data(data, source_url)
                except json.JSONDecodeError:
                    logger.debug(f"POST response is not JSON: {response.text[:200]}")
            
            return []
            
        except Exception as e:
            logger.error(f"API endpoint scraping failed: {str(e)}")
            return []
    
    def _scrape_with_rss(self, rss_url: str, source_url: str) -> List[Dict[str, Any]]:
        """Scrape tenders from RSS feeds"""
        try:
            logger.info(f"Scraping from RSS feed: {rss_url}")
            
            # Parse RSS feed
            feed = feedparser.parse(rss_url)
            
            if not feed.entries:
                logger.warning("No entries found in RSS feed")
                return []
            
            tenders = []
            for entry in feed.entries[:50]:  # Limit to first 50 entries
                try:
                    tender = {
                        'title': entry.get('title', '')[:200],
                        'description': entry.get('summary', '')[:500],
                        'deadline': self._extract_deadline_from_rss(entry),
                        'budget': '',
                        'requirements': [],
                        'industry': 'Information Technology',
                        'location': self._extract_location_from_rss(entry),
                        'source_url': source_url,
                        'rss_link': entry.get('link', ''),
                        'published_date': entry.get('published', ''),
                        'scraped_at': datetime.now().isoformat()
                    }
                    
                    if tender['title']:
                        tenders.append(tender)
                        
                except Exception as e:
                    logger.debug(f"Error parsing RSS entry: {str(e)}")
                    continue
            
            logger.info(f"Successfully parsed {len(tenders)} tenders from RSS feed")
            return tenders
            
        except Exception as e:
            logger.error(f"RSS scraping failed: {str(e)}")
            return []
    
    def _extract_deadline_from_rss(self, entry) -> str:
        """Extract deadline from RSS entry"""
        # Try different date fields
        date_fields = ['deadline', 'closing_date', 'due_date', 'expiry_date']
        for field in date_fields:
            if hasattr(entry, field) and getattr(entry, field):
                return str(getattr(entry, field))
        
        # Try to extract from description
        if hasattr(entry, 'summary'):
            deadline_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})', entry.summary)
            if deadline_match:
                return deadline_match.group(1)
        
        return ''
    
    def _extract_location_from_rss(self, entry) -> str:
        """Extract location from RSS entry"""
        # Try different location fields
        location_fields = ['location', 'country', 'region', 'area']
        for field in location_fields:
            if hasattr(entry, field) and getattr(entry, field):
                return str(getattr(entry, field))
        
        # Try to extract from description
        if hasattr(entry, 'summary'):
            location_patterns = [
                'Kenya', 'Nairobi', 'Mombasa', 'Kisumu', 'Nakuru',
                'Tanzania', 'Dar es Salaam', 'Dodoma', 'Arusha', 'Mwanza',
                'Africa', 'East Africa', 'Sub-Saharan Africa'
            ]
            
            for pattern in location_patterns:
                if pattern.lower() in entry.summary.lower():
                    return pattern
        
        return ''
    
    def _scrape_finca_tanzania(self, url: str) -> List[Dict[str, Any]]:
        """Special handler for FINCA Tanzania site"""
        try:
            logger.info("Using special handler for FINCA Tanzania")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            tenders = []
            
            # Look for tender links and documents
            tender_links = soup.find_all('a', href=lambda x: x and any(ext in x.lower() for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx']))
            
            for link in tender_links:
                try:
                    link_text = link.get_text(strip=True)
                    link_href = link.get('href', '')
                    
                    # Check if this looks like a tender
                    if any(keyword in link_text.lower() for keyword in ['tender', 'rfp', 'request', 'supply', 'service']):
                        tender = {
                            'title': link_text,
                            'description': f"Tender document available at {link_href}",
                            'deadline': '',  # Would need to extract from document
                            'budget': '',
                            'requirements': [],
                            'industry': 'Information Technology',
                            'location': 'Tanzania',
                            'source_url': url,
                            'document_url': link_href,
                            'scraped_at': datetime.now().isoformat()
                        }
                        tenders.append(tender)
                        
                except Exception as e:
                    logger.debug(f"Error processing FINCA tender link: {str(e)}")
                    continue
            
            # Also look for any text content that mentions tenders
            tender_texts = soup.find_all(text=re.compile(r'tender|rfp|request.*proposal', re.I))
            for text_elem in tender_texts:
                parent = text_elem.parent
                if parent and parent.name in ['div', 'p', 'span']:
                    parent_text = parent.get_text(strip=True)
                    if len(parent_text) > 20 and any(keyword in parent_text.lower() for keyword in ['tender', 'rfp', 'supply', 'service']):
                        tender = {
                            'title': parent_text[:200],
                            'description': parent_text[:500],
                            'deadline': '',
                            'budget': '',
                            'requirements': [],
                            'industry': 'Information Technology',
                            'location': 'Tanzania',
                            'source_url': url,
                            'scraped_at': datetime.now().isoformat()
                        }
                        tenders.append(tender)
                        break  # Only take the first meaningful one
            
            return tenders
            
        except Exception as e:
            logger.error(f"FINCA Tanzania scraping failed: {str(e)}")
            return []
    
    def _scrape_nest_tanzania(self, url: str) -> List[Dict[str, Any]]:
        """Special handler for NeST Tanzania site"""
        try:
            logger.info("Using special handler for NeST Tanzania")
            
            # Try to find embedded data in the page
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for embedded JSON data
            embedded_data = self._extract_embedded_data(soup, url)
            if embedded_data:
                return embedded_data
            
            # Look for any JavaScript variables that might contain tender data
            scripts = soup.find_all('script')
            for script in scripts:
                script_content = script.get_text()
                
                # Look for common patterns in JavaScript
                if 'tenders' in script_content.lower() or 'opportunities' in script_content.lower():
                    # Try to extract data from JavaScript
                    js_data = self._extract_js_data(script_content, url)
                    if js_data:
                        return js_data
            
            # IMPROVED: Try to find any tender-related content in the HTML
            tender_keywords = ['tender', 'opportunity', 'rfp', 'bid', 'procurement']
            found_tenders = []
            
            for keyword in tender_keywords:
                # Look for text containing tender keywords
                text_elements = soup.find_all(text=re.compile(keyword, re.I))
                for text_elem in text_elements:
                    if text_elem and text_elem.parent:
                        parent = text_elem.parent
                        parent_text = parent.get_text(strip=True)
                        
                        # Check if this looks like meaningful tender content
                        if (len(parent_text) > 30 and 
                            any(tender_word in parent_text.lower() for tender_word in tender_keywords) and
                            not any(skip_word in parent_text.lower() for skip_word in ['menu', 'navigation', 'header', 'footer']) and
                            not parent_text.startswith('{') and  # Skip JSON content
                            not parent_text.startswith('[')):    # Skip array content
                            
                            # Try to extract a title
                            title = parent_text[:200]
                            if len(title) > 20:
                                tender = {
                                    'title': title,
                                    'description': parent_text[:500],
                                    'deadline': '',
                                    'budget': '',
                                    'requirements': [],
                                    'industry': 'Information Technology',
                                    'location': 'Tanzania',
                                    'source_url': url,
                                    'scraped_at': datetime.now().isoformat()
                                }
                                found_tenders.append(tender)
                                break  # Only take one per keyword to avoid duplicates
            
            if found_tenders:
                logger.info(f"Found {len(found_tenders)} potential tenders in HTML content")
                return found_tenders
            
            # If no embedded data found, try to simulate user interaction
            # This would require Playwright, so we'll return empty for now
            logger.info("No embedded data found in NeST Tanzania, may require JavaScript execution")
            return []
            
        except Exception as e:
            logger.error(f"NeST Tanzania scraping failed: {str(e)}")
            return []
    
    def _extract_embedded_data(self, soup, source_url: str) -> List[Dict[str, Any]]:
        """Extract embedded data from HTML"""
        try:
            tenders = []
            
            # Look for JSON-LD structured data
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    if script.string:  # Check if script has content
                        data = json.loads(script.string)
                        if isinstance(data, dict):
                            tender = self._parse_structured_data(data, source_url)
                            if tender:
                                tenders.append(tender)
                        elif isinstance(data, list):
                            for item in data:
                                tender = self._parse_structured_data(item, source_url)
                                if tender:
                                    tenders.append(tender)
                except:
                    continue
            
            # Look for data attributes - FIXED: handle string values properly
            data_elements = soup.find_all(attrs=lambda x: x and any(key.startswith('data-') for key in x.keys() if key))
            for elem in data_elements:
                if elem and hasattr(elem, 'attrs') and elem.attrs:  # Check if element and attrs exist
                    data_attrs = {k: v for k, v in elem.attrs.items() if k.startswith('data-')}
                    if data_attrs:
                        # Check if this looks like tender data
                        if any(keyword in str(data_attrs).lower() for keyword in ['tender', 'opportunity', 'rfp']):
                            tender = self._parse_data_attributes(data_attrs, elem, source_url)
                            if tender:
                                tenders.append(tender)
            
            return tenders
            
        except Exception as e:
            logger.error(f"Error extracting embedded data: {str(e)}")
            return []
    
    def _extract_js_data(self, script_content: str, source_url: str) -> List[Dict[str, Any]]:
        """Extract data from JavaScript content"""
        try:
            tenders = []
            
            # Look for common JavaScript patterns
            import re
            
            # Look for JSON-like structures
            json_patterns = [
                r'(\{[^{}]*"tender"[^{}]*\})',
                r'(\{[^{}]*"opportunity"[^{}]*\})',
                r'(\{[^{}]*"rfp"[^{}]*\})',
                r'(\[[^{}]*\{[^{}]*"title"[^{}]*\}[^{}]*\])'
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, script_content, re.IGNORECASE)
                for match in matches:
                    try:
                        # Try to clean and parse the match
                        cleaned_match = match.replace("'", '"').replace('\\', '')
                        data = json.loads(cleaned_match)
                        if isinstance(data, dict):
                            tender = self._parse_structured_data(data, source_url)
                            if tender:
                                tenders.append(tender)
                        elif isinstance(data, list):
                            for item in data:
                                tender = self._parse_structured_data(item, source_url)
                                if tender:
                                    tenders.append(tender)
                    except:
                        continue
            
            return tenders
            
        except Exception as e:
            logger.error(f"Error extracting JS data: {str(e)}")
            return []
    
    def _parse_data_attributes(self, data_attrs: Dict, element, source_url: str) -> Optional[Dict[str, Any]]:
        """Parse data attributes to extract tender information"""
        try:
            tender = {}
            
            # Extract title from data attributes or element text
            tender['title'] = data_attrs.get('data-title') or data_attrs.get('data-name') or element.get_text(strip=True)[:200]
            
            # Extract description
            tender['description'] = data_attrs.get('data-description') or data_attrs.get('data-summary', '')[:500]
            
            # Extract dates
            if data_attrs.get('data-deadline'):
                tender['deadline'] = data_attrs['data-deadline']
            elif data_attrs.get('data-closing-date'):
                tender['deadline'] = data_attrs['data-closing-date']
            
            # Extract budget
            if data_attrs.get('data-budget'):
                tender['budget'] = data_attrs['data-budget']
            
            # Set defaults
            tender.setdefault('industry', 'Information Technology')
            tender.setdefault('requirements', [])
            tender.setdefault('source_url', source_url)
            tender.setdefault('scraped_at', datetime.now().isoformat())
            
            return tender if tender.get('title') else None
            
        except Exception as e:
            logger.error(f"Error parsing data attributes: {str(e)}")
            return None
    
    def _extract_tender_data_static(self, element, soup) -> Dict[str, Any]:
        """Extract tender data from BeautifulSoup element"""
        try:
            tender = {}
            
            # Extract title - try multiple selectors
            title_selectors = [
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                'a[href*="tender"]', 'a[href*="notice"]', 'a[href*="procurement"]',
                'strong', 'b', '.title', '.tender-title', '.notice-title'
            ]
            
            title_elem = None
            for selector in title_selectors:
                title_elem = element.find(selector)
                if title_elem and title_elem.get_text(strip=True):
                    break
            
            if title_elem:
                tender['title'] = title_elem.get_text(strip=True)
            
            # Extract description - try multiple approaches
            desc_elem = element.find(['p', 'span', 'div', '.description', '.summary', '.content'])
            if desc_elem:
                tender['description'] = desc_elem.get_text(strip=True)[:500]
            
            # Extract deadline with more patterns
            deadline_text = element.get_text()
            deadline_patterns = [
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # DD/MM/YY or DD-MM-YY
                r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',  # YYYY/MM/DD or YYYY-MM-DD
                r'(Deadline|Due|Closing|Submission).*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(Deadline|Due|Closing|Submission).*?(\d{4}[/-]\d{1,2}[/-]\d{1,2})'
            ]
            
            for pattern in deadline_patterns:
                deadline_match = re.search(pattern, deadline_text, re.I)
                if deadline_match:
                    tender['deadline'] = deadline_match.group(1) if deadline_match.groups()[0] in ['Deadline', 'Due', 'Closing', 'Submission'] else deadline_match.group(1)
                    break
            
            # Extract budget with more patterns
            budget_patterns = [
                r'(\$|USD|EUR|GBP|KES|TZS)\s*([\d,]+(?:\.\d{2})?)',
                r'Budget.*?(\$|USD|EUR|GBP|KES|TZS)\s*([\d,]+(?:\.\d{2})?)',
                r'Value.*?(\$|USD|EUR|GBP|KES|TZS)\s*([\d,]+(?:\.\d{2})?)'
            ]
            
            for pattern in budget_patterns:
                budget_match = re.search(pattern, deadline_text, re.I)
                if budget_match:
                    tender['budget'] = f"{budget_match.group(1)} {budget_match.group(2)}"
                    break
            
            # Extract location with more patterns
            location_patterns = [
                'Kenya', 'Nairobi', 'Mombasa', 'Kisumu', 'Nakuru',
                'Tanzania', 'Dar es Salaam', 'Dodoma', 'Arusha', 'Mwanza',
                'Africa', 'East Africa', 'Sub-Saharan Africa'
            ]
            
            for pattern in location_patterns:
                if pattern.lower() in deadline_text.lower():
                    tender['location'] = pattern
                    break
            
            # Extract industry/sector
            industry_patterns = [
                'Information Technology', 'IT', 'ICT', 'Technology',
                'Software', 'Hardware', 'Cloud', 'Digital', 'Telecommunications',
                'Infrastructure', 'Construction', 'Engineering', 'Healthcare',
                'Education', 'Finance', 'Banking', 'Agriculture'
            ]
            
            for pattern in industry_patterns:
                if pattern.lower() in deadline_text.lower():
                    tender['industry'] = pattern
                    break
            
            # Set default values
            tender.setdefault('industry', 'Information Technology')
            tender.setdefault('requirements', [])
            tender.setdefault('source_url', '')
            tender.setdefault('scraped_at', datetime.now().isoformat())
            
            return tender
            
        except Exception as e:
            logger.error(f"Error extracting tender data: {str(e)}")
            return {}
    
    def _extract_tender_data_dynamic(self, element, page) -> Dict[str, Any]:
        """Extract tender data from Playwright element"""
        try:
            tender = {}
            
            # Extract title - get cleaner text
            title_text = element.inner_text()
            if not title_text or len(title_text.strip()) < 10:
                return {}
            
            # Clean up the title text - remove excessive whitespace and newlines
            title_text = ' '.join(title_text.split())
            tender['title'] = title_text.strip()[:200]
            
            # Extract description - look for more specific content
            desc_elem = element.query_selector('p, span, div, td')
            if desc_elem:
                desc_text = desc_elem.inner_text()
                if desc_text and len(desc_text.strip()) > 20:
                    # Clean up description text
                    desc_text = ' '.join(desc_text.split())
                    tender['description'] = desc_text.strip()[:500]
            
            # Extract deadline - look for date patterns
            deadline_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})', title_text)
            if deadline_match:
                tender['deadline'] = deadline_match.group(1)
            
            # Extract budget - look for currency patterns
            budget_match = re.search(r'(\$|USD|EUR|GBP|KES|TZS)\s*([\d,]+(?:\.\d{2})?)', title_text, re.I)
            if budget_match:
                tender['budget'] = f"{budget_match.group(1)} {budget_match.group(2)}"
            
            # Set default values
            tender.setdefault('industry', 'Information Technology')
            tender.setdefault('requirements', [])
            tender.setdefault('source_url', page.url)
            tender.setdefault('scraped_at', datetime.now().isoformat())
            
            return tender
            
        except Exception as e:
            logger.error(f"Error extracting tender data from dynamic element: {str(e)}")
            return {}
    
    def _extract_tender_data_selenium(self, element, driver) -> Dict[str, Any]:
        """Extract tender data from Selenium element"""
        try:
            tender = {}
            
            # Extract title
            title_text = element.text
            if not title_text or len(title_text.strip()) < 10:
                return {}
            
            tender['title'] = title_text.strip()[:200]
            
            # Extract description
            try:
                desc_elem = element.find_element(By.CSS_SELECTOR, 'p, span, div')
                tender['description'] = desc_elem.text.strip()[:500]
            except:
                pass
            
            # Extract deadline
            deadline_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})', title_text)
            if deadline_match:
                tender['deadline'] = deadline_match.group(1)
            
            # Extract budget
            budget_match = re.search(r'(\$|USD|EUR|GBP)\s*([\d,]+(?:\.\d{2})?)', title_text, re.I)
            if budget_match:
                tender['budget'] = f"{budget_match.group(1)} {budget_match.group(2)}"
            
            # Set default values
            tender.setdefault('industry', 'Information Technology')
            tender.setdefault('requirements', [])
            tender.setdefault('source_url', driver.current_url)
            tender.setdefault('scraped_at', datetime.now().isoformat())
            
            return tender
            
        except Exception as e:
            logger.error(f"Error extracting tender data from Selenium element: {str(e)}")
            return {}
    
    def _parse_api_data(self, data: List[Dict], source_url: str) -> List[Dict[str, Any]]:
        """Parse data from API responses with improved handling"""
        tenders = []
        
        # Handle different data structures
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # Try common API response patterns
            items = []
            for key in ['data', 'results', 'items', 'tenders', 'opportunities', 'notices']:
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    break
            
            # If no list found, try to extract from other fields
            if not items and 'content' in data:
                if isinstance(data['content'], list):
                    items = data['content']
                elif isinstance(data['content'], dict):
                    items = [data['content']]
            
            # If still no items, try to use the data itself as a single item
            if not items:
                items = [data]
        else:
            logger.warning(f"Unexpected API data type: {type(data)}")
            return []
        
        for item in items:
            try:
                if not isinstance(item, dict):
                    continue
                
                tender = {
                    'title': self._extract_title_from_api(item),
                    'description': self._extract_description_from_api(item),
                    'deadline': self._extract_deadline_from_api(item),
                    'budget': self._extract_budget_from_api(item),
                    'location': self._extract_location_from_api(item),
                    'industry': self._extract_industry_from_api(item),
                    'requirements': self._extract_requirements_from_api(item),
                    'source_url': source_url,
                    'scraped_at': datetime.now().isoformat()
                }
                
                # Additional fields that might be available
                if 'id' in item:
                    tender['tender_id'] = str(item['id'])
                if 'reference' in item:
                    tender['tender_reference'] = str(item['reference'])
                if 'url' in item:
                    tender['tender_url'] = str(item['url'])
                if 'published_date' in item:
                    tender['published_date'] = str(item['published_date'])
                
                if tender['title']:
                    tenders.append(tender)
                    
            except Exception as e:
                logger.debug(f"Error parsing API item: {str(e)}")
                continue
        
        return tenders
    
    def _extract_title_from_api(self, item: Dict) -> str:
        """Extract title from API item"""
        title_fields = ['title', 'name', 'subject', 'heading', 'tender_title', 'opportunity_title']
        for field in title_fields:
            if field in item and item[field]:
                title = str(item[field]).strip()
                if len(title) > 5:
                    return title[:200]
        return ''
    
    def _extract_description_from_api(self, item: Dict) -> str:
        """Extract description from API item"""
        desc_fields = ['description', 'summary', 'content', 'details', 'scope', 'objective']
        for field in desc_fields:
            if field in item and item[field]:
                desc = str(item[field]).strip()
                if len(desc) > 10:
                    return desc[:500]
        return ''
    
    def _extract_deadline_from_api(self, item: Dict) -> str:
        """Extract deadline from API item"""
        deadline_fields = ['deadline', 'closing_date', 'due_date', 'expiry_date', 'submission_deadline', 'end_date']
        for field in deadline_fields:
            if field in item and item[field]:
                deadline = str(item[field]).strip()
                if deadline:
                    return deadline
        return ''
    
    def _extract_budget_from_api(self, item: Dict) -> str:
        """Extract budget from API item"""
        budget_fields = ['budget', 'value', 'amount', 'estimated_value', 'contract_value', 'project_value']
        for field in budget_fields:
            if field in item and item[field]:
                budget = str(item[field]).strip()
                if budget:
                    return budget
        return ''
    
    def _extract_location_from_api(self, item: Dict) -> str:
        """Extract location from API item"""
        location_fields = ['location', 'country', 'region', 'area', 'city', 'state']
        for field in location_fields:
            if field in item and item[field]:
                location = str(item[field]).strip()
                if location:
                    return location
        
        # Try to extract from description if available
        if 'description' in item:
            desc = str(item['description']).lower()
            location_patterns = [
                'Kenya', 'Nairobi', 'Mombasa', 'Kisumu', 'Nakuru',
                'Tanzania', 'Dar es Salaam', 'Dodoma', 'Arusha', 'Mwanza',
                'Africa', 'East Africa', 'Sub-Saharan Africa'
            ]
            
            for pattern in location_patterns:
                if pattern.lower() in desc:
                    return pattern
        
        return ''
    
    def _extract_industry_from_api(self, item: Dict) -> str:
        """Extract industry from API item"""
        industry_fields = ['industry', 'sector', 'category', 'domain', 'field']
        for field in industry_fields:
            if field in item and item[field]:
                industry = str(item[field]).strip()
                if industry:
                    return industry
        
        # Try to infer from title or description
        text_to_check = ''
        if 'title' in item:
            text_to_check += ' ' + str(item['title'])
        if 'description' in item:
            text_to_check += ' ' + str(item['description'])
        
        text_to_check = text_to_check.lower()
        
        # Define industry keywords
        industry_keywords = {
            'Information Technology': ['it', 'ict', 'technology', 'software', 'hardware', 'digital', 'cloud', 'cybersecurity'],
            'Telecommunications': ['telecom', 'communication', 'network', 'broadband', 'fiber'],
            'Infrastructure': ['infrastructure', 'construction', 'engineering', 'building'],
            'Healthcare': ['health', 'medical', 'hospital', 'clinic'],
            'Education': ['education', 'school', 'university', 'training'],
            'Finance': ['finance', 'banking', 'financial', 'accounting']
        }
        
        for industry, keywords in industry_keywords.items():
            if any(keyword in text_to_check for keyword in keywords):
                return industry
        
        return 'Information Technology'  # Default
    
    def _extract_requirements_from_api(self, item: Dict) -> List[str]:
        """Extract requirements from API item"""
        requirements_fields = ['requirements', 'criteria', 'qualifications', 'specifications', 'conditions']
        for field in requirements_fields:
            if field in item and item[field]:
                reqs = item[field]
                if isinstance(reqs, list):
                    return [str(req) for req in reqs if req]
                elif isinstance(reqs, str):
                    # Try to split by common delimiters
                    if ';' in reqs:
                        return [req.strip() for req in reqs.split(';') if req.strip()]
                    elif ',' in reqs:
                        return [req.strip() for req in reqs.split(',') if req.strip()]
                    else:
                        return [reqs.strip()]
        
        return []
    
    def _post_process_tenders(self, tenders: List[Dict[str, Any]], source_url: str) -> List[Dict[str, Any]]:
        """Post-process and clean tender data"""
        processed_tenders = []
        
        for tender in tenders:
            try:
                # Clean and validate data
                if not tender.get('title') or len(tender['title'].strip()) < 5:
                    continue
                
                # Ensure required fields
                tender['title'] = tender['title'].strip()
                tender['source_url'] = source_url
                tender['scraped_at'] = datetime.now().isoformat()
                
                # Clean description
                if tender.get('description'):
                    tender['description'] = tender['description'].strip()
                    if len(tender['description']) > 500:
                        tender['description'] = tender['description'][:500] + "..."
                
                # Validate deadline format
                if tender.get('deadline'):
                    # Try to standardize date format
                    deadline = tender['deadline']
                    if isinstance(deadline, str):
                        # Add basic date validation
                        if re.match(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}', deadline):
                            tender['deadline'] = deadline
                        else:
                            tender['deadline'] = ''
                
                processed_tenders.append(tender)
                
            except Exception as e:
                logger.debug(f"Error post-processing tender: {str(e)}")
                continue
        
        return processed_tenders
    
    def _get_sample_tenders(self, source_url: str) -> List[Dict[str, Any]]:
        """Return sample tender data for testing purposes"""
        return [
            {
                "title": "Cloud Migration Services for Government Agency",
                "description": "Seeking vendors to help migrate legacy systems to cloud infrastructure with security compliance requirements.",
                "deadline": "2025-02-15",
                "budget": "USD 250,000",
                "requirements": ["AWS Certified", "ISO 27001", "3+ similar projects"],
                "industry": "Information Technology",
                "location": "Kenya",
                "source_url": source_url,
                "scraped_at": datetime.now().isoformat()
            },
            {
                "title": "Cybersecurity Infrastructure Upgrade",
                "description": "Implementation of comprehensive cybersecurity solutions including endpoint protection and threat monitoring.",
                "deadline": "2025-03-01",
                "budget": "USD 180,000",
                "requirements": ["Cybersecurity expertise", "Government compliance", "24/7 support"],
                "industry": "Information Technology",
                "location": "Tanzania",
                "source_url": source_url,
                "scraped_at": datetime.now().isoformat()
            }
        ]

    def _extract_tenders_from_table(self, page, selector: str) -> List[Dict[str, Any]]:
        """Extract tenders from table structures"""
        try:
            tenders = []
            
            if selector == 'table':
                # Get all tables
                tables = page.query_selector_all('table')
                for table in tables:
                    table_tenders = self._extract_tenders_from_single_table(table, page)
                    tenders.extend(table_tenders)
            else:
                # Get all table rows
                rows = page.query_selector_all('tr')
                if rows:
                    # Group rows by table context
                    table_tenders = self._extract_tenders_from_rows(rows, page)
                    tenders.extend(table_tenders)
            
            return tenders
            
        except Exception as e:
            logger.error(f"Error extracting tenders from table: {str(e)}")
            return []
    
    def _extract_tenders_from_single_table(self, table, page) -> List[Dict[str, Any]]:
        """Extract tenders from a single table element"""
        try:
            tenders = []
            
            # Get all rows in this table
            rows = table.query_selector_all('tr')
            if len(rows) < 2:  # Need at least header + data row
                return []
            
            # Try to identify header row and data rows
            header_row = rows[0]
            data_rows = rows[1:]
            
            # Extract header information
            headers = []
            header_cells = header_row.query_selector_all('th, td')
            for cell in header_cells:
                header_text = cell.inner_text().strip().lower()
                headers.append(header_text)
            
            # Process data rows - IMPROVED: better filtering
            for row in data_rows[:20]:  # Limit to first 20 data rows
                cells = row.query_selector_all('td')
                if len(cells) >= 2:
                    tender = self._extract_tender_from_table_row(cells, headers, page)
                    if tender and tender.get('title'):
                        # Additional filtering for quality
                        title = tender['title']
                        if (len(title) > 20 and 
                            not any(skip_word in title.lower() for skip_word in ['menu', 'navigation', 'header', 'footer', 'sidebar'])):
                            tenders.append(tender)
            
            return tenders
            
        except Exception as e:
            logger.error(f"Error extracting from single table: {str(e)}")
            return []
    
    def _extract_tenders_from_rows(self, rows, page) -> List[Dict[str, Any]]:
        """Extract tenders from table rows when table context is unclear"""
        try:
            tenders = []
            
            # Look for rows with multiple cells that might contain tender data
            for row in rows[:50]:  # Limit to first 50 rows
                cells = row.query_selector_all('td')
                if len(cells) >= 2:
                    # Check if this row contains tender-like content
                    row_text = row.inner_text().strip()
                    if any(keyword in row_text.lower() for keyword in ['tender', 'rfp', 'bid', 'procurement', 'supply', 'service']):
                        tender = self._extract_tender_from_table_row(cells, [], page)
                        if tender and tender.get('title'):
                            tenders.append(tender)
            
            return tenders
            
        except Exception as e:
            logger.error(f"Error extracting from rows: {str(e)}")
            return []
    
    def _extract_tender_from_table_row(self, cells, headers, page) -> Dict[str, Any]:
        """Extract tender data from a table row"""
        try:
            tender = {}
            
            # Extract data based on cell position and headers
            if len(cells) >= 1:
                # First cell often contains tender number or title
                first_cell_text = cells[0].inner_text().strip()
                if first_cell_text and len(first_cell_text) > 5:
                    # Clean up the text
                    first_cell_text = ' '.join(first_cell_text.split())
                    # Check if this looks like a tender number
                    if re.match(r'^[A-Z]{2}-[A-Z]+-\d+', first_cell_text):
                        tender['tender_number'] = first_cell_text
                    elif len(first_cell_text) > 20:
                        tender['title'] = first_cell_text
            
            if len(cells) >= 2:
                # Second cell often contains title/description
                second_cell_text = cells[1].inner_text().strip()
                if second_cell_text and len(second_cell_text) > 10:
                    # Clean up the text
                    second_cell_text = ' '.join(second_cell_text.split())
                    if not tender.get('title'):
                        tender['title'] = second_cell_text
                    else:
                        tender['description'] = second_cell_text
            
            if len(cells) >= 3:
                # Third cell might contain dates
                third_cell_text = cells[2].inner_text().strip()
                if third_cell_text:
                    # Clean up the text
                    third_cell_text = ' '.join(third_cell_text.split())
                    # Try to extract date information
                    date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})', third_cell_text)
                    if date_match:
                        tender['deadline'] = date_match.group(1)
                    else:
                        tender['issue_date'] = third_cell_text
            
            if len(cells) >= 4:
                # Fourth cell might contain closing date
                fourth_cell_text = cells[3].inner_text().strip()
                if fourth_cell_text:
                    # Clean up the text
                    fourth_cell_text = ' '.join(fourth_cell_text.split())
                    date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})', fourth_cell_text)
                    if date_match:
                        tender['deadline'] = date_match.group(1)
            
            # Set default values
            tender.setdefault('industry', 'Information Technology')
            tender.setdefault('requirements', [])
            tender.setdefault('source_url', page.url)
            tender.setdefault('scraped_at', datetime.now().isoformat())
            
            # Clean up title if we have tender number but no title
            if not tender.get('title') and tender.get('tender_number'):
                tender['title'] = tender['tender_number']
            
            return tender
            
        except Exception as e:
            logger.error(f"Error extracting tender from table row: {str(e)}")
            return {}
    
    def _extract_tenders_from_static_table(self, table, source_url: str) -> List[Dict[str, Any]]:
        """Extract tenders from a static HTML table"""
        try:
            tenders = []
            rows = table.find_all('tr')
            
            if len(rows) < 2:  # Need at least header + data row
                return []
            
            # Extract headers
            headers = []
            header_row = rows[0]
            header_cells = header_row.find_all(['th', 'td'])
            for cell in header_cells:
                header_text = cell.get_text(strip=True).lower()
                headers.append(header_text)
            
            # Process data rows
            for row in rows[1:21]:  # Limit to first 20 data rows
                cells = row.find_all('td')
                if len(cells) >= 2:
                    tender = self._extract_tender_from_static_table_row(cells, headers, source_url)
                    if tender and tender.get('title'):
                        tenders.append(tender)
            
            return tenders
            
        except Exception as e:
            logger.error(f"Error extracting from static table: {str(e)}")
            return []
    
    def _extract_tender_from_static_table_row(self, cells, headers, source_url: str) -> Dict[str, Any]:
        """Extract tender data from a static table row"""
        try:
            tender = {}
            
            # Extract data based on cell position and headers
            if len(cells) >= 1:
                first_cell_text = cells[0].get_text(strip=True)
                if first_cell_text and len(first_cell_text) > 5:
                    # Clean up the text
                    first_cell_text = ' '.join(first_cell_text.split())
                    tender['tender_number'] = first_cell_text
            
            if len(cells) >= 2:
                second_cell_text = cells[1].get_text(strip=True)
                if second_cell_text and len(second_cell_text) > 10:
                    # Clean up the text
                    second_cell_text = ' '.join(second_cell_text.split())
                    tender['title'] = second_cell_text
            
            if len(cells) >= 3:
                third_cell_text = cells[2].get_text(strip=True)
                if third_cell_text:
                    # Clean up the text
                    third_cell_text = ' '.join(third_cell_text.split())
                    # Try to extract date information
                    date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})', third_cell_text)
                    if date_match:
                        tender['deadline'] = date_match.group(1)
                    else:
                        tender['issue_date'] = third_cell_text
            
            if len(cells) >= 4:
                fourth_cell_text = cells[3].get_text(strip=True)
                if fourth_cell_text:
                    # Clean up the text
                    fourth_cell_text = ' '.join(fourth_cell_text.split())
                    date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})', fourth_cell_text)
                    if date_match:
                        tender['deadline'] = date_match.group(1)
            
            # Set default values
            tender.setdefault('industry', 'Information Technology')
            tender.setdefault('requirements', [])
            tender.setdefault('source_url', source_url)
            tender.setdefault('scraped_at', datetime.now().isoformat())
            
            # Clean up title if we have tender number but no title
            if not tender.get('title') and tender.get('tender_number'):
                tender['title'] = tender['tender_number']
            
            return tender
            
        except Exception as e:
            logger.error(f"Error extracting tender from static table row: {str(e)}")
            return {}
    
    def _parse_structured_data(self, data: Dict, source_url: str) -> Optional[Dict[str, Any]]:
        """Parse structured data (JSON-LD, microdata)"""
        try:
            tender = {}
            
            # Skip organization and other non-tender structured data
            if data.get('@type') in ['Organization', 'WebSite', 'WebPage']:
                return None
            
            # Only process if this looks like tender-related data
            if not any(keyword in str(data).lower() for keyword in ['tender', 'opportunity', 'rfp', 'bid', 'procurement', 'supply', 'service']):
                return None
            
            # Extract title
            tender['title'] = data.get('name') or data.get('title') or data.get('description', '')[:200]
            
            # Extract description
            tender['description'] = data.get('description') or data.get('summary', '')[:500]
            
            # Extract dates
            if data.get('closingDate'):
                tender['deadline'] = data['closingDate']
            elif data.get('dueDate'):
                tender['deadline'] = data['dueDate']
            
            # Extract budget
            if data.get('budget'):
                tender['budget'] = str(data['budget'])
            
            # Extract location
            if data.get('location'):
                if isinstance(data['location'], dict):
                    tender['location'] = data['location'].get('name', '')
                else:
                    tender['location'] = str(data['location'])
            
            # Set defaults
            tender.setdefault('industry', 'Information Technology')
            tender.setdefault('requirements', [])
            tender.setdefault('source_url', source_url)
            tender.setdefault('scraped_at', datetime.now().isoformat())
            
            return tender if tender.get('title') else None
            
        except Exception as e:
            logger.error(f"Error parsing structured data: {str(e)}")
            return None

# Global scraper instance
scraper = TenderScraper()

def scrape_web(url: str, site_config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Main scraping function for external use"""
    return scraper.scrape_web(url, site_config)
