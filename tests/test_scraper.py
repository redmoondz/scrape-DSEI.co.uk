#!/usr/bin/env python3
"""
Test script for DSEI scraper
This script tests the scraper with a limited number of pages to verify functionality
"""

import sys
from pathlib import Path

# Add src to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from dsei_scraper import DSEICompanyScraper, Config
import logging

def test_scraper():
    """Test the scraper with limited pages"""
    print("Testing DSEI Company Scraper...")
    
    # Set up logging for testing
    logging.basicConfig(level=logging.INFO)
    
    # Create config and scraper instance
    config = Config()
    scraper = DSEICompanyScraper(config)
    
    # Test with just 1 page to start
    print("Testing with 1 page...")
    scraper.scrape_all_companies(start_page=1, max_pages=1)
    
    # Print results
    print(f"\nTest completed!")
    print(f"Companies found: {len(scraper.companies_data)}")
    
    if scraper.companies_data:
        print("\nFirst company example:")
        first_company = scraper.companies_data[0]
        for key, value in first_company.items():
            print(f"  {key}: {value[:100]}{'...' if len(str(value)) > 100 else ''}")
    
    print(f"\nCheck 'dsei_companies.csv' for full results")

if __name__ == "__main__":
    test_scraper()
