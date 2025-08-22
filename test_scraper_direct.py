#!/usr/bin/env python3
"""Direct test of the scraper with site configurations"""

from tools.scraper import scrape_web
import json

def test_scraper_direct():
    """Test the scraper directly with site configurations"""
    
    print("Testing Scraper Directly")
    print("=" * 50)
    
    # Load tender sites
    with open('data/tender_sites.json', 'r') as f:
        tender_sites = json.load(f)
    
    print(f"Loaded {len(tender_sites)} tender sites")
    
    # Test each site individually
    for i, site in enumerate(tender_sites):
        print(f"\n{i+1}. Testing site: {site.get('name', 'Unknown')}")
        print(f"   URL: {site.get('url', 'N/A')}")
        print(f"   API URL: {site.get('api_url', 'N/A')}")
        print(f"   RSS URL: {site.get('rss_url', 'N/A')}")
        print(f"   Scraper Type: {site.get('scraper_type', 'auto')}")
        
        try:
            # Try the main URL first
            if site.get('url'):
                print(f"   Testing main URL...")
                tenders = scrape_web(site['url'], site)
                print(f"   Main URL result: {len(tenders)} tenders")
                if tenders:
                    print(f"   Sample tender: {tenders[0].get('title', 'No title')[:100]}...")
            
            # Try API URL if available
            elif site.get('api_url'):
                print(f"   Testing API URL...")
                tenders = scrape_web(site['api_url'], site)
                print(f"   API URL result: {len(tenders)} tenders")
                if tenders:
                    print(f"   Sample tender: {tenders[0].get('title', 'No title')[:100]}...")
            
            # Try RSS URL if available
            elif site.get('rss_url'):
                print(f"   Testing RSS URL...")
                tenders = scrape_web(site['rss_url'], site)
                print(f"   RSS URL result: {len(tenders)} tenders")
                if tenders:
                    print(f"   Sample tender: {tenders[0].get('title', 'No title')[:100]}...")
            
            # If no specific URLs, try the site name as a fallback
            else:
                print(f"   No specific URLs found, testing with site name...")
                # This should trigger the fallback logic in the wrapper
                tenders = scrape_web(site['name'], site)
                print(f"   Site name result: {len(tenders)} tenders")
                if tenders:
                    print(f"   Sample tender: {tenders[0].get('title', 'No title')[:100]}...")
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("Direct scraper testing completed!")

if __name__ == "__main__":
    test_scraper_direct()
