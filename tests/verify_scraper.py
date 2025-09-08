#!/usr/bin/env python3
"""
Quick verification script to test connection and basic functionality
"""

import requests
from bs4 import BeautifulSoup
import re

def test_connection():
    """Test basic connection to the website"""
    print("Testing connection to DSEI website...")
    
    # Set up session with headers
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:142.0) Gecko/20100101 Firefox/142.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    
    # Test URL
    test_url = "https://www.dsei.co.uk/visit/exhibiting-companies?&page=1&searchgroup=65207D8C-exhibitors-list"
    
    try:
        response = session.get(test_url, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Connection successful!")
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for company links
            company_links = soup.find_all('a', class_='js-librarylink-entry')
            print(f"Found {len(company_links)} company links")
            
            if company_links:
                print("✅ Company links found!")
                
                # Test slug extraction
                for i, link in enumerate(company_links[:3]):  # Test first 3
                    if hasattr(link, 'get') and callable(getattr(link, 'get', None)):
                        href = link.get('href', '') or ''
                        if isinstance(href, str):
                            match = re.search(r"'exhibitors-list/([^']+)'", href)
                            if match:
                                slug = match.group(1)
                                print(f"  Sample slug {i+1}: {slug}")
                
                print("✅ Slug extraction working!")
                return True
            else:
                print("❌ No company links found")
                
                # Debug: show page title and some content
                title = soup.find('title')
                if title:
                    print(f"Page title: {title.get_text()}")
                
                # Show first few divs to understand structure
                divs = soup.find_all('div')[:5]
                print(f"Found {len(soup.find_all('div'))} div elements total")
                
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        return False
    
    return False

def test_company_detail():
    """Test fetching a company detail page"""
    print("\nTesting company detail page...")
    
    # Use Wind River as example (from the provided HTML)
    detail_url = "https://www.dsei.co.uk/exhibitors-list/wind-river?=&page=1&searchgroup=libraryentry-exhibitors-list"
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:142.0) Gecko/20100101 Firefox/142.0',
        'Accept': '*/*',
        'X-Requested-With': 'XMLHttpRequest',
    })
    
    try:
        response = session.get(detail_url, timeout=30)
        print(f"Detail page status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Test data extraction
            title_element = soup.find('h1', class_='m-exhibitor-entry__item__header__title')
            if title_element:
                company_name = title_element.get_text(strip=True)
                print(f"✅ Company name found: {company_name}")
            
            # Test category extraction
            category_elements = soup.find_all('li', class_='m-exhibitor-entry__item__header__categories__item')
            if category_elements:
                print(f"✅ Found {len(category_elements)} categories")
                for cat in category_elements[:3]:
                    print(f"  - {cat.get_text(strip=True)}")
            
            # Test description extraction
            desc_element = soup.find('div', class_='m-exhibitor-entry__item__body__description')
            if desc_element:
                description = desc_element.get_text(strip=True)
                print(f"✅ Description found ({len(description)} chars)")
                print(f"  Preview: {description[:100]}...")
            
            return True
        else:
            print(f"❌ Failed to fetch detail page: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Detail page error: {e}")
    
    return False

if __name__ == "__main__":
    print("DSEI Scraper Verification\n" + "="*30)
    
    # Test basic connection and list page
    list_success = test_connection()
    
    # Test detail page
    detail_success = test_company_detail()
    
    print(f"\n" + "="*30)
    print("VERIFICATION SUMMARY:")
    print(f"List page: {'✅ PASS' if list_success else '❌ FAIL'}")
    print(f"Detail page: {'✅ PASS' if detail_success else '❌ FAIL'}")
    
    if list_success and detail_success:
        print("\n🎉 Scraper should work correctly!")
        print("You can now run: python dsei_scraper.py")
    else:
        print("\n⚠️ There may be issues with the scraper.")
        print("Check network connection and website availability.")
