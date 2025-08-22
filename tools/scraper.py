import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import time
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
import random
from urllib.parse import urljoin, urlparse
import json
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
    """Advanced tender scraper with multiple strategies"""
    
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
    
    def scrape_web(self, url: str) -> List[Dict[str, Any]]:
        """
        Scrapes tender listings from a specific portal URL using combined approach.
        Returns a list of structured tender opportunities.
        
        Args:
            url (str): The URL of the tender site to scrape
            
        Returns:
            List[Dict[str, Any]]: List of tender objects with structured data
        """
        try:
            logger.info(f"Starting scraping process for: {url}")
            
            # Apply rate limiting
            self.rate_limiter.wait_if_needed()
            
            # Try multiple scraping strategies
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
                
                # Try multiple selectors for tender elements
                tender_selectors = [
                    '[class*="tender"]',
                    '[class*="opportunity"]',
                    '[class*="rfp"]',
                    '[class*="bid"]',
                    '[class*="procurement"]',
                    'tr[data-*]',
                    '.listing-item',
                    '.card',
                    '.tender-item',
                    '.opportunity-item'
                ]
                
                tenders = []
                for selector in tender_selectors:
                    try:
                        elements = page.query_selector_all(selector)
                        if elements:
                            logger.info(f"Found {len(elements)} elements with selector: {selector}")
                            for element in elements[:20]:  # Limit to first 20
                                tender = self._extract_tender_data_dynamic(element, page)
                                if tender and tender.get('title'):
                                    tenders.append(tender)
                            if tenders:
                                break
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
            
            # Look for tender patterns
            tender_elements = soup.find_all(['div', 'tr', 'li'], 
                class_=re.compile(r'tender|opportunity|rfp|bid|procurement', re.I))
            
            if not tender_elements:
                # Fallback: look for elements containing tender-related text
                tender_elements = soup.find_all(text=re.compile(
                    r'tender|opportunity|rfp|bid|procurement', re.I))
                tender_elements = [elem.parent for elem in tender_elements if elem.parent]
            
            tenders = []
            for element in tender_elements[:20]:
                tender = self._extract_tender_data_static(element, soup)
                if tender and tender.get('title'):
                    tenders.append(tender)
            
            return tenders
            
        except Exception as e:
            logger.error(f"Requests scraping failed for {url}: {str(e)}")
            return []
    
    def _scrape_with_api_endpoints(self, url: str) -> List[Dict[str, Any]]:
        """Try to find and use API endpoints for data"""
        try:
            # Try common API patterns
            api_patterns = [
                url.replace('/website/Tenders/index', '/api/tenders'),
                url.replace('/Public/Notice', '/api/notices'),
                url.replace('/tenders/', '/api/tenders/'),
                url + '/api/tenders',
                url + '/api/opportunities'
            ]
            
            for api_url in api_patterns:
                try:
                    response = self.session.get(api_url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, list) and len(data) > 0:
                            return self._parse_api_data(data, url)
                        elif isinstance(data, dict) and 'data' in data:
                            return self._parse_api_data(data['data'], url)
                except Exception as e:
                    logger.debug(f"API endpoint {api_url} failed: {str(e)}")
                    continue
            
            return []
            
        except Exception as e:
            logger.error(f"API scraping failed for {url}: {str(e)}")
            return []
    
    def _extract_tender_data_static(self, element, soup) -> Dict[str, Any]:
        """Extract tender data from BeautifulSoup element"""
        try:
            tender = {}
            
            # Extract title
            title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'strong', 'b'])
            if title_elem:
                tender['title'] = title_elem.get_text(strip=True)
            
            # Extract description
            desc_elem = element.find(['p', 'span', 'div'])
            if desc_elem:
                tender['description'] = desc_elem.get_text(strip=True)[:500]
            
            # Extract deadline
            deadline_text = element.get_text()
            deadline_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})', deadline_text)
            if deadline_match:
                tender['deadline'] = deadline_match.group(1)
            
            # Extract budget
            budget_match = re.search(r'(\$|USD|EUR|GBP)\s*([\d,]+(?:\.\d{2})?)', deadline_text, re.I)
            if budget_match:
                tender['budget'] = f"{budget_match.group(1)} {budget_match.group(2)}"
            
            # Extract location
            location_patterns = ['Kenya', 'Nairobi', 'Tanzania', 'Dar es Salaam', 'Africa', 'East Africa']
            for pattern in location_patterns:
                if pattern.lower() in deadline_text.lower():
                    tender['location'] = pattern
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
            
            # Extract title
            title_text = element.inner_text()
            if not title_text or len(title_text.strip()) < 10:
                return {}
            
            tender['title'] = title_text.strip()[:200]
            
            # Extract description
            desc_elem = element.query_selector('p, span, div')
            if desc_elem:
                tender['description'] = desc_elem.inner_text().strip()[:500]
            
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
        """Parse data from API responses"""
        tenders = []
        
        for item in data:
            try:
                tender = {
                    'title': item.get('title', item.get('name', item.get('description', ''))[:200],
                    'description': item.get('description', item.get('summary', ''))[:500],
                    'deadline': item.get('deadline', item.get('closing_date', item.get('due_date', ''))),
                    'budget': item.get('budget', item.get('value', item.get('amount', ''))),
                    'location': item.get('location', item.get('country', item.get('region', ''))),
                    'industry': item.get('industry', item.get('sector', 'Information Technology')),
                    'requirements': item.get('requirements', item.get('criteria', [])),
                    'source_url': source_url,
                    'scraped_at': datetime.now().isoformat()
                }
                
                if tender['title']:
                    tenders.append(tender)
                    
            except Exception as e:
                logger.debug(f"Error parsing API item: {str(e)}")
                continue
        
        return tenders
    
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

# Global scraper instance
scraper = TenderScraper()

def scrape_web(url: str) -> List[Dict[str, Any]]:
    """Main scraping function for external use"""
    return scraper.scrape_web(url)
