#!/usr/bin/env python3
"""Tests for the web scraper using offline sample data."""

import json
from typing import List, Dict

import pytest

from tools.scraper import scrape_web, scraper
from config import config


@pytest.fixture
def tender_sites() -> List[Dict]:
    """Load tender site configurations."""
    with open("data/tender_sites.json", "r") as f:
        return json.load(f)


@pytest.fixture(autouse=True)
def use_sample_data(monkeypatch):
    """Force scraper to use sample data and avoid network calls."""
    monkeypatch.setattr(config, "USE_SAMPLE_DATA", True)
    # Patch all network-dependent scraping methods to return no data.
    for method in [
        "_scrape_with_api_endpoint",
        "_scrape_with_rss",
        "_scrape_with_playwright",
        "_scrape_with_selenium_fallback",
        "_scrape_with_requests",
        "_scrape_with_api_endpoints",
        "_scrape_with_default_strategy",
    ]:
        monkeypatch.setattr(scraper, method, lambda *args, **kwargs: [], raising=False)


def _get_test_url(site: Dict) -> str:
    """Select the most appropriate URL from the site config."""
    return site.get("url") or site.get("api_url") or site.get("rss_url") or site.get("name", "")


def test_scrape_web_returns_valid_tenders(tender_sites):
    """scrape_web should return non-empty tender data with required fields."""
    required_keys = {"title", "description", "deadline", "source_url", "scraped_at"}

    for site in tender_sites:
        url = _get_test_url(site)
        tenders = scrape_web(url, site)

        # Verify a list is returned and it contains data
        assert isinstance(tenders, list), "scrape_web should return a list"
        assert tenders, f"No tenders returned for {site.get('name')}"

        # Verify each tender has expected structure
        for tender in tenders:
            assert isinstance(tender, dict), "Each tender should be a dictionary"
            missing = required_keys - tender.keys()
            assert not missing, f"Missing keys {missing} in tender from {site.get('name')}"
